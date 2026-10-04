"""Synthetic display fixtures only. Refuses any non-visual test container."""
import asyncio,base64,io,os
from datetime import datetime
from PIL import Image,ImageDraw
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.lab import Lab,EnvironmentCheck
from app.models.training import Score
from app.models.report import DiagnosticReport,ReportType
from app.services.production_data import put_setting
assert os.getenv('VISUAL_FIXTURE_ALLOWED')=='true'
async def main():
    image=Image.new('RGB',(640,360),'#174d7a');draw=ImageDraw.Draw(image)
    draw.rectangle((40,70,600,290),outline='#64ecff',width=3);draw.text((65,110),'SYNTHETIC UI FIXTURE - NOT SCHOOL PHOTO',fill='white');draw.rectangle((100,170,400,260),fill='#286e8c')
    out=io.BytesIO();image.save(out,format='PNG');uri='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()
    async with AsyncSessionLocal() as db:
        score=(await db.execute(select(Score).where(Score.student_id=='perf-student-0').limit(1))).scalar_one()
        assert score,'Requires synthetic smoke seed'
        lab=await db.get(Lab,'perf-lab-0');lab.reference_image_url=uri
        if not await db.get(EnvironmentCheck,'visual-fixture-environment'):
            details={k:{'score':20,'max_score':25,'issues':['Synthetic visual acceptance fixture'], 'confidence':.9} for k in ['equipment_placement','surface_cleanliness','safety_compliance','environmental_hygiene']}
            details['__suggestions__']=['仅验证页面、复核与证据显示，不是模型效果结论。']
            db.add(EnvironmentCheck(id='visual-fixture-environment',student_id='perf-student-0',lab_id=lab.id,score_id=score.id,uploaded_image_url=uri,total_score=80,details=details,summary='合成视觉验收记录：供教师页面复核交互测试。',checked_at=datetime.utcnow()))
            await put_setting(db,'environment_meta:visual-fixture-environment',{'reference_images':[uri],'needs_review':True,'fixture':True})
        if not await db.get(DiagnosticReport,'visual-fixture-report'):
            content='> 合成视觉验收样本：不是实际模型生成，不用于教学或AI效果验收。\n\n'+ '\n\n'.join('## '+title+'\n\n'+body for title,body in [
                ('基本信息','合成学生0；合成项目0；仅验证排版和证据跳转。'),('成绩概况',f'该条结构化成绩为 {score.total_score} 分。'),('未通过步骤','以关联实训原始步骤记录为准。'),('相关薄弱能力','此为合成样例，不作真实教学判断。'),('环境规范情况','关联的合成图片用于页面显示与复核测试。'),('改进建议','使用真实老师确认的规则和照片完成正式业务验收。')])
            db.add(DiagnosticReport(id='visual-fixture-report',student_id='perf-student-0',report_type=ReportType.SINGLE,title='合成项目0 · 浏览器视觉验收样本',content=content,score_id=score.id,generated_at=datetime.utcnow()))
        await db.commit()
    print('Synthetic report/environment display fixtures ready; no AI call')
asyncio.run(main())
