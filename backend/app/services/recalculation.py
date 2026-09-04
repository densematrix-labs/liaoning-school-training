from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import Score, TrainingProject, TrainingRecord
from app.services.ability import AbilityService


def _record_step_map(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        return {str(key): value or {} for key, value in raw.items()}
    if isinstance(raw, list):
        mapped: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            step_id = item.get("step_id") or item.get("id") or f"step-{index + 1}"
            mapped[str(step_id)] = item
        return mapped
    return {}


class RecalculationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def recalculate_score(self, score_id: str) -> dict[str, Any]:
        result = await self.db.execute(
            select(Score, TrainingRecord, TrainingProject)
            .join(TrainingRecord, TrainingRecord.id == Score.record_id)
            .join(TrainingProject, TrainingProject.id == Score.project_id)
            .where(Score.id == score_id)
        )
        row = result.first()
        if not row:
            raise ValueError("成绩记录不存在")

        score, record, project = row
        before_total = score.total_score
        source_steps = _record_step_map(record.steps_data)
        new_details: dict[str, dict[str, Any]] = {}
        total_score = 0.0
        max_score = 0.0
        failed_abilities: set[str] = set()
        mapping = project.ability_mapping or {}

        for index, step in enumerate(project.steps or []):
            step_id = str(step.get("id") or f"step-{index + 1}")
            source = source_steps.get(step_id, {})
            passed = bool(source.get("passed", False))
            step_max = float(step.get("score", step.get("max_score", 0)) or 0)
            failed_score = float(step.get("failed_score", 0) or 0)
            step_score = step_max if passed else min(failed_score, step_max)
            related = list(mapping.get(step_id) or step.get("abilities") or [])
            if not passed:
                failed_abilities.update(related)
            total_score += step_score
            max_score += step_max
            new_details[step_id] = {
                "passed": passed,
                "source_status": "通过" if passed else "未通过",
                "score": step_score,
                "max_score": step_max,
                "deduction": round(step_max - step_score, 2),
                "reason": source.get("reason"),
                "related_abilities": related,
                "applied_rule": {
                    "passed_score": step_max,
                    "failed_score": failed_score,
                    "rule_version": project.scoring_rules.get("version", 1) if project.scoring_rules else 1,
                },
            }

        if not new_details:
            raise ValueError("实训项目未配置操作步骤，无法重算")

        score.total_score = round(total_score, 2)
        score.max_score = round(max_score, 2)
        score.details = new_details
        score.failed_abilities = sorted(failed_abilities)
        project.max_score = round(max_score, 2)
        project.scoring_rules = {
            **(project.scoring_rules or {}),
            "version": int((project.scoring_rules or {}).get("version", 1)),
            "mode": "passed_or_failed",
        }
        await self.db.commit()
        await AbilityService(self.db).recalculate_profile(score.student_id)

        return {
            "score_id": score.id,
            "student_id": score.student_id,
            "project_id": project.id,
            "source_record_id": record.external_id,
            "before_total": before_total,
            "after_total": score.total_score,
            "max_score": score.max_score,
            "details": new_details,
            "rule_version": project.scoring_rules["version"],
        }

    async def recalculate_project(self, project_id: str, score_id: str | None = None) -> dict[str, Any]:
        query = select(Score.id).where(Score.project_id == project_id)
        if score_id:
            query = query.where(Score.id == score_id)
        query = query.order_by(Score.calculated_at.desc())
        ids = list((await self.db.execute(query)).scalars().all())
        if not ids:
            raise ValueError("该项目暂无可重算的成绩")

        results = []
        affected_students: set[str] = set()
        for item_id in ids:
            item = await self.recalculate_score(item_id)
            results.append(item)
            affected_students.add(item["student_id"])
        return {
            "project_id": project_id,
            "recalculated_count": len(results),
            "affected_students": len(affected_students),
            "sample": results[0],
        }
