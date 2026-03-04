# 系统架构设计文档

**项目名称**: 辽轨智能实训能力评估平台  
**版本**: v1.0  
**设计日期**: 2026-03-04  
**设计者**: DenseMatrix AI Agent (Pal)

---

## 一、系统概述

### 1.1 系统定位

本平台是面向职业院校的智能实训能力评估系统，核心价值在于：
- **自动化成绩分析**：从现有实训设备数据库自动读取学生操作结果并计算成绩
- **能力图谱构建**：将实训表现映射至专业能力体系，生成可视化能力雷达图
- **AI 驱动诊断**：借助 VLM 进行实训室环境检查，借助 LLM 生成个性化诊断报告
- **统一信息门户**：为学生和教师提供便捷的数据查阅与报告下载入口

### 1.2 技术栈选型

| 层级 | 技术选择 | 理由 |
|------|----------|------|
| **前端** | React + Vite + TypeScript + Tailwind | 现代前端标准，开发效率高 |
| **后端** | Python FastAPI | AI 生态好，异步性能强 |
| **数据库** | PostgreSQL | 稳定可靠，JSON 支持好 |
| **缓存** | Redis | 热数据缓存、Session 存储 |
| **AI 服务** | DenseMatrix LLM Proxy | 统一模型访问入口 |
| **部署** | Docker Compose | 单机部署，运维简单 |
| **监控** | Prometheus + Grafana | 标准化监控方案 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户接入层                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │   学生 Web     │  │   教师 Web     │  │   大屏展示     │            │
│  │  (查看成绩)    │  │ (管理/分析)    │  │  (实时监控)    │            │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘            │
└──────────┼───────────────────┼───────────────────┼──────────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API 网关 (Nginx)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  HTTPS 终端 | 负载均衡 | 限流 | 静态资源服务 | WebSocket 代理    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           服务层 (FastAPI)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  用户认证    │  │  成绩管理    │  │  能力分析    │  │  报告生成  │  │
│  │  Service     │  │  Service     │  │  Service     │  │  Service   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  数据同步    │  │  环境检查    │  │  大屏数据    │  │  通知推送  │  │
│  │  Service     │  │  Service     │  │  Service     │  │  Service   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│   数据存储层     │  │   AI 服务层      │  │     外部数据源           │
│  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────────────┐  │
│  │ PostgreSQL │  │  │  │ LLM Proxy  │  │  │  │ 校方 MySQL DB      │  │
│  │ (业务数据)  │  │  │  │ (诊断报告) │  │  │  │ (实训设备数据)     │  │
│  └────────────┘  │  │  └────────────┘  │  │  └────────────────────┘  │
│  ┌────────────┐  │  │  ┌────────────┐  │  └──────────────────────────┘
│  │   Redis    │  │  │  │ VLM API    │  │
│  │ (缓存/会话) │  │  │  │ (图像检测) │  │
│  └────────────┘  │  │  └────────────┘  │
│  ┌────────────┐  │  └──────────────────┘
│  │ 文件存储    │  │
│  │ (报告/图片) │  │
│  └────────────┘  │
└──────────────────┘
```

### 2.2 数据流架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据采集与处理流程                               │
└─────────────────────────────────────────────────────────────────────────┘

1. 实训数据同步
   校方 MySQL ──定时任务(每日)──→ 数据同步服务 ──→ PostgreSQL

2. 成绩计算
   PostgreSQL(原始数据) ──→ 成绩计算服务 ──→ PostgreSQL(成绩记录)

3. 能力分析
   PostgreSQL(成绩记录) ──→ 能力分析服务 ──→ 能力图谱(JSON)

4. 环境检查
   学生上传照片 ──→ VLM 检测服务 ──→ 检查结果 ──→ PostgreSQL

5. 诊断报告
   成绩+能力+检查 ──→ LLM 报告服务 ──→ PDF 报告 ──→ 文件存储

6. 大屏数据
   PostgreSQL ──→ 大屏数据服务 ──→ Redis(缓存) ──→ WebSocket 推送
```

