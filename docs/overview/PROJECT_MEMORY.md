# 项目记忆 - AutoGeo

> 开发者备注：这是项目的核心记忆文档，记录技术栈、API、进度等关键信息。老王定期更新！

---

## 项目概述

**项目名称：** AutoGeo - AI 驱动的 GEO 自动化平台

**项目描述：** 一个基于 AI 的 GEO(Generative Engine Optimization) 自动化平台，实现从关键词蒸馏、文章生成、多平台发布到收录监控的全链路自动化。

**当前状态：** 🚀 核心功能已打通，进入完善阶段

**整体完成度：** **85%**

| 模块 | 完成度 |
|------|--------|
| GEO 核心流程 (关键词→文章→发布→监控) | 95% |
| 多平台发布 (知乎/头条/百家号/搜狐) | 90% |
| AI 收录检测 (豆包/千问/DeepSeek) | 90% |
| 爆火文章采集 (知乎/头条) | 85% |
| 知识库管理 | 80% |
| 智能建站 (AEO) | 75% |
| 数据报表 | 85% |
| 用户认证 | 50% |

---

## 技术架构

### 整体架构
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              AutoGeo 应用架构 (v2.2)                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────┐│
│  │   Electron 主进程    │         │    Python 后端       │         │    n8n AI    ││
│  │  (Node.js 运行时)    │◄───────►│   (FastAPI 服务)     │◄───────►│   工作流引擎  ││
│  │                      │  spawn  │                      │ webhook │              ││
│  │  - 窗口管理          │         │  - 账号管理 API      │         │  - 关键词蒸馏││
│  │  - IPC 通信          │         │  - 文章管理 API      │         │  - 文章生成  ││
│  │  - 后端进程管理      │         │  - 发布管理 API      │         │  - 收录分析  ││
│  │  - 系统托盘          │         │  - GEO/AI API        │         │  - AI中台    ││
│  │                      │         │  - Playwright 自动化 │         │              ││
│  │                      │         │  - 智能建站 API       │         │              ││
│  └──────────┬───────────┘         └──────────┬───────────┘         └──────────────┘│
│             │                                │                                    │
│             │ IPC                            │ HTTP/WebSocket                    │
│             │                                │                                    │
│  ┌──────────▼─────────────────────────────────────────────────────────────────┐  │
│  │                    渲染进程 (Renderer Process)                               │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                        Vue 3 应用                                        │  │  │
│  │  │  (账号/文章/发布/GEO/建站/报表/设置等 20+ 页面)                          │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 技术栈总览

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **桌面** | Electron | ^28.0.0 | 跨平台桌面应用 |
| **前端** | Vue 3 | ^3.4.0 | UI框架 |
| **前端** | TypeScript | ^5.3.0 | 类型安全 |
| **前端** | Vite | ^5.0.0 | 构建工具 |
| **前端** | Element Plus | ^2.5.0 | UI组件库 |
| **前端** | Pinia | ^2.1.7 | 状态管理 |
| **前端** | ECharts | ^5.6.0 | 数据可视化 |
| **后端** | FastAPI | 0.109.0 | Web框架 |
| **后端** | SQLAlchemy | 2.0.25 | ORM |
| **后端** | Playwright | 1.40.0 | 浏览器自动化 |
| **后端** | APScheduler | 3.10.4 | 定时任务 |
| **后端** | Jinja2 | - | 模板引擎（智能建站） |
| **后端** | paramiko | 3.4.0 | SFTP 部署（智能建站） |
| **后端** | boto3 | 1.34.19 | S3/OSS 部署（智能建站） |
| **AI中台** | n8n | latest | 工作流引擎 |
| **AI服务** | DeepSeek | - | 大模型API |
| **数据库** | SQLite | - | 本地存储 |

### 关键端口

| 服务 | 地址 |
|------|------|
| Vite Dev Server | http://127.0.0.1:5173 |
| Python FastAPI | http://127.0.0.1:8001 |
| WebSocket | ws://127.0.0.1:8001/ws |
| n8n | http://127.0.0.1:5678 |
| n8n Webhook | http://127.0.0.1:5678/webhook/* |

---

## 核心功能模块

### 1. 账号管理 ✅
- [x] 多平台账号管理 (知乎/头条/百家号/搜狐)
- [x] 浏览器授权登录 (Playwright 自动化)
- [x] Cookies + localStorage 加密存储 (AES-256)
- [x] 账号有效性验证
- [x] 账号 CRUD 操作

