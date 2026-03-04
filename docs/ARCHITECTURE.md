# 辽轨智能实训能力评估平台 - 系统架构设计

## 1. 架构决策记录 (ADR)

### ADR-001: 架构风格选择

**状态**: Accepted

**背景**: 
这是一个面向单客户（铁路职业学院）的 B2B SaaS Demo 项目。需要在短时间内（1-2 周）交付可演示的完整功能。团队规模小（1-2 人开发），后期可能扩展为标准产品。

**决策**:
采用 **Modular Monolith** 架构，使用 Clean Architecture 分层。

**理由**:
1. 团队规模 < 10 人，不需要微服务
2. 单一数据库（校方 MySQL）作为数据源
3. Demo 阶段需要快速迭代，monolith 部署简单
4. Clean Architecture 分层保证代码可维护性，未来可拆分

**后果**:
- ✅ 开发速度快，部署简单
- ✅ 代码结构清晰，可测试
- ⚠️ 未来需拆分时有一定工作量（但 Clean Architecture 减轻了这个问题）

### ADR-002: 数据库选择

**状态**: Accepted

**背景**:
校方已有 MySQL 数据库存储实训操作记录。需要决定平台自身数据的存储方案。

**决策**:
- **外部数据源**: 校方 MySQL（只读同步）
- **平台数据**: SQLite（Demo 阶段）→ PostgreSQL（生产阶段）

**理由**:
1. Demo 阶段用 SQLite 可以打包单文件演示，部署简单
2. SQLAlchemy ORM 保证切换到 PostgreSQL 无缝
3. 校方数据保持只读，通过定时任务同步

### ADR-003: AI 服务集成

**状态**: Accepted

**背景**:
需要 AI 能力支持两个功能：
1. 图像检测（实训室环境规范检查）
2. 自然语言生成（诊断报告）

**决策**:
通过 DenseMatrix LLM Proxy（`llm-proxy.densematrix.ai`）调用外部模型，首选 `gemini-3-flash-preview`。

**理由**:
1. 统一入口，简化 API Key 管理
2. 支持 Vision + Text，一个模型覆盖两个需求
3. 成本可控（flash 系列便宜）

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React + Vite)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  学生门户     │  │  教师门户     │  │  大屏展示     │  │  管理后台     │     │
│  │  - 成绩查看   │  │  - 班级数据   │  │  - 实时数据   │  │  - 能力配置   │     │
│  │  - 能力图谱   │  │  - 统计分析   │  │  - 图表展示   │  │  - 映射管理   │     │
│  │  - 诊断报告   │  │  - 导出功能   │  │  - 动态刷新   │  │  - 用户管理   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTP/REST
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Middleware: Auth, CORS, Logging, Error Handling, Rate Limiting        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │
│  │ /students │  │ /teachers │  │ /training │  │ /reports  │  │ /env-check│ │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────┐               ┌───────────────┐               ┌───────────────┐
│ Use Cases     │               │ Domain        │               │ Infrastructure│
│ (Application) │               │ (Entities)    │               │ (Adapters)    │
│               │               │               │               │               │
│ • 成绩计算     │──────────────▶│ • Student     │◀──────────────│ • SQLite/PG   │
│ • 能力映射     │               │ • Training    │               │ • LLM Proxy   │
│ • 报告生成     │               │ • Ability     │               │ • File Storage│
│ • 环境检查     │               │ • Report      │               │ • MySQL Sync  │
│ • 数据同步     │               │ • EnvCheck    │               │               │
└───────────────┘               └───────────────┘               └───────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │           External Services           │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐│
                    │  │校方MySQL│  │LLM Proxy│  │ Storage ││
                    │  │(只读)   │  │(AI能力) │  │ (图片)  ││
                    │  └─────────┘  └─────────┘  └─────────┘│
                    └───────────────────────────────────────┘
