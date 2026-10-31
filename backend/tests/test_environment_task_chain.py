import base64
from datetime import datetime
import httpx
import pytest
from sqlalchemy import select,func
from app.config import settings
from app.models.workflow import EnvironmentTask,TaskStatus
from app.models.training import Score
from tests.test_acceptance_workflows import acceptance_data,domain_ids
from tests.test_release_integrations import image_bytes,release_mode

async def test_retry_chain_filters_authorization_and_score_isolation(client,test_db,auth_headers,acceptance_data,release_mode):
 ids=acceptance_data;image='data:image/png;base64,'+base64.b64encode(image_bytes()).decode()
 async with test_db() as db:
  original=(await db.get(Score,ids['score'])).total_score
  db.add(EnvironmentTask(id='timeout-original',student_id=ids['student'],lab_id=ids['lab'],score_id=ids['score'],image_data=image,status=TaskStatus.FAILED,created_by=ids['teacher'],error_message='AI 服务超时（ReadTimeout）',completed_at=datetime.utcnow()))
  await db.commit()
  start=(await db.get(EnvironmentTask,'timeout-original')).created_at.isoformat()
 r=await client.post('/api/v1/environment/tasks/timeout-original/retry',headers=auth_headers)
 assert r.status_code==200,r.text
 retry=r.json();assert retry['parent_task_id']=='timeout-original' and retry['root_task_id']=='timeout-original' and retry['status']=='pending'
 assert (await client.post('/api/v1/environment/tasks/'+retry['id']+'/retry',headers=auth_headers)).status_code==409
 r=await client.get('/api/v1/environment/tasks',params={'student_id':ids['student'],'status':'failed','task_id':'timeout-original'},headers=auth_headers)
 assert r.status_code==200 and r.json()['total']==1 and 'ReadTimeout' in r.json()['items'][0]['error_message']
 assert 'image_data' not in r.json()['items'][0]
 r=await client.get('/api/v1/environment/tasks',params={'student_id':ids['student'],'date_from':start,'date_to':start,'task_id':'timeout-original'},headers=auth_headers)
 assert r.status_code==200 and r.json()['total']==1
 assert (await client.get('/api/v1/environment/tasks',params={'student_id':ids['student'],'date_from':'invalid'},headers=auth_headers)).status_code==400
 assert (await client.get('/api/v1/environment/tasks',params={'student_id':ids['student'],'status':'bogus'},headers=auth_headers)).status_code==400
 assert (await client.get('/api/v1/environment/tasks',params={'student_id':ids['student'],'page_size':201},headers=auth_headers)).status_code==422
 other=await client.post('/api/v1/auth/login',json={'username':'ACCEPT-S','password':'123456'});sh={'Authorization':'Bearer '+other.json()['access_token']}
 assert (await client.get('/api/v1/environment/tasks',params={'student_id':'not-own-student'},headers=sh)).status_code==403
 async with test_db() as db:
  assert (await db.get(Score,ids['score'])).total_score==original
  assert (await db.get(EnvironmentTask,'timeout-original')).status==TaskStatus.FAILED
  assert (await db.execute(select(func.count()).select_from(EnvironmentTask))).scalar_one()==2

async def test_gateway_timeout_is_specific_and_contains_no_secret(monkeypatch):
 from app.services.ai_gateway import completion
 monkeypatch.setattr(settings,'LLM_BASE_URL','https://test.invalid/v1');monkeypatch.setattr(settings,'LLM_API_KEY','test-secret-never-expose');monkeypatch.setenv('AI_FALLBACK_ROUTES','[]')
 async def fail(*a,**k):raise httpx.ReadTimeout('private provider detail')
 monkeypatch.setattr(httpx.AsyncClient,'post',fail)
 with pytest.raises(RuntimeError,match='ReadTimeout') as ex:await completion([{'role':'user','content':'test'}],vision=True)
 assert '超时' in str(ex.value) and 'test-secret' not in str(ex.value) and 'private provider' not in str(ex.value)
