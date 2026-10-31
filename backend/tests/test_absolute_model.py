from types import SimpleNamespace as Obj
from datetime import datetime
import pytest
from app.services.evaluation import evaluate, summarize_major_abilities, summarize_sub_abilities
from tests.test_acceptance_workflows import acceptance_data, domain_ids

def test_points_only_major_example_and_threshold_independence():
    parent=Obj(id='m',name='大类',graduation_threshold=.6,weight=999)
    children=[Obj(id=str(i),name=str(i),major_ability_id='m',weight=points) for i,points in enumerate([20,30,50])]
    values,details=summarize_major_abilities({'0':.5,'1':.8,'2':.8},[parent],children)
    assert values['m']==pytest.approx(.74)
    assert sum(c['earned_score'] for c in details[0]['children'])==74
    parent.weight=.0001;parent.graduation_threshold=.8
    assert summarize_major_abilities({'0':.5,'1':.8,'2':.8},[parent],children)[0]==values

def test_multiple_mappings_do_not_increase_training_score_or_add_edge_weights():
    score=Obj(id='s',project_id='p',calculated_at=datetime(2026,1,1),details={'x':{'score':20,'max_score':50,'related_abilities':['a','b']}})
    values,_=summarize_sub_abilities([score])
    assert values=={'a':.4,'b':.4}
    assert score.details['x']['score']==20
    with pytest.raises(ValueError):summarize_sub_abilities([score],.5)

def test_unassessed_child_is_not_zero_score_evidence_or_ready():
    parent=Obj(id='m',name='大类',graduation_threshold=0,weight=1)
    child=Obj(id='a',name='子能力',major_ability_id='m',weight=20)
    assert evaluate([],[parent],[child])=={'sub':{},'major':{'m':0},'ready':False}

async def test_both_reference_creation_endpoints_share_cap(client,auth_headers,acceptance_data):
    lab=acceptance_data['lab']
    path=f'/api/v1/admin/operations/labs/{lab}/reference-images'
    for i in range(2):
        response=await client.post(path,headers=auth_headers,json={'image_url':f'/standard-{i}.png','label':str(i)})
        assert response.status_code==200,response.text
    assert (await client.post(path,headers=auth_headers,json={'image_url':'/third.png'})).status_code==400
    import io
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(8,8)).save(image,format='PNG')
    rejected=await client.post(f'/api/v1/release/labs/{lab}/reference',headers=auth_headers,files={'file':('third.png',image.getvalue(),'image/png')})
    assert rejected.status_code==400
    rows=(await client.get(path,headers=auth_headers)).json()
    assert len(rows)==2
