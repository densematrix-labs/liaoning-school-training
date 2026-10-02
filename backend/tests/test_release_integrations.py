"""Deployment boundaries, signed OIDC, AI failures and durable worker tests."""
import asyncio,base64,hashlib,io,json,time
from datetime import datetime,timedelta
from unittest.mock import AsyncMock
from urllib.parse import urlparse,parse_qs
import httpx
import pytest
import jwt
from sqlalchemy import select,delete
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from tests.test_acceptance_workflows import acceptance_data,domain_ids
from tests.test_release import release_mode,row,image_bytes
from app.config import settings
from app.database import get_db
from app.models.user import User,UserRole
from app.models.operations import SystemSetting,AuditLog
from app.models.workflow import ReportTask,EnvironmentTask,TaskStatus,MockSyncException
from app.models.training import TrainingProject,Score
from app.services.production_data import setting,put_setting
from app.services.auth import AuthService

async def test_offline_bootstrap_never_seeds_demo(test_db,monkeypatch):
    import app.offline as offline
    import app.services.operations_runtime as runtime
    import app.init_data as seed
    monkeypatch.setattr(offline,'AsyncSessionLocal',test_db)
    monkeypatch.setattr(offline,'init_db',AsyncMock())
    monkeypatch.setattr(settings,'SECRET_KEY','x'*48)
    monkeypatch.setattr(settings,'RELEASE_MODE',True)
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','strong-initial-password')
    monkeypatch.setattr(runtime.worker,'start',AsyncMock());monkeypatch.setattr(runtime.worker,'stop',AsyncMock())
    monkeypatch.setattr(seed,'init_mock_data',AsyncMock())
    async with offline.lifespan(offline.site):
        async with test_db() as db:
            users=(await db.execute(select(User))).scalars().all()
            assert len(users)==1 and users[0].role==UserRole.ADMIN
            assert AuthService.verify_password('strong-initial-password',users[0].password_hash)
        seed.init_mock_data.assert_not_called()
    async with offline.lifespan(offline.site):pass
    assert runtime.worker.start.await_count==2
    monkeypatch.setattr(offline,'MODE','demo')
    with pytest.raises(RuntimeError,match='switch'):
        async with offline.lifespan(offline.site):pass
    monkeypatch.setattr(offline,'MODE','invalid')
    with pytest.raises(RuntimeError,match='must be'):
        async with offline.lifespan(offline.site):pass
    monkeypatch.setattr(offline,'MODE','pilot');monkeypatch.setattr(settings,'SECRET_KEY','short')
    with pytest.raises(RuntimeError,match='unique'):
        async with offline.lifespan(offline.site):pass
    monkeypatch.setattr(settings,'SECRET_KEY','x'*48)
    async with test_db() as db:await db.execute(delete(SystemSetting));await db.commit()
    with pytest.raises(RuntimeError,match='migration'):
        async with offline.lifespan(offline.site):pass
    async with test_db() as db:await db.execute(delete(User));await db.commit()
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD','bad')
    with pytest.raises(RuntimeError,match='16'):
        async with offline.lifespan(offline.site):pass
    async with test_db() as db:await db.execute(delete(SystemSetting));await db.commit()
    import app.services.scheduler as scheduler
    monkeypatch.setattr(offline,'MODE','demo')
    monkeypatch.setattr(scheduler.sync_scheduler,'start',lambda:None)
    monkeypatch.setattr(scheduler.sync_scheduler,'stop',AsyncMock())
    async with offline.lifespan(offline.site):pass
    seed.init_mock_data.assert_awaited_once()