```

---

## 3. 目录结构（Clean Architecture）

```
liaoning-school-training/
├── docs/
│   ├── ARCHITECTURE.md          # 架构设计文档
│   ├── API.md                   # API 文档
│   └── PROJECT-BRIEF.md         # 项目任务书
├── backend/
│   ├── app/
│   │   ├── domain/              # 领域层 (Entities)
│   │   │   ├── entities/
│   │   │   │   ├── student.py
│   │   │   │   ├── teacher.py
│   │   │   │   ├── training_record.py
│   │   │   │   ├── ability.py
│   │   │   │   └── report.py
│   │   │   ├── value_objects/
│   │   │   │   ├── ability_score.py
│   │   │   │   └── training_step.py
│   │   │   └── interfaces/      # 抽象接口 (Ports)
│   │   │       ├── student_repository.py
│   │   │       ├── training_repository.py
│   │   │       ├── ai_service.py
│   │   │       └── sync_service.py
│   │   ├── use_cases/           # 应用层 (Use Cases)
│   │   │   ├── calculate_score.py
│   │   │   ├── generate_ability_map.py
│   │   │   ├── generate_report.py
│   │   │   ├── check_environment.py
│   │   │   └── sync_training_data.py
│   │   ├── adapters/            # 适配器层 (Adapters)
│   │   │   ├── repositories/
│   │   │   │   ├── sqlite_student_repo.py
│   │   │   │   └── sqlite_training_repo.py
│   │   │   ├── services/
│   │   │   │   ├── llm_proxy_service.py
│   │   │   │   └── mysql_sync_service.py
│   │   │   └── controllers/
│   │   │       ├── student_controller.py
│   │   │       ├── training_controller.py
│   │   │       ├── report_controller.py
│   │   │       └── env_check_controller.py
│   │   ├── infrastructure/      # 基础设施层
│   │   │   ├── database.py
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── metrics.py
│   │   └── main.py              # FastAPI 入口
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── alembic/                 # 数据库迁移
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # 通用组件
│   │   ├── pages/
│   │   │   ├── student/         # 学生端页面
│   │   │   ├── teacher/         # 教师端页面
│   │   │   ├── dashboard/       # 大屏展示
│   │   │   └── admin/           # 管理后台
│   │   ├── lib/
│   │   │   ├── api.ts           # API 调用
│   │   │   └── utils.ts
│   │   ├── stores/              # 状态管理 (Zustand)
│   │   └── locales/             # i18n
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
├── mock-data/                   # Mock 数据
│   ├── students.json
│   ├── teachers.json
│   ├── abilities.json
│   ├── training_records.json
│   └── images/                  # AI 生成的实训室照片
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── deploy.yml
└── README.md
```

---

## 4. 数据模型设计

### 4.1 能力体系

```python
# 大类能力
class MajorAbility:
    id: str
    name: str          # 如 "安全操作能力"
    description: str
    weight: float      # 权重 (0-1)

# 子能力
class SubAbility:
    id: str
    major_ability_id: str  # FK
    name: str          # 如 "安全防护穿戴"
    description: str
    weight: float

# 能力映射表
class AbilityMapping:
    training_step_id: str  # FK
    sub_ability_id: str    # FK
```

### 4.2 实训数据

```python
# 实训室
class TrainingRoom:
    id: str
    name: str          # 如 "机车模拟驾驶室"
    description: str
    standard_image_url: str  # 标准状态照片

# 实训项目
class TrainingProject:
    id: str
    room_id: str       # FK
    name: str          # 如 "机车启动与制动操作"
    description: str

# 实训步骤
class TrainingStep:
    id: str
    project_id: str    # FK
    sequence: int      # 步骤序号
    name: str          # 如 "确认制动系统状态"
    description: str
    score_weight: float

# 实训记录
class TrainingRecord:
    id: str
    student_id: str
    project_id: str
    step_results: List[StepResult]  # 每步骤的 pass/fail
    total_score: float
    created_at: datetime
    env_check_result: Optional[EnvCheckResult]

class StepResult:
    step_id: str
    passed: bool
    timestamp: datetime
```

### 4.3 学生能力图谱

```python
# 学生能力快照
class StudentAbilitySnapshot:
    student_id: str
    major_ability_id: str
    score: float           # 0-100
    training_count: int    # 累计实训次数
    updated_at: datetime

# 毕业达标评估
class GraduationAssessment:
    student_id: str
    total_progress: float  # 0-100
    weak_abilities: List[str]  # 薄弱能力 ID
    assessment_date: datetime
```

### 4.4 诊断报告

```python
class DiagnosisReport:
    id: str
    student_id: str
    report_type: str       # "single" | "periodic"
    training_record_id: Optional[str]  # 单次报告关联
    period_start: Optional[datetime]   # 阶段报告
    period_end: Optional[datetime]
    content: str           # AI 生成的报告内容
    created_at: datetime
```

### 4.5 环境检查

```python
class EnvCheckResult:
    id: str
    training_record_id: str
    uploaded_image_url: str
    standard_image_url: str
    ai_analysis: dict      # AI 返回的分析结果
    issues: List[str]      # 发现的问题
    passed: bool
    created_at: datetime
