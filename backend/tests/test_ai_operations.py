from datetime import datetime
from app.models.operations import AuditLog
from app.services.production_data import put_setting
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login


async def test_ai_operations_uses_real_audit_and_safe_maintenance_metadata(client, test_db, auth_headers, acceptance_data):
    sentinel = 'PRIVATE-SENTINEL-DO-NOT-RETURN'
    async with test_db() as db:
        db.add_all([
            AuditLog(id='ok-text', action='ai_call', object_type='model', object_id='text-model', result='success', created_at=datetime(2026, 10, 1),
                     after={'model': 'text-model', 'vision': False, 'usage': {'prompt_tokens': 100, 'completion_tokens': 30}, 'api_key': sentinel, 'messages': sentinel}),
            AuditLog(id='ok-vision', action='ai_call', object_type='model', object_id='vision-model', result='success', created_at=datetime(2026, 10, 2), after={'vision': True}),
            AuditLog(id='fail-call', action='ai_call', object_type='model', result='failed', reason='ReadTimeout', created_at=datetime(2026, 10, 3)),
            AuditLog(id='not-ai', action='GET', object_type='model', result='success', after={'api_key': sentinel}),
        ])
        await put_setting(db, 'release:worker', {'heartbeat': datetime.utcnow().isoformat(), 'status': 'running'})
        await put_setting(db, 'release:last_backup', {'time': '2026-10-29T01:00:00', 'status': 'completed', 'filename': sentinel, 'encryption_key': sentinel})
        await put_setting(db, 'release:connectivity', {'time': '2026-10-29T02:00:00', 'ai': {'reachable': True, 'note': '模型列表'}, 'school_database': {'reachable': True}})
        await db.commit()
    r = await client.get('/api/v1/release/ai-operations', headers=auth_headers)
    assert r.status_code == 200 and sentinel not in r.text
    data = r.json()
    assert data['counts'] == {'success': 2, 'failed': 1}
    assert {x['id'] for x in data['calls']} == {'ok-text', 'ok-vision', 'fail-call'}
    text = next(x for x in data['calls'] if x['id'] == 'ok-text')
    assert not {'model','vendor','prompt_tokens','completion_tokens','cost'} & text.keys()
    vision = next(x for x in data['calls'] if x['id'] == 'ok-vision')
    assert vision['kind'] == '图片检查' and 'prompt_tokens' not in vision
    state = data['maintenance']
    assert state['database'] == 'connected' and not state['worker']['stale']
    assert state['last_backup'] == {'time': '2026-10-29T01:00:00', 'status': 'completed'}
    assert state['connectivity']['time'] == '2026-10-29T02:00:00'
    failed = (await client.get('/api/v1/release/ai-operations?result=failed', headers=auth_headers)).json()['calls']
    assert len(failed) == 1 and failed[0]['id'] == 'fail-call' and failed[0]['reason'] == 'ReadTimeout'
    assert (await client.get('/api/v1/release/ai-operations?result=invalid', headers=auth_headers)).status_code == 400
    student = await _login(client, 'ACCEPT-S')
    teacher = await _login(client, 'ACCEPT-T')
    for headers in (student, teacher):
        assert (await client.get('/api/v1/release/ai-operations', headers=headers)).status_code == 403