async def test_offline_routes_security_static_and_audit(test_db,auth_headers,acceptance_data,monkeypatch,tmp_path):
    import app.offline as offline
    import app.services.operations_runtime as runtime
    monkeypatch.setattr(offline,'MODE','pilot');monkeypatch.setattr(offline,'AsyncSessionLocal',test_db)
    monkeypatch.setattr(runtime,'AsyncSessionLocal',test_db);monkeypatch.setattr(offline,'STATIC',tmp_path)
    (tmp_path/'index.html').write_text('<head></head><div>site</div>');(tmp_path/'app.js').write_text('console.log(1)')
    async def dbdep():
        async with test_db() as db:yield db
    offline.site.dependency_overrides[get_db]=dbdep
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=offline.app),base_url='http://test') as client:
            for path in ['/','/index.html','/student']:
                res=await client.get(path);assert res.status_code==200 and '__SHIXUN_DEMO__=false' in res.text
            for path,code in [('/app.js',200),('/missing.png',404),('/docs',404),('/api/v1/dashboard/overview',401)]:assert (await client.get(path)).status_code==code
            assert (await client.get('/health')).json()['database']=='connected'
            teacher={'Authorization':'Bearer '+AuthService.create_access_token({'sub':acceptance_data['teacher'],'role':'teacher'})}
            assert (await client.get('/api/v1/dashboard/overview',headers=teacher)).status_code==403
            assert (await client.post('/api/v1/admin/sync',headers=auth_headers)).status_code==409
            assert (await client.delete('/api/v1/admin/labs/x',headers=auth_headers)).status_code==409
            res=await client.post('/api/v1/release/catalog/majors',headers=auth_headers,json={'name':'Rail','code':'R2'})
            assert res.status_code==200 and res.headers['x-request-id']
            assert (await client.get('/api/not-found',headers=auth_headers)).status_code==404
            assert (await client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+AuthService.create_access_token({'sub':'missing','role':'admin'})})).status_code==401
        async with test_db() as db:
            audits=(await db.execute(select(AuditLog).where(AuditLog.object_type=='api'))).scalars().all()
            assert any(x.result=='failed' for x in audits) and any(x.result=='success' for x in audits)
        events=[]
        async def send(event):events.append(event)
        await offline.app({'type':'websocket','path':'/api/v1/dashboard/ws'},None,send)
        assert events==[{'type':'websocket.close','code':1008}]
        with pytest.raises(Exception):await offline.static_site('../outside')
        def broken():raise OSError('unavailable')
        monkeypatch.setattr(offline,'AsyncSessionLocal',broken)
        assert (await offline.readiness()).status_code==503
    finally:offline.site.dependency_overrides.clear()