---

## 三、模块设计

### 3.1 用户认证模块

**功能**：用户登录、权限控制、会话管理

```python
# 用户角色
class UserRole(str, Enum):
    STUDENT = "student"      # 学生：查看自己的成绩和报告
    TEACHER = "teacher"      # 教师：查看班级数据、导出报告
    ADMIN = "admin"          # 管理员：系统配置、用户管理

# 认证方式
- 一期：独立账号体系（JWT Token）
- 后续：可对接校园网统一认证
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/logout` | POST | 用户登出 |
| `/api/auth/me` | GET | 获取当前用户信息 |
| `/api/auth/refresh` | POST | 刷新 Token |

### 3.2 数据同步模块

**功能**：从校方 MySQL 同步实训数据

```python
# 同步配置
class SyncConfig:
    source_db_url: str      # 校方 MySQL 连接串
    sync_interval: str      # 同步频率 (cron 表达式)
    tables: List[str]       # 需要同步的表
    
# 同步策略
- 增量同步：基于 updated_at 字段
- 全量同步：每周一次，用于数据校验
- 失败重试：最多 3 次，指数退避
```

**数据映射**：
```
校方数据库                      本地数据库
────────────────────────────────────────────────
training_records           →    raw_training_records
student_info              →    students
equipment_status          →    equipment_operations
```

### 3.3 成绩管理模块

**功能**：计算单次实训成绩、查询历史成绩

**评分逻辑**：
```python
def calculate_score(training_record: TrainingRecord, rules: ScoringRules) -> Score:
    """
    计算单次实训成绩
    
    1. 获取该实训的所有操作步骤
    2. 对每个步骤：
       - 如果通过：得满分
       - 如果未通过：根据规则扣分
    3. 累加得到总分
    4. 标注未通过步骤及其对应的能力项
    """
    total_score = 0
    failed_steps = []
    
    for step in training_record.steps:
        step_rule = rules.get_rule(step.step_id)
        if step.passed:
            total_score += step_rule.full_score
        else:
            total_score += step_rule.full_score - step_rule.deduction
            failed_steps.append({
                "step_id": step.step_id,
                "step_name": step_rule.name,
                "deduction": step_rule.deduction,
                "related_abilities": step_rule.abilities
            })
    
    return Score(
        total=total_score,
        max_score=rules.max_score,
        passed_steps=len(training_record.steps) - len(failed_steps),
        failed_steps=failed_steps
    )
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/scores/` | GET | 获取成绩列表（支持筛选） |
| `/api/scores/{id}` | GET | 获取单次成绩详情 |
| `/api/scores/student/{student_id}` | GET | 获取学生历史成绩 |
| `/api/scores/class/{class_id}` | GET | 获取班级成绩汇总 |

### 3.4 能力分析模块

**功能**：构建学生能力图谱、评估毕业达标情况

**能力体系结构**：
```yaml
# 示例：铁路运输专业能力体系
abilities:
  - id: safety
    name: 安全操作能力
    weight: 0.25
    sub_abilities:
      - id: safety_awareness
        name: 安全意识
      - id: emergency_response
        name: 应急处理
      - id: protective_equipment
        name: 防护装备使用
        
  - id: equipment
    name: 设备使用能力
    weight: 0.25
    sub_abilities:
      - id: signal_operation
        name: 信号设备操作
      - id: communication_device
        name: 通信设备使用
      - id: maintenance_tool
        name: 维护工具使用
        
  - id: procedure
    name: 规程执行能力
    weight: 0.25
    sub_abilities:
      - id: standard_process
        name: 标准流程执行
      - id: documentation
        name: 文档记录
      - id: reporting
        name: 汇报沟通
        
  - id: professional
    name: 专业技术能力
    weight: 0.25
    sub_abilities:
      - id: fault_diagnosis
        name: 故障诊断
      - id: parameter_setting
        name: 参数设置
      - id: quality_inspection
        name: 质量检验
```

