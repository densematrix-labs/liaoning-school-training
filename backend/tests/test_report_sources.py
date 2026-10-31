import copy
import pytest
from app.config import settings
from app.models.report import DiagnosticReport
from app.models.training import Score
from app.services.production_data import put_setting
from app.services.report_sources import comparison, require_complete_report_steps
from app.services.report import ReportService
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login


@pytest.mark.parametrize('key', ['step_name', 'passed', 'score', 'max_score'])
async def test_missing_step_fields_block_before_any_ai_call(test_db, monkeypatch, key):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    async def forbidden(*a, **k):
        pytest.fail('Incomplete source must not reach AI')
    monkeypatch.setattr('app.services.ai_gateway.completion', forbidden)
    step = {'step_name': '操作', 'passed': False, 'score': 0, 'max_score': 30}
    step.pop(key)
    async with test_db() as db:
        with pytest.raises(ValueError, match='未采集，无法判断'):
            await ReportService(db)._generate_report_content('匿名学员', [{'steps': [step]}], [], 'single', False, [])


def test_missing_differs_from_zero_and_failed():
    require_complete_report_steps([{'steps': [{'step_name': '操作', 'passed': False, 'score': 0, 'max_score': 30}]}])
    assert comparison('得分', 0, 0)['status'] == '一致'
    assert comparison('状态', False, False)['status'] == '一致'
    assert comparison('原因', None, None)['status'] == '报告未留存，无法核对'
    assert comparison('得分', 33.3, 50)['status'] == '不一致，需复核'
    with pytest.raises(ValueError, match='步骤数据未采集'):
        require_complete_report_steps([{'steps': []}])


@pytest.mark.parametrize('key', ['step_name', 'passed', 'score', 'max_score'])
async def test_source_assembly_preserves_missing_fields_and_does_not_save_report(test_db, acceptance_data, monkeypatch, key):
    from app.models.training import TrainingProject
    from sqlalchemy import select, func
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    async def forbidden(*a, **k):
        pytest.fail('Missing source data must be rejected before recalculation or inference')
    monkeypatch.setattr('app.services.ability.AbilityService.recalculate_profile', forbidden)
    monkeypatch.setattr('app.services.ai_gateway.completion', forbidden)
    async with test_db() as db:
        score = await db.get(Score, acceptance_data['score'])
        steps = copy.deepcopy(score.details)
        steps['step-1'].pop(key, None)
        score.details = steps
        if key == 'step_name':
            project = await db.get(TrainingProject, acceptance_data['project'])
            project.steps = []
        await db.commit()
        before = await db.scalar(select(func.count()).select_from(DiagnosticReport))
        with pytest.raises(ValueError, match='未采集，无法判断'):
            await ReportService(db).generate_report(acceptance_data['student'], score_id=score.id)
        assert await db.scalar(select(func.count()).select_from(DiagnosticReport)) == before


async def test_sources_compare_frozen_input_and_flag_changes_without_rewriting(client, test_db, acceptance_data, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    async with test_db() as db:
        score = await db.get(Score, ids['score'])
        snapshot = {'snapshot': {'student_name': '验收学生', 'class_name': '验收班'}, 'score_ids': [ids['score']],
                    'input_scores': [{'total_score': 50, 'max_score': 100, 'steps': []}],
                    'input_abilities': [{'name': '规范操作', 'score': 50, 'threshold': 60}], 'input_environment': []}
        await put_setting(db, 'report_meta:' + ids['report'], copy.deepcopy(snapshot))
        await db.commit()
    endpoint = '/api/v1/reports/' + ids['report'] + '/sources'
    data = (await client.get(endpoint, headers=auth_headers)).json()
    assert data['student_name'] == '验收学生'
    assert data['environment_status'].startswith('无关联环境记录，无法判断')
    assert data['abilities'][0]['comparison'] == '一致'
    assert all(r['status'] == '一致' for r in data['rows'] if r['field'] in {'总分', '满分', '学生姓名', '班级'})
    async with test_db() as db:
        score = await db.get(Score, ids['score'])
        score.total_score = 70
        await db.commit()
    changed = (await client.get(endpoint, headers=auth_headers)).json()
    assert next(r for r in changed['rows'] if r['field'] == '总分') == comparison('总分', 50, 70)
    async with test_db() as db:
        from app.services.production_data import setting
        assert await setting(db, 'report_meta:' + ids['report'], {}) == snapshot
    # Existing ownership guard also protects the newly added source route.
    teacher = await _login(client, 'ACCEPT-T')
    assert (await client.get(endpoint, headers=teacher)).status_code == 200
    async with test_db() as db:
        from app.models.student import Class
        cls = await db.get(Class, ids['class'])
        cls.teacher_id = None
        await db.commit()
    assert (await client.get(endpoint, headers=teacher)).status_code == 403
