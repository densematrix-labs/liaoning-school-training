"""Release regressions: real evidence, authorization, offline data and failures."""
import base64
import io
import json
import sqlite3
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, func

from tests.test_acceptance_workflows import acceptance_data, domain_ids
from app.config import settings
from app.models.operations import AuditLog, SystemSetting
from app.models.training import TrainingProject, TrainingRecord, Score
from app.models.user import User, UserRole
from app.models.workflow import MockSyncException, ReportTask, TaskStatus
from app.services.production_data import ProductionIngest, score_steps, truth, identifier, setting, put_setting, read_mysql
from app.services.catalog import parse_upload, save_item
from app.services.auth import AuthService


@pytest.fixture
def release_mode(monkeypatch):
    monkeypatch.setattr(settings,"RELEASE_MODE",True)


def row(source_id="REAL-1"):
    return {"source_record_id":source_id,"student_no":"ACCEPT001","project_code":"P-001","completed_at":"2026-09-01T08:00:00+08:00",
            "steps":{"step-1":{"passed":True},"step-2":{"passed":"false","reason":"操作失败"}}}


@pytest.mark.parametrize("value,expected",[(True,True),(False,False),("false",False),("0",False),(0,False),("通过",True),("未通过",False),("TRUE",True)])
def test_boolean_is_not_python_string_truthiness(value,expected):
    assert truth(value) is expected


@pytest.mark.parametrize("value",[None,"unknown",2,[],{},"False "])
def test_unknown_step_status_is_rejected(value):
    with pytest.raises(ValueError):
        truth(value)


@pytest.mark.parametrize("value",["bad; DROP TABLE users","schema.table","field name","","x` OR 1"])
def test_sql_mapping_cannot_inject(value):
    with pytest.raises(ValueError):
        identifier(value)


async def test_real_ingest_dedup_quarantine_and_immutable_source(test_db,acceptance_data,release_mode):
    async with test_db() as db:
        service=ProductionIngest(db)
        bad=row("bad");bad["steps"]={"step-1":True}
        task=await service.run([row(),row(),bad],actor_id=acceptance_data["teacher"])
        assert (task.read_count,task.success_count,task.skipped_count,task.error_count)==(3,1,1,1)
        record=(await db.execute(select(TrainingRecord).where(TrainingRecord.external_id.like("src:%")))).scalar_one()
        score=(await db.execute(select(Score).where(Score.record_id==record.id))).scalar_one()
        assert score.total_score==50 and score.details["step-2"]["passed"] is False
        assert record.completed_at==datetime(2026,9,1,0,0)
        evidence=await setting(db,"source:"+record.id)
        assert evidence["source_record_id"]=="REAL-1" and evidence["batch_id"]==task.id
        changed=row();changed["steps"]["step-2"]["passed"]=True
        task=await service.run([changed],actor_id=acceptance_data["teacher"])
        assert task.error_count==1 and task.success_count==0
        assert (await db.get(Score,score.id)).total_score==50
        assert (await db.execute(select(func.count()).select_from(MockSyncException))).scalar()==2


@pytest.mark.parametrize("mutation",["missing_student","missing_id","missing_time","bad_time","unknown_project","bad_steps","duplicate_steps","bad_weight"])
async def test_invalid_source_never_creates_score(test_db,acceptance_data,mutation):
    data=row()
    async with test_db() as db:
        if mutation=="missing_student":data["student_no"]="unknown"
        if mutation=="missing_id":data.pop("source_record_id")
        if mutation=="missing_time":data.pop("completed_at")
        if mutation=="bad_time":data["completed_at"]="yesterday"
        if mutation=="unknown_project":data["project_code"]="wrong"
        if mutation=="bad_steps":data["steps"]="[]"
        if mutation=="duplicate_steps":data["steps"]=[{"id":"x","passed":True},{"id":"x","passed":True}]
        if mutation=="bad_weight":
            project=await db.get(TrainingProject,acceptance_data["project"])
            project.steps=[{"id":"step-1","score":float("inf")},{"id":"step-2","score":10}]
        task=await ProductionIngest(db).run([data],actor_id=acceptance_data["teacher"])
        assert task.error_count==1
        assert (await db.execute(select(func.count()).select_from(Score))).scalar()==1


