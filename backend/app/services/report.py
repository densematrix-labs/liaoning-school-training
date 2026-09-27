from typing import Optional, List
import json
import httpx
import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.report import DiagnosticReport, ReportType
from app.models.student import Student, Class
from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.ability import MajorAbility, SubAbility
from app.models.lab import EnvironmentCheck
from app.models.workflow import ReportTask, TaskStatus
from app.database import AsyncSessionLocal
from app.services.ability import AbilityService
from app.schemas.report import DiagnosticReportResponse
from app.schemas.report import ReportTaskResponse
from app.services.presentation import report_reference, training_record_reference


INTERNAL_CODE_PATTERN = re.compile(r"\b(?:step|sa|ma)-[a-z0-9-]+\b", re.IGNORECASE)
UUID_PATTERN = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.IGNORECASE)


def sanitize_report_content(
    content: str,
    *,
    student_name: str,
    step_names: dict[str, str],
    ability_names: dict[str, str],
) -> str:
    """Remove internal identifiers and restore the real name locally."""
    cleaned = (content or "").replace("```markdown", "").replace("```", "")
    cleaned = re.sub(r"学员-[A-Za-z0-9_-]+", student_name, cleaned)
    replacements = {**step_names, **ability_names}
    for internal_id, human_name in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        cleaned = re.sub(re.escape(str(internal_id)), str(human_name), cleaned, flags=re.IGNORECASE)
    cleaned = INTERNAL_CODE_PATTERN.sub("相关业务项", cleaned)
    cleaned = UUID_PATTERN.sub("内部记录", cleaned)
    cleaned = "\n".join(
        line for line in cleaned.splitlines()
        if not re.search(r"模型来源|model\s*(?:name|source|provider)|bailian|dashscope", line, re.IGNORECASE)
    )
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_report(
        self,
        student_id: str,
        report_type: str = "single",
        score_id: Optional[str] = None,
    ) -> DiagnosticReportResponse:
        if report_type not in {"single", "periodic"}:
            raise ValueError("报告类型仅支持 single 或 periodic")

        # Get student info
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            raise ValueError("学生不存在")
        
        # Rebuild from score details before every report so the narrative and
        # the displayed graph share one traceable source of truth.
        profile = await AbilityService(self.db).recalculate_profile(student_id)
        
        # Get major abilities
        abilities_result = await self.db.execute(
            select(MajorAbility).order_by(MajorAbility.display_order)
        )
        abilities = abilities_result.scalars().all()
        ability_map = {a.id: a for a in abilities}
        sub_abilities = list((await self.db.execute(select(SubAbility))).scalars().all())
        sub_ability_names = {item.id: item.name for item in sub_abilities}
        
        # Get scores
        if report_type == "single":
            query = select(Score).where(Score.student_id == student_id)
            if score_id:
                query = query.where(Score.id == score_id)
            else:
                query = query.order_by(Score.calculated_at.desc()).limit(1)
            scores_result = await self.db.execute(query)
            scores = scores_result.scalars().all()
        else:
            scores_result = await self.db.execute(
                select(Score)
                .where(Score.student_id == student_id)
                .order_by(Score.calculated_at.desc())
                .limit(10)
            )
            scores = scores_result.scalars().all()

        if not scores:
            raise ValueError("暂无可用于生成报告的成绩数据")
        
        # Build report data
        scores_data = []
        selected_step_names: dict[str, str] = {}
        selected_record: TrainingRecord | None = None
        selected_project: TrainingProject | None = None
        for score in scores:
            if not score:
                continue
            project_result = await self.db.execute(
                select(TrainingProject).where(TrainingProject.id == score.project_id)
            )
            project = project_result.scalar_one_or_none()
            record = (await self.db.execute(
                select(TrainingRecord).where(TrainingRecord.id == score.record_id)
            )).scalar_one_or_none() if score.record_id else None
            if selected_record is None:
                selected_record = record
            if selected_project is None:
                selected_project = project
            project_step_names = {
                str(item.get("id")): item.get("name", "相关操作步骤")
                for item in (project.steps or [])
            } if project else {}
            selected_step_names.update(project_step_names)
            score_completed_at = record.completed_at if record and record.completed_at else score.calculated_at
            
            scores_data.append({
                "project_name": project.name if project else "未知项目",
                "completed_at": score_completed_at.isoformat() if score_completed_at else None,
                "total_score": score.total_score,
                "max_score": score.max_score,
                "percentage": round(score.total_score / score.max_score * 100, 1) if score.max_score > 0 else 0,
                "failed_abilities": [
                    sub_ability_names.get(str(ability_id), "相关能力")
                    for ability_id in (score.failed_abilities or [])
                ],
                "steps": [
                    {
                        "step_name": project_step_names.get(str(step_id), "相关操作步骤"),
                        "passed": detail.get("passed", False),
                        "score": detail.get("score", 0),
                        "max_score": detail.get("max_score", 0),
                        "reason": detail.get("reason"),
                    }
                    for step_id, detail in (score.details or {}).items()
                ],
            })

        selected_score_ids = [item.id for item in scores]
        env_rows = list((await self.db.execute(
            select(EnvironmentCheck)
            .where(EnvironmentCheck.student_id == student_id)
            .where(EnvironmentCheck.score_id.in_(selected_score_ids) if selected_score_ids else False)
            .order_by(EnvironmentCheck.checked_at.desc())
        )).scalars().all())
        environment_data = [
            {
                "total_score": item.total_score,
                "summary": item.summary,
                "details": item.details,
            }
            for item in env_rows
        ]
        
        # Build ability data
        ability_data = []
        if profile and profile.major_abilities:
            for ability_id, score in profile.major_abilities.items():
                ability = ability_map.get(ability_id)
                if ability:
                    ability_data.append({
                        "name": ability.name,
                        "score": round(score * 100, 1),
                        "threshold": ability.graduation_threshold * 100,
                        "status": "达标" if score >= ability.graduation_threshold else "待提升",
                    })
        
        # Generate report content via LLM
        content = await self._generate_report_content(
            # 校外模型只接收任务必需的脱敏标识，真实姓名仅在本地报告元数据中关联。
            student_name=f"学员-{student.id[-6:]}",
            scores_data=scores_data,
            ability_data=ability_data,
            report_type=report_type,
            graduation_ready=profile.graduation_ready if profile else False,
            environment_data=environment_data,
        )
        content = sanitize_report_content(
            content,
            student_name=student.name,
            step_names=selected_step_names,
            ability_names=sub_ability_names,
        )
        class_obj = (await self.db.execute(
            select(Class).where(Class.id == student.class_id)
        )).scalar_one_or_none()
        summary_lines = [
            "## 学生与实训摘要",
            f"- **学生：** {student.name}",
            f"- **班级：** {class_obj.name if class_obj else '—'}",
        ]
        if report_type == "single" and scores:
            completed_at = selected_record.completed_at if selected_record else scores[0].calculated_at
            completed_label = completed_at.strftime("%Y-%m-%d %H:%M") if completed_at else "—"
            summary_lines.extend([
                f"- **实训项目：** {selected_project.name if selected_project else '未知项目'}",
                f"- **完成时间：** {completed_label}",
                f"- **实训成绩：** {scores[0].total_score:g}/{scores[0].max_score:g} 分",
            ])
        else:
            summary_lines.append(f"- **覆盖范围：** 最近 {len(scores)} 次实训")
        content = "\n".join(summary_lines) + "\n\n" + content
        
        # Save report
        if report_type == "single":
            completed_at = selected_record.completed_at if selected_record else scores[0].calculated_at
            completed_label = completed_at.strftime("%Y-%m-%d %H:%M") if completed_at else "时间待确认"
            title = f"{selected_project.name if selected_project else '单次实训'} · {completed_label} · {student.name}诊断报告"
        else:
            title = f"{student.name} · 阶段综合诊断报告"
        
        report = DiagnosticReport(
            id=str(uuid.uuid4()),
            student_id=student_id,
            report_type=ReportType(report_type),
            title=title,
            content=content,
            score_id=scores[0].id if report_type == "single" else None,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        return await self._build_report_response(report, student)
    
    async def _generate_report_content(
        self,
        student_name: str,
        scores_data: List[dict],
        ability_data: List[dict],
        report_type: str,
        graduation_ready: bool,
        environment_data: List[dict],
    ) -> str:
        """Generate report content via LLM"""
        
        prompt = f"""你是一位专业的职业教育指导老师。请根据以下数据为学生生成诊断报告。

## 学生信息
- 匿名称呼：{student_name}
- 专业：铁道机车运用与维护
- 报告类型：{"单次实训诊断" if report_type == "single" else "阶段性综合诊断"}

## 实训成绩数据
{json.dumps(scores_data, ensure_ascii=False, indent=2)}

## 能力图谱数据
{json.dumps(ability_data, ensure_ascii=False, indent=2)}

## 环境规范检查数据
{json.dumps(environment_data, ensure_ascii=False, indent=2) if environment_data else "本次实训暂无环境检查记录，请在报告中明确写明，不得虚构。"}

## 毕业达标状态
{"已达标" if graduation_ready else "尚未达标"}

请生成一份适合教师直接阅读和归档的诊断报告，严格使用结构清晰的 Markdown，包含以下部分：

## 基本信息与成绩概况
（先用 3-5 条项目符号列出实训项目、总成绩、关键步骤结果、环境检测结果和毕业状态）

## 整体评价
（先用一行加粗结论，再用 100-150 字总结整体表现和优势领域）

## 能力分析
（每个大类能力使用三级标题，明确写出当前分、达标线、状态和 50-80 字分析）

## 薄弱环节
（使用有序列表，列出未通过步骤及需要重点提升的 2-3 个具体能力点）

## 环境规范情况
（引用环境检查分数、问题和建议；没有记录时明确说明暂无记录）

## 提升建议
（使用有序列表，每条包含“训练动作、完成标准、建议周期”）

## 毕业达标评估
（用引用块给出是否达标、差距维度和 30-50 字结论）

排版要求：不要输出连续的大段文字；单段不超过 120 字；关键分数和结论使用加粗；不要输出代码块。请用鼓励性但务实的语气撰写。直接输出 Markdown 内容，不要额外说明。"""

        prompt += "\n数据中已经将所有内部步骤编码和能力编码替换为业务名称。不得猜测、复述或生成任何 step-、sa-、ma-、UUID、源记录编号、模型名称或模型来源。"

        if not settings.LLM_API_KEY:
            raise RuntimeError(f"{settings.LLM_PROVIDER} 未配置，无法生成真实诊断报告")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"{settings.LLM_PROVIDER} 返回异常状态：{exc.response.status_code}"
            ) from exc
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise RuntimeError(f"{settings.LLM_PROVIDER} 调用失败，请稍后重试") from exc

    async def create_task(
        self,
        student_id: str,
        report_type: str,
        score_id: Optional[str],
        created_by: str,
    ) -> ReportTaskResponse:
        if report_type not in {"single", "periodic"}:
            raise ValueError("报告类型仅支持 single 或 periodic")
        if report_type == "single" and not score_id:
            latest = (await self.db.execute(
                select(Score.id)
                .where(Score.student_id == student_id)
                .order_by(Score.calculated_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            score_id = latest
        if report_type == "single" and not score_id:
            raise ValueError("暂无可用于生成单次报告的成绩")
        if score_id:
            owned = (await self.db.execute(
                select(Score.id).where(Score.id == score_id, Score.student_id == student_id)
            )).scalar_one_or_none()
            if not owned:
                raise ValueError("成绩记录不属于该学生")
        task = ReportTask(
            id=str(uuid.uuid4()),
            student_id=student_id,
            score_id=score_id,
            report_type=report_type,
            status=TaskStatus.PENDING,
            created_by=created_by,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return await self.get_task(task.id)

    async def get_task(self, task_id: str) -> Optional[ReportTaskResponse]:
        task = (await self.db.execute(select(ReportTask).where(ReportTask.id == task_id))).scalar_one_or_none()
        if not task:
            return None
        report = await self.get_report(task.report_id) if task.report_id else None
        return ReportTaskResponse(
            id=task.id,
            student_id=task.student_id,
            score_id=task.score_id,
            report_type=task.report_type,
            status=task.status.value,
            report_id=task.report_id,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            report=report,
        )
    
    async def get_student_reports(
        self,
        student_id: str,
        limit: int = 10,
        report_type: Optional[str] = None,
        score_id: Optional[str] = None,
    ) -> List[DiagnosticReportResponse]:
        if report_type not in {None, "single", "periodic"}:
            raise ValueError("报告类型仅支持 single 或 periodic")
        query = select(DiagnosticReport).where(DiagnosticReport.student_id == student_id)
        if report_type:
            query = query.where(DiagnosticReport.report_type == ReportType(report_type))
        if score_id:
            query = query.where(DiagnosticReport.score_id == score_id)
        result = await self.db.execute(
            query.order_by(DiagnosticReport.generated_at.desc()).limit(limit)
        )
        reports = result.scalars().all()
        
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        
        return [await self._build_report_response(report, student) for report in reports]
    
    async def get_report(self, report_id: str) -> Optional[DiagnosticReportResponse]:
        result = await self.db.execute(
            select(DiagnosticReport).where(DiagnosticReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return None
        
        student = (await self.db.execute(
            select(Student).where(Student.id == report.student_id)
        )).scalar_one_or_none()
        return await self._build_report_response(report, student)

    async def _build_report_response(
        self,
        report: DiagnosticReport,
        student: Student | None = None,
    ) -> DiagnosticReportResponse:
        if student is None:
            student = (await self.db.execute(
                select(Student).where(Student.id == report.student_id)
            )).scalar_one_or_none()

        class_obj = None
        if student:
            class_obj = (await self.db.execute(
                select(Class).where(Class.id == student.class_id)
            )).scalar_one_or_none()

        score = None
        project = None
        record = None
        if report.score_id:
            score = (await self.db.execute(
                select(Score).where(Score.id == report.score_id)
            )).scalar_one_or_none()
        if score:
            project = (await self.db.execute(
                select(TrainingProject).where(TrainingProject.id == score.project_id)
            )).scalar_one_or_none()
            if score.record_id:
                record = (await self.db.execute(
                    select(TrainingRecord).where(TrainingRecord.id == score.record_id)
                )).scalar_one_or_none()

        projects = list((await self.db.execute(select(TrainingProject))).scalars().all())
        step_names = {
            str(step.get("id")): step.get("name", "相关操作步骤")
            for item in projects
            for step in (item.steps or [])
            if step.get("id")
        }
        ability_names = {
            item.id: item.name
            for item in (await self.db.execute(select(SubAbility))).scalars().all()
        }
        student_name = student.name if student else "学生"
        content = sanitize_report_content(
            report.content or "",
            student_name=student_name,
            step_names=step_names,
            ability_names=ability_names,
        )

        completed_at = record.completed_at if record and record.completed_at else (score.calculated_at if score else None)
        percentage = (
            round(score.total_score / score.max_score * 100, 1)
            if score and score.max_score
            else None
        )
        if report.report_type == ReportType.SINGLE:
            if score:
                completed_label = completed_at.strftime("%Y-%m-%d %H:%M") if completed_at else "时间待确认"
                title = f"{project.name if project else '单次实训'} · {completed_label} · {student_name}诊断报告"
            else:
                generated_label = report.generated_at.strftime("%Y-%m-%d %H:%M") if report.generated_at else "时间待确认"
                title = f"单次实训诊断 · {generated_label} · {student_name}"
        else:
            generated_label = report.generated_at.strftime("%Y-%m-%d") if report.generated_at else ""
            title = f"{student_name} · 阶段综合诊断报告{f' · {generated_label}' if generated_label else ''}"

        if "## 学生与实训摘要" not in content:
            summary = [
                "## 学生与实训摘要",
                f"- **学生：** {student_name}",
                f"- **班级：** {class_obj.name if class_obj else '—'}",
            ]
            if score:
                summary.extend([
                    f"- **实训项目：** {project.name if project else '未知项目'}",
                    f"- **完成时间：** {completed_at.strftime('%Y-%m-%d %H:%M') if completed_at else '—'}",
                    f"- **实训成绩：** {score.total_score:g}/{score.max_score:g} 分（{percentage:g}%）",
                ])
            else:
                summary.append("- **报告范围：** 阶段综合表现")
            content = "\n".join(summary) + "\n\n" + content

        return DiagnosticReportResponse(
            id=report.id,
            student_id=report.student_id,
            student_name=student_name,
            report_type=report.report_type.value,
            score_id=report.score_id,
            title=title,
            content=content,
            generated_at=report.generated_at,
            report_reference=report_reference(report.generated_at, report.id),
            project_name=project.name if project else None,
            training_completed_at=completed_at,
            score_total=score.total_score if score else None,
            score_max=score.max_score if score else None,
            score_percentage=percentage,
            class_id=student.class_id if student else None,
            class_name=class_obj.name if class_obj else None,
            record_reference=training_record_reference(
                completed_at,
                record.id if record else (score.id if score else report.id),
            ) if score else None,
        )


async def process_report_task(task_id: str) -> None:
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        task = (await db.execute(select(ReportTask).where(ReportTask.id == task_id))).scalar_one_or_none()
        if not task:
            return
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.error_message = None
        await db.commit()
        try:
            report = await ReportService(db).generate_report(
                student_id=task.student_id,
                report_type=task.report_type,
                score_id=task.score_id,
            )
            task = (await db.execute(select(ReportTask).where(ReportTask.id == task_id))).scalar_one()
            task.status = TaskStatus.COMPLETED
            task.report_id = report.id
            task.completed_at = datetime.utcnow()
            await db.commit()
        except Exception as exc:
            await db.rollback()
            task = (await db.execute(select(ReportTask).where(ReportTask.id == task_id))).scalar_one_or_none()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)[:1000]
                task.completed_at = datetime.utcnow()
                await db.commit()
