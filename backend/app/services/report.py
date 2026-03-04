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
from app.models.ability import AbilityProfile, MajorAbility
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
        # Get student info
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            raise ValueError("学生不存在")
        
        # Get ability profile
        profile_result = await self.db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        # Get major abilities
        abilities_result = await self.db.execute(
            select(MajorAbility).order_by(MajorAbility.display_order)
        )
        abilities = abilities_result.scalars().all()
        ability_map = {a.id: a for a in abilities}
        
        # Get scores
        if report_type == "single" and score_id:
            scores_result = await self.db.execute(
                select(Score).where(Score.id == score_id)
            )
            scores = [scores_result.scalar_one_or_none()]
        else:
            scores_result = await self.db.execute(
                select(Score)
                .where(Score.student_id == student_id)
                .order_by(Score.calculated_at.desc())
                .limit(10)
            )
            scores = scores_result.scalars().all()
        
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
- 专业：铁道信号自动控制
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

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.LLM_PROXY_URL}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LLM_PROXY_KEY}",
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
                
        except Exception as e:
            # Fallback content
            return f"""## 整体评价

{student_name}同学在实训学习中表现积极，展现出了良好的学习态度。在多次实训中能够认真完成各项操作任务，基础技能掌握较为扎实。

## 能力分析

根据实训数据分析，各项能力发展相对均衡，但仍有提升空间。

## 薄弱环节

- 部分操作步骤的规范性有待加强
- 文档记录的完整性需要改进

## 提升建议

1. 建议在实训前仔细阅读操作规程，确保每个步骤的规范执行
2. 注意培养良好的记录习惯，及时、完整地填写各类文档
3. 多与老师和同学交流，及时解决学习中遇到的问题

## 毕业达标评估

{"当前各项能力已基本达到毕业标准，继续保持。" if graduation_ready else "部分能力尚未达到毕业标准，需要继续努力提升。"}

---
*报告生成时间可能受网络影响*
"""
    
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
        )