### 2. GEO 关键词蒸馏 ✅
- [x] 项目/客户管理
- [x] 关键词 CRUD
- [x] AI 关键词蒸馏 (对接 n8n webhook)
- [x] 问题变体生成
- [x] 数据持久化到数据库

### 3. GEO 文章生成 ✅
- [x] AI 文章生成 (对接 n8n)
- [x] 文章质检评分
- [x] 文章列表/详情/删除
- [x] 关联项目和关键词

### 4. 多平台发布 ✅
- [x] 批量发布任务创建
- [x] 实时进度推送 (WebSocket)
- [x] 发布记录查询
- [x] 失败重试
- [x] 平台适配器: 知乎、头条、百家号、搜狐

### 5. AI 收录检测 ✅
- [x] 单条/批量收录检测
- [x] AI 平台自动化 (豆包/千问/DeepSeek)
- [x] 检测记录管理
- [x] 命中率统计
- [x] 趋势分析
- [x] 项目/平台表现分析

### 6. 爆火文章采集 ✅
- [x] 知乎/头条文章采集
- [x] 参考文章管理
- [x] RAGFlow 知识库同步

### 7. 知识库管理 ✅
- [x] 分类管理
- [x] 条目 CRUD
- [x] RAGFlow 客户端集成

### 8. 智能建站 (AEO) ✅
- [x] 配置向导 (实时预览)
- [x] 双模板风格 (商务旗舰版/现代生活版)
- [x] Jinja2 模板渲染
- [x] SFTP/S3 部署

### 9. 数据报表 ✅
- [x] 总览报表
- [x] 趋势分析
- [x] 平台分布
- [x] 排名统计
- [x] 项目统计

### 10. 定时任务 ✅
- [x] 任务调度 (APScheduler)
- [x] 启动/停止控制
- [x] 任务列表

### 11. 客户管理 ✅
- [x] 客户模型（一个客户可以有多个项目）
- [x] CRUD 接口
- [x] 客户项目关联查询

### 12. 用户认证 🔄
- [x] User 模型
- [ ] 登录鉴权守卫

---

## 后端 API 清单

### 路由文件列表 (`backend/api/`)

| 文件 | 路由前缀 | 主要接口 |
|------|----------|----------|
| `account.py` | `/api/accounts` | 账号列表、授权启动、授权状态查询、更新、删除、批量检测 |
| `auth.py` | `/api/accounts/auth` | 浏览器授权流程管理 |
| `article.py` | `/api/articles` | 文章CRUD、分页搜索、标记发布 |
| `article_collection.py` | `/api/article-collection` | 爆火文章采集 |
| `client.py` | `/api/clients` | 客户管理（一个客户可有多个项目） |
| `geo.py` | `/api/geo` | GEO文章生成、质检、收录检测、列表、删除 |
| `index_check.py` | `/api/index-check` | 收录检测、记录查询、命中率、趋势、分析 |
| `keywords.py` | `/api/keywords` | 项目CRUD、关键词蒸馏、问题变体生成、关键词CRUD |
| `knowledge.py` | `/api/knowledge` | 知识库分类与条目管理 |
| `notifications.py` | `/api/notifications` | 通知消息管理 |
| `publish.py` | `/api/publish` | 批量发布任务创建、进度查询、发布记录、重试 |
| `reports.py` | `/api/reports` | 数据报表 (总览、趋势、平台分布、排名、统计) |
| `scheduler.py` | `/api/scheduler` | 定时任务管理 |
| `site_builder.py` | `/api/site-builder` | 智能建站 (生成/部署) |
| `upload.py` | `/api/upload` | 文件上传 |

### 服务层文件列表 (`backend/services/`)

| 服务文件 | 功能描述 |
|----------|----------|
| `auth_service.py` | 浏览器授权认证服务 |
| `account_validator.py` | 账号有效性验证 |
| `crypto.py` | AES-256 加密工具 |
| `keyword_service.py` | 关键词蒸馏 (对接 n8n) |
| `geo_article_service.py` | GEO 文章生成与质检 |
| `index_check_service.py` | AI 平台收录检测 |
| `article_collector_service.py` | 爆火文章采集 |
| `publisher.py` | 文章发布调度 |
| `playwright_mgr.py` | Playwright 浏览器管理器 |
| `notification_service.py` | 通知服务 |
| `scheduler_service.py` | 定时任务调度 |
| `ragflow_client.py` | RAGFlow 知识库客户端 |
| `n8n_service.py` | n8n 工作流调用服务 |
| `deploy_service.py` | 网站部署服务 |
| `site_generator.py` | 网站页面生成器 |
| `websocket_manager.py` | WebSocket 实时推送 |

