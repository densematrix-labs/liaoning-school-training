from datetime import datetime
from types import SimpleNamespace

import pytest
from app.config import settings
from app.models.training import Score, TrainingProject
from app.services.ability import AbilityService
from app.services.evaluation import summarize_sub_abilities
from app.services.mapping_points import validate_mapping_points
from app.services.production_data import score_steps
from tests.test_acceptance_workflows import acceptance_data, domain_ids


def test_each_association_has_independent_points_without_changing_training_scores():
    project = SimpleNamespace(
        steps=[{'id': 'one', 'score': 50}, {'id': 'two', 'score': 50}],
        ability_mapping={'one': ['a', 'b'], 'two': ['a', 'b']},
        scoring_rules={'scoring_mode': 'absolute', 'ability_mapping_points': {
            'one': {'a': 20, 'b': 80}, 'two': {'a': 80, 'b': 20}}})
    details, total, maximum, _ = score_steps(project, {'one': True, 'two': False})
    score = SimpleNamespace(id='record', project_id='project', calculated_at=datetime(2026, 10, 30), details=details)
    values, _ = summarize_sub_abilities([score])
    assert values == {'a': .2, 'b': .8}
    assert (total, maximum) == (50, 100)
    # Changing live configuration cannot mutate saved evaluation evidence.
    project.scoring_rules['ability_mapping_points']['one']['a'] = 999
    assert summarize_sub_abilities([score])[0] == values
    assert score.details['one']['score'] == 50


@pytest.mark.parametrize('value', [0, -1, 'NaN', 'Infinity', '', True, None])
def test_invalid_points_rejected(value):
    with pytest.raises(ValueError):
        validate_mapping_points({'one': ['a']}, {'one': {'a': value}})


def test_unknown_association_rejected_and_old_snapshots_keep_their_result():
    with pytest.raises(ValueError):
        validate_mapping_points({'one': ['a']}, {'one': {'b': 10}})
    score = SimpleNamespace(id='old', project_id='p', calculated_at=None, details={
        'one': {'score': 20, 'max_score': 20, 'related_abilities': ['a', 'a']},
        'two': {'score': 0, 'max_score': 80, 'related_abilities': ['a']}})
    values, details = summarize_sub_abilities([score])
    assert values['a'] == .2
    assert details['a']['evidence_count'] == 2


async def test_save_readback_recalculate_and_history_snapshot(client, test_db, auth_headers, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    path = f"/api/v1/release/catalog/projects/{ids['project']}"
    points = {'step-1': {ids['sub']: 20}, 'step-2': {ids['sub']: 80}}
    saved = await client.put(path, headers=auth_headers, json={'scoring_rules': {
        'scoring_mode': 'absolute', 'repeat_mode': 'all', 'ability_mapping_points': points}})
    assert saved.status_code == 200, saved.text
    assert saved.json()['scoring_rules']['ability_mapping_points'] == points
    catalog = (await client.get('/api/v1/release/catalog/projects', headers=auth_headers)).json()
    assert next(x for x in catalog['items'] if x['id'] == ids['project'])['scoring_rules']['ability_mapping_points'] == points
    async with test_db() as db:
        profile = await AbilityService(db).get_student_profile(ids['student'])
        assert profile.sub_ability_details[0]['aggregation']['percentage'] == 50
    result = await client.post(f"/api/v1/admin/projects/{ids['project']}/recalculate", headers=auth_headers, json={'score_id': ids['score']})
    assert result.status_code == 200, result.text
    assert result.json()['sample']['before_total'] == result.json()['sample']['after_total'] == 50
    async with test_db() as db:
        score = await db.get(Score, ids['score'])
        assert score.details['step-2']['ability_mapping_points'] == {ids['sub']: 80}
        profile = await AbilityService(db).get_student_profile(ids['student'])
        aggregation = profile.sub_ability_details[0]['aggregation']
        assert aggregation['percentage'] == 33.3
        assert {e['contribution_points'] for e in profile.sub_ability_details[0]['evidence']} == {20, 80}
    # A later edit alone still leaves the recalculated snapshot unchanged.
    points['step-1'][ids['sub']] = 90
    await client.put(path, headers=auth_headers, json={'scoring_rules': {'ability_mapping_points': points}})
    async with test_db() as db:
        assert (await AbilityService(db).get_student_profile(ids['student'])).sub_ability_details[0]['aggregation'] == aggregation


async def test_import_export_and_invalid_config_are_isolated(client, test_db, auth_headers, acceptance_data):
    ids = acceptance_data
    rows = f"project_id,step_id,sub_ability_id,enabled,contribution_points\n{ids['project']},step-1,{ids['sub']},true,25\n{ids['project']},step-2,{ids['sub']},true,-1\n"
    imported = await client.post('/api/v1/release/mappings/import', headers=auth_headers,
        files={'file': ('mapping.csv', rows.encode(), 'text/csv')})
    assert imported.status_code == 200, imported.text
    assert imported.json()['success'] == imported.json()['errors'] == 1
    exported = await client.get('/api/v1/release/business-export/mappings.csv', headers=auth_headers)
    assert '贡献分值' in exported.text and ',25.0' in exported.text
    async with test_db() as db:
        project = await db.get(TrainingProject, ids['project'])
        assert project.scoring_rules['ability_mapping_points'] == {'step-1': {ids['sub']: 25}}
        version = project.scoring_rules['version']
    rejected = await client.put(f"/api/v1/release/catalog/projects/{ids['project']}", headers=auth_headers,
        json={'scoring_rules': {'ability_mapping_points': {'step-1': {ids['sub']: 0}}}})
    assert rejected.status_code == 400
    async with test_db() as db:
        project = await db.get(TrainingProject, ids['project'])
        assert project.scoring_rules['version'] == version
        assert project.scoring_rules['ability_mapping_points']['step-1'][ids['sub']] == 25
