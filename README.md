# 辽轨智能实训能力评估平台

> 职业院校实训智能评估与能力建模系统 Demo

[![Deploy](https://img.shields.io/badge/Deploy-shixun.demo.densematrix.ai-blue)](https://shixun.demo.densematrix.ai)

## 项目概述

为辽宁省铁路职业技术学院开发的智能实训能力评估平台 Demo。该平台利用现有实训设备数据，通过 AI 技术实现：

- 🎯 **自动化成绩分析** — 对接实训设备数据库，自动计算实训成绩
- 📊 **学生能力建模** — 生成多维度能力图谱，评估毕业达标进度
- 🤖 **智能诊断报告** — AI 生成个性化学习建议和提升方案
- 📷 **环境规范检查** — AI 图像识别检查实训室整理情况
- 📺 **大屏数据展示** — 展厅级别的实时数据可视化

## 技术栈

### 后端
- **框架**: Python FastAPI
- **数据库**: SQLite (Demo) / PostgreSQL (生产)
- **架构**: Clean Architecture
- **AI**: DenseMatrix LLM Proxy (Gemini)

### 前端
- **框架**: React + Vite + TypeScript
- **样式**: TailwindCSS
- **图表**: Recharts / ECharts
- **设计**: 蓝色工业风（铁路大屏风格）

## 快速开始

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/densematrix-labs/liaoning-school-training.git
cd liaoning-school-training

# 启动服务
docker compose up -d

# 访问
# 前端: http://localhost:3080
# 后端 API: http://localhost:8080
# API 文档: http://localhost:8080/docs
```

### 环境变量

```bash
# backend/.env
DATABASE_URL=sqlite:///./app.db
LLM_PROXY_URL=https://llm-proxy.densematrix.ai
LLM_PROXY_KEY=sk-wskhgeyawc
```

## 项目结构

```
liaoning-school-training/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── domain/         # 领域层（实体、接口）
│   │   ├── use_cases/      # 应用层（业务逻辑）
│   │   ├── adapters/       # 适配器层（实现）
│   │   └── infrastructure/ # 基础设施层
│   └── tests/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   │   ├── student/   # 学生端
│   │   │   ├── teacher/   # 教师端
│   │   │   ├── dashboard/ # 大屏展示
│   │   │   └── admin/     # 管理后台
│   │   ├── components/    # 通用组件
│   │   └── lib/          # 工具函数
│   └── tests/
├── mock-data/             # Mock 数据
├── docs/                  # 文档
│   ├── ARCHITECTURE.md   # 架构设计
│   └── API.md           # API 文档
└── docker-compose.yml
```

## 功能模块

### 学生端
- 查看个人实训成绩和历史记录
- 查看能力雷达图和毕业进度
- 下载 AI 生成的诊断报告

### 教师端
- 查看班级整体实训数据
- 统计分析和导出功能
- 预警信息管理

### 大屏展示
- 实时实训动态滚动
- 能力分布雷达图
- 班级对比柱状图
- 预警信息展示

### 管理后台
- 能力体系配置
- 实训步骤与能力映射
- 用户管理

## 开发团队

[DenseMatrix (上海凝矩科技)](https://densematrix.ai)

## License

MIT
