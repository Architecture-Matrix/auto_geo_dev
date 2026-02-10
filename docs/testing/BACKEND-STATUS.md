# AutoGeo 后端实现状态

**更新日期**: 2025-02-10
**版本**: v2.2.0
**状态**: 核心功能已完成，进入完善阶段

---

## 📊 总体进度

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 项目基础架构 | ✅ | 100% |
| 数据库层 | ✅ | 100% |
| 账号授权 | ✅ | 100% |
| 文章管理 | ✅ | 100% |
| 发布模块 | ✅ | 100% |
| GEO功能 | ✅ | 100% |
| 收录检测 | ✅ | 100% |
| 报表统计 | ✅ | 100% |
| 爆火文章采集 | ✅ | 100% |
| 知识库管理 | ✅ | 100% |
| 智能建站 | ✅ | 100% |
| 定时任务 | ✅ | 100% |
| 预警通知 | ✅ | 100% |
| 用户认证 | 🔄 | 50% |

---

## ✅ 已完成模块

### 1. 项目基础架构

- [x] FastAPI 项目结构
- [x] 配置管理 (config.py) - 支持 4 个发布平台 + 3 个 AI 平台
- [x] 依赖清单 (requirements.txt)
- [x] CORS 中间件配置
- [x] WebSocket 支持 - 实时进度推送
- [x] 生命周期管理 - 优雅关闭机制
- [x] 日志配置 (loguru)
- [x] n8n 工作流集成

### 2. 数据库层 (15 张表)

- [x] SQLite 数据库初始化
- [x] SQLAlchemy ORM 配置
- [x] 数据模型定义:
  - `Account` - 账号表（加密存储 Cookie/StorageState）
  - `Article` - 文章表
  - `PublishRecord` - 发布记录表
  - `Project` - GEO 项目表
  - `Keyword` - 关键词表
  - `QuestionVariant` - 问题变体表
  - `IndexCheckRecord` - 收录检测记录表
  - `GeoArticle` - GEO 文章表（含质检字段）
  - `KnowledgeCategory` - 知识库分类表
  - `Knowledge` - 知识库条目表
  - `ReferenceArticle` - 参考文章表（爆火采集）
  - `ScheduledTask` - 定时任务配置表
  - `Candidate` - AI 招聘候选人表
  - `SiteProject` - AEO 智能建站项目表
  - `User` - 系统用户表
- [x] 数据库会话管理 (get_db 依赖注入)
- [x] 级联删除配置

### 3. API 层 (16 个路由文件)

#### 3.1 账号管理 API (`api/account.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/accounts` | 获取账号列表（支持平台/状态筛选） |
| GET | `/api/accounts/{id}` | 获取账号详情 |
| POST | `/api/accounts` | 创建账号 |
| PUT | `/api/accounts/{id}` | 更新账号 |
| DELETE | `/api/accounts/{id}` | 删除账号 |
| POST | `/api/accounts/batch-check` | 批量检测账号有效性 |

**支持平台**：知乎、百家号、搜狐号、头条号

#### 3.2 授权流程 API (`api/auth.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/accounts/auth/start` | 开始授权（打开浏览器） |
| GET | `/api/accounts/auth/status/{task_id}` | 查询授权状态 |
| POST | `/api/accounts/auth/confirm/{task_id}` | 手动确认授权完成 |
| DELETE | `/api/accounts/auth/task/{task_id}` | 取消授权任务 |

#### 3.3 文章管理 API (`api/article.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/articles` | 获取文章列表（分页、搜索） |
| GET | `/api/articles/{id}` | 获取文章详情 |
| POST | `/api/articles` | 创建文章 |
| PUT | `/api/articles/{id}` | 更新文章 |
| DELETE | `/api/articles/{id}` | 删除文章 |
| POST | `/api/articles/{id}/publish` | 标记已发布 |

#### 3.4 发布管理 API (`api/publish.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/publish/platforms` | 获取支持的发布平台 |
| POST | `/api/publish/create` | 创建批量发布任务 |
| GET | `/api/publish/progress/{task_id}` | 获取发布进度 |
| GET | `/api/publish/records` | 获取发布记录 |
| POST | `/api/publish/retry/{record_id}` | 重试发布 |

#### 3.5 关键词管理 API (`api/keywords.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/keywords/projects` | 获取项目列表 |
| POST | `/api/keywords/projects` | 创建项目 |
| GET | `/api/keywords/projects/{id}` | 获取项目详情 |
| GET | `/api/keywords/projects/{id}/keywords` | 获取项目的关键词 |
| POST | `/api/keywords/distill` | **AI 蒸馏关键词**（调用 n8n） |
| POST | `/api/keywords/generate-questions` | **生成问题变体** |
| GET | `/api/keywords/keywords/{id}/questions` | 获取问题变体列表 |
| DELETE | `/api/keywords/keywords/{id}` | 停用关键词 |

