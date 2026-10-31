"""Administrator exports: explicit business fields; no credentials or hidden settings."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from app.adapters.controllers.auth import get_current_admin
from app.database import get_db
from app.services.catalog import CATALOG, as_dict
from app.services.audit import record_audit
from app.models.training import TrainingProject
from app.models.student import Student
from app.models.report import DiagnosticReport
from app.services.ability import AbilityService

router=APIRouter(prefix='/api/v1/release',tags=['基础与评价数据导出'],dependencies=[Depends(get_current_admin)])
class SafeWriter:
    def __init__(self,out):self.writer=csv.writer(out)
    def writerow(self,row):
        self.writer.writerow(["'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for v in row])

LABELS={'id':'记录ID','name':'名称','username':'账号','role':'角色','major_id':'专业ID','class_id':'班级ID','teacher_id':'教师ID','year':'年级','user_id':'账号ID','student_no':'学号','enrollment_year':'入学年','code':'编码','description':'说明','duration':'时长分钟','lab_id':'实训室ID','steps':'步骤定义','scoring_rules':'评分规则','ability_mapping':'能力映射','weight':'权重','full_score':'子能力满分','pass_score':'达标分（100分制）','graduation_threshold':'达标阈值','display_order':'顺序','major_ability_id':'所属大类ID','building':'楼栋','floor':'楼层','capacity':'容量','status':'状态','equipment':'设备清单','current_students':'当前人数','reference_image_url':'参考图片'}

@router.get('/catalog-export/{kind}.csv')
async def export_catalog(kind:str,admin=Depends(get_current_admin),db=Depends(get_db)):
    import json
    if kind not in CATALOG: raise HTTPException(404,'对象类型不存在')
    model,fields,_=CATALOG[kind]
    rows=(await db.execute(select(model).order_by(model.id))).scalars().all()
    cols=['id']+fields
    output=io.StringIO();writer=SafeWriter(output);writer.writerow([LABELS.get(k,k) for k in cols])
    for row in rows:
        data=as_dict(row,fields)
        writer.writerow([json.dumps(data[k],ensure_ascii=False) if isinstance(data[k],(dict,list)) else data[k] for k in cols])
    await record_audit(db,actor_id=admin.id,actor_name=admin.name,action='data_export',object_type=kind,object_id=kind,after={'rows':len(rows),'fields':cols})
    await db.commit()
    return Response(output.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind}.csv"'})

@router.get('/business-export/{kind}.csv')
async def export_business(kind:str,student_id:str|None=None,admin=Depends(get_current_admin),db=Depends(get_db)):
    output=io.StringIO();w=SafeWriter(output);count=0
    if kind=='steps':
        w.writerow(['项目ID','项目名称','步骤ID','步骤名称','说明','满分','启用'])
        for p in (await db.execute(select(TrainingProject).order_by(TrainingProject.id))).scalars():
            for s in p.steps or []:
                w.writerow([p.id,p.name,s.get('id'),s.get('name'),s.get('description'),s.get('score'),s.get('enabled',True)]);count+=1
    elif kind=='mappings':
        w.writerow(['项目ID','项目名称','步骤ID','子能力ID','贡献分值'])
        for p in (await db.execute(select(TrainingProject).order_by(TrainingProject.id))).scalars():
            for step,subs in (p.ability_mapping or {}).items():
                definition=next((s for s in p.steps or [] if str(s['id'])==step), {})
                rules=p.scoring_rules or {}
                default=float(definition.get('score', 0)) * (1 if rules.get('scoring_mode')=='absolute' else float(definition.get('weight', 1)))
                if rules.get('scoring_mode')=='proportional':
                    default=float(rules.get('total_score', 0))*float(definition.get('weight', 0))/100
                from app.services.mapping_points import step_mapping_points
                points=step_mapping_points(rules,step,subs,default)
                for sub in subs:w.writerow([p.id,p.name,step,sub,points[sub]]);count+=1
    elif kind=='evaluations':
        w.writerow(['学生ID','学生姓名','大类能力ID','能力名称','达成值','达标阈值','达标状态'])
        if not student_id: raise HTTPException(400,'请选择学生范围，避免无界全量能力计算')
        student=await db.get(Student,student_id)
        if not student: raise HTTPException(404,'学生不存在')
        profile=await AbilityService(db).get_student_profile(student.id)
        for a in profile.radar_data if profile else []:
            d=a.model_dump() if hasattr(a,'model_dump') else a
            w.writerow([student.id,student.name,d.get('ability_id'),d.get('name'),d.get('score'),d.get('threshold'),'达标' if d.get('score',0)>=d.get('threshold',60) else '未达标']);count+=1
    elif kind=='report-summaries':
        w.writerow(['报告ID','学生ID','报告类型','标题','生成时间','摘要'])
        q=select(DiagnosticReport).order_by(DiagnosticReport.id)
        if student_id:q=q.where(DiagnosticReport.student_id==student_id)
        for report in (await db.execute(q)).scalars():
            w.writerow([report.id,report.student_id,report.report_type.value,report.title,report.generated_at,(report.content or '')[:500]]);count+=1
    else:raise HTTPException(404,'导出类型不存在')
    await record_audit(db,actor_id=admin.id,actor_name=admin.name,action='data_export',object_type=kind,object_id=student_id or kind,after={'rows':count})
    await db.commit()
    return Response(output.getvalue().encode('utf-8-sig'),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind}.csv"'})