async def test_oidc_signed_end_to_end_and_replays(test_db,auth_headers,monkeypatch):
    import app.routers.sso as sso
    from starlette.requests import Request
    issuer='https://school.example'
    cfg={'issuer':issuer,'client_id':'school-app','client_secret':'private-test-secret','redirect_uri':'https://training.example/api/v1/sso/callback'}
    for k,v in cfg.items():monkeypatch.setenv('OIDC_'+k.upper(),v)
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    nums=key.public_key().public_numbers()
    def enc(n):return base64.urlsafe_b64encode(n.to_bytes((n.bit_length()+7)//8,'big')).decode().rstrip('=')
    jwks={'keys':[{'kty':'RSA','kid':'school-key','use':'sig','alg':'RS256','n':enc(nums.n),'e':enc(nums.e)}]}
    metadata={'issuer':issuer,'authorization_endpoint':issuer+'/authorize','token_endpoint':issuer+'/token','jwks_uri':issuer+'/keys'}
    claims={'iss':issuer,'aud':cfg['client_id'],'sub':'teacher-1','exp':int(time.time())+300,'iat':int(time.time())}
    class Remote:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url):return httpx.Response(200,json=jwks if url.endswith('/keys') else metadata,request=httpx.Request('GET',url))
        async def post(self,url,**kwargs):
            assert kwargs['data']['code_verifier']
            return httpx.Response(200,json={'id_token':jwt.encode(claims,private,algorithm='RS256',headers={'kid':'school-key'})},request=httpx.Request('POST',url))
    monkeypatch.setattr(sso.httpx,'AsyncClient',lambda **kw:Remote())
    async with test_db() as db:
        identity='oidc_identity:'+hashlib.sha256((issuer+'|teacher-1').encode()).hexdigest()
        await put_setting(db,identity,{'user_id':'test-user-1'});await db.commit()
        response=await sso.start(db);params=parse_qs(urlparse(response.headers['location']).query)
        assert params['code_challenge_method']==['S256']
        state=params['state'][0];claims['nonce']=params['nonce'][0]
        req=Request({'type':'http','headers':[(b'cookie',('oidc_state='+state).encode())]})
        response=await sso.callback(req,'code',state,db)
        assert response.status_code==302 and response.headers['location']=='/login?sso=1'
        cookie=response.headers.getlist('set-cookie')[-1].split(';')[0]
        req2=Request({'type':'http','headers':[(b'cookie',cookie.encode())]})
        tokens=json.loads((await sso.exchange(req2,db)).body)
        assert AuthService.decode_token(tokens['access_token']).user_id=='test-user-1'
        with pytest.raises(Exception):await sso.exchange(req2,db)
        with pytest.raises(Exception):await sso.callback(req,'code',state,db)
        response=await sso.start(db);state=parse_qs(urlparse(response.headers['location']).query)['state'][0]
        req=Request({'type':'http','headers':[(b'cookie',('oidc_state='+state).encode())]})
        with pytest.raises(Exception) as bad:await sso.callback(req,'code',state,db)
        assert bad.value.status_code==401
        metadata['issuer']='https://evil.example'
        with pytest.raises(Exception):await sso.discovery(cfg)
        metadata['issuer']=issuer;metadata['jwks_uri']='http://insecure'
        with pytest.raises(Exception):await sso.discovery(cfg)
    monkeypatch.setenv('OIDC_ISSUER','http://school.example')
    with pytest.raises(Exception):sso.config()

async def test_ai_failover_structured_output_and_audit(test_db,monkeypatch):
    import app.services.ai_gateway as gateway
    monkeypatch.setattr(settings,'LLM_BASE_URL','https://first.example/v1');monkeypatch.setattr(settings,'LLM_API_KEY','test-only')
    monkeypatch.setenv('AI_FALLBACK_ROUTES',json.dumps([{'url':'https://second.example/v1','key_env':'TEST_AI_KEY','model':'fallback','vision_model':'vision'}]));monkeypatch.setenv('TEST_AI_KEY','test-only')
    called=[]
    class Remote:
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,url,**kwargs):
            called.append(url)
            if 'first' in url:raise httpx.ConnectError('unreachable')
            return httpx.Response(200,json={'choices':[{'message':{'content':'{"valid":true}'}}],'usage':{'total_tokens':10}},request=httpx.Request('POST',url))
    monkeypatch.setattr(gateway.httpx,'AsyncClient',lambda **kw:Remote())
    async with test_db() as db:
        result,model=await gateway.completion([{'role':'user','content':'匿名数据'}],db=db,vision=True)
        assert result=={'valid':True} and model=='vision' and len(called)==2
        audit=(await db.execute(select(AuditLog).where(AuditLog.action=='ai_call'))).scalar_one()
        assert len(audit.after['payload_sha256'])==64 and '匿名数据' not in json.dumps(audit.after)
        monkeypatch.setenv('AI_FALLBACK_ROUTES','[]')
        with pytest.raises(RuntimeError):await gateway.completion([],db=db)
        monkeypatch.setattr(settings,'LLM_BASE_URL','http://insecure')
        with pytest.raises(RuntimeError,match='HTTPS'):await gateway.completion([])
        monkeypatch.setattr(settings,'LLM_API_KEY','')
        with pytest.raises(RuntimeError):await gateway.completion([],db=db)

