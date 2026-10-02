"""Run ONLY in an empty disposable release container; writes synthetic test data."""
import asyncio,csv,io,json,os,statistics,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
from sqlalchemy import select,func
from app.database import AsyncSessionLocal
from app.models.user import User,UserRole
from app.models.student import Major,Class,Student
from app.models.lab import Lab
from app.models.ability import MajorAbility,SubAbility
from app.models.training import TrainingProject,Score,TrainingRecord
from app.services.auth import AuthService
from app.services.operations_runtime import backup_database,restore_to_new_directory

async def main():
    assert os.getenv('RELEASE_SMOKE_ALLOWED')=='true','Only explicitly disposable test instances'
    started=time.monotonic()
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.count()).select_from(Student))).scalar()==0,'Refuse nonempty business database'
        db.add(Major(id='perf-major',code='SYNTHETIC',name='合成测试专业'));await db.flush()
        hashed=AuthService.get_password_hash('synthetic-only-password')
        db.add_all([User(id=f'perf-teacher-{i}',username=f'perf-teacher-{i}',name=f'合成教师{i}',role=UserRole.TEACHER,password_hash=hashed) for i in range(4)])
        db.add_all([User(id=f'perf-user-{i}',username=f'perf-user-{i}',name=f'合成学生{i}',role=UserRole.STUDENT,password_hash=hashed) for i in range(140)])
        db.add_all([Lab(id=f'perf-lab-{i}',name=f'合成实训室{i}') for i in range(4)])
        db.add_all([MajorAbility(id=f'perf-ability-{i}',name=f'合成能力{i}',weight=1,graduation_threshold=.6,display_order=i) for i in range(5)])
        await db.flush()
        db.add_all([Class(id=f'perf-class-{i}',name=f'合成班{i}',major_id='perf-major',teacher_id=f'perf-teacher-{i}',year=2026) for i in range(4)])
        db.add_all([SubAbility(id=f'perf-sub-{i}',major_ability_id=f'perf-ability-{i}',name=f'合成子能力{i}',weight=1) for i in range(5)])
        await db.flush()
        db.add_all([Student(id=f'perf-student-{i}',user_id=f'perf-user-{i}',student_no=f'SYN{i:04d}',name=f'合成学生{i}',major_id='perf-major',class_id=f'perf-class-{i%4}',enrollment_year=2026) for i in range(140)])
        db.add_all([TrainingProject(id=f'perf-project-{i}',name=f'合成项目{i}',major_id='perf-major',lab_id=f'perf-lab-{i}',steps=[{'id':'s1','name':'检查','score':50},{'id':'s2','name':'操作','score':50}],scoring_rules={'code':f'SYN-P{i}','version':1},ability_mapping={'s1':['perf-sub-0','perf-sub-1'],'s2':['perf-sub-2','perf-sub-3','perf-sub-4']},max_score=100) for i in range(4)])
        await db.commit()
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8080',timeout=300) as client:
        login=await client.post('/api/v1/auth/login',json={'username':os.getenv('BOOTSTRAP_ADMIN_USER','admin'),'password':os.environ['BOOTSTRAP_ADMIN_PASSWORD']});login.raise_for_status()
        admin={'Authorization':'Bearer '+login.json()['access_token']}
        data=io.StringIO();writer=csv.DictWriter(data,fieldnames=['source_record_id','student_no','project_code','completed_at','steps']);writer.writeheader()
        for i in range(1000):writer.writerow({'source_record_id':f'SYN-{i}','student_no':f'SYN{i%140:04d}','project_code':f'SYN-P{i%4}','completed_at':(datetime(2026,9,1,8,tzinfo=timezone(timedelta(hours=8)))+timedelta(minutes=i)).isoformat(),'steps':json.dumps({'s1':True,'s2':i%3!=0})})
        t=time.monotonic();response=await client.post('/api/v1/release/records/import',headers=admin,files={'file':('synthetic.csv',data.getvalue())});response.raise_for_status();first=response.json();first['seconds']=round(time.monotonic()-t,3)
        assert first['success']==1000 and first['errors']==0,first
        t=time.monotonic();response=await client.post('/api/v1/release/records/import',headers=admin,files={'file':('synthetic.csv',data.getvalue())});response.raise_for_status();repeat=response.json();repeat['seconds']=round(time.monotonic()-t,3)
        assert repeat['success']==0 and repeat['skipped']==1000,repeat
        tokens=[AuthService.create_access_token({'sub':f'perf-user-{i}','role':'student'}) for i in range(50)]
        duration=int(os.getenv('SMOKE_LOAD_SECONDS','60'));end=time.monotonic()+duration;latencies=[];failures=[]
        async def visitor(i):
            while time.monotonic()<end:
                before=time.monotonic()
                try:
                    response=await client.get('/api/v1/scores/',headers={'Authorization':'Bearer '+tokens[i]});response.raise_for_status();assert response.json()['total']>0
                    latencies.append(time.monotonic()-before)
                except Exception as exc:failures.append(type(exc).__name__)
                await asyncio.sleep(max(0,.5-(time.monotonic()-before)))
        await asyncio.gather(*(visitor(i) for i in range(50)))
        t=time.monotonic();overview=await client.get('/api/v1/students/classes/perf-class-0/overview',headers=admin);overview.raise_for_status();summary_seconds=time.monotonic()-t
        assert overview.json()['student_count']==35 and len(overview.json()['ability_distribution'])==5
    backup=backup_database();restored=restore_to_new_directory('/backups/'+backup['filename'],'/tmp/release-restored',os.environ['BACKUP_ENCRYPTION_KEY'])
    assert restored['counts']['students']==140 and restored['counts']['scores']==1000
    ordered=sorted(latencies)
    result={'environment':'isolated Docker Desktop linux/amd64, synthetic data, not school acceptance','students':140,'labs':4,'abilities':5,'import':first,'duplicate_import':repeat,'load':{'distinct_users':50,'seconds':duration,'requests':len(latencies),'errors':len(failures),'p95_seconds':round(ordered[min(len(ordered)-1,int(len(ordered)*.95))],3),'max_seconds':round(max(ordered),3)},'class_overview_seconds':round(summary_seconds,3),'backup_restore':restored,'elapsed_seconds':round(time.monotonic()-started,3)}
    Path('/data/release-smoke-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