async def test_ingest_disable_and_environment_link(test_db,acceptance_data):
    async with test_db() as db:
        await put_setting(db,"state:projects:"+acceptance_data["project"],{"enabled":False})
        task=await ProductionIngest(db).run([row()],actor_id=acceptance_data["teacher"])
        assert task.error_count==1
        await put_setting(db,"state:projects:"+acceptance_data["project"],{"enabled":True})
        data=row();data["environment_image"]="data:image/png;base64,AA=="
        task=await ProductionIngest(db).run([data],actor_id=acceptance_data["teacher"])
        assert task.success_count==1


async def test_login_limit_refresh_type_rotation_disable_logout(client,test_db,auth_headers):
    for _ in range(5):
        assert (await client.post('/api/v1/auth/login',json={"username":"nobody","password":"wrong"})).status_code==401
    assert (await client.post('/api/v1/auth/login',json={"username":"nobody","password":"wrong"})).status_code==429
    login=await client.post('/api/v1/auth/login',json={"username":"testuser","password":"testpass"})
    tokens=login.json()
    assert (await client.post('/api/v1/auth/refresh',headers={"Authorization":"Bearer "+tokens["access_token"]})).status_code==401
    headers={"Authorization":"Bearer "+tokens["refresh_token"]}
    assert (await client.get('/api/v1/auth/me',headers=headers)).status_code==401
    refreshed=await client.post('/api/v1/auth/refresh',headers=headers)
    assert refreshed.status_code==200
    assert (await client.post('/api/v1/auth/refresh',headers=headers)).status_code==401
    assert (await client.post('/api/v1/auth/logout',headers=auth_headers)).status_code==200
    assert (await client.get('/api/v1/auth/me',headers=auth_headers)).status_code==401
    async with test_db() as db:
        from app.services.account_security import revoke
        await revoke(db,'test-user-1',False);await db.commit()
    assert (await client.post('/api/v1/auth/login',json={"username":"testuser","password":"testpass"})).status_code==401


async def test_catalog_import_partial_rows_versions_soft_disable(client,auth_headers,test_db):
    path='/api/v1/release/catalog/majors'
    assert (await client.get(path)).status_code==401
    response=await client.post(path,headers=auth_headers,json={"code":"RAIL","name":"铁道专业"})
    assert response.status_code==200,response.text
    item_id=response.json()["id"]
    assert (await client.post(path,headers=auth_headers,json={"code":"RAIL","name":"重复"})).status_code==400
    updated=await client.put(path+'/'+item_id,headers=auth_headers,json={"name":"铁道新专业","enabled":False})
    assert updated.status_code==200 and updated.json()["enabled"] is False
    versions=(await client.get('/api/v1/release/versions/majors/'+item_id,headers=auth_headers)).json()
    assert len(versions)==2 and versions[0]["before"]["name"]=="铁道专业"
    content='code,name\nRAIL,重复\nNEW,新专业\n,缺编码\n'
    preview=await client.post(path+'/import?preview=true',headers=auth_headers,files={"file":('data.csv',content)})
    assert preview.status_code==200 and preview.json()["success"]==1
    imported=await client.post(path+'/import',headers=auth_headers,files={"file":('data.csv',content)})
    assert imported.json()["success"]==1
    listing=(await client.get(path,headers=auth_headers)).json()
    assert len(listing["items"])==2
    assert (await client.get('/api/v1/release/templates/records.csv',headers=auth_headers)).status_code==200
    assert (await client.get('/api/v1/release/templates/unknown.csv',headers=auth_headers)).status_code==404
    assert (await client.get('/api/v1/release/catalog/unknown',headers=auth_headers)).status_code==404
    assert (await client.put('/api/v1/release/catalog/accounts/test-user-1',headers=auth_headers,json={"enabled":False})).status_code==400
    audit=(await client.get('/api/v1/release/audit',headers=auth_headers,params={"object_type":"majors","result":"success","date_from":"2020-01-01"})).json()
    assert len(audit)>=3


