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
from app.services.ability import AbilityService
from app.schemas.report import DiagnosticReportResponse


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
                "project_name": project.name if project else "未知项目",
                "total_score": score.total_score,
                "max_score": score.max_score,
                "percentage": round(score.total_score / score.max_score * 100, 1) if score.max_score > 0 else 0,
                "failed_abilities": score.failed_abilities or [],
            })
        
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
            student_name=student.name,
            scores_data=scores_data,
            ability_data=ability_data,
            report_type=report_type,
            graduation_ready=profile.graduation_ready if profile else False,
        )
        
        # Save report
        title = f"{'单次实训' if report_type == 'single' else '阶段性'}诊断报告 - {student.name}"
        
        report = DiagnosticReport(
            id=str(uuid.uuid4()),
            student_id=student_id,
            report_type=ReportType(report_type),
            title=title,
            content=content,
            score_id=score_id,
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

## 毕业达标状态
{"已达标" if graduation_ready else "尚未达标"}

请生成一份诊断报告，使用 Markdown 格式，包含以下部分：

## 整体评价
（100-150字，总结学生的整体表现，突出优势领域）

## 能力分析
（按大类能力逐一分析，每项 50-80 字）

## 薄弱环节
（列出需要重点提升的 2-3 个具体能力点）

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
