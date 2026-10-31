import csv
import io
from datetime import datetime
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login
from app.models.operations import AuditLog
from app.models.student import Class

async def test_exports_are_real_files_scoped_and_never_include_credentials(client,auth_headers,acceptance_data):
    student=await _login(client,'ACCEPT-S')
    for kind in ['students','classes','projects','abilities','accounts']:
        path=f'/api/v1/release/catalog-export/{kind}.csv'
        assert (await client.get(path,headers=student)).status_code==403
        r=await client.get(path,headers=auth_headers)
        assert r.status_code==200 and r.content.startswith(b'\xef\xbb\xbf')
        assert 'password_hash' not in r.text and 'password' not in next(csv.reader(io.StringIO(r.text)) )
    for kind in ['steps','mappings','evaluations','report-summaries']:
        p=f'/api/v1/release/business-export/{kind}.csv?student_id={acceptance_data["student"]}'
        assert (await client.get(p,headers=student)).status_code==403
        r=await client.get(p,headers=auth_headers)
        assert r.status_code==200 and len(list(csv.reader(io.StringIO(r.content.decode('utf-8-sig')))))>1

async def test_error_envelope_has_code_location_without_echoing_input(client,auth_headers,acceptance_data):
    r=await client.get('/api/v1/scores/student/'+acceptance_data['student']+'?page_size=9999',headers=auth_headers)
    assert r.status_code==422
    d=r.json();assert d['code']=='PARAMETER_INVALID' and d['request_id'] and d['status']=='error'
    assert d['detail'][0]['loc'][-1]=='page_size' and 'input' not in d['detail'][0]
    r=await client.get('/api/v1/release/catalog/accounts')
    assert r.status_code==401 and r.json()['code']=='AUTH_REQUIRED'

async def test_object_id_filter_does_not_substitute_object_type(client,auth_headers,test_db):
    async with test_db() as db:
        db.add_all([AuditLog(action='fixture',object_type='score',object_id='a',result='success'),AuditLog(action='fixture',object_type='score',object_id='b',result='failed',reason='test timeout')]);await db.commit()
    r=await client.get('/api/v1/release/audit?object_id=b&result=failed',headers=auth_headers)
    assert r.status_code==200 and len(r.json())==1
    assert r.json()[0]['object_id']=='b' and r.json()[0]['reason']=='test timeout'

def test_direct_identifiers_are_removed_from_nested_free_text_not_only_field_names():
    from app.services.ai_privacy import report_payload
    import json
    source=[{'student_no':'P2026001','project_name':'训练','total_score':70,'steps':[{'step_name':'接线','passed':False,'score':0,'max_score':30,'reason':'张某 P2026001 尚未记录原因','secret':'must drop'}]}]
    out=report_payload(source,[{'name':'设备检查','score':33.3,'threshold':60,'private':'drop'}],[],{'record_0.total_score':70},'single',['张某','P2026001'])
    text=json.dumps(out,ensure_ascii=False)
    assert '张某' not in text and 'P2026001' not in text and 'secret' not in text and 'private' not in text
    assert out['scores'][0]['total_score']==70 and out['scores'][0]['steps'][0]['score']==0
    assert source[0]['steps'][0]['reason']=='张某 P2026001 尚未记录原因'

async def test_review_saved_history_contains_real_old_state_and_scoped_access(client,test_db,acceptance_data,monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,'RELEASE_MODE',True)
    teacher=await _login(client,'ACCEPT-T')
    path='/api/v1/environment/checks/'+acceptance_data['check']
    r=await client.post(path+'/review',headers=teacher,json={'status':'modified','reviewed_details':{'equipment_placement':{'score':20,'max_score':30},'surface_cleanliness':{'score':22,'max_score':30},'safety_compliance':{'score':18,'max_score':20},'environmental_hygiene':{'score':20,'max_score':20}},'reviewed_summary':'本地测试','note':'复核保存备注'})
    assert r.status_code==200
    rows=(await client.get(path+'/review-history',headers=teacher)).json()
    assert len(rows)==1 and rows[0]['before']['status']=='pending'
    assert rows[0]['after']['note']=='复核保存备注' and rows[0]['actor_id']==acceptance_data['teacher']

async def test_export_formula_text_is_not_executable_spreadsheet_formula(client,auth_headers,test_db,acceptance_data):
    async with test_db() as db:
        row=await db.get(Class,acceptance_data['class']);row.name='=IMPORTXML("bad")';await db.commit()
    r=await client.get('/api/v1/release/catalog-export/classes.csv',headers=auth_headers)
    rows=list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
    assert rows[1][1].startswith("'=")
