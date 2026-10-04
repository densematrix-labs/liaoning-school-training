# 单容器离线部署与恢复

## 交付与前提

主包：`liaogui-offline-amd64-20261003.zip`。包含已构建镜像 `image.tar.gz`、SHA256SUMS、镜像元数据、依赖版本、源码提交号、安装/启动/停止/备份/恢复脚本和本文档。安装不执行 npm、pip、apt 或 docker pull。

目标：Ubuntu 20 及以上，64 位 x86（amd64），已安装且可用的 Docker Engine。建议 4 核、8GB 内存、至少 40GB 可用磁盘；这是部署建议，不是正式性能保证。ARM64、国产架构或裸机没有 Docker 时，需先按实际系统准备对应离线介质。不能把应用镜像宣称为任意 Ubuntu 裸机通用安装盘。Docker daemon 权限接近系统管理权限，由校方分配。

## 安装

1. 通过校方认可介质传入 zip，解压，保留原包及校验文件。
2. 进入解压目录执行 `bash preflight.sh`。SHA256SUMS 同时覆盖镜像、脚本和文档。
3. 执行 `bash install.sh`。默认创建 `site/`，随机生成管理员口令、JWT 密钥、备份密钥，只写入 `site/site.env`（0600），不输出到终端或聊天。
4. 默认监听 `127.0.0.1:8080`。管理员在服务器私下查看初始口令，通过校方 HTTPS 反向代理访问。经校方同意需要直接绑定局域网时，首次执行 `BIND_ADDRESS=校内服务器IP bash install.sh`。不自行打开公网入口。
5. `docker logs --tail 100 liaogui-training` 查看日志，`docker inspect --format '{{.State.Health.Status}}' liaogui-training` 查看健康。

所有脚本支持环境变量 `INSTALL_DIR`、`CONTAINER_NAME`、`DATA_DIR`、`BACKUP_DIR`、`PORT`、`BIND_ADDRESS`。更改后每次维护使用同一组值；建议写入校方运维记录。脚本不会执行 env 文件内容。

## 文件与进程

- 单镜像：FastAPI + 静态前端 + Python 依赖。启动入口 `app.offline:app`，单 uvicorn worker。
- `site/data/training.db`：业务库，含身份/原始数据/规则/任务/审计/图片内容。
- `site/backups/`：加密备份及校验和；可指定为独立挂载盘。不能只依赖和业务盘相同的物理磁盘。
- `site/site.env`：实施配置与密钥，不提交 Git、不发群聊、不放公开共享目录。
- 容器 UID 10001，根文件系统只读，/tmp 为临时盘，关闭额外 capabilities，限制 Docker 日志大小。
- pilot 不会创建演示学生；不能把 demo 数据卷切换成 pilot。旧库未标记时必须先备份、核实、迁移，不自动升级未知真实库。

## 配置顺序

普通使用者无需配置 API Key。供应商实施人员在服务器私下配置：

1. 按 `site.env.example` 设置校方数据库主机、端口、只读账号、库名和 CA；映射在“上线管理 → 校方数据源”配置。不要授予 INSERT/UPDATE/DELETE/DDL 权限。
2. AI 使用 OpenAI-compatible HTTPS 接口：`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`VLM_MODEL`。默认模型名只是历史默认值，不构成百万上下文合格证明；须选择已核验型号并完成真实样例测试。`AI_FALLBACK_ROUTES` 支持实施人员提供的后备配置；不能在网页暴露 Key。
3. 校园 SSO：确认 OIDC 后配置 `OIDC_ISSUER/CLIENT_ID/CLIENT_SECRET/REDIRECT_URI`，回调须 HTTPS；账号页面绑定 issuer+subject。默认拒绝未绑定身份，也不相信远端随意声明的本地管理员角色。
4. 摄像头抓拍只允许 `CAMERA_ALLOWED_HOSTS` 列出的主机；不跟随重定向。设备厂商自有 SDK/认证/事件关联需根据资料联调。没摄像头先用网页图片上传。
5. 修改 env 后 `bash stop.sh` 再按原绑定参数 `bash start.sh`。数据库内对象配置不需重启。校方反向代理对批量导入接口的读取超时建议设为至少 300 秒；普通查询与 AI 任务提交仍使用短请求。

## 备份

- 每天自动进行一次；默认保留 30 天，可设 `BACKUP_RETENTION_DAYS`（最低 7）。审计保留 `AUDIT_RETENTION_DAYS`，最低 180。
- 手动：`bash backup.sh` 或管理员“上线管理 → 运行与备份”。
- 内容：一致性 SQLite 快照、上传目录（存在时）、数据库内配置、加密运行配置 `runtime-config.json`、manifest 与数据库 SHA256。
- 运行配置可能含 DB/AI/SSO 凭据，因此整个归档加密。**备份解密密钥必须另存安全介质**；丢失密钥不能恢复。备份文件本身不替代密钥保管。
- 保留应用镜像与 SOURCE_COMMIT，恢复时优先使用生成备份的对应版本。

## 恢复及回退

`bash restore.sh /绝对路径/backup-xxx.enc /新的空目录` 在无网络临时容器内解密，拒绝覆盖非空目录，校验 SHA256 与 SQLite 完整性，输出 users/students/scores 行数。

确认后停止原容器，以 `DATA_DIR=/新的空目录 bash start.sh` 启动。原数据目录保留不动。运行配置在恢复目录中的 `runtime-config.json`，由实施人员核对后恢复到 site.env；不要将旧网络/SSO地址不加检查地覆盖新环境。恢复脚本不自动切换线上数据。

升级：旧版本先备份 → 保留旧镜像、旧 env、旧数据 → docker load 新包 → 停旧容器 → 启动新版本 → 登录/记录数/评分/日志核验。失败时回到旧镜像及升级前数据快照；不要假定任意版本数据库可逆迁移。当前安装脚本遇同名容器直接拒绝，不强制删容器。

## 断网行为与排障

- 本地登录、基础配置、真实文件导入、确定性评分、历史查询、已生成报告下载不依赖外网。
- AI 不可达时任务失败/可重提，不替换历史业务数据。
- SSO 依赖校园认证服务；服务不可达时使用预置本地运维账号（权限仍受审计）。
- “数据库 connected”只表示本地库；“验证校方数据库与 AI 连通性”才会探测外部依赖。模型列表可达不等于推理质量/P95 已验收。
- source 同步失败看运行页与服务器日志；逐行错误到同步历史导出；修正原始行后回放。源 ID 相同而内容改变必须人工确认，不能当普通重复自动覆盖。
- 没有标准状态图片/图片错误/成绩关联不符会明确报错。
- 任务失败后先查看原因再重提；服务重启将运行中任务标为中断，pending 继续处理。

## 正式验收边界

本地模拟签名 OIDC 不等于学校 SSO 已接通；模拟模型回包测试不等于 AI 效果和耗时已验收；Docker Desktop 的 linux/amd64 断网运行不等于实际 Ubuntu 服务器验收。按另行私下交付的差距清单收齐条件后执行正式验收。