**能力计算逻辑**：
```python
def calculate_ability_profile(student_id: str, scores: List[Score]) -> AbilityProfile:
    """
    计算学生能力图谱
    
    1. 汇总所有实训成绩中的能力得分
    2. 计算每个子能力的平均掌握度
    3. 汇总到大类能力
    4. 生成雷达图数据
    5. 评估毕业达标情况
    """
    ability_scores = defaultdict(list)
    
    for score in scores:
        for step in score.all_steps:
            for ability_id in step.related_abilities:
                ability_scores[ability_id].append(
                    step.score / step.max_score  # 归一化
                )
    
    # 计算各能力平均值
    ability_averages = {
        aid: sum(scores) / len(scores) 
        for aid, scores in ability_scores.items()
    }
    
    # 汇总到大类
    major_abilities = aggregate_to_major(ability_averages)
    
    # 生成雷达图数据
    radar_data = generate_radar(major_abilities)
    
    # 毕业达标判断（所有大类能力 >= 0.6）
    graduation_ready = all(v >= 0.6 for v in major_abilities.values())
    
    return AbilityProfile(
        student_id=student_id,
        sub_abilities=ability_averages,
        major_abilities=major_abilities,
        radar_data=radar_data,
        graduation_ready=graduation_ready,
        updated_at=datetime.now()
    )
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/abilities/student/{student_id}` | GET | 获取学生能力图谱 |
| `/api/abilities/class/{class_id}` | GET | 获取班级能力分布 |
| `/api/abilities/radar/{student_id}` | GET | 获取雷达图数据 |

### 3.5 环境检查模块

**功能**：AI 检测实训室环境规范性

**VLM 检测流程**：
```python
async def check_lab_environment(
    uploaded_image: bytes,
    lab_id: str,
    reference_image_url: str
) -> EnvironmentCheckResult:
    """
    使用 VLM 检测实训室环境
    
    1. 获取该实训室的标准照片
    2. 构建 VLM prompt
    3. 调用 VLM API 进行对比分析
    4. 解析结果
    """
    
    prompt = f"""
你是一个实训室环境检查专家。请对比以下两张图片：
- 图片1（标准状态）：实训室的标准整理状态
- 图片2（当前状态）：学生实训后的当前状态

请检查以下几个方面，并给出评分（0-100）和具体问题：

1. **器材归位**（30分）
   - 工具是否放回指定位置
   - 设备是否归位整齐

2. **台面整洁**（30分）
   - 工作台是否清理干净
   - 是否有残留物品

3. **安全规范**（20分）
   - 电源是否关闭
   - 危险物品是否妥善存放

4. **环境卫生**（20分）
   - 地面是否干净
   - 是否有垃圾

请以 JSON 格式返回结果：
{{
  "total_score": <总分>,
  "categories": {{
    "equipment_placement": {{"score": <分数>, "issues": [<问题列表>]}},
    "surface_cleanliness": {{"score": <分数>, "issues": [<问题列表>]}},
    "safety_compliance": {{"score": <分数>, "issues": [<问题列表>]}},
    "environmental_hygiene": {{"score": <分数>, "issues": [<问题列表>]}}
  }},
  "summary": "<整体评价>"
}}
"""
    
    # 调用 LLM Proxy
    response = await llm_client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": reference_image_url}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(uploaded_image).decode()}"}}
                ]
            }
        ]
    )
    
    result = json.loads(response.choices[0].message.content)
    return EnvironmentCheckResult(**result)
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/environment/check` | POST | 上传照片进行检查 |
| `/api/environment/reference/{lab_id}` | GET | 获取实训室标准照片 |
| `/api/environment/history/{student_id}` | GET | 获取学生环境检查历史 |

### 3.6 诊断报告模块

**功能**：生成个性化诊断报告

