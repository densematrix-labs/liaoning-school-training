"""Regression checks for configurable class mapping and evidence boundaries."""
from sqlalchemy import select,func
from app.models.student import Student,Class
from app.models.training import Score
from app.models.workflow import MockSyncException
from app.services.production_data import ProductionIngest
from tests.test_acceptance_workflows import acceptance_data,domain_ids
from tests.test_release import row,release_mode


async def test_class_mismatch_isolated_without_creating_score(test_db,acceptance_data):
    async with test_db() as db:
        bad={**row(),"class_name":"not-the-student-class"}
        task=await ProductionIngest(db).run([bad],actor_id=acceptance_data['teacher'])
        assert task.error_count==1 and task.success_count==0
        assert (await db.execute(select(func.count()).select_from(Score))).scalar()==1
        error=(await db.execute(select(MockSyncException).where(MockSyncException.task_id==task.id))).scalar_one()
        assert '班级' in error.reason


async def test_class_mapping_preserved_in_provenance(test_db,acceptance_data):
    from app.services.production_data import setting
    from app.models.training import TrainingRecord
    async with test_db() as db:
        student=(await db.execute(select(Student).where(Student.student_no==row()['student_no']))).scalar_one()
        class_obj=await db.get(Class,student.class_id)
        good={**row(),"class_name":class_obj.name}
        task=await ProductionIngest(db).run([good],actor_id=acceptance_data['teacher'])
        assert task.success_count==1
        records=(await db.execute(select(TrainingRecord))).scalars().all()
        evidence=[await setting(db,'source:'+r.id,{}) for r in records]
        assert any(e.get('class_name')==class_obj.name and e.get('batch_id')==task.id for e in evidence)


async def test_database_proof_restricted_to_admin(client,student_headers):
    for path,method in [('/api/v1/release/source/evidence','get'),('/api/v1/release/backups/verify','post')]:
        assert (await getattr(client,method)(path,headers=student_headers)).status_code==403
        assert (await getattr(client,method)(path)).status_code in (401,403)
