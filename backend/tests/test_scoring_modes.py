from types import SimpleNamespace
import pytest
from app.services.production_data import score_steps, ScoringError

def project(mode, total=200, weights=(20,30,50)):
    return SimpleNamespace(scoring_rules={'scoring_mode':mode,'total_score':total},ability_mapping={},steps=[{'id':str(i),'score':v,'weight':w,'failed_score':0} for i,(v,w) in enumerate(zip((20,30,50),weights))])

def test_absolute_ignores_legacy_multiplier():
    details,score,maximum,_=score_steps(project('absolute'),{'0':True,'1':False,'2':True})
    assert (score,maximum)==(70,100)
    assert details['2']['max_score']==50

def test_proportional_uses_configured_total_and_not_step_points():
    p=project('proportional');p.steps[0]['score']=9876
    details,score,maximum,_=score_steps(p,{'0':True,'1':False,'2':True})
    assert (score,maximum)==(140,200)
    assert [v['max_score'] for v in details.values()]==[40,60,100]
    assert all(v['applied_rule']['configured_total']==200 for v in details.values())

@pytest.mark.parametrize('total,weights',[(0,(20,30,50)),(float('nan'),(20,30,50)),(100,(20,20,50)),(100,(0,50,50)),(100,(20,float('inf'),50))])
def test_invalid_proportional_rules_do_not_produce_score(total,weights):
    with pytest.raises(ScoringError):score_steps(project('proportional',total,weights),{'0':True,'1':True,'2':True})

def test_disabled_steps_not_counted_in_ratios():
    p=project('proportional',100,(20,30,50));p.steps[1]['enabled']=False
    with pytest.raises(ScoringError):score_steps(p,{'0':True,'2':True})
    p.steps[0]['weight']=50
    assert score_steps(p,{'0':True,'2':False})[1:3]==(50,100)

def test_relative_child_weights_need_not_sum_to_one_and_threshold_is_independent():
    from app.services.evaluation import summarize_major_abilities
    parent=SimpleNamespace(id='m',name='设备检查',weight=1,graduation_threshold=.6)
    children=[SimpleNamespace(id=str(i),name=str(i),major_ability_id='m',weight=w) for i,w in enumerate((1,2,1))]
    first,rows=summarize_major_abilities({'0':.4,'1':1,'2':1},[parent],children)
    assert first['m']==.85 and rows[0]['full_score']==4
    parent.graduation_threshold=.9
    second,rows=summarize_major_abilities({'0':.4,'1':1,'2':1},[parent],children)
    assert second==first and [s.weight for s in children]==[1,2,1]
    assert rows[0]['threshold']==90
