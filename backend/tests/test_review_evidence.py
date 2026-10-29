import io,zipfile
from datetime import datetime
from unittest.mock import AsyncMock
import httpx,pytest
from docx import Document
from tests.test_acceptance_workflows import acceptance_data,domain_ids
from app.models.training import TrainingProject,TrainingRecord
from app.services.production_data import score_steps

def test_disabled_steps_ignore_known_results_but_reject_unknown():
    p=TrainingProject(steps=[{'id':'a','score':20,'enabled':True},{'id':'b','score':80,'enabled':False}],scoring_rules={'enabled':True},ability_mapping={})
    details,total,maximum,_=score_steps(p,{'a':True,'b':False})
    assert total==maximum==20 and list(details)==['a']
    with pytest.raises(ValueError):score_steps(p,{'a':True,'unknown':True})

async def test_mapping_import_isolates_invalid_rows_and_keeps_versions(client,auth_headers,student_headers,acceptance_data):
    ids=acceptance_data;data=f"project_id,step_id,sub_ability_id,enabled\n{ids['project']},step-1,{ids['sub']},false\nmissing,step-1,{ids['sub']},true\n"
    r=await client.post('/api/v1/release/mappings/import',headers=auth_headers,files={'file':('mapping.csv',data)})
    assert r.status_code==200 and r.json()['success']==1 and r.json()['errors']==1
    projects=(await client.get('/api/v1/release/catalog/projects',headers=auth_headers)).json()['items']
    assert projects[0]['ability_mapping']['step-1']==[]
    versions=(await client.get(f"/api/v1/release/versions/projects/{ids['project']}",headers=auth_headers)).json()
    assert versions[0]['before']['ability_mapping']['step-1']==[ids['sub']]
    assert (await client.post('/api/v1/release/mappings/import',headers=student_headers,files={'file':('mapping.csv',data)})).status_code==403

async def test_batch_verification_1000_steps_does_not_replace_scores(client,test_db,auth_headers,acceptance_data):
    ids=acceptance_data
    async with test_db() as db:
        db.add_all([TrainingRecord(id=f'batch-{i}',external_id=f'BATCH-{i}',student_id=ids['student'],project_id=ids['project'],steps_data={'step-1':{'passed':True},'step-2':{'passed':i%2==0}},completed_at=datetime.utcnow()) for i in range(500)])
        await db.commit()
    r=await client.post('/api/v1/release/score-verification',headers=auth_headers);assert r.status_code==200
    result=r.json();assert result['steps']>=1000 and result['records']==501
    assert result['consistency_percent']==100 and result['first_sha256']==result['second_sha256'] and result['errors']==[]
    score=(await client.get(f"/api/v1/scores/{ids['score']}",headers=auth_headers)).json();assert score['total_score']==50

async def test_download_is_real_docx_and_access_scoped(client,auth_headers,student_headers,acceptance_data):
    path=f"/api/v1/reports/{acceptance_data['report']}/download.docx"
    r=await client.get(path,headers=auth_headers);assert r.status_code==200 and zipfile.is_zipfile(io.BytesIO(r.content))
    assert 'wordprocessingml.document' in r.headers['content-type']
    assert any('诊断' in p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert (await client.get(path,headers=student_headers)).status_code==403

async def test_mjpeg_uses_first_frame_and_enforces_host(monkeypatch):
    from app.services.images import image_data_url
    from PIL import Image
    import base64
    out=io.BytesIO();Image.new('RGB',(64,64),'white').save(out,format='JPEG');data=out.getvalue()
    async def body(request):return httpx.Response(200,headers={'content-type':'multipart/x-mixed-replace; boundary=frame'},content=b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+data+b'\r\n--frame\r\n')
    original=httpx.AsyncClient
    monkeypatch.setenv('CAMERA_ALLOWED_HOSTS','camera.example')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(body),**kw))
    image=await image_data_url('http://camera.example/video');assert base64.b64decode(image.split(',')[1])==data
    with pytest.raises(ValueError):await image_data_url('http://unapproved.example/video')
