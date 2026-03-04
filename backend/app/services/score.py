from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.student import Student, Class
from app.schemas.training import (
    ScoreResponse,
    ScoreDetailResponse,
    ScoreListResponse,
    StepScoreDetail,
    ClassScoreSummary,
)


class ScoreService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_student_scores(
        self,
        student_id: str,
        page: int = 1,
        page_size: int = 20,
        project_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> ScoreListResponse:
        query = select(Score).where(Score.student_id == student_id)
        
        if project_id:
            query = query.where(Score.project_id == project_id)
        if date_from:
            query = query.where(Score.calculated_at >= date_from)
        if date_to:
            query = query.where(Score.calculated_at <= date_to)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(Score.calculated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        scores = result.scalars().all()
        
        # Build response
        score_responses = []
        total_score_sum = 0
        
        for score in scores:
            # Get project name
            project_result = await self.db.execute(
                select(TrainingProject).where(TrainingProject.id == score.project_id)
            )
            project = project_result.scalar_one_or_none()
            
            percentage = (score.total_score / score.max_score * 100) if score.max_score > 0 else 0
            total_score_sum += percentage
            
            score_responses.append(ScoreResponse(
                id=score.id,
                student_id=score.student_id,
                project_id=score.project_id,
                project_name=project.name if project else None,
                total_score=score.total_score,
                max_score=score.max_score,
                percentage=round(percentage, 1),
                calculated_at=score.calculated_at,
            ))
        
        avg_score = total_score_sum / len(score_responses) if score_responses else None
        
        return ScoreListResponse(
            scores=score_responses,
            total=total,
            page=page,
            page_size=page_size,
            average_score=round(avg_score, 1) if avg_score else None,
        )
    
    async def get_score_detail(self, score_id: str) -> ScoreDetailResponse:
        result = await self.db.execute(
            select(Score).where(Score.id == score_id)
        )
        score = result.scalar_one_or_none()
        if not score:
            return None
        
        # Get project info
        project_result = await self.db.execute(
            select(TrainingProject).where(TrainingProject.id == score.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        # Get student info
        student_result = await self.db.execute(
            select(Student).where(Student.id == score.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Parse step details
        step_details = []
        if score.details and project and project.steps:
            steps_map = {s["id"]: s for s in project.steps}
            for step_id, detail in score.details.items():
                step_info = steps_map.get(step_id, {})
                step_details.append(StepScoreDetail(
                    step_id=step_id,
                    step_name=step_info.get("name", step_id),
                    passed=detail.get("passed", False),
                    score=detail.get("score", 0),
                    max_score=step_info.get("score", 10),
                    deduction=detail.get("deduction"),
                    reason=detail.get("reason"),
                    related_abilities=step_info.get("abilities", []),
                ))
        
        percentage = (score.total_score / score.max_score * 100) if score.max_score > 0 else 0
        
        return ScoreDetailResponse(
            id=score.id,
            student_id=score.student_id,
            student_name=student.name if student else None,
            project_id=score.project_id,
            project_name=project.name if project else None,
            total_score=score.total_score,
            max_score=score.max_score,
            percentage=round(percentage, 1),
            calculated_at=score.calculated_at,
            details=step_details,
            failed_abilities=score.failed_abilities or [],
        )
    
    async def get_class_scores(
        self,
        class_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> ScoreListResponse:
        # Get all students in class
        students_result = await self.db.execute(
            select(Student).where(Student.class_id == class_id)
        )
        students = students_result.scalars().all()
        student_ids = [s.id for s in students]
        student_map = {s.id: s for s in students}
        
        if not student_ids:
            return ScoreListResponse(scores=[], total=0, page=page, page_size=page_size)
        
        query = select(Score).where(Score.student_id.in_(student_ids))
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(Score.calculated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        scores = result.scalars().all()
        
        score_responses = []
        total_score_sum = 0
        
        for score in scores:
            project_result = await self.db.execute(
                select(TrainingProject).where(TrainingProject.id == score.project_id)
            )
            project = project_result.scalar_one_or_none()
            
            student = student_map.get(score.student_id)
            percentage = (score.total_score / score.max_score * 100) if score.max_score > 0 else 0
            total_score_sum += percentage
            
            score_responses.append(ScoreResponse(
                id=score.id,
                student_id=score.student_id,
                student_name=student.name if student else None,
                project_id=score.project_id,
                project_name=project.name if project else None,
                total_score=score.total_score,
                max_score=score.max_score,
                percentage=round(percentage, 1),
                calculated_at=score.calculated_at,
            ))
        
        avg_score = total_score_sum / len(score_responses) if score_responses else None
        
        return ScoreListResponse(
            scores=score_responses,
            total=total,
            page=page,
            page_size=page_size,
            average_score=round(avg_score, 1) if avg_score else None,
        )
    
    async def get_class_summary(self, class_id: str) -> ClassScoreSummary:
        # Get class info
        class_result = await self.db.execute(
            select(Class).where(Class.id == class_id)
        )
        class_obj = class_result.scalar_one_or_none()
        
        # Get students
        students_result = await self.db.execute(
            select(Student).where(Student.class_id == class_id)
        )
        students = students_result.scalars().all()
        student_ids = [s.id for s in students]
        
        if not student_ids:
            return ClassScoreSummary(
                class_id=class_id,
                class_name=class_obj.name if class_obj else "",
                student_count=0,
                average_score=0,
                pass_rate=0,
                training_count=0,
            )
        
        # Get all scores for class
        scores_result = await self.db.execute(
            select(Score).where(Score.student_id.in_(student_ids))
        )
        scores = scores_result.scalars().all()
        
        if not scores:
            return ClassScoreSummary(
                class_id=class_id,
                class_name=class_obj.name if class_obj else "",
                student_count=len(students),
                average_score=0,
                pass_rate=0,
                training_count=0,
            )
        
        total_percentage = 0
        pass_count = 0
        
        for score in scores:
            percentage = (score.total_score / score.max_score * 100) if score.max_score > 0 else 0
            total_percentage += percentage
            if percentage >= 60:
                pass_count += 1
        
        return ClassScoreSummary(
            class_id=class_id,
            class_name=class_obj.name if class_obj else "",
            student_count=len(students),
            average_score=round(total_percentage / len(scores), 1),
            pass_rate=round(pass_count / len(scores) * 100, 1),
            training_count=len(scores),
        )