async def test_worker_drains_pages_and_recovers_errors(test_db,auth_headers,acceptance_data,monkeypatch,release_mode):
    import app.services.operations_runtime as runtime
    monkeypatch.setattr(runtime,'AsyncSessionLocal',test_db);worker=runtime.ReleaseWorker()
    async with test_db() as db:
        assert await worker.sync_source() is None
        with pytest.raises(ValueError):await worker.sync_source(force=True)
        await put_setting(db,'release:source',{'enabled':True,'table':'records','fields':{'steps':'steps'},'batch_size':1,'frequency_hours':24});await db.commit()
    calls=[]
    def read(cfg,credentials,cursor):
        calls.append(cursor)
        return [{**row(str(len(calls))),'updated_at':'2026-09-01T00:00:00'}] if len(calls)<=2 else []
    monkeypatch.setattr(runtime,'read_mysql',read)
    result=await worker.sync_source(force=True)
    assert result['read']==2 and result['success']==2 and len(calls)==3
    assert await worker.sync_source() is None
    def fail(*args):raise ConnectionError('offline')
    monkeypatch.setattr(runtime,'read_mysql',fail)
    with pytest.raises(ValueError):await worker.sync_source(force=True)
    async with test_db() as db:
        assert (await setting(db,'release:last_sync_error'))['status']=='failed'
        await put_setting(db,'release:source',{'enabled':False})
        db.add(ReportTask(id='interrupted',student_id=acceptance_data['student'],report_type='periodic',created_by='test-user-1',status=TaskStatus.RUNNING))
        db.add(AuditLog(action='old',object_type='test',created_at=datetime.utcnow()-timedelta(days=181)));await db.commit()
    monkeypatch.setattr(worker,'run',AsyncMock());await worker.start();await asyncio.sleep(0);await worker.stop()
    async with test_db() as db:assert (await db.get(ReportTask,'interrupted')).status==TaskStatus.FAILED
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY','configured');monkeypatch.setattr(runtime,'backup_database',lambda:{'filename':'safe.enc'})
    await worker.tick()
    async with test_db() as db:
        assert (await setting(db,'release:last_backup'))['status']=='completed'
        assert (await setting(db,'release:worker'))['status']=='running'
        assert not (await db.execute(select(AuditLog).where(AuditLog.action=='old'))).scalars().all()
        await put_setting(db,'release:last_backup',{});await db.commit()
    monkeypatch.setattr(runtime,'backup_database',fail);await worker.tick()
    async with test_db() as db:assert (await setting(db,'release:backup_error'))['status']=='failed'

async def test_real_environment_student_upload_review_and_report_snapshot(client,test_db,auth_headers,acceptance_data,monkeypatch,release_mode):
    import app.services.environment as env
    import app.services.ai_gateway as gateway
    from app.services.report import ReportService
    from app.services.environment_validation import CATEGORIES
    ids=acceptance_data;image='data:image/png;base64,'+base64.b64encode(image_bytes()).decode()
    assert (await client.post('/api/v1/release/labs/'+ids['lab']+'/reference',headers=auth_headers,files={'file':('ref.png',image_bytes())})).status_code==200
    for lab,data in [('missing',image_bytes()),(ids['lab'],b'not-image')]:assert (await client.post('/api/v1/release/labs/'+lab+'/reference',headers=auth_headers,files={'file':('bad.png',data)})).status_code in [400,404]
    student={'Authorization':'Bearer '+AuthService.create_access_token({'sub':ids['student_user'],'role':'student'})}
    task=await client.post('/api/v1/environment/tasks',headers=student,json={'student_id':ids['student'],'score_id':ids['score'],'lab_id':ids['lab'],'image_base64':image})
    assert task.status_code==200,task.text
    assert (await client.get('/api/v1/environment/tasks/'+task.json()['id'],headers=student)).status_code==200
    assert (await client.post('/api/v1/environment/tasks',headers=student,json={'student_id':ids['student'],'score_id':'wrong','lab_id':ids['lab'],'image_base64':image})).status_code==400
    async def complete(messages,**kwargs):
        if kwargs.get('vision'):
            assert image in json.dumps(messages)
            return {'total_score':100,'summary':'整洁','suggestions':[],'categories':{k:{'score':v,'max_score':v,'issues':[],'confidence':.95} for k,v in CATEGORIES.items()}},'test-vision'
        facts=json.loads(messages[1]['content'])['facts']
        return {**{key:'依据实训记录分析。' for key in ['overview','score_analysis','weaknesses','environment','suggestions','training_plan']},'evidence':[{'key':k,'value':v} for k,v in facts.items()]},'test-text'
    monkeypatch.setattr(gateway,'completion',complete);monkeypatch.setattr(env,'AsyncSessionLocal',test_db)
    await env.process_environment_task(task.json()['id'])
    completed=(await client.get('/api/v1/environment/tasks/'+task.json()['id'],headers=student)).json()
    assert completed['status']=='completed',completed
    check=completed['check_id']
    assert (await client.post('/api/v1/environment/checks/'+check+'/review',headers=student,json={'status':'confirmed'})).status_code==403
    review=await client.post('/api/v1/environment/checks/'+check+'/review',headers=auth_headers,json={'status':'confirmed','note':'教师确认'})
    assert review.status_code==200,review.text
    async with test_db() as db:
        service=ReportService(db);report=await service.generate_report(ids['student'],'single',ids['score']);old_total=report.score_total
        score=await db.get(Score,ids['score']);score.total_score=1;await db.commit()
        assert (await service.get_report(report.id)).score_total==old_total
        periodic=await service.generate_report(ids['student'],'periodic',date_from=datetime(2020,1,1),date_to=datetime(2030,1,1))
        assert '2020-01-01' in periodic.content
        with pytest.raises(ValueError):await service.generate_report(ids['student'],'periodic',date_from=datetime(1990,1,1),date_to=datetime(1991,1,1))