### Playwright 子模块

| 路径 | 平台/功能 |
|------|----------|
| `playwright/publishers/zhihu.py` | 知乎发布器 |
| `playwright/publishers/toutiao.py` | 头条发布器 |
| `playwright/publishers/baijiahao.py` | 百家号发布器 |
| `playwright/publishers/sohu.py` | 搜狐号发布器 |
| `playwright/collectors/zhihu.py` | 知乎文章采集器 |
| `playwright/collectors/toutiao.py` | 头条文章采集器 |
| `playwright/ai_platforms/deepseek.py` | DeepSeek 平台自动化 |
| `playwright/ai_platforms/doubao.py` | 豆包平台自动化 |
| `playwright/ai_platforms/qianwen.py` | 千问平台自动化 |

---

## 前端页面清单

### 页面组件 (`fronted/src/views/`)

| 页面文件 | 路由路径 | 功能 |
|----------|----------|------|
| `layout/MainLayout.vue` | `/` | 主布局框架 |
| `dashboard/DashboardPage.vue` | `/dashboard` | 首页仪表盘 |
| `geo/Dashboard.vue` | `/geo/dashboard` | GEO 数据概览 |
| `geo/Projects.vue` | `/geo/projects` | GEO 项目管理 |
| `geo/Keywords.vue` | `/geo/keywords` | 关键词蒸馏 |
| `geo/Articles.vue` | `/geo/articles` | GEO 文章生成 |
| `geo/Monitor.vue` | `/geo/monitor` | 收录监控 |
| `site-builder/ConfigWizard.vue` | `/site-builder` | 智能建站向导 |
| `account/AccountList.vue` | `/accounts` | 账号列表管理 |
| `account/AccountAdd.vue` | `/accounts/add` | 添加账号 |
| `auth/AuthFlow.vue` | - | 授权流程组件 |
| `article/ArticleList.vue` | `/articles` | 文章列表 |
| `article/ArticleEdit.vue` | `/articles/add`, `/articles/edit/:id` | 文章编辑/新建 |
| `publish/PublishPage.vue` | `/publish` | 批量发布 |
| `publish/PublishHistory.vue` | `/history` | 发布记录 |
| `client/ClientPage.vue` | `/clients` | 客户管理 |
| `knowledge/KnowledgePage.vue` | `/knowledge` | 知识库管理 |
| `scheduler/SchedulerPage.vue` | `/scheduler` | 定时任务管理 |
| `report/DataReport.vue` | `/data-report` | 数据报表 |
| `settings/SettingsPage.vue` | `/settings` | 系统设置 |

### 前端 API 服务 (`fronted/src/services/api/index.ts`)

版本: **v2.2 加固版**

| API 模块 | 接口数量 |
|----------|----------|
| `accountApi` | 6 个 (列表、授权、状态、更新、删除、检测) |
| `geoKeywordApi` | 7 个 (项目/关键词管理、蒸馏、问题生成) |
| `geoArticleApi` | 6 个 (列表、生成、质检、收录检测、详情、删除) |
| `indexCheckApi` | 10 个 (检测、记录、趋势、统计) |
| `reportsApi` | 8 个 (总览、趋势、分布、排名、统计、对比) |
| `schedulerApi` | 3 个 (列表、启动、停止) |

---

## 数据库模型

### 模型列表 (`backend/database/models.py`)

| 模型 | 表名 | 用途 |
|------|------|------|
| `Account` | `accounts` | 平台账号 (cookies/storage_state) |
| `Article` | `articles` | 通用文章 |
| `PublishRecord` | `publish_records` | 发布记录 |
| `Project` | `projects` | GEO 项目/客户 |
| `Keyword` | `keywords` | GEO 关键词 |
| `QuestionVariant` | `question_variants` | 问题变体 |
| `IndexCheckRecord` | `index_check_records` | 收录检测记录 |
| `GeoArticle` | `geo_articles` | GEO 生成文章 |
| `KnowledgeCategory` | `knowledge_categories` | 知识库分类 |
| `Knowledge` | `knowledge_items` | 知识库条目 |
| `User` | `users` | 系统用户 |
| `ReferenceArticle` | `reference_articles` | 参考文章 (爆火采集) |
| `ScheduledTask` | `scheduled_tasks` | 定时任务配置 |
| `Client` | `clients` | 客户表（一个客户可有多个项目） |
| `SiteProject` | `site_projects` | AEO 智能建站项目 |

