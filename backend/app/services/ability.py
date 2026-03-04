from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import defaultdict

from app.models.ability import MajorAbility, SubAbility, AbilityProfile
from app.models.training import Score
from app.models.student import Student
from app.schemas.ability import (
    AbilityProfileResponse,
    RadarDataPoint,
    MajorAbilityResponse,
    SubAbilityResponse,
    ClassAbilityDistribution,
)


class AbilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_abilities(self) -> List[MajorAbilityResponse]:
        result = await self.db.execute(
            select(MajorAbility).order_by(MajorAbility.display_order)
        )
        major_abilities = result.scalars().all()
        
        responses = []
        for ma in major_abilities:
            sub_result = await self.db.execute(
                select(SubAbility).where(SubAbility.major_ability_id == ma.id)
            )
            subs = sub_result.scalars().all()
            
            responses.append(MajorAbilityResponse(
                id=ma.id,
                name=ma.name,
                description=ma.description,
                weight=ma.weight,
                graduation_threshold=ma.graduation_threshold,
                icon=ma.icon,
                sub_abilities=[
                    SubAbilityResponse(
                        id=s.id,
                        major_ability_id=s.major_ability_id,
                        name=s.name,
                        description=s.description,
                        weight=s.weight,
                    ) for s in subs
                ]
            ))
        
        return responses
    
    async def get_student_profile(self, student_id: str) -> Optional[AbilityProfileResponse]:
        # Get student info
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        if not student:
            return None
        
        # Get or calculate profile
        profile_result = await self.db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            # Calculate profile from scores
            profile = await self._calculate_profile(student_id)
        
        if not profile:
            return None
        
        # Build radar data
        radar_data = []
        major_abilities_result = await self.db.execute(
            select(MajorAbility).order_by(MajorAbility.display_order)
        )
        major_abilities = major_abilities_result.scalars().all()
        
        major_ability_scores = profile.major_abilities or {}
        
        strongest = None
        strongest_score = 0
        weakest = None
        weakest_score = 100
        
        for ma in major_abilities:
            score = major_ability_scores.get(ma.id, 0) * 100  # Convert to percentage
            radar_data.append(RadarDataPoint(
                ability_id=ma.id,
                ability_name=ma.name,
                score=round(score, 1),
                full_score=100.0,
                threshold=ma.graduation_threshold * 100,
            ))
            
            if score > strongest_score:
                strongest_score = score
                strongest = ma.name
            if score < weakest_score:
                weakest_score = score
                weakest = ma.name
        
        # Generate suggestions
        suggestions = []
        for ma in major_abilities:
            score = major_ability_scores.get(ma.id, 0)
            if score < ma.graduation_threshold:
                suggestions.append(f"建议加强「{ma.name}」的训练，当前达成率 {round(score * 100, 1)}%，目标 {round(ma.graduation_threshold * 100)}%")
        
        return AbilityProfileResponse(
            id=profile.id,
            student_id=student_id,
            student_name=student.name,
            major_abilities={k: round(v * 100, 1) for k, v in major_ability_scores.items()},
            sub_abilities={k: round(v * 100, 1) for k, v in (profile.sub_abilities or {}).items()},
            graduation_ready=profile.graduation_ready,
            radar_data=radar_data,
            updated_at=profile.updated_at,
            strongest_ability=strongest,
            weakest_ability=weakest,
            improvement_suggestions=suggestions[:3] if suggestions else None,
        )
    
    async def _calculate_profile(self, student_id: str) -> Optional[AbilityProfile]:
        """Calculate ability profile from all scores"""
        scores_result = await self.db.execute(
            select(Score).where(Score.student_id == student_id)
        )
        scores = scores_result.scalars().all()
        
        if not scores:
            return None
        
        # Aggregate ability scores
        ability_scores = defaultdict(list)
        
        for score in scores:
            if score.details:
                for step_id, detail in score.details.items():
                    abilities = detail.get("related_abilities", [])
                    step_score = detail.get("score", 0)
                    max_score = detail.get("max_score", 10)
                    normalized = step_score / max_score if max_score > 0 else 0
                    
                    for ability_id in abilities:
                        ability_scores[ability_id].append(normalized)
        
        # Calculate sub-ability averages
        sub_ability_avgs = {}
        for ability_id, scores_list in ability_scores.items():
            sub_ability_avgs[ability_id] = sum(scores_list) / len(scores_list)
        
        # Calculate major ability averages
        major_abilities_result = await self.db.execute(select(MajorAbility))
        major_abilities = major_abilities_result.scalars().all()
        
        major_ability_avgs = {}
        all_ready = True
        
        for ma in major_abilities:
            sub_result = await self.db.execute(
                select(SubAbility).where(SubAbility.major_ability_id == ma.id)
            )
            subs = sub_result.scalars().all()
            
            sub_scores = []
            for sub in subs:
                if sub.id in sub_ability_avgs:
                    sub_scores.append(sub_ability_avgs[sub.id] * sub.weight)
            
            if sub_scores:
                major_ability_avgs[ma.id] = sum(sub_scores) / sum(s.weight for s in subs if s.id in sub_ability_avgs)
            else:
                major_ability_avgs[ma.id] = 0
            
            if major_ability_avgs[ma.id] < ma.graduation_threshold:
                all_ready = False
        
        # Create or update profile
        profile_result = await self.db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if profile:
            profile.sub_abilities = sub_ability_avgs
            profile.major_abilities = major_ability_avgs
            profile.graduation_ready = all_ready
        else:
            import uuid
            profile = AbilityProfile(
                id=str(uuid.uuid4()),
                student_id=student_id,
                sub_abilities=sub_ability_avgs,
                major_abilities=major_ability_avgs,
                graduation_ready=all_ready,
            )
            self.db.add(profile)
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    async def get_class_distribution(self, class_id: str) -> ClassAbilityDistribution:
        """Get ability distribution for a class"""
        from app.models.student import Class
        
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
        
        # Get profiles
        student_ids = [s.id for s in students]
        profiles_result = await self.db.execute(
            select(AbilityProfile).where(AbilityProfile.student_id.in_(student_ids))
        )
        profiles = profiles_result.scalars().all()
        
        # Aggregate
        abilities_data = defaultdict(lambda: {"scores": [], "distribution": [0, 0, 0, 0, 0]})
        graduation_ready_count = 0
        
        for profile in profiles:
            if profile.graduation_ready:
                graduation_ready_count += 1
            
            for ability_id, score in (profile.major_abilities or {}).items():
                score_pct = score * 100
                abilities_data[ability_id]["scores"].append(score_pct)
                
                # Distribution buckets: 0-20, 20-40, 40-60, 60-80, 80-100
                bucket = min(int(score_pct / 20), 4)
                abilities_data[ability_id]["distribution"][bucket] += 1
        
        # Get ability names
        major_abilities_result = await self.db.execute(select(MajorAbility))
        major_abilities = major_abilities_result.scalars().all()
        ability_names = {ma.id: ma.name for ma in major_abilities}
        
        abilities_response = {}
        for ability_id, data in abilities_data.items():
            avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            abilities_response[ability_id] = {
                "name": ability_names.get(ability_id, ability_id),
                "avg": round(avg, 1),
                "distribution": data["distribution"],
            }
        
        return ClassAbilityDistribution(
            class_id=class_id,
            class_name=class_obj.name if class_obj else "",
            abilities=abilities_response,
            graduation_ready_count=graduation_ready_count,
            total_students=len(students),
        )