async def test_real_import_replay_and_connectivity_apis(client,test_db,auth_headers,acceptance_data,monkeypatch):
    import csv
    import app.routers.release as release
    data=row();data['steps']=json.dumps(data['steps']);buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=list(data));writer.writeheader();writer.writerow(data)
    res=await client.post('/api/v1/release/records/import',headers=auth_headers,files={'file':('real.csv',buffer.getvalue())})
    assert res.status_code==200 and res.json()['success']==1
    for path in ['records/import','catalog/majors/import']:assert (await client.post('/api/v1/release/'+path,headers=auth_headers,files={'file':('bad.exe',b'a')})).status_code==400
    assert (await client.post('/api/v1/release/exceptions/missing/retry',headers=auth_headers)).status_code==404
    async with test_db() as db:
        error=MockSyncException(task_id=res.json()['task_id'],row_number=2,source_record_id='retry',reason='invalid',raw_data={**row('retry'),'steps':{'wrong':True}})
        db.add(error);await db.commit();error_id=error.id
    replay=await client.post('/api/v1/release/exceptions/'+error_id+'/retry',headers=auth_headers,json=row('retry'));assert replay.json()['success']==1
    monkeypatch.setattr(release.worker,'sync_source',AsyncMock(return_value={'read':0}));assert (await client.post('/api/v1/release/source/sync',headers=auth_headers)).json()['read']==0
    monkeypatch.setattr(release.worker,'sync_source',AsyncMock(side_effect=ValueError('missing')));assert (await client.post('/api/v1/release/source/sync',headers=auth_headers)).status_code==400
    monkeypatch.setattr(release,'backup_database',lambda:{'filename':'encrypted.enc'});assert (await client.post('/api/v1/release/backups',headers=auth_headers)).status_code==200
    monkeypatch.setattr(settings,'LLM_API_KEY','');assert (await client.post('/api/v1/release/connectivity',headers=auth_headers)).json()['ai']['reachable'] is False
    assert (await client.get('/api/v1/release/templates/accounts.csv',headers=auth_headers)).status_code==200
    assert (await client.put('/api/v1/release/catalog/majors/missing',headers=auth_headers,json={'name':'wrong'})).status_code==400
    assert (await client.get('/api/v1/release/audit?date_to=2030-01-01&actor_id=test-user-1',headers=auth_headers)).status_code==200