---

## n8n 工作流

### 云端配置

- **云端地址:** https://n8n.opencaio.cn
- **当前版本:** GEOv0.0.3

### 已激活 Webhook

| Webhook | 功能 | 调用方 |
|---------|------|--------|
| `/webhook/keyword-distill` | 关键词蒸馏 | `keyword_service.py` |
| `/webhook/geo-article-generate` | GEO 文章生成 | `geo_article_service.py` |

---

## 启动方式

### 1️⃣ 启动后端 (第一个终端)
```bash
cd E:\CodingPlace\AI\Architecture-Matrix\auto_geo_dev\backend
python main.py
# 服务地址: http://127.0.0.1:8001
# API 文档: http://127.0.0.1:8001/docs
```

### 2️⃣ 启动前端 (第二个终端)
```bash
cd E:\CodingPlace\AI\Architecture-Matrix\auto_geo_dev\fronted
npm run dev
# 访问地址: http://127.0.0.1:5173
```

### 3️⃣ 退出顺序
1. 先 Ctrl+C 停止前端
2. 再 Ctrl+C 停止后端

---

## 目录结构

```
auto_geo_dev/
├── backend/                    # Python 后端
│   ├── api/                    # API 路由 (16个文件)
│   ├── services/               # 业务逻辑
│   │   ├── playwright/         # Playwright 子模块
│   │   │   ├── publishers/     # 发布器 (知乎/头条/百家/搜狐)
│   │   │   ├── collectors/     # 采集器 (知乎/头条)
│   │   │   └── ai_platforms/   # AI平台 (豆包/千问/DeepSeek)
│   │   └── *.py                # 核心服务
│   ├── database/               # 数据库
│   │   └── models.py           # ORM 模型 (15个)
│   ├── templates/              # Jinja2 模板 (智能建站)
│   │   ├── corporate_v1.html   # 商务旗舰版
│   │   └── cowboy_v1.html      # 现代生活版
│   ├── static/sites/           # 生成的站点文件
│   ├── schemas/                # Pydantic 模型
│   ├── scripts/                # 工具脚本
│   ├── config.py               # 配置文件
│   └── main.py                 # FastAPI 入口
│
├── fronted/                    # Electron 前端
│   ├── electron/               # Electron 主进程
│   │   ├── main/               # 主进程代码
│   │   └── preload/            # 预加载脚本
│   ├── src/                    # Vue 渲染进程
│   │   ├── views/              # 页面组件 (20个)
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── services/           # API 服务
│   │   ├── router/             # 路由配置
│   │   └── core/               # 核心配置
│   └── package.json
│
├── tests/                      # 测试目录
│   ├── scripts/                # 测试脚本
│   ├── test_*.py               # 测试文件
│   └── conftest.py
│
├── n8n/                        # n8n 工作流
│   ├── workflows/              # 工作流定义
│   └── README.md
│
├── docs/                       # 文档
│   ├── architecture/           # 架构文档
│   ├── features/               # 功能文档
│   ├── overview/               # 概览文档
│   ├── security/               # 安全文档
│   └── testing/                # 测试文档
│
├── .env.example                # 环境变量模板
├── quickstart.cmd              # 快速启动脚本
└── README.md                   # 项目说明
```

---

## 安全配置

### 加密机制
- **算法**: AES-256 (Fernet)
- **密钥派生**: PBKDF2HMAC + SHA256
- **加密内容**: Cookies、localStorage

### 环境变量设置
```bash
# 1. 复制模板
cp .env.example .env

# 2. 生成密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. 编辑 .env 填入密钥
ENCRYPTION_KEY=你的32字节密钥
```

---

## 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2025-02-10 | v2.2 | 新增智能建站功能文档，更新架构文档 |
| 2025-01-22 | v2.1 | 新增 n8n AI 中台 |
| 2025-01-10 | v1.1.2 | 新增环境变量模板和安全文档 |
| 2025-01-08 | v2.0 | 框架搭建完成 |

---

## 下一步计划

1. **用户认证** - 完善登录鉴权守卫
2. **智能建站** - 配置持久化、模板扩展
3. **测试覆盖** - 系统性测试文件
4. **错误处理** - 边界情况处理优化

---

**文档维护者：** 老王
**最后更新：** 2025-02-10