**报告生成流程**：
```python
async def generate_diagnostic_report(
    student_id: str,
    report_type: ReportType  # single（单次）或 periodic（阶段性）
) -> DiagnosticReport:
    """
    生成诊断报告
    
    1. 收集相关数据
    2. 构建 LLM prompt
    3. 生成报告内容
    4. 渲染为 PDF
    """
    
    # 收集数据
    student = await get_student(student_id)
    scores = await get_student_scores(student_id, report_type)
    ability_profile = await get_ability_profile(student_id)
    env_checks = await get_environment_checks(student_id)
    
    prompt = f"""
你是一位专业的职业教育指导老师。请根据以下数据为学生生成诊断报告：

## 学生信息
- 姓名：{student.name}
- 专业：{student.major}
- 班级：{student.class_name}

## 实训成绩
{format_scores(scores)}

## 能力图谱
{format_ability_profile(ability_profile)}

## 环境检查记录
{format_env_checks(env_checks)}

请生成一份诊断报告，包含以下部分：

1. **整体评价**（100-200字）
   - 总结学生的整体表现
   - 突出优势领域

2. **能力分析**（按大类能力逐一分析）
   - 当前水平
   - 与培养目标的差距
   - 进步趋势（如果有历史数据）

3. **薄弱环节**
   - 列出需要重点提升的具体能力点
   - 说明影响（为什么重要）

4. **提升建议**
   - 针对每个薄弱环节给出具体可操作的建议
   - 推荐的练习或资源

5. **毕业达标评估**
   - 当前距离毕业标准的差距
   - 预计达标时间（如果继续当前进度）

请用鼓励性但务实的语气撰写。
"""
    
    response = await llm_client.chat.completions.create(
        model="gemini-3-pro-preview",  # 使用更强的模型生成报告
        messages=[{"role": "user", "content": prompt}]
    )
    
    report_content = response.choices[0].message.content
    
    # 渲染 PDF
    pdf_path = await render_report_pdf(student, report_content, ability_profile.radar_data)
    
    return DiagnosticReport(
        student_id=student_id,
        report_type=report_type,
        content=report_content,
        pdf_url=pdf_path,
        generated_at=datetime.now()
    )
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/reports/generate` | POST | 生成诊断报告 |
| `/api/reports/{report_id}` | GET | 获取报告详情 |
| `/api/reports/student/{student_id}` | GET | 获取学生报告列表 |
| `/api/reports/{report_id}/pdf` | GET | 下载 PDF 报告 |

### 3.7 大屏展示模块

**功能**：实时展示学生整体实训情况

**大屏数据结构**：
```typescript
interface DashboardData {
  // 实时统计
  realtime: {
    activeStudents: number;        // 当前在训学生数
    todayTrainings: number;        // 今日实训次数
    averageScore: number;          // 今日平均分
  };
  
  // 班级排名
  classRanking: Array<{
    className: string;
    averageScore: number;
    trainingCount: number;
    rank: number;
  }>;
  
  // 能力分布（全校）
  abilityDistribution: {
    safety: { avg: number; distribution: number[] };
    equipment: { avg: number; distribution: number[] };
    procedure: { avg: number; distribution: number[] };
    professional: { avg: number; distribution: number[] };
  };
  
  // 趋势图（近30天）
  trend: Array<{
    date: string;
    trainingCount: number;
    averageScore: number;
    passRate: number;
  }>;
  
  // 实训室状态
  labStatus: Array<{
    labId: string;
    labName: string;
    status: 'available' | 'in_use' | 'maintenance';
    currentStudents: number;
  }>;
}
```

**WebSocket 推送**：
```python
# 大屏数据每 30 秒更新一次
@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await get_dashboard_data()
            await websocket.send_json(data)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
```