#### 3.6 GEO 文章 API (`api/geo.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/geo/generate` | **AI 生成文章**（调用 n8n） |
| POST | `/api/geo/articles/{id}/check-quality` | **质检文章**（AI 味检测） |
| POST | `/api/geo/articles/{id}/check-index` | **收录检测** |
| GET | `/api/geo/articles/{id}` | 获取文章详情 |
| GET | `/api/geo/keywords/{keyword_id}/articles` | 获取关键词的文章列表 |
| PUT | `/api/geo/articles/{id}` | 更新文章 |
| DELETE | `/api/geo/articles/{id}` | 删除文章 |
| GET | `/api/geo/articles` | 获取文章列表（支持筛选） |

#### 3.7 收录检测 API (`api/index_check.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/index-check/check` | **执行 AI 平台收录检测** |
| POST | `/api/index-check/batch-check` | 批量收录检测 |
| GET | `/api/index-check/records` | 获取检测记录 |
| DELETE | `/api/index-check/records/{id}` | 删除记录 |
| DELETE | `/api/index-check/records/batch` | 批量删除记录 |
| GET | `/api/index-check/keywords/{id}/hit-rate` | 获取命中率统计 |
| GET | `/api/index-check/trends` | 获取收录趋势数据 |
| GET | `/api/index-check/project-analysis/{id}` | 项目收录分析 |
| GET | `/api/index-check/platform-performance` | 平台表现统计 |

#### 3.8 报表统计 API (`api/reports.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reports/overview` | 总体概览数据 |
| GET | `/api/reports/trends` | 收录趋势数据 |
| GET | `/api/reports/platform-distribution` | 平台分布统计 |
| GET | `/api/reports/ranking` | 排名统计 |
| GET | `/api/reports/project-stats/{id}` | 项目统计数据 |
| GET | `/api/reports/comparison` | 对比分析 |
| GET | `/api/reports/leaderboard` | 排行榜 |
| POST | `/api/reports/execute-check` | 执行检测并返回报表 |

#### 3.9 爆火文章采集 API (`api/article_collection.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/article-collection/collect` | 采集爆火文章 |
| GET | `/api/article-collection/references` | 获取参考文章列表 |
| GET | `/api/article-collection/references/{id}` | 获取参考文章详情 |
| DELETE | `/api/article-collection/references/{id}` | 删除参考文章 |

#### 3.10 知识库管理 API (`api/knowledge.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/categories` | 获取分类列表 |
| POST | `/api/knowledge/categories` | 创建分类 |
| PUT | `/api/knowledge/categories/{id}` | 更新分类 |
| DELETE | `/api/knowledge/categories/{id}` | 删除分类 |
| GET | `/api/knowledge/items` | 获取条目列表 |
| POST | `/api/knowledge/items` | 创建条目 |
| PUT | `/api/knowledge/items/{id}` | 更新条目 |
| DELETE | `/api/knowledge/items/{id}` | 删除条目 |

#### 3.11 智能建站 API (`api/site_builder.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/sites/build` | 构建站点（Jinja2 渲染） |
| POST | `/sites/deploy` | 部署站点（SFTP/S3） |

#### 3.12 定时任务 API (`api/scheduler.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scheduler/jobs` | 获取所有定时任务 |
| POST | `/api/scheduler/start` | 启动定时服务 |
| POST | `/api/scheduler/stop` | 停止定时服务 |

#### 3.13 通知 API (`api/notifications.py`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notifications` | 获取通知列表 |
| PUT | `/api/notifications/{id}/read` | 标记已读 |

#### 3.14 其他 API

| 文件 | 说明 |
|------|------|
| `candidate.py` | AI 招聘候选人管理 |
| `upload.py` | 文件上传 |

---

### 4. 业务服务层 (`services/`)

#### 核心服务

| 模块 | 功能 |
|------|------|
| `crypto.py` | AES-256 加密/解密（Cookie/StorageState） |
| `playwright_mgr.py` | Playwright 浏览器管理、授权任务、发布任务 |
| `keyword_service.py` | 关键词蒸馏（n8n）、生成问题变体 |
| `geo_article_service.py` | GEO 文章生成（n8n）、质检 |
| `index_check_service.py` | AI 平台收录检测（豆包/千问/DeepSeek） |
| `article_collector_service.py` | 爆火文章采集 |
| `notification_service.py` | 预警通知服务（WebSocket/Log） |
| `scheduler_service.py` | 定时任务管理（APScheduler） |
| `n8n_service.py` | n8n 工作流 HTTP 客户端 |
| `ragflow_client.py` | RAGFlow 知识库客户端 |
| `site_generator.py` | 网站页面生成器（Jinja2） |
| `deploy_service.py` | 网站部署服务（SFTP/S3） |
| `websocket_manager.py` | WebSocket 实时推送 |

#### Playwright 发布适配器 (`services/playwright/publishers/`)

| 文件 | 平台 |
|------|------|
| `base.py` | 基础发布适配器（抽象类） |
| `zhihu.py` | 知乎 |
| `baijiahao.py` | 百家号 |
| `sohu.py` | 搜狐号 |
| `toutiao.py` | 头条号 |