async def test_catalog_all_types_and_relationship_validation(test_db,acceptance_data,auth_headers,client):
    ids=acceptance_data
    base='/api/v1/release/catalog/'
    payloads={"accounts":{"username":"newteacher","name":"新教师","role":"teacher","password":"long-password-123"},
        "classes":{"name":"新增班","major_id":ids["major"],"year":2026},
        "labs":{"name":"第四实训室","capacity":30},
        "abilities":{"name":"新能力","weight":1,"graduation_threshold":0.6},
        "sub-abilities":{"name":"新子能力","major_ability_id":ids["ability"],"weight":1},
        "projects":{"name":"新项目","major_id":ids["major"],"lab_id":ids["lab"],"steps":[{"id":"x","score":10,"weight":2}],"ability_mapping":{"x":[ids["sub"]]},"scoring_rules":{"code":"new-project","repeat_mode":"highest"}}}
    for kind,data in payloads.items():
        response=await client.post(base+kind,headers=auth_headers,json=data)
        assert response.status_code==200,(kind,response.text)
    invalid=[('accounts',{"username":"x","name":"X","role":"admin","password":"short"}),
             ('classes',{"name":"X","major_id":"bad","year":2026}),('abilities',{"name":"X","weight":-1}),
             ('projects',{"name":"X","major_id":ids["major"],"steps":[{"id":"x","score":10}],"ability_mapping":{"x":["not-there"]}})]
    for kind,data in invalid:
        assert (await client.post(base+kind,headers=auth_headers,json=data)).status_code==400


def test_csv_xlsx_import_and_oversize():
    from openpyxl import Workbook
    book=Workbook();book.active.append(['name','code']);book.active.append(['专业','R'])
    buffer=io.BytesIO();book.save(buffer)
    assert parse_upload('data.xlsx',buffer.getvalue())==[{"name":"专业","code":"R"}]
    for name,data in [('bad.txt',b'a'),('empty.csv',b'name\n'),('big.csv',b'x'*(20*1024*1024+1))]:
        with pytest.raises(ValueError):parse_upload(name,data)


def test_mysql_readonly_cursor_query(monkeypatch):
    import pymysql
    calls=[]
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,*args):calls.append(args)
        def fetchall(self):return [{"source_record_id":"one","updated_at":datetime(2026,1,1)}]
    class Connection:
        def cursor(self):return Cursor()
        def rollback(self):calls.append(('rollback',))
        def close(self):calls.append(('close',))
    monkeypatch.setattr(pymysql,'connect',lambda **kw:Connection())
    fields={key:key for key in ['source_record_id','student_no','project_code','completed_at','steps','updated_at']}
    result=read_mysql({"table":"training","fields":fields},{"host":"db","user":"readonly","password":"test","database":"school"},['2026-01-01','zero'])
    assert result[0]['updated_at']=='2026-01-01T00:00:00'
    assert calls[0][0]=='SET TRANSACTION READ ONLY'
    assert 'ORDER BY `updated_at`, `source_record_id` LIMIT %s' in calls[2][0]
    assert calls[2][1][-1]==1000 and calls[-1]==('close',)


def test_encrypted_backup_restore_and_no_overwrite(tmp_path,monkeypatch):
    from app.services.operations_runtime import backup_database,restore_to_new_directory
    source=tmp_path/'training.db'
    with sqlite3.connect(source) as db:
        for table in ['users','students','scores']:
            db.execute(f'CREATE TABLE {table} (id TEXT)');db.execute(f"INSERT INTO {table} VALUES ('one')")
    key=Fernet.generate_key().decode()
    monkeypatch.setenv('BACKUP_ENCRYPTION_KEY',key)
    monkeypatch.setattr(settings,'DATABASE_URL','sqlite+aiosqlite:///'+str(source))
    result=backup_database(tmp_path/'backups')
    file=tmp_path/'backups'/result['filename']
    assert b'SQLite' not in file.read_bytes()
    restored=restore_to_new_directory(file,tmp_path/'restore',key)
    assert restored['counts']=={'users':1,'students':1,'scores':1}
    with pytest.raises(ValueError):restore_to_new_directory(file,tmp_path/'restore',key)
    with pytest.raises(InvalidToken):restore_to_new_directory(file,tmp_path/'wrong-key',Fernet.generate_key().decode())


def image_bytes():
    from PIL import Image
    buffer=io.BytesIO();Image.new('RGB',(64,64),'white').save(buffer,format='PNG');return buffer.getvalue()


async def test_images_validate_actual_pixels_and_local_data(tmp_path,monkeypatch):
    from app.services.images import validate_bytes,image_data_url
    data=image_bytes()
    assert validate_bytes(data)=='image/png'
    with pytest.raises(ValueError):validate_bytes(b'not a png')
    root=tmp_path/'static';root.mkdir();(root/'ref.png').write_bytes(data)
    monkeypatch.setenv('STATIC_DIR',str(root))
    result=await image_data_url('/ref.png')
    assert base64.b64decode(result.split(',')[1])==data
    assert await image_data_url(result)==result
    for source in ['http://127.0.0.1/private','/../../etc/passwd','data:image/png;base64,bad']:
        with pytest.raises(ValueError):await image_data_url(source)