async def test_release_rules_recalculation_versions_and_admin_validation(client,test_db,auth_headers,acceptance_data,release_mode):
    from app.services.catalog import save_item
    from app.services.recalculation import RecalculationService,_record_step_map
    ids=acceptance_data
    async with test_db() as db:
        admin=await db.get(User,'test-user-1')
        invalid=[('unknown',{},None),('labs',{'name':'x','unknown':1},None),('labs',{'name':'x','capacity':100001},None),
            ('projects',{'name':'x','major_id':ids['major'],'steps':'{}'},None),
            ('projects',{'name':'x','major_id':ids['major'],'steps':[{'id':'','score':10}]},None),
            ('projects',{'name':'x','major_id':ids['major'],'ability_mapping':{'missing':[]}},None),
            ('projects',{'name':'x','major_id':ids['major'],'steps':[{'id':'s','score':1}],'ability_mapping':{'s':'bad'}},None),
            ('projects',{'name':'x','major_id':ids['major'],'scoring_rules':{'repeat_mode':'bad'}},None),
            ('accounts',{'enabled':'false'},admin.id),('accounts',{'password':'short'},admin.id)]
        for kind,data,item_id in invalid:
            with pytest.raises(ValueError):await save_item(db,kind,data,admin,item_id)
            await db.rollback();admin=await db.get(User,'test-user-1')
        await save_item(db,'accounts',{'password':'new-strong-password','oidc_issuer':'https://school','oidc_subject':'known'},admin,ids['teacher'])
        await db.commit()
        with pytest.raises(ValueError):await save_item(db,'accounts',{'oidc_issuer':'https://school','oidc_subject':'known'},admin,ids['student_user'])
        await db.rollback()
        result=await RecalculationService(db).recalculate_score(ids['score']);assert result['after_total']==50
        snapshots=(await db.execute(select(SystemSetting).where(SystemSetting.key.like('ability_snapshot:%')))).scalars().all()
        assert snapshots and snapshots[0].value['score_ids']==[ids['score']]
        assert _record_step_map([None,{'id':'one','passed':False},{'passed':True}])['one']['passed'] is False
        assert _record_step_map(None)=={}
        with pytest.raises(ValueError):await RecalculationService(db).recalculate_score('missing')
    assert (await client.get('/api/v1/abilities/student/'+ids['student']+'/snapshots',headers=auth_headers)).json()
    for path,data in [('abilities/'+ids['ability'],{'name':'新大类','weight':1}),('labs/'+ids['lab'],{'name':'新实训室'}),('projects/'+ids['project']+'/configuration',{'steps':[{'id':'step-1','score':40},{'id':'step-2','score':60}],'ability_mapping':{}})]:
        res=await client.put('/api/v1/admin/'+path,headers=auth_headers,json=data);assert res.status_code==200,(path,res.text)
    trend=await client.get('/api/v1/abilities/student/'+ids['student']+'/trend',headers=auth_headers,params={'date_from':'2020-01-01','date_to':'2030-01-01','project_id':ids['project']})
    assert trend.status_code==200 and trend.json()['points']

@pytest.mark.parametrize('change',['not-object','missing','wrong-category','bad-score','bad-confidence','bad-issues','bad-summary'])
def test_environment_invalid_provider_response(change):
    from app.services.environment_validation import validate_result,CATEGORIES
    data={'total_score':100,'summary':'整洁','suggestions':[],'categories':{k:{'score':v,'max_score':v,'issues':[],'confidence':.9} for k,v in CATEGORIES.items()}}
    if change=='not-object':data=[]
    if change=='missing':data.pop('categories')
    if change=='wrong-category':data['categories']['other']=data['categories'].pop('equipment_placement')
    if change=='bad-score':data['categories']['equipment_placement']['score']=999
    if change=='bad-confidence':data['categories']['equipment_placement']['confidence']=2
    if change=='bad-issues':data['categories']['equipment_placement']['issues']='bad'
    if change=='bad-summary':data['summary']=''
    with pytest.raises((ValueError,TypeError)):validate_result(data)

async def test_network_image_allowlist_size_and_provider_json(monkeypatch):
    from app.services.images import image_data_url,validate_bytes
    from PIL import Image
    b=io.BytesIO();Image.new('RGB',(2,2)).save(b,format='PNG')
    for data in [b.getvalue(),b'x'*(10*1024*1024+1)]:
        with pytest.raises(ValueError):validate_bytes(data)
    monkeypatch.setenv('CAMERA_ALLOWED_HOSTS','camera.school')
    class Remote:
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def stream(self,method,url):yield httpx.Response(200,content=image_bytes(),request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:Remote())
    assert (await image_data_url('https://camera.school/photo.png')).startswith('data:image/png;base64,')
    with pytest.raises(ValueError):await image_data_url('https://user:password@camera.school/photo.png')
    from app.services.ai_gateway import validate_report
    for bad in [{},{'evidence':[],**{k:'' for k in ['overview','score_analysis','weaknesses','environment','suggestions','training_plan']}}, {'evidence':[],**{k:'text' for k in ['overview','score_analysis','weaknesses','environment','suggestions','training_plan']}}]:
        with pytest.raises(ValueError):validate_report(bad,{})