#### Playwright 采集器 (`services/playwright/collectors/`)

| 文件 | 平台 |
|------|------|
| `zhihu.py` | 知乎文章采集 |
| `toutiao.py` | 头条文章采集 |

#### AI 平台检测器 (`services/playwright/ai_platforms/`)

| 文件 | 平台 |
|------|------|
| `base.py` | 基础检测器（抽象类） |
| `doubao.py` | 豆包收录检测 |
| `qianwen.py` | 通义千问收录检测 |
| `deepseek.py` | DeepSeek 收录检测 |

---

### 5. 智能建站模块

#### 模板文件 (`templates/`)

| 文件 | 风格 |
|------|------|
| `corporate_v1.html` | 商务旗舰版（深色） |
| `cowboy_v1.html` | 现代生活版（浅色） |

#### 功能特性

- [x] Jinja2 模板渲染
- [x] 实时预览（防抖 800ms）
- [x] 双模板风格切换
- [x] SFTP 部署（paramiko）
- [x] S3/OSS 部署（boto3）
- [x] 自定义主题颜色
- [x] 动态区块配置

---

## 🔧 技术栈

| 组件 | 技术 | 版本 |
|-----|------|------|
| Web 框架 | FastAPI | 0.109.0 |
| ASGI 服务器 | Uvicorn | 0.27.0 |
| ORM | SQLAlchemy | 2.0.25 |
| 数据验证 | Pydantic | 2.5.3 |
| 浏览器自动化 | Playwright | 1.40.0 |
| 加密 | cryptography | 41.0.7 |
| 日志 | loguru | 0.7.2 |
| 定时任务 | APScheduler | 3.10.4 |
| 异步 HTTP | httpx | 0.26.0 |
| WebSocket | websockets | 12.0 |
| 模板引擎 | Jinja2 | - |
| SFTP 部署 | paramiko | 3.4.0 |
| S3 部署 | boto3 | 1.34.19 |

---

## 📝 运行命令

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 启动服务
python main.py

# 服务地址: http://127.0.0.1:8001
# API 文档: http://127.0.0.1:8001/docs
```

---

## 🔌 外部集成

| 服务 | 用途 | 状态 |
|------|------|------|
| n8n | AI 关键词蒸馏、文章生成 | ✅ 云端已部署 |
| 豆包 | AI 平台收录检测 | ✅ |
| 通义千问 | AI 平台收录检测 | ✅ |
| DeepSeek | AI 平台收录检测 | ✅ |
| RAGFlow | 知识库同步 | ✅ |

---

## 📌 配置参数

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 服务地址 | `127.0.0.1:8001` | 后端监听地址 |
| 数据库 | SQLite | `backend/database/auto_geo.db` |
| CORS | `localhost:5173` | 前端跨域白名单 |
| 发布超时 | 300 秒 | 单个发布任务超时 |
| 最大并发 | 3 个 | 同时发布的最大数量 |
| 重试次数 | 2 次 | 发布失败重试 |

---

## 📁 目录结构

```
backend/
├── api/                        # API 路由 (16个文件)
│   ├── account.py              # 账号管理
│   ├── auth.py                 # 授权流程
│   ├── article.py              # 文章管理
│   ├── article_collection.py   # 文章采集
│   ├── candidate.py            # AI 招聘候选人
│   ├── geo.py                  # GEO 文章
│   ├── index_check.py          # 收录检测
│   ├── keywords.py             # 关键词管理
│   ├── knowledge.py            # 知识库
│   ├── notifications.py        # 通知
│   ├── publish.py              # 发布管理
│   ├── reports.py              # 数据报表
│   ├── scheduler.py            # 定时任务
│   ├── site_builder.py         # 智能建站
│   └── upload.py               # 文件上传
│
├── services/                   # 业务逻辑
│   ├── playwright/             # Playwright 子模块
│   │   ├── publishers/         # 发布器
│   │   ├── collectors/         # 采集器
│   │   └── ai_platforms/       # AI 平台
│   ├── crypto.py
│   ├── keyword_service.py
│   ├── geo_article_service.py
│   ├── index_check_service.py
│   ├── article_collector_service.py
│   ├── notification_service.py
│   ├── scheduler_service.py
│   ├── n8n_service.py
│   ├── ragflow_client.py
│   ├── site_generator.py
│   ├── deploy_service.py
│   └── websocket_manager.py
│
├── templates/                  # Jinja2 模板
│   ├── corporate_v1.html
│   └── cowboy_v1.html
│
├── static/sites/               # 生成的站点文件
├── database/                   # 数据库
│   └── models.py               # ORM 模型 (15个)
├── schemas/                    # Pydantic 模型
├── scripts/                    # 工具脚本
├── config.py                   # 配置文件
└── main.py                     # FastAPI 入口
```

---

**维护者**: 老王
**最后更新**: 2025-02-10
