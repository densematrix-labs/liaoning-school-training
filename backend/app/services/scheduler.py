import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.operations import SystemSetting
from app.models.user import User, UserRole
from app.models.workflow import EnvironmentTask, MockSyncTask, TaskStatus
from app.services.environment import process_environment_task
from app.services.sync import SyncService, demo_rows


class SyncScheduler:
    def __init__(self, poll_seconds: int = 60):
        self.poll_seconds = poll_seconds
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="training-data-sync-scheduler")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def tick(self) -> bool:
        # Environment inspection tasks are created with each completed training
        # record that includes a camera capture. Process a bounded batch on
        # every scheduler tick, independently from the periodic score sync.
        async with AsyncSessionLocal() as db:
            environment_task_ids = list((await db.execute(
                select(EnvironmentTask.id)
                .where(EnvironmentTask.status == TaskStatus.PENDING)
                .order_by(EnvironmentTask.created_at)
                .limit(3)
            )).scalars().all())
        if environment_task_ids:
            await asyncio.gather(*(
                process_environment_task(task_id)
                for task_id in environment_task_ids
            ))

        async with AsyncSessionLocal() as db:
            setting = (await db.execute(select(SystemSetting).where(SystemSetting.key == "sync_schedule"))).scalar_one_or_none()
            config = setting.value if setting else {"enabled": True, "frequency_hours": 24, "hour": 2}
            if not config.get("enabled", True):
                return bool(environment_task_ids)
            latest = (await db.execute(select(MockSyncTask).order_by(MockSyncTask.started_at.desc()).limit(1))).scalar_one_or_none()
            frequency = timedelta(hours=max(1, int(config.get("frequency_hours", 24))))
            now = datetime.utcnow()
            if latest and latest.started_at and now - latest.started_at.replace(tzinfo=None) < frequency:
                return bool(environment_task_ids)
            if not latest and now.hour != int(config.get("hour", 2)):
                return bool(environment_task_ids)
            admin = (await db.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))).scalar_one_or_none()
            if not admin:
                return bool(environment_task_ids)
            await SyncService(db).run(demo_rows(1000), actor_id=admin.id, actor_name="系统定时任务")
            return True

    async def _run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                # A failed scheduled run must never take down score/ability queries.
                pass
            await asyncio.sleep(self.poll_seconds)


sync_scheduler = SyncScheduler()
