from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models.lab import Lab
from app.models.operations import SystemSetting
from app.models.student import Student
from app.models.student import Class, Major
from app.models.user import User, UserRole
from app.models.workflow import MockSyncTask, TaskStatus


@pytest.mark.asyncio
async def test_demo_bootstrap_reaches_acceptance_scale(test_db, monkeypatch, tmp_path):
    import app.init_data as init_data

    monkeypatch.setattr(init_data, "AsyncSessionLocal", test_db)
    await init_data.init_mock_data()
    # A second run exercises the restart-safe upgrade path.
    await init_data.init_mock_data()
    async with test_db() as db:
        students = (await db.execute(select(func.count()).select_from(Student))).scalar_one()
        labs = (await db.execute(select(func.count()).select_from(Lab))).scalar_one()
        assert students == 140
        assert labs >= 4

    monkeypatch.setattr(init_data, "MOCK_DATA_DIR", tmp_path)
    assert init_data.load_json("missing.json") == {}


@pytest.mark.asyncio
async def test_upgrade_expands_small_existing_database(test_db):
    import app.init_data as init_data

    async with test_db() as db:
        db.add_all([
            User(id="scale-user", username="scale-user", password_hash="x", name="规模学生", role=UserRole.STUDENT),
            Major(id="scale-major", code="SCALE", name="规模专业"),
            Class(id="scale-class", name="规模班", major_id="scale-major", year=2024),
            Student(id="scale-student", user_id="scale-user", student_no="SCALE001", name="规模学生", major_id="scale-major", class_id="scale-class", enrollment_year=2024),
            Lab(id="scale-lab-1", name="实训室1"),
            Lab(id="scale-lab-2", name="实训室2"),
            Lab(id="scale-lab-3", name="实训室3"),
        ])
        await db.commit()
        await init_data.upgrade_demo_data(db)
        assert (await db.execute(select(func.count()).select_from(Student))).scalar_one() == 140
        assert (await db.execute(select(func.count()).select_from(Lab))).scalar_one() == 4


@pytest.mark.asyncio
async def test_scheduler_tick_and_lifecycle(test_db, monkeypatch):
    import asyncio
    import app.services.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", test_db)
    async with test_db() as db:
        db.add(User(id="scheduler-admin", username="scheduler-admin", password_hash="x", name="定时管理员", role=UserRole.ADMIN))
        db.add(SystemSetting(key="sync_schedule", value={"enabled": False, "frequency_hours": 24, "hour": 2}, updated_by="scheduler-admin"))
        await db.commit()

    scheduler = scheduler_module.SyncScheduler(poll_seconds=0.01)
    assert await scheduler.tick() is False
    async with test_db() as db:
        setting = (await db.execute(select(SystemSetting).where(SystemSetting.key == "sync_schedule"))).scalar_one()
        setting.value = {"enabled": True, "frequency_hours": 24, "hour": datetime.utcnow().hour}
        db.add(MockSyncTask(id="recent-sync", status=TaskStatus.COMPLETED, read_count=0, success_count=0, skipped_count=0, error_count=0, created_by="scheduler-admin", started_at=datetime.utcnow(), completed_at=datetime.utcnow()))
        await db.commit()
    assert await scheduler.tick() is False
    async with test_db() as db:
        recent = (await db.execute(select(MockSyncTask).where(MockSyncTask.id == "recent-sync"))).scalar_one()
        recent.started_at = datetime.utcnow() - timedelta(days=2)
        await db.commit()
    called = []

    async def fake_run(_service, rows, *, actor_id, actor_name=None):
        called.append((len(rows), actor_id, actor_name))
        return object()

    monkeypatch.setattr(scheduler_module.SyncService, "run", fake_run)
    assert await scheduler.tick() is True
    assert called == [(1000, "scheduler-admin", "系统定时任务")]
    scheduler.start()
    scheduler.start()
    await asyncio.sleep(.02)
    await scheduler.stop()
    await scheduler.stop()


@pytest.mark.asyncio
async def test_dashboard_websocket_and_application_lifespan(test_db, monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    import app.routers.dashboard as dashboard_router
    import app.main as main_module
    import app.init_data as init_data
    import app.services.scheduler as scheduler_module

    monkeypatch.setattr(dashboard_router, "AsyncSessionLocal", test_db)

    class FakeWebSocket:
        accepted = False
        sent = None

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            self.sent = data

    async def stop_after_first(_seconds):
        raise WebSocketDisconnect()

    socket = FakeWebSocket()
    monkeypatch.setattr(dashboard_router.asyncio, "sleep", stop_after_first)
    await dashboard_router.dashboard_websocket(socket)
    assert socket.accepted is True
    assert socket.sent is not None

    calls = []

    async def fake_init_db():
        calls.append("db")

    async def fake_init_mock_data():
        calls.append("seed")

    def fake_start():
        calls.append("start")

    async def fake_stop():
        calls.append("stop")

    monkeypatch.setattr(main_module, "init_db", fake_init_db)
    monkeypatch.setattr(init_data, "init_mock_data", fake_init_mock_data)
    monkeypatch.setattr(scheduler_module.sync_scheduler, "start", fake_start)
    monkeypatch.setattr(scheduler_module.sync_scheduler, "stop", fake_stop)
    async with main_module.lifespan(main_module.app):
        calls.append("inside")
    assert calls == ["db", "seed", "start", "inside", "stop"]


@pytest.mark.asyncio
async def test_database_session_commit_rollback_and_init(monkeypatch):
    import app.database as database

    class FakeSession:
        def __init__(self):
            self.calls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def commit(self):
            self.calls.append("commit")

        async def rollback(self):
            self.calls.append("rollback")

        async def close(self):
            self.calls.append("close")

    sessions = []

    def session_factory():
        item = FakeSession()
        sessions.append(item)
        return item

    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
    generator = database.get_db()
    assert await anext(generator) is sessions[0]
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    assert sessions[0].calls == ["commit", "close"]

    generator = database.get_db()
    await anext(generator)
    with pytest.raises(RuntimeError):
        await generator.athrow(RuntimeError("boom"))
    assert sessions[1].calls == ["rollback", "close"]

    class FakeConnection:
        async def run_sync(self, callback):
            assert callback == database.Base.metadata.create_all

    class FakeBegin:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, *args):
            return None

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(database, "engine", FakeEngine())
    await database.init_db()
