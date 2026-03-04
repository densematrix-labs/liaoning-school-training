# 辽轨智能实训能力评估平台

辽宁铁道职业技术学院智能实训能力评估平台 Demo。

## 功能模块

### 1. 学生端
- 查看实训成绩和历史记录
- 能力雷达图展示
- AI 生成的个性化诊断报告
- 毕业达标进度追踪

### 2. 教师端
- 班级学生数据管理
- 成绩统计与分析
- 能力分布可视化
- 数据导出功能

### 3. 大屏展示
- 实时实训动态
- 今日数据概览
- 能力分布雷达图
- 班级对比柱状图
- 预警信息提示

### 4. 管理后台
- 能力体系配置
- 实训室管理
- 能力映射管理
- 数据同步

## 技术栈

### 后端
- Python 3.11
- FastAPI
- SQLAlchemy (异步)
- SQLite (Demo) / PostgreSQL (生产)
- JWT 认证

### 前端
- React 18 + TypeScript
- Vite
- TailwindCSS
- Recharts
- React Query
- Zustand

### AI 集成
- LLM Proxy (DenseMatrix)
- Gemini Flash (诊断报告生成)
- Vision API (环境检查)

## 快速开始

### Docker Compose (推荐)

```bash
docker compose up -d
```

访问:
- 前端: http://localhost:3080
- 后端 API: http://localhost:8080
- API 文档: http://localhost:8080/docs

### 本地开发

后端:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

前端:
```bash
cd frontend
npm install
npm run dev
```

## 演示账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 学生 | 2023010101 | 123456 |
| 教师 | T20150012 | 123456 |
| 管理员 | T20100008 | 123456 |

## 配色方案

蓝色工业风：
- 主色: `#1a365d` (深蓝)
- 辅色: `#4299e1` (科技蓝)
- 背景: `#1a202c` (深色)
- 强调: `#00d4ff` (高亮蓝)

## 部署

目标服务器: langsheng (39.109.116.180)
域名: `shixun.demo.densematrix.ai`
端口: frontend 3080, backend 8080

## 项目结构

```
liaoning-school-training/
├── backend/
│   ├── app/
│   │   ├── adapters/controllers/  # API 路由
│   │   ├── models/                # 数据模型
│   │   ├── schemas/               # Pydantic 模式
│   │   ├── services/              # 业务逻辑
│   │   └── main.py                # 入口
│   ├── tests/                     # 测试
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/            # 通用组件
│   │   ├── pages/                 # 页面组件
│   │   ├── stores/                # 状态管理
│   │   └── lib/                   # 工具函数
│   └── Dockerfile
├── mock-data/                     # Mock 数据
├── docs/                          # 文档
├── docker-compose.yml
└── .github/workflows/deploy.yml   # CI/CD
```

## 许可证

© 2026 DenseMatrix AI
