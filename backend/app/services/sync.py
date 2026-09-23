import csv
import io
import uuid
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.models.training import Score, TrainingProject, TrainingRecord
from app.models.workflow import MockSyncException, MockSyncTask, TaskStatus
from app.services.ability import AbilityService
from app.services.audit import record_audit


PENDING_SYNC_SETTING_KEY = "pending_mock_sync_import"


def demo_rows(size: int = 1000) -> list[dict[str, Any]]:
    valid_count = max(1, size - 10)
    rows = [
        {
            "source_record_id": f"DEMO-SYNC-{index:06d}",
            "student_index": index,
            "project_index": index,
            "completed_at": datetime(2026, 9, 1, 8, 0).isoformat(),
        }
        for index in range(valid_count)
    ]
    rows.extend({**rows[index], "duplicate": True} for index in range(min(5, valid_count)))
    rows.extend(
        {
            "source_record_id": f"DEMO-INVALID-{index:03d}",
            "student_index": index,
            "project_index": index,
            "completed_at": "invalid-time",
            "invalid": True,
        }
        for index in range(5)
    )
    return rows[:size]


def parse_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        rows: Iterable[dict[str, Any]],
        *,
        actor_id: str,
        actor_name: str | None = None,
    ) -> MockSyncTask:
        source_rows = list(rows)
        task = MockSyncTask(
            id=str(uuid.uuid4()),
            status=TaskStatus.RUNNING,
            read_count=len(source_rows),
            success_count=0,
            skipped_count=0,
            error_count=0,
            created_by=actor_id,
            started_at=datetime.utcnow(),
        )
        self.db.add(task)
        await self.db.flush()

        students = list((await self.db.execute(select(Student).order_by(Student.student_no))).scalars().all())
        projects = list((await self.db.execute(select(TrainingProject).order_by(TrainingProject.name))).scalars().all())
        affected_students: set[str] = set()

        for row_number, raw in enumerate(source_rows, start=2):
            source_id = str(raw.get("source_record_id") or raw.get("external_id") or "").strip()
            try:
                if not source_id:
                    raise ValueError("缺少源记录唯一标识")
                if raw.get("invalid") or not students or not projects:
                    raise ValueError("步骤标识、学生或实训项目无法匹配")
                existing = (await self.db.execute(
                    select(TrainingRecord.id).where(TrainingRecord.external_id == source_id)
                )).scalar_one_or_none()
                if existing:
                    task.skipped_count += 1
                    continue

                student_index = int(raw.get("student_index", row_number))
                project_index = int(raw.get("project_index", row_number))
                student = students[student_index % len(students)]
                project = projects[project_index % len(projects)]
                completed_raw = raw.get("completed_at")
                completed_at = datetime.fromisoformat(str(completed_raw)) if completed_raw else datetime.utcnow()

                steps_data: dict[str, Any] = {}
                details: dict[str, Any] = {}
                total = 0.0
                maximum = 0.0
                failed: set[str] = set()
                for step_index, step in enumerate(project.steps or []):
                    step_id = str(step.get("id") or f"step-{step_index + 1}")
                    passed = (row_number + step_index) % 7 != 0
                    step_max = float(step.get("score", 0) or 0)
                    failed_score = float(step.get("failed_score", 0) or 0)
                    value = step_max if passed else min(step_max, failed_score)
                    abilities = list((project.ability_mapping or {}).get(step_id) or step.get("abilities") or [])
                    if not passed:
                        failed.update(abilities)
                    steps_data[step_id] = {"passed": passed, "reason": None if passed else "演示数据：步骤未通过"}
                    details[step_id] = {
                        "passed": passed,
                        "source_status": "通过" if passed else "未通过",
                        "score": value,
                        "max_score": step_max,
                        "deduction": step_max - value,
                        "reason": None if passed else "演示数据：步骤未通过",
                        "related_abilities": abilities,
                        "applied_rule": {
                            "passed_score": step_max,
                            "failed_score": failed_score,
                            "rule_version": (project.scoring_rules or {}).get("version", 1),
                        },
                    }
                    total += value
                    maximum += step_max

                if not details:
                    raise ValueError("实训项目未配置可用步骤")
                record = TrainingRecord(
                    id=str(uuid.uuid4()),
                    external_id=source_id,
                    student_id=student.id,
                    project_id=project.id,
                    steps_data=steps_data,
                    completed_at=completed_at,
                )
                self.db.add(record)
                await self.db.flush()
                self.db.add(Score(
                    id=str(uuid.uuid4()),
                    student_id=student.id,
                    project_id=project.id,
                    record_id=record.id,
                    total_score=round(total, 2),
                    max_score=round(maximum, 2),
                    details=details,
                    failed_abilities=sorted(failed),
                    calculated_at=completed_at,
                ))
                task.success_count += 1
                affected_students.add(student.id)
            except (ValueError, TypeError) as exc:
                task.error_count += 1
                self.db.add(MockSyncException(
                    id=str(uuid.uuid4()),
                    task_id=task.id,
                    row_number=row_number,
                    source_record_id=source_id or None,
                    reason=str(exc),
                    raw_data=raw,
                ))

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        await record_audit(
            self.db,
            actor_id=actor_id,
            actor_name=actor_name,
            action="data_sync",
            object_type="sync_task",
            object_id=task.id,
            after={
                "read": task.read_count,
                "success": task.success_count,
                "skipped": task.skipped_count,
                "errors": task.error_count,
            },
        )
        await self.db.commit()
        for student_id in affected_students:
            await AbilityService(self.db).recalculate_profile(student_id)
        return task