**API 设计**：
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard/summary` | GET | 获取大屏汇总数据 |
| `/api/dashboard/trend` | GET | 获取趋势数据 |
| `/ws/dashboard` | WebSocket | 实时数据推送 |

---

## 四、数据库设计

### 4.1 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- student, teacher, admin
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 学生表
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    student_no VARCHAR(50) UNIQUE NOT NULL,  -- 学号
    name VARCHAR(100) NOT NULL,
    major_id UUID REFERENCES majors(id),
    class_id UUID REFERENCES classes(id),
    enrollment_year INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 专业表
CREATE TABLE majors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE,
    ability_schema JSONB,  -- 能力体系定义
    created_at TIMESTAMP DEFAULT NOW()
);

-- 班级表
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    major_id UUID REFERENCES majors(id),
    teacher_id UUID REFERENCES users(id),
    year INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 实训项目表
CREATE TABLE training_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    major_id UUID REFERENCES majors(id),
    lab_id UUID REFERENCES labs(id),
    scoring_rules JSONB,  -- 评分规则
    ability_mapping JSONB,  -- 步骤-能力映射
    created_at TIMESTAMP DEFAULT NOW()
);

-- 原始实训记录（从校方同步）
CREATE TABLE raw_training_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(100) UNIQUE,  -- 校方数据库的原始 ID
    student_no VARCHAR(50) NOT NULL,
    project_id UUID REFERENCES training_projects(id),
    steps_data JSONB,  -- 每个步骤的完成情况
    completed_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT NOW()
);

-- 成绩记录
CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    project_id UUID REFERENCES training_projects(id),
    raw_record_id UUID REFERENCES raw_training_records(id),
    total_score DECIMAL(5,2),
    max_score DECIMAL(5,2),
    details JSONB,  -- 每个步骤的得分详情
    failed_abilities JSONB,  -- 未达标的能力项
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- 能力图谱
CREATE TABLE ability_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) UNIQUE,
    sub_abilities JSONB,  -- 子能力得分
    major_abilities JSONB,  -- 大类能力得分
    radar_data JSONB,  -- 雷达图数据
    graduation_ready BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 实训室表
CREATE TABLE labs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    reference_image_url VARCHAR(500),  -- 标准状态照片
    created_at TIMESTAMP DEFAULT NOW()
);

-- 环境检查记录
CREATE TABLE environment_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    lab_id UUID REFERENCES labs(id),
    score_id UUID REFERENCES scores(id),
    uploaded_image_url VARCHAR(500),
    total_score INTEGER,
    details JSONB,  -- 各项检查结果
    checked_at TIMESTAMP DEFAULT NOW()
);

-- 诊断报告
CREATE TABLE diagnostic_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    report_type VARCHAR(20),  -- single, periodic
    content TEXT,
    pdf_url VARCHAR(500),
    generated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_students_class ON students(class_id);
CREATE INDEX idx_scores_student ON scores(student_id);
CREATE INDEX idx_scores_project ON scores(project_id);
CREATE INDEX idx_ability_profiles_student ON ability_profiles(student_id);
CREATE INDEX idx_raw_training_completed ON raw_training_records(completed_at);
```

---

## 五、API 设计规范

### 5.1 RESTful 规范

```yaml
# 基础路径
/api/v1/

# 认证
Authorization: Bearer <jwt_token>

# 响应格式
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2026-03-04T12:00:00Z"
}

# 错误响应
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "字段验证失败",
    "details": { ... }
  },
  "timestamp": "2026-03-04T12:00:00Z"
}

# 分页
?page=1&page_size=20

# 筛选
?class_id=xxx&date_from=2026-01-01&date_to=2026-03-01
```

