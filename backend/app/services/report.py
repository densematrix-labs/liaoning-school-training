from typing import Optional, List
import json
import httpx
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.report import DiagnosticReport, ReportType
from app.models.student import Student
from app.models.training import Score, TrainingProject
from app.models.ability import MajorAbility
from app.models.lab import EnvironmentCheck
from app.models.workflow import ReportTask, TaskStatus
from app.database import AsyncSessionLocal
from app.services.ability import AbilityService
from app.schemas.report import DiagnosticReportResponse
from app.schemas.report import ReportTaskResponse


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
        for score in scores:
            if not score:
                continue
            project_result = await self.db.execute(
                select(TrainingProject).where(TrainingProject.id == score.project_id)
            )
            project = project_result.scalar_one_or_none()
            
            scores_data.append({
                "score_id": score.id,
                "project_name": project.name if project else "未知项目",
                "total_score": score.total_score,
                "max_score": score.max_score,
                "percentage": round(score.total_score / score.max_score * 100, 1) if score.max_score > 0 else 0,
                "failed_abilities": score.failed_abilities or [],
                "steps": [
                    {
                        "step_id": step_id,
                        "step_name": next((item.get("name") for item in (project.steps or []) if str(item.get("id")) == str(step_id)), step_id) if project else step_id,
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
                "score_id": item.score_id,
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
        
        # Save report
        title = f"{'单次实训' if report_type == 'single' else '阶段性'}诊断报告 - {student.name}"
        
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
        
        return DiagnosticReportResponse(
            id=report.id,
            student_id=student_id,
            student_name=student.name,
            report_type=report_type,
            title=title,
            content=content,
            generated_at=report.generated_at,
            model=settings.LLM_MODEL,
            source=settings.LLM_PROVIDER,
        )
    
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
- 姓名：{student_name}
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

请生成一份诊断报告，使用 Markdown 格式，包含以下部分：

## 基本信息与成绩概况
（明确引用实训项目、总成绩和至少一个步骤结果）

## 整体评价
（100-150字，总结学生的整体表现，突出优势领域）

## 能力分析
（按大类能力逐一分析，每项 50-80 字）

## 薄弱环节
（列出未通过步骤及需要重点提升的 2-3 个具体能力点）

## 环境规范情况
（引用环境检查结果；没有记录时明确说明暂无记录）

## 提升建议
（针对薄弱环节给出 3 条具体可操作的建议）

## 毕业达标评估
（评估当前距离毕业标准的情况，30-50 字）

请用鼓励性但务实的语气撰写。直接输出 Markdown 内容，不要额外说明。"""

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
    ) -> List[DiagnosticReportResponse]:
        result = await self.db.execute(
            select(DiagnosticReport)
            .where(DiagnosticReport.student_id == student_id)
            .order_by(DiagnosticReport.generated_at.desc())
            .limit(limit)
        )
        reports = result.scalars().all()
        
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        
        return [
            DiagnosticReportResponse(
                id=r.id,
                student_id=r.student_id,
                student_name=student.name if student else None,
                report_type=r.report_type.value,
                title=r.title,
                content=r.content,
                generated_at=r.generated_at,
                model=settings.LLM_MODEL,
                source=settings.LLM_PROVIDER,
            )
            for r in reports
        ]
    
    async def get_report(self, report_id: str) -> Optional[DiagnosticReportResponse]:
        result = await self.db.execute(
            select(DiagnosticReport).where(DiagnosticReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return None
        
        student_result = await self.db.execute(
            select(Student).where(Student.id == report.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        return DiagnosticReportResponse(
            id=report.id,
            student_id=report.student_id,
            student_name=student.name if student else None,
            report_type=report.report_type.value,
            title=report.title,
            content=report.content,
            generated_at=report.generated_at,
            model=settings.LLM_MODEL,
            source=settings.LLM_PROVIDER,
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
