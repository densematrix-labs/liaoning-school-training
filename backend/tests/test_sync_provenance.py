from datetime import datetime,timedelta
from app.services.production_data import put_setting,setting
from tests.test_acceptance_workflows import acceptance_data,domain_ids
from tests.test_release import release_mode

async def test_auto_due_time_and_manual_trigger_are_persisted_separately(test_db,acceptance_data,auth_headers,monkeypatch,release_mode):
    import app.services.operations_runtime as runtime
    monkeypatch.setattr(runtime,'AsyncSessionLocal',test_db)
    monkeypatch.setattr(runtime,'read_mysql',lambda *args:[])
    worker=runtime.ReleaseWorker()
    config={'enabled':True,'table':'records','fields':{'steps':'steps'},'frequency_hours':24,'next_run_at':(datetime.utcnow()+timedelta(hours=1)).isoformat()}
    async with test_db() as db:
        await put_setting(db,'release:source',config);await db.commit()
    assert await worker.sync_source() is None
    manual=await worker.sync_source(force=True)
    async with test_db() as db:
        entry=await setting(db,'release:sync_run:'+manual['task_id'])
        assert entry['trigger']=='manual' and entry['status']=='completed'
        assert entry['completed_at']>=entry['started_at']
        config['next_run_at']=(datetime.utcnow()-timedelta(seconds=1)).isoformat()
        await put_setting(db,'release:source',config)
        await put_setting(db,'release:last_sync',{'time':(datetime.utcnow()-timedelta(seconds=2)).isoformat()})
        await db.commit()
    automatic=await worker.sync_source()
    async with test_db() as db:
        entry=await setting(db,'release:sync_run:'+automatic['task_id'])
        assert entry['trigger']=='automatic' and entry['status']=='completed'
        assert entry['id']!=manual['task_id']
    assert await worker.sync_source() is None