def test_ai_evidence_validation_and_review_thresholds():
    from app.services.ai_gateway import validate_report
    from app.services.environment_validation import validate_result,CATEGORIES
    result={key:'基于本次实训结果分析。' for key in ['overview','score_analysis','weaknesses','environment','suggestions','training_plan']}
    result['evidence']=[{'key':'score','value':50}]
    assert '能力概况' in validate_report(result,{'score':50})
    result['evidence'][0]['value']=99
    with pytest.raises(ValueError):validate_report(result,{'score':50})
    result['evidence'][0]['value']=50;result['overview']='成绩为 99 分'
    with pytest.raises(ValueError):validate_report(result,{'score':50})
    environment={'total_score':100,'summary':'整洁','suggestions':[],'categories':{k:{'score':v,'max_score':v,'issues':[],'confidence':0.9} for k,v in CATEGORIES.items()}}
    assert validate_result(environment)['needs_review'] is False
    environment['categories']['equipment_placement']['confidence']=0.6
    assert validate_result(environment)['needs_review'] is True
    environment['total_score']=20
    with pytest.raises(ValueError):validate_result(environment)


def test_weighted_evaluation_repeat_policies_and_missing_evidence():
    from app.services.evaluation import evaluate,select_repeated
    abilities=[SimpleNamespace(id='major',graduation_threshold=.6)]
    subs=[SimpleNamespace(id='a',major_ability_id='major',weight=1),SimpleNamespace(id='b',major_ability_id='major',weight=1)]
    scores=[SimpleNamespace(id='s1',total_score=50,max_score=100,calculated_at=datetime(2026,1,1),details={'x':{'score':50,'max_score':100,'related_abilities':['a']}})]
    value=evaluate(scores,abilities,subs)
    assert value['major']['major']==.25 and not value['ready']
    later=SimpleNamespace(id='s2',total_score=100,max_score=100,calculated_at=datetime(2026,1,2),details={})
    for policy in ['latest','highest']:
        project=SimpleNamespace(id='p',scoring_rules={'repeat_mode':policy})
        assert select_repeated([(scores[0],project),(later,project)])[0][0].id=='s2'
    with pytest.raises(ValueError):evaluate(scores,abilities,subs,0)


async def test_period_report_requires_valid_explicit_range(test_db,acceptance_data,release_mode):
    from app.services.report import ReportService
    async with test_db() as db:
        service=ReportService(db)
        with pytest.raises(ValueError):await service.create_task(acceptance_data['student'],'periodic',None,acceptance_data['teacher'])
        with pytest.raises(ValueError):await service.create_task(acceptance_data['student'],'periodic',None,acceptance_data['teacher'],datetime(2026,2,1),datetime(2026,1,1))
        task=await service.create_task(acceptance_data['student'],'periodic',None,acceptance_data['teacher'],datetime(2026,1,1),datetime(2026,10,1))
        options=await setting(db,'report_options:'+task.id)
        assert options['date_from']=='2026-01-01T00:00:00'


async def test_source_and_runtime_apis(client,auth_headers,monkeypatch):
    assert (await client.get('/api/v1/release/source',headers=auth_headers)).status_code==200
    fields={key:key for key in ['source_record_id','student_no','project_code','completed_at','steps','updated_at']}
    assert (await client.put('/api/v1/release/source',headers=auth_headers,json={'table':'records','fields':fields})).status_code==200
    assert (await client.put('/api/v1/release/source',headers=auth_headers,json={'table':'records; drop','fields':fields})).status_code==400
    assert (await client.get('/api/v1/release/status',headers=auth_headers)).json()['database']=='connected'
    assert (await client.get('/api/v1/release/metrics',headers=auth_headers)).status_code==200
    monkeypatch.delenv('BACKUP_ENCRYPTION_KEY',raising=False)
    assert (await client.post('/api/v1/release/backups',headers=auth_headers)).status_code==400


async def test_oidc_unconfigured_and_csrf_rejected(client,monkeypatch):
    for key in ['ISSUER','CLIENT_ID','CLIENT_SECRET','REDIRECT_URI']:monkeypatch.delenv('OIDC_'+key,raising=False)
    assert (await client.get('/api/v1/sso/status')).json()['enabled'] is False
    assert (await client.get('/api/v1/sso/login')).status_code==503
    assert (await client.get('/api/v1/sso/callback?code=bad&state=wrong')).status_code==400
    assert (await client.post('/api/v1/sso/exchange')).status_code==401