### 5.2 API 端点汇总

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **认证** | `/api/v1/auth/login` | POST | 登录 |
| | `/api/v1/auth/logout` | POST | 登出 |
| | `/api/v1/auth/me` | GET | 当前用户 |
| **成绩** | `/api/v1/scores` | GET | 成绩列表 |
| | `/api/v1/scores/{id}` | GET | 成绩详情 |
| | `/api/v1/scores/student/{id}` | GET | 学生成绩 |
| | `/api/v1/scores/class/{id}` | GET | 班级成绩 |
| **能力** | `/api/v1/abilities/student/{id}` | GET | 学生能力图谱 |
| | `/api/v1/abilities/class/{id}` | GET | 班级能力分布 |
| **环境** | `/api/v1/environment/check` | POST | 环境检查 |
| | `/api/v1/environment/reference/{lab_id}` | GET | 标准照片 |
| **报告** | `/api/v1/reports/generate` | POST | 生成报告 |
| | `/api/v1/reports/{id}` | GET | 报告详情 |
| | `/api/v1/reports/{id}/pdf` | GET | 下载 PDF |
| **大屏** | `/api/v1/dashboard/summary` | GET | 大屏数据 |
| | `/ws/dashboard` | WebSocket | 实时推送 |

---

## 六、部署架构

### 6.1 Docker Compose 配置

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3100:80"
    depends_on:
      - backend
    networks:
      - training-network

  backend:
    build: ./backend
    ports:
      - "8100:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/training
      - REDIS_URL=redis://redis:6379
      - LLM_PROXY_URL=https://llm-proxy.densematrix.ai
      - LLM_PROXY_KEY=sk-wskhgeyawc
    depends_on:
      - db
      - redis
    networks:
      - training-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=training
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - training-network

  redis:
    image: redis:7
    networks:
      - training-network

networks:
  training-network:
    driver: bridge

volumes:
  postgres_data:
```

### 6.2 Nginx 配置

```nginx
server {
    listen 80;
    server_name liaoning-training.demo.densematrix.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name liaoning-training.demo.densematrix.ai;

    ssl_certificate /etc/letsencrypt/live/liaoning-training.demo.densematrix.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/liaoning-training.demo.densematrix.ai/privkey.pem;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 七、性能设计

### 7.1 缓存策略

| 数据类型 | 缓存时间 | 说明 |
|----------|----------|------|
| 大屏汇总数据 | 30s | 高频访问，短期缓存 |
| 学生能力图谱 | 5min | 每次实训后更新 |
| 班级统计 | 1h | 日内变化不大 |
| 评分规则 | 1d | 很少变化 |

### 7.2 性能指标

| 指标 | 目标值 |
|------|--------|
| API 平均响应时间 | < 200ms |
| 报告生成时间 | < 10s |
| 环境检查时间 | < 5s |
| 大屏数据刷新 | 30s |
| 系统可用性 | ≥ 99% |

---

## 八、安全设计

### 8.1 认证与授权

- JWT Token 有效期：2 小时
- Refresh Token 有效期：7 天
- 基于角色的访问控制（RBAC）

### 8.2 数据安全

- 所有通信使用 HTTPS
- 密码使用 bcrypt 加密存储
- 敏感日志脱敏处理
- 数据库连接池限制

### 8.3 输入验证

- 所有输入参数使用 Pydantic 验证
- 文件上传限制类型和大小（图片 < 10MB）
- SQL 注入防护（ORM 参数化查询）

---

## 九、监控与日志

### 9.1 Prometheus Metrics

```python
# 核心指标
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}
training_records_synced_total
scores_calculated_total
reports_generated_total
vlm_requests_total{status}
llm_requests_total{model, status}
```

### 9.2 日志规范

```python
# 日志格式
{
  "timestamp": "2026-03-04T12:00:00Z",
  "level": "INFO",
  "service": "training-api",
  "trace_id": "xxx",
  "message": "Score calculated",
  "data": {
    "student_id": "xxx",
    "score": 85
  }
}
```

---

## 十、后续扩展方向

| 方向 | 说明 | 预计时间 |
|------|------|----------|
| 视频实训检测 | 实训视频的 VLM 分析 | 二期 |
| 实训预约系统 | 学生在线预约实训室 | 二期 |
| 多学校支持 | SaaS 化，支持多租户 | 三期 |
| 移动端 | 学生端 App | 三期 |

---

*本文档为系统架构设计初稿，具体实现细节可能根据开发过程调整。*
