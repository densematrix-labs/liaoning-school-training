from typing import List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections import defaultdict

from app.models.training import Score, TrainingProject
from app.models.student import Student, Class
from app.models.ability import AbilityProfile, MajorAbility
from app.models.lab import Lab
from app.schemas.dashboard import (
    DashboardResponse,
    RealtimeStats,
    ClassRanking,
    AbilityDistributionItem,
    TrendDataPoint,
    LabStatusItem,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard_data(self) -> DashboardResponse:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Realtime stats
        realtime = await self._get_realtime_stats(today_start)
        
        # Class ranking
        class_ranking = await self._get_class_ranking()
        
        # Ability distribution
        ability_distribution = await self._get_ability_distribution()
        
        # Trend data (last 30 days)
        trend = await self._get_trend_data(30)
        
        # Lab status
        lab_status = await self._get_lab_status()
        
        return DashboardResponse(
            realtime=realtime,
            class_ranking=class_ranking,
            ability_distribution=ability_distribution,
            trend=trend,
            lab_status=lab_status,
            updated_at=now,
        )
    
    async def _get_realtime_stats(self, today_start: datetime) -> RealtimeStats:
        # Today's scores
        today_scores_result = await self.db.execute(
            select(Score).where(Score.calculated_at >= today_start)
        )
        today_scores = today_scores_result.scalars().all()
        
        # Count unique students today
        active_students = len(set(s.student_id for s in today_scores))
        
        # Calculate average and pass rate
        if today_scores:
            total_pct = sum(
                (s.total_score / s.max_score * 100) if s.max_score > 0 else 0
                for s in today_scores
            )
            avg_score = total_pct / len(today_scores)
            pass_count = sum(
                1 for s in today_scores
                if (s.total_score / s.max_score * 100 if s.max_score > 0 else 0) >= 60
            )
            pass_rate = pass_count / len(today_scores) * 100
        else:
            avg_score = 0
            pass_rate = 0
        
        return RealtimeStats(
            active_students=active_students,
            today_trainings=len(today_scores),
            average_score=round(avg_score, 1),
            pass_rate=round(pass_rate, 1),
        )
    
    async def _get_class_ranking(self) -> List[ClassRanking]:
        # Get all classes
        classes_result = await self.db.execute(select(Class))
        classes = classes_result.scalars().all()
        
        rankings = []
        for cls in classes:
            # Get students in class
            students_result = await self.db.execute(
                select(Student).where(Student.class_id == cls.id)
            )
            students = students_result.scalars().all()
            student_ids = [s.id for s in students]
            
            if not student_ids:
                continue
            
            # Get scores
            scores_result = await self.db.execute(
                select(Score).where(Score.student_id.in_(student_ids))
            )
            scores = scores_result.scalars().all()
            
            if not scores:
                continue
            
            total_pct = sum(
                (s.total_score / s.max_score * 100) if s.max_score > 0 else 0
                for s in scores
            )
            avg_score = total_pct / len(scores)
            
            rankings.append({
                "class_id": cls.id,
                "class_name": cls.name,
                "average_score": round(avg_score, 1),
                "training_count": len(scores),
            })
        
        # Sort and assign ranks
        rankings.sort(key=lambda x: x["average_score"], reverse=True)
        result = []
        for i, r in enumerate(rankings):
            result.append(ClassRanking(
                class_id=r["class_id"],
                class_name=r["class_name"],
                average_score=r["average_score"],
                training_count=r["training_count"],
                rank=i + 1,
            ))
        
        return result
    
    async def _get_ability_distribution(self) -> List[AbilityDistributionItem]:
        # Get all profiles
        profiles_result = await self.db.execute(select(AbilityProfile))
        profiles = profiles_result.scalars().all()
        
        # Get abilities
        abilities_result = await self.db.execute(
            select(MajorAbility).order_by(MajorAbility.display_order)
        )
        abilities = abilities_result.scalars().all()
        
        # Aggregate
        ability_scores = defaultdict(list)
        for profile in profiles:
            if profile.major_abilities:
                for ability_id, score in profile.major_abilities.items():
                    ability_scores[ability_id].append(score * 100)
        
        result = []
        for ability in abilities:
            scores = ability_scores.get(ability.id, [])
            
            if scores:
                avg = sum(scores) / len(scores)
                # Distribution buckets
                distribution = [0, 0, 0, 0, 0]
                for score in scores:
                    bucket = min(int(score / 20), 4)
                    distribution[bucket] += 1
            else:
                avg = 0
                distribution = [0, 0, 0, 0, 0]
            
            result.append(AbilityDistributionItem(
                ability_id=ability.id,
                ability_name=ability.name,
                avg=round(avg, 1),
                distribution=distribution,
            ))
        
        return result
    
    async def _get_trend_data(self, days: int) -> List[TrendDataPoint]:
        now = datetime.utcnow()
        result = []
        
        for i in range(days - 1, -1, -1):
            date = now - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            scores_result = await self.db.execute(
                select(Score).where(
                    Score.calculated_at >= day_start,
                    Score.calculated_at < day_end,
                )
            )
            scores = scores_result.scalars().all()
            
            if scores:
                total_pct = sum(
                    (s.total_score / s.max_score * 100) if s.max_score > 0 else 0
                    for s in scores
                )
                avg_score = total_pct / len(scores)
                pass_count = sum(
                    1 for s in scores
                    if (s.total_score / s.max_score * 100 if s.max_score > 0 else 0) >= 60
                )
                pass_rate = pass_count / len(scores) * 100
            else:
                avg_score = 0
                pass_rate = 0
            
            result.append(TrendDataPoint(
                date=day_start.strftime("%Y-%m-%d"),
                training_count=len(scores),
                average_score=round(avg_score, 1),
                pass_rate=round(pass_rate, 1),
            ))
        
        return result
    
    async def _get_lab_status(self) -> List[LabStatusItem]:
        labs_result = await self.db.execute(select(Lab))
        labs = labs_result.scalars().all()
        
        return [
            LabStatusItem(
                lab_id=lab.id,
                lab_name=lab.name,
                status=lab.status.value,
                current_students=lab.current_students or 0,
                capacity=lab.capacity or 40,
            )
            for lab in labs
        ]
