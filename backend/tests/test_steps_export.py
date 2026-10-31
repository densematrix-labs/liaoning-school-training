import csv
import io
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login

async def test_export_steps_preserves_score_and_access_scope(client,auth_headers,student_headers,acceptance_data):
    score=acceptance_data['score']
    path=f'/api/v1/scores/{score}/steps.csv'
    result=await client.get(path,headers=auth_headers)
    assert result.status_code==200
    rows=list(csv.DictReader(io.StringIO(result.content.decode('utf-8-sig'))))
    assert len(rows)==2
    assert sum(float(r['得分']) for r in rows)==50
    detail=(await client.get(f'/api/v1/scores/{score}',headers=auth_headers)).json()
    assert {r['实训记录编号'] for r in rows}=={detail['record_reference']}
    assert any(r['状态']=='未通过' for r in rows)
    own=await _login(client,'ACCEPT-S')
    assert (await client.get(path,headers=own)).status_code==200
    assert (await client.get(path,headers=student_headers)).status_code==403
    assert (await client.get(path)).status_code in (401,403)

async def test_ability_retry_keeps_failure_reason_and_restricts_access(client,auth_headers,student_headers,acceptance_data,monkeypatch):
    from app.services.ability import AbilityService
    from unittest.mock import AsyncMock
    original=AbilityService.recalculate_profile
    monkeypatch.setattr(AbilityService,'recalculate_profile',AsyncMock(side_effect=RuntimeError('injected failure')))
    path=f"/api/v1/release/evaluations/{acceptance_data['student']}/recalculate"
    failure=await client.post(path,headers=auth_headers)
    assert failure.status_code==200 and failure.json()['status']=='failed'
    assert failure.json()['error_type']=='RuntimeError'
    assert failure.json()['reason']=='能力评价更新失败，请重新计算或联系管理员'
    assert 'injected failure' not in failure.text
    rows=(await client.get('/api/v1/release/evaluations',headers=auth_headers)).json()
    assert rows[0]['status']=='failed' and rows[0]['student_id']==acceptance_data['student']
    monkeypatch.setattr(AbilityService,'recalculate_profile',original)
    assert (await client.post(path,headers=auth_headers)).json()['status']=='completed'
    rows=(await client.get('/api/v1/release/evaluations',headers=auth_headers)).json()
    assert rows[0]['status']=='completed' and rows[0]['profile_updated_at']
    assert (await client.post(path,headers=student_headers)).status_code==403
    assert (await client.get('/api/v1/release/evaluations',headers=student_headers)).status_code==403
