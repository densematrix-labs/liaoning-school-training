from sqlalchemy import select, func
from app.models.training import TrainingProject, TrainingRecord, Score
from app.services.production_data import ProductionIngest
from tests.test_acceptance_workflows import acceptance_data, domain_ids
from tests.test_release import row


async def test_three_scoring_failures_never_create_formal_scores(client, test_db, auth_headers, student_headers, acceptance_data):
    async with test_db() as db:
        db.add(TrainingProject(id='no-rule', name='缺规则项目', major_id=acceptance_data['major'], steps=[], scoring_rules={'code':'NO-RULE'}, ability_mapping={}))
        await db.commit()
        rows=[{**row('FAIL-RULE'),'project_code':'NO-RULE'},
              {**row('FAIL-STEP'),'steps':{'step-1':True,'step-2':False,'unknown-step':True}},
              {**row('FAIL-SOURCE'),'steps':{'step-1':True}}]
        task=await ProductionIngest(db).run(rows, actor_id=acceptance_data['teacher'], source='exception-test')
        assert task.error_count==3 and task.success_count==0
        assert (await db.execute(select(func.count()).select_from(Score))).scalar()==1
        assert (await db.execute(select(func.count()).select_from(TrainingRecord))).scalar()==1
    response=await client.get('/api/v1/release/scoring-exceptions',headers=auth_headers)
    assert response.status_code==200
    items=response.json()['items']
    assert {x['code'] for x in items}=={'missing_rule','unknown_step','incomplete_source'}
    assert all(x['formal_score_count']==0 and x['formal_score_ids']==[] and x['reason'] for x in items)
    assert {x['status'] for x in items}=={'exception','incomplete'}
    assert (await client.get('/api/v1/release/scoring-exceptions',headers=student_headers)).status_code==403
    # A successful retry must cease claiming that no formal score exists.
    async with test_db() as db:
        task=await ProductionIngest(db).run([row('FAIL-SOURCE')],actor_id=acceptance_data['teacher'],source='exception-test')
        assert task.success_count==1
    items=(await client.get('/api/v1/release/scoring-exceptions',headers=auth_headers)).json()['items']
    fixed=next(x for x in items if x['source_record_id']=='FAIL-SOURCE')
    assert fixed['current_status']=='resolved' and fixed['formal_score_count']==1


async def test_step_description_uses_scoring_snapshot_not_updated_configuration(client,test_db,auth_headers,acceptance_data):
    async with test_db() as db:
        project=await db.get(TrainingProject,acceptance_data['project'])
        project.steps=[{**s,'description':'计分时的操作说明正文'} for s in project.steps]
        await db.commit()
        task=await ProductionIngest(db).run([row('DESCRIPTION')],actor_id=acceptance_data['teacher'])
        assert task.success_count==1
        project=await db.get(TrainingProject,acceptance_data['project'])
        project.steps=[{**s,'description':'后来修改的说明'} for s in project.steps]
        score=(await db.execute(select(Score).where(Score.id!=acceptance_data['score']))).scalar_one()
        score_id=score.id
        await db.commit()
    response=await client.get('/api/v1/scores/'+score_id,headers=auth_headers)
    assert response.status_code==200
    step=response.json()['details'][1]
    assert step['step_description']=='计分时的操作说明正文'
    assert step['description_source']=='计分时规则快照'
    assert step['passed'] is False and step['score']==10 and step['related_ability_names']