```

---

## 5. API 设计

### 5.1 学生端 API

```
GET  /api/v1/students/me                    # 获取当前学生信息
GET  /api/v1/students/me/training-records   # 获取实训记录列表
GET  /api/v1/students/me/training-records/{id}  # 获取单次实训详情
GET  /api/v1/students/me/ability-map        # 获取能力图谱
GET  /api/v1/students/me/reports            # 获取诊断报告列表
GET  /api/v1/students/me/reports/{id}       # 获取报告详情
GET  /api/v1/students/me/graduation-progress  # 获取毕业进度
```

### 5.2 教师端 API

```
GET  /api/v1/teachers/me/classes                # 获取管理的班级
GET  /api/v1/teachers/classes/{id}/students     # 获取班级学生列表
GET  /api/v1/teachers/classes/{id}/statistics   # 获取班级统计
GET  /api/v1/teachers/students/{id}/details     # 获取学生详情
GET  /api/v1/teachers/export/class/{id}         # 导出班级数据
```

### 5.3 大屏展示 API

```
GET  /api/v1/dashboard/overview             # 全局概览数据
GET  /api/v1/dashboard/realtime             # 实时实训数据
GET  /api/v1/dashboard/ability-distribution # 能力分布统计
GET  /api/v1/dashboard/training-trend       # 实训趋势图
```

### 5.4 实训与 AI API

```
POST /api/v1/training/env-check             # 上传照片进行环境检查
     Body: { image: base64, room_id: string }
     Response: { passed: bool, issues: [], analysis: {} }

POST /api/v1/training/generate-report       # 生成诊断报告
     Body: { student_id: string, type: "single"|"periodic", training_record_id?: string }
     Response: { report_id: string, content: string }
```

### 5.5 管理端 API

```
GET/POST/PUT/DELETE /api/v1/admin/abilities      # 能力体系管理
GET/POST/PUT/DELETE /api/v1/admin/training-rooms # 实训室管理
GET/POST/PUT/DELETE /api/v1/admin/mappings       # 能力映射管理
POST /api/v1/admin/sync                          # 手动触发数据同步
```

---

## 6. AI 集成设计

### 6.1 环境检查 Prompt

```python
ENV_CHECK_PROMPT = """
你是一个实训室环境检查专家。请对比以下两张图片：
1. 标准状态照片（实训室应有的整洁状态）
2. 待检查照片（学生实训后的实际状态）

请检查以下几个方面：
- 器材归位：所有工具和设备是否放回原位
- 台面整洁：工作台面是否清理干净
- 杂物遗留：是否有垃圾、遗留物品
- 安全隐患：是否存在可能的安全问题

输出格式（JSON）：
{
  "passed": true/false,
  "overall_score": 0-100,
  "categories": {
    "equipment_placement": { "score": 0-100, "issues": ["具体问题..."] },
    "surface_cleanliness": { "score": 0-100, "issues": [] },
    "debris_check": { "score": 0-100, "issues": [] },
    "safety_check": { "score": 0-100, "issues": [] }
  },
  "summary": "整体评价..."
}
"""
```

### 6.2 诊断报告 Prompt

```python
DIAGNOSIS_REPORT_PROMPT = """
你是一位经验丰富的职业教育导师。请基于以下学生数据生成个性化的诊断报告。

学生信息：
{student_info}

能力评估数据：
{ability_data}

实训历史记录：
{training_history}

请生成一份包含以下内容的报告（使用中文，语言要专业但易懂）：

1. **能力现状总结**（100-150字）
   - 整体能力水平评价
   - 突出的优势能力

2. **薄弱环节分析**（150-200字）
   - 具体指出哪些能力需要提升
   - 分析可能的原因

3. **个性化提升建议**（200-250字）
   - 针对每个薄弱点提供具体、可操作的建议
   - 推荐的练习方法和资源

4. **下一阶段目标**（50-100字）
   - 设定短期（1周）和中期（1月）目标
   - 预期达成的能力提升

请确保建议是具体、可操作的，避免泛泛而谈。
"""
```

---

## 7. 大屏展示设计

### 7.1 布局规划（1920x1080）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         辽轨智能实训能力评估平台                               │
│                            2026-03-04 00:45:30                               │
├───────────────────────┬──────────────────────────┬───────────────────────────┤
│                       │                          │                           │
│   今日实训概览         │    能力分布雷达图         │    实训趋势图              │
│   ┌─────────────────┐ │    ┌────────────────┐    │    ┌─────────────────────┐│
│   │ 今日实训: 45 人  │ │    │    ◇ 安全操作   │    │    │  ▃▅▇█▆▄▂▁▂▄▆▇█▆▃   ││
│   │ 合格率: 87.5%   │ │    │  ◇       ◇     │    │    │  实训人次变化趋势    ││
│   │ 在训人数: 12    │ │    │ ◇         ◇    │    │    └─────────────────────┘│
│   │ 环境检查: 38/45 │ │    │   ◇     ◇      │    │                           │
│   └─────────────────┘ │    └────────────────┘    │                           │
│                       │                          │                           │
├───────────────────────┴──────────────────────────┴───────────────────────────┤
│                                                                              │
│   实时实训动态                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │ 09:32  张三(机电2301) 完成【机车启动操作】✅ 92分                        │  │
│   │ 09:28  李四(机电2302) 开始【电气系统检修】⏳                            │  │
│   │ 09:25  王五(机电2301) 完成【走行部检修】✅ 85分                          │  │
│   │ 09:20  赵六(机电2303) 环境检查通过 ✅                                    │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├─────────────────────────────────────┬────────────────────────────────────────┤
│                                     │                                        │
│   各班级能力对比                     │   预警信息                              │
│   ┌───────────────────────────────┐ │   ┌────────────────────────────────┐  │
│   │ █████████ 机电2301 (78.5)     │ │   │ ⚠️ 张伟 - 安全操作能力低于60%    │  │
│   │ ████████  机电2302 (75.2)     │ │   │ ⚠️ 李明 - 连续3次实训未通过      │  │
│   │ ███████   机电2303 (71.8)     │ │   │ ⚠️ 实训室2 - 今日环境检查异常    │  │
│   └───────────────────────────────┘ │   └────────────────────────────────┘  │
│                                     │                                        │
└─────────────────────────────────────┴────────────────────────────────────────┘
```