async def test_class_export_matches_shared_evaluator_and_disabled_schema(client,test_db,auth_headers,acceptance_data,release_mode):
    ids=acceptance_data
    overview=await client.get('/api/v1/students/classes/'+ids['class']+'/overview',headers=auth_headers)
    assert overview.status_code==200 and overview.json()['ability_distribution'][0]['average']==50
    exported=await client.get('/api/v1/students/classes/'+ids['class']+'/overview.csv',headers=auth_headers)
    assert exported.status_code==200 and 'ability_distribution' in exported.text and 'ACCEPT001' in exported.text
    async with test_db() as db:
        await put_setting(db,'state:abilities:'+ids['ability'],{'enabled':False});await db.commit()
    assert (await client.get('/api/v1/abilities/schema',headers=auth_headers)).json()==[]
    from app.services.time_utils import utc_boundary
    assert utc_boundary(datetime(2026,10,1,8))==datetime(2026,10,1)

async def test_environment_failures_are_durable_and_references_can_be_retired(client,test_db,auth_headers,acceptance_data,monkeypatch,release_mode):
    import app.services.environment as env
    from app.models.lab import Lab
    from app.models.operations import ReferenceImage
    from app.schemas.lab import EnvironmentReviewRequest
    ids=acceptance_data;image='data:image/png;base64,'+base64.b64encode(image_bytes()).decode()
    monkeypatch.setattr(env,'AsyncSessionLocal',test_db)
    async with test_db() as db:
        service=env.EnvironmentCheckService(db)
        for lab,score in [('missing',ids['score']),(ids['lab'],None),(ids['lab'],'wrong')]:
            with pytest.raises(ValueError):await service.check_environment(ids['student'],lab,image,score)
        lab=await db.get(Lab,ids['lab']);lab.reference_image_url=None;await db.commit()
        with pytest.raises(ValueError):await service.check_environment(ids['student'],ids['lab'],image,ids['score'])
        with pytest.raises(ValueError):await service.create_task('missing',ids['lab'],image,ids['score'],ids['teacher'])
        with pytest.raises(ValueError):await service.create_task(ids['student'],'missing',image,ids['score'],ids['teacher'])
        assert await service.get_check('missing') is None
        for details in [{}, {'surface_cleanliness':{'score':999}}]:
            with pytest.raises(ValueError):await service.review_check(ids['check'],ids['teacher'],EnvironmentReviewRequest(status='modified',reviewed_details=details))
            await db.rollback()
        with pytest.raises(ValueError):await service.review_check('missing',ids['teacher'],EnvironmentReviewRequest(status='confirmed'))
        task=await service.create_task(ids['student'],ids['lab'],image,ids['score'],ids['teacher'])
    await env.process_environment_task('missing');await env.process_environment_task(task.id);await env.process_environment_task(task.id)
    async with test_db() as db:
        saved=await db.get(EnvironmentTask,task.id);assert saved.status==TaskStatus.FAILED and saved.error_message
        assert len(await env.EnvironmentCheckService(db).get_student_history(ids['student']))==1
    await client.post('/api/v1/release/labs/'+ids['lab']+'/reference',headers=auth_headers,files={'file':('ref.png',image_bytes())})
    refs=(await client.get('/api/v1/admin/operations/labs/'+ids['lab']+'/reference-images',headers=auth_headers)).json()
    ref=refs[0]['id']
    assert (await client.put('/api/v1/release/references/'+ref,headers=auth_headers,json={'enabled':False,'label':'旧标准'})).json()['enabled'] is False
    assert (await client.put('/api/v1/release/references/'+ref,headers=auth_headers,json={'enabled':'unknown'})).status_code==400
    assert (await client.put('/api/v1/release/references/missing',headers=auth_headers,json={'enabled':False})).status_code==404
    async with test_db() as db:
        with pytest.raises(ValueError):await env.EnvironmentCheckService(db).check_environment(ids['student'],ids['lab'],image,ids['score'])

