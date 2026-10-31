from datetime import datetime
from sqlalchemy import select
from app.models.training import Score, TrainingProject, TrainingRecord
from app.services.ability import AbilityService
from app.services.production_data import put_setting
from app.config import settings
from tests.test_acceptance_workflows import acceptance_data, domain_ids


async def test_two_different_steps_support_one_subability_with_same_evaluation_basis(test_db, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    async with test_db() as db:
        profile = await AbilityService(db).get_student_profile(ids['student'])
        sub = next(x for x in profile.sub_ability_details if x['id'] == ids['sub'])
        assert {x['step_id'] for x in sub['evidence']} == {'step-1', 'step-2'}
        assert sub['aggregation']['step_count'] == 2
        assert sub['aggregation']['evidence_count'] == 2
        assert sub['aggregation']['weighted_earned'] == 50
        assert sub['aggregation']['effective_weight'] == 100
        assert sub['aggregation']['percentage'] == 50 and sub['score'] == .5
        # Changing a current mapping does not rewrite historical score mappings.
        project = await db.get(TrainingProject, ids['project'])
        project.ability_mapping = {'step-1': [], 'step-2': []}
        await db.commit()
        again = await AbilityService(db).get_student_profile(ids['student'])
        assert again.sub_ability_details[0]['aggregation'] == sub['aggregation']


async def test_evidence_and_summary_only_use_the_same_selected_records_with_decay(test_db, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    async with test_db() as db:
        original = await db.get(Score, ids['score'])
        original.calculated_at = datetime(2026, 1, 1)
        db.add(TrainingRecord(id='later-record', external_id='LATER-EVIDENCE', student_id=ids['student'],
                              project_id=ids['project'], completed_at=datetime(2026, 1, 2), steps_data={}))
        db.add(Score(id='later', student_id=ids['student'], project_id=ids['project'], record_id='later-record',
                     total_score=100, max_score=100, details={'step-1': {'passed': True, 'score': 40, 'max_score': 40, 'related_abilities': [ids['sub']]}, 'step-2': {'passed': True, 'score': 60, 'max_score': 60, 'related_abilities': [ids['sub']]}},
                     calculated_at=datetime(2026, 1, 2)))
        await db.commit()
        project = await db.get(TrainingProject, ids['project'])
        project.scoring_rules = {**project.scoring_rules, 'repeat_mode': 'latest'}
        await put_setting(db, 'release:evaluation', {'decay': .5})
        await db.commit()
        profile = await AbilityService(db).get_student_profile(ids['student'])
        sub = profile.sub_ability_details[0]
        assert {x['score_id'] for x in sub['evidence']} == {'later'}
        assert sub['aggregation']['percentage'] == 100 and sub['score'] == 1
        project.scoring_rules = {**project.scoring_rules, 'repeat_mode': 'all'}
        await db.commit()
        profile = await AbilityService(db).get_student_profile(ids['student'])
        sub = profile.sub_ability_details[0]
        assert sub['aggregation']['evidence_count'] == 4 and sub['aggregation']['step_count'] == 2
        assert sub['aggregation']['weighted_earned'] == 150
        assert sub['aggregation']['effective_weight'] == 200
        assert sub['aggregation']['percentage'] == 75 and sub['score'] == .75


async def test_three_history_records_explain_33_3_and_parent_aggregation(test_db, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    async with test_db() as db:
        original = await db.get(Score, ids['score'])
        record = await db.get(TrainingRecord, ids['record'])
        record.completed_at = original.calculated_at = datetime(2026, 10, 2)
        for index, value in enumerate([0, 0, 30]):
            detail = {'step-2': {'passed': value > 0, 'step_name': '测量与接线操作', 'score': value, 'max_score': 30,
                                 'related_abilities': [ids['sub']], 'applied_rule': {'weight': 1, 'rule_version': 7}}}
            if index == 0:
                original.details = detail
                original.total_score, original.max_score = value, 30
            else:
                day = [2, 7, 12][index]
                db.add(TrainingRecord(id=f'proof-record-{index}', external_id=f'PROOF-33-{index}', student_id=ids['student'],
                                      project_id=ids['project'], completed_at=datetime(2026, 10, day), steps_data={}))
                db.add(Score(id=f'proof-score-{index}', student_id=ids['student'], project_id=ids['project'],
                             record_id=f'proof-record-{index}', total_score=value, max_score=30,
                             details=detail, calculated_at=datetime(2026, 10, day)))
        await db.commit()
        profile = await AbilityService(db).get_student_profile(ids['student'])
        scope = profile.history_scope
        assert scope['available_records'] == scope['selected_records'] == 3
        assert scope['date_from'].startswith('2026-10-02') and scope['date_to'].startswith('2026-10-12')
        sub = next(x for x in profile.sub_ability_details if x['id'] == ids['sub'])
        assert sub['aggregation']['weighted_earned'] == 30
        assert sub['aggregation']['effective_weight'] == 90
        assert sub['aggregation']['percentage'] == 33.3 and sub['score'] == .33
        assert all(x['mapping_target_id'] == ids['sub'] and x['step_weight'] == 1 and x['effective_weight'] == 30 for x in sub['evidence'])
        assert all(x['rule_version'] == 7 and x['mapping_source'] == '计分时能力映射快照' for x in sub['evidence'])
        parent = next(x for x in profile.major_ability_calculations if x['id'] == ids['ability'])
        assert parent['full_score'] == 1 and parent['percentage'] == 33.3
