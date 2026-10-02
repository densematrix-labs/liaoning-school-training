"""Build internal traceability without committing the procurement source publicly."""
import csv,re,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
folder=root/'docs/release/internal'
source=folder/'采购需求基线_20260906.txt'
text=source.read_text().split('三、技术参数评分方法')[0]
rows=[]
for line in text.splitlines():
    match=re.match(r'^[▲●]?(\d\.\d\.\d)\s+(.+)$',line.strip())
    if match and match[1] not in {x[0] for x in rows}:rows.append((match[1],match[2]))
# The baseline comparison is evidence-based, not a declaration of final acceptance.
groups={
'1.1':('G02/G03/G04/G06','真实源适配和映射缺失','backend/app/services/production_data.py','接入代码完成；真库联调未完成：E06–E08'),
'1.2':('G04/G05/G06/G07','旧调度和导入运行演示路径','backend/app/services/operations_runtime.py; backend/app/routers/release.py','代码完成；真实 1000 条验收依赖 E08/E23'),
'2.1':('G07/G09/G10','项目/步骤配置缺完整验证和版本','backend/app/services/catalog.py','代码完成；校方规则确认 E03'),
'2.2':('G09/G10/G11','不完整状态/重复策略/历史规则边界不足','backend/app/services/production_data.py; backend/app/services/recalculation.py','代码完成；真实评分标准依赖 E03/E08'),
'2.3':('G10','已有明细/筛选/导出，源证据不足','backend/app/services/score.py; backend/app/routers/scores.py','功能存在并加固；真实样本对账未完成 E08'),
'3.1':('G07/G10/G11','配置及历史映射依据不足','backend/app/services/catalog.py; backend/app/services/ability.py','代码完成；培养方案/映射 E02/E04'),
'3.2':('G11/G12','个人/趋势/班级算法存在差异','backend/app/services/evaluation.py; backend/app/services/ability.py','统一计算与快照完成；教学正确性需 E02/E04'),
'3.3':('G11/G12','已有雷达/毕业判定，需真实规则及同口径','backend/app/routers/abilities.py; backend/app/routers/students.py','代码完成；至少五类真实能力和现场演示 E02/E08'),
'4.1':('G21/G22','供应商输出/调用管理不足，型号能力证据缺失','backend/app/services/ai_gateway.py','调用代码完成；真实模型能力和服务合同 E15/E16'),
'4.2':('G20/G21/G22/G23','报告范围、证据及失败边界不足','backend/app/services/report.py','代码完成；真实报告效果/20份 P95 验收未完成 E15/E23/E25'),
'4.3':('G23','已有个人报告查阅/下载，班级统计导出缺失','backend/app/routers/reports.py; backend/app/routers/students.py','查询/导出完成；真实报告内容依赖 E15/E25'),
'5.1':('G24/G25/G26','网页上传缺失、标准图未真正用于多图推理','frontend/src/components/EnvironmentUpload.tsx; backend/app/services/images.py','代码完成；标准图 E18；设备联调 E19/E20'),
'5.2':('G24/G26/G27/G28','图片结果结构、复核和真实校内传输不足','backend/app/services/environment.py; backend/app/services/environment_validation.py','代码完成；真实效果/200张/连续视频 E18/E25/E26'),
'6.1':('G12/G23/G25','已有学生门户，需真实数据和上传入口','frontend/src/pages/student; backend/app/routers/permissions.py','功能完成；真实初始化 E02–E05'),
'6.2':('G12/G23/G25/G28','已有教师门户，汇总口径/导出/复核边界不足','frontend/src/pages/teacher; backend/app/routers/students.py','功能完成；教师授权和实际演示 E05/E26'),
'6.3':('G05/G06/G07/G10/G26','批量基础管理/真实同步/版本不足','frontend/src/pages/admin/Release.tsx; backend/app/routers/release.py','代码完成；规则/数据/视频 E02–E08/E26'),
'6.4':('G13/G14/G15/G20','演示公开大屏和会话安全不足','backend/app/offline.py; backend/app/services/account_security.py','代码及越权回归完成；现场三角色验收 E05/E09'),
'7.1':('G04/G06/G07/G15','接口真实接入/文档/完整鉴权不足','docs/release/openapi.json; backend/app/routers/release.py','接口/文档完成；外部系统联调资料 E06/E09'),
'7.2':('G13/G15/G18/G21','密码/会话/凭据及调用数据保护不足','backend/app/services/auth.py; backend/app/services/ai_gateway.py','代码完成；HTTPS/真实数据出域许可 E13/E17'),
'7.3':('G16/G17/G18/G19','静态健康、审计/备份恢复不足','backend/app/services/operations_runtime.py; deploy/offline','代码及本地演练完成；现场备份介质/恢复演练 E22'),
'8.1':('G17/G20/G30/G34','已有短测不能代表目标服务器验收','scripts/release_smoke.py; docs/release/VERIFICATION.md','正式性能/24h及可能72h未完成：E10/E23–E25'),
'8.2':('G30/G31/G33','交付包/手册未跟上真实系统','deploy/offline; docs/release','包/文档完成状态看 VERIFICATION；现场实施/培训 E01–E26'),
'8.3':('G33','未冻结验收数据、无双方签署记录','docs/release/ACCEPTANCE.md','验收模板完成；实际验收未完成 E01/E08/E23–E26')}
with (folder/'requirements-traceability.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['参数编号','参数标题','差距ID','原有差距','实现/验证入口','当前状态及外部依赖'])
    for key,title in rows:
        detail=groups[key.rsplit('.',1)[0]]
        if key=='4.1.4':detail=('E15','未取得百万 token 模型能力证据','供应商证明+实际服务型号核验','未完成：不能用默认 qwen-plus 名称或模拟测试宣称达标')
        if key=='5.1.3':detail=('G24/E19/E20','摄像机型号/接口/事件关联未知','采集地址白名单+通用图片字节适配','通用入口完成；设备专有接口联调未完成')
        writer.writerow([key,title,*detail])
(folder/'source-manifest.json').write_text(json.dumps({'source':'项目本地老师意见修订版_20260906.docx','official_final_confirmed':False,'source_docx_sha256':hashlib.sha256((root/'docs/智能实训能力评估平台项目参数_老师意见修订版_20260906.docx').read_bytes()).hexdigest(),'extracted_text_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parameter_count':len(rows),'comparison_base':'e8d358b'},ensure_ascii=False,indent=2))
print('Mapped parameter count:',len(rows))