async def test_runtime_network_probes_and_sqlite_pragmas(client,test_db,auth_headers,monkeypatch,release_mode):
    import sqlite3
    from app.database import sqlite_options
    db=sqlite3.connect(':memory:');sqlite_options(db,None)
    assert db.execute('PRAGMA foreign_keys').fetchone()[0]==1;db.close()
    import app.routers.release as release
    import app.services.production_data as source
    monkeypatch.setattr(settings,'LLM_API_KEY','probe-only')
    class Remote:
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def get(self,url,**kw):return httpx.Response(200,json={'data':[]},request=httpx.Request('GET',url))
    # Keep the already-created ASGI client independent of the remote probe.
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:Remote())
    async with test_db() as db:
        await put_setting(db,'release:source',{'fields':{'id':'id'}});await db.commit()
        monkeypatch.setattr(source,'read_mysql',lambda *args:[])
        result=await release.connectivity(db)
        assert result['ai']['reachable'] and result['school_database']['reachable']
        async def fail(*a,**kw):raise httpx.ConnectError('offline')
        monkeypatch.setattr(Remote,'get',fail)
        def dbfail(*a):raise OSError('offline')
        monkeypatch.setattr(source,'read_mysql',dbfail)
        result=await release.connectivity(db)
        assert not result['ai']['reachable'] and not result['school_database']['reachable']
    from app.services.time_utils import utc_boundary
    assert utc_boundary(None) is None

async def test_score_page_has_bounded_query_count(test_db,acceptance_data):
    from app.services.score import ScoreService
    from sqlalchemy import event
    async with test_db() as db:
        statements=[]
        def capture(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
        engine=db.bind.sync_engine;event.listen(engine,'before_cursor_execute',capture)
        try:
            page=await ScoreService(db).get_student_scores(acceptance_data['student'])
            assert page.total==1 and page.scores[0].project_name=='验收实训项目'
            assert len(statements)==2,statements
        finally:event.remove(engine,'before_cursor_execute',capture)

async def test_real_ingest_crosses_transaction_checkpoints(test_db,acceptance_data,release_mode):
    from app.services.production_data import ProductionIngest
    async with test_db() as db:
        rows=[row('checkpoint-'+str(i)) for i in range(205)]
        result=await ProductionIngest(db).run(rows,actor_id=acceptance_data['teacher'])
        assert (result.success_count,result.error_count)==(205,0)
        repeated=await ProductionIngest(db).run(rows,actor_id=acceptance_data['teacher'])
        assert (repeated.success_count,repeated.skipped_count)==(0,205)

async def test_worker_backup_concurrent_wal_writer(tmp_path,monkeypatch):
    """A write during backup must not invalidate the worker's read snapshot."""
    import sqlite3
    import app.services.operations_runtime as runtime
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.database import Base
    path=tmp_path/'worker.db'
    engine=create_async_engine('sqlite+aiosqlite:///'+str(path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    with sqlite3.connect(path) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
    factory=async_sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(runtime,'AsyncSessionLocal',factory)
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY','configured')
    def concurrent_backup():
        with sqlite3.connect(path) as connection:
            connection.execute("INSERT INTO system_settings (key,value,updated_at) VALUES ('concurrent', '{}', CURRENT_TIMESTAMP)")
        return {'filename':'synthetic.enc'}
    monkeypatch.setattr(runtime,'backup_database',concurrent_backup)
    try:
        await runtime.ReleaseWorker().tick()
        async with factory() as db:
            assert (await setting(db,'release:last_backup'))['status']=='completed'
            assert (await setting(db,'release:worker'))['status']=='running'
    finally:
        await engine.dispose()
