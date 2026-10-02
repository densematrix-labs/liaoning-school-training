# 接口、数据字典和接入约定

完整机器可读接口：同目录 `openapi.json`（从当前应用生成，含路径、请求/响应 schema、参数与 HTTP 错误）。正式入口为 `/api/v1`，Authorization: Bearer access_token；refresh endpoint 仅接收 refresh_token。401 需重登，403 权限不足，400 业务数据错误，422 参数结构错误；错误体有 detail，容器响应附 x-request-id 以定位日志。所有受保护请求按当前数据库账号状态复核，不只相信 JWT 角色。

## 核心对象

- users：账号 ID、username、bcrypt password_hash、name、student/teacher/admin role；不输出口令哈希。
- majors/classes/students：专业、班级（teacher_id 为授权教师）、学生（user_id、student_no、class_id、major_id）。ID 是平台关联键，学号是对账字段，不按姓名猜身份。
- labs：实训室和标准图片入口；reference_images 支持多图及 enabled，environment_meta 保存每次实际使用的参考图。
- training_projects：步骤列表、scoring_rules、ability_mapping、max_score。步骤支持 enabled/weight/score/failed_score；步骤顺序即数组顺序。
- training_records：外部唯一 ID、学生、项目、原始步骤、完成时间。SystemSetting `source:记录ID` 保存源系统/源 ID/原始时间/批次/指纹/规则和映射快照。
- scores：总分、满分、每步骤原状态/规则/得分/关联子能力/失败原因。只从结构化原始记录计算，不由模型猜分。
- major_abilities/sub_abilities：分层能力、父子关系、权重与阈值；`state:*` 保存启停及补充编码。
- ability_profiles：当前持久计算结果；`ability_snapshot:*` 保存计算时间/所选成绩/规则/权重/阈值与结果。
- diagnostic_reports/report_tasks：单次/阶段正文与任务状态、发起人、时间、失败原因；`report_meta:*` 保存模型、数据范围、成绩集合及展示快照。
- environment_checks/environment_tasks/environment_reviews：现场图、AI 原始分项、参考图快照、人工复核和任务状态，均与 score/student/lab 关联。
- audit_logs/configuration_versions：谁在何时对何对象做何动作、结果/原因和前后值。
- mock_sync_tasks/mock_sync_exceptions：表名来自旧版本；release 用于真实同步任务及逐行隔离记录，**名称不表示真实导入仍生成 mock 数据**。
- system_settings：版本、来源证据、SSO 一次性状态、账号安全状态、调度、运维心跳等。保存在校内并随数据库加密备份。

## 评分与能力计算口径

有效步骤必须完整匹配，明确通过/未通过。步骤得分 = (通过分或失败分) × 权重；总分是步骤得分和；满分是有效步骤满分和。缺规则/未知状态/缺步骤均隔离。

子能力根据关联步骤的得分/满分作分值加权；大类按子能力权重汇总。未测试子能力贡献为零，不用“只平均测过的项”抬高毕业达标。默认不作时间衰减。重复策略 all/average 保留各次，latest 取最近一次，highest 取最高得分率；原记录不删除。项目和时间范围过滤先发生，再计算。毕业达标要求所有启用大类达到各自阈值。以上是实现默认口径，正式教学解释以校方确认规则为准。

阶段报告的 range_first_score 是指定范围第一条实训产生的能力值，range_change 是范围内最终汇总相对此基线的百分点变化，不是“学期开始前能力”。报告已生成后不随重算覆盖正文/当时成绩快照。

## 真实记录导入

每行一次完成实训，字段：

- source_record_id：来源系统中的稳定唯一 ID。
- student_no：与平台学生学号完全匹配。
- project_code：与 scoring_rules.code（未配置则项目 ID）匹配。
- completed_at：ISO8601，建议 `2026-10-01T08:30:00+08:00`。
- steps：JSON 对象，例如 `{"step-1":{"passed":true},"step-2":{"passed":false,"reason":"顺序错误"}}`。
- environment_image（可选）：图片 data URL 或管理员批准主机的抓拍地址。不提供则不会凭空生成环境判断。

同 source+source_record_id 及相同内容重复导入跳过；内容变化隔离，不能静默修改成绩。补齐错误数据后可按异常 ID 重试，使用原任务来源。单次 CSV/XLSX 1—5000 条、≤20MB，XLSX 解压大小受限；模板提供 UTF-8 BOM。

## MySQL 只读约定

通用适配器读取一行一次完成实训、steps JSON 的表/现有只读视图。映射必需 source_record_id、student_no、project_code、completed_at、steps、updated_at；游标为 updated_at+source_record_id，必须稳定可排序。表/列名只接受简单标识符，不执行用户 SQL。批次 1—5000 行，多页逐页检查点；错误行保存原始值后游标才能推进。

这不是对未知厂商 schema 的“万能适配”。若校方每步骤一行、多表关联、设备序列号代替学号、无法可靠判断实训完成，必须取得数据字典后完成适配，或由校方提供既有只读视图；不擅改对方数据库结构。

## 常用接口

- POST /auth/login、POST /auth/refresh、POST /auth/logout、GET /auth/me。
- GET /sso/status、GET /sso/login、GET /sso/callback、POST /sso/exchange。
- /release/catalog/{kind}：查询/新增；/{id} 更新；/import 文件预校验或导入；/release/templates/{kind}.csv 下载模板。
- /release/source 配置/读取；POST /release/source/sync；POST /release/records/import；POST /release/exceptions/{id}/retry。
- GET /admin/sync/history，GET /admin/sync/{id}/exceptions.csv。
- GET /scores/student/{id}、/scores/class/{id}、/scores/{id}、/scores/class/{id}/export.csv。
- GET /abilities/student/{id}、/trend、/snapshots；GET /students/classes/{id}/overview 与 /overview.csv。
- POST /reports/tasks，GET /reports/tasks/{id}；报告查询/下载精确路径见 openapi.json。
- POST /environment/tasks，GET /environment/tasks/{id}、/history/{student_id}；POST /environment/checks/{id}/review。
- POST /release/labs/{id}/reference，PUT /release/references/{id}（enabled/label）；GET /admin/operations/labs/{id}/reference-images。
- GET /release/audit、/release/status、/release/metrics；POST /release/connectivity、/release/backups。

字段和输出格式以随包 openapi.json 为准。业务接口可供另一个系统在授权下调用，但当前未提供无范围共享“万能管理员 token”；集成账号及数据边界须双方确认。