### 7.2 数据刷新策略

| 数据区域 | 刷新频率 | 方式 |
|---------|---------|------|
| 今日概览 | 30s | Polling |
| 实时动态 | 10s | Polling |
| 能力分布 | 5min | Polling |
| 趋势图 | 1min | Polling |
| 预警信息 | 30s | Polling |

---

## 8. 安全与性能

### 8.1 认证方案

Demo 阶段采用简化方案：
- 学生/教师：学号/工号 + 密码（Mock 数据）
- 管理员：固定账号（demo/demo123）
- JWT Token（24h 有效期）

### 8.2 性能目标

| 指标 | 目标值 |
|-----|--------|
| API 响应时间 | < 500ms (p95) |
| 大屏渲染 | < 2s 首屏 |
| AI 报告生成 | < 10s |
| 环境检查 | < 8s |

### 8.3 监控

- Prometheus Metrics 导出
- Health Check Endpoint
- 错误日志集中收集

---

## 9. 部署架构

```
                     ┌──────────────────────┐
                     │   Cloudflare DNS     │
                     │ shixun.demo.dm.ai    │
                     │   (proxied=false)    │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │   Let's Encrypt      │
                     │   SSL Certificate    │
                     └──────────┬───────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    langsheng (39.109.116.180)                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                        Nginx                             │  │
│  │  - HTTPS termination                                     │  │
│  │  - Reverse proxy                                         │  │
│  │  - Static file serving                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│           ┌──────────────────┴──────────────────┐             │
│           ▼                                      ▼             │
│  ┌─────────────────┐                    ┌─────────────────┐   │
│  │   Frontend      │                    │   Backend       │   │
│  │   (Nginx)       │                    │   (FastAPI)     │   │
│  │   Port: 3080    │                    │   Port: 8080    │   │
│  └─────────────────┘                    └─────────────────┘   │
│                                                  │             │
│                                                  ▼             │
│                                         ┌─────────────────┐   │
│                                         │   SQLite DB     │   │
│                                         │   /data/app.db  │   │
│                                         └─────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## 10. 开发计划

| 阶段 | 内容 | 预计时间 |
|-----|------|---------|
| Phase 1 | 架构设计 + Mock 数据生成 | 0.5 天 |
| Phase 2 | 后端核心 API | 1 天 |
| Phase 3 | 前端学生/教师端 | 1 天 |
| Phase 4 | 大屏展示 | 0.5 天 |
| Phase 5 | AI 集成（环境检查 + 报告） | 0.5 天 |
| Phase 6 | 测试 + 部署 | 0.5 天 |

**总计**: 约 4 天

---

*文档版本: v1.0*
*创建时间: 2026-03-04*
*作者: Pal (DenseMatrix AI)*
