# AutoGeo GEO全自动化系统 开发计划

**版本**: v1.0
**日期**: 2025-01-16
**作者**: 开发者
**状态**: 计划中

---

## 文档说明

本文档是**可执行的开发计划**，按阶段划分任务，每个任务包含：
- **新建文件**：需要创建的文件路径
- **代码框架**：核心代码结构
- **验证标准**：如何验证完成

---

## 总体架构

```
用户 → 前端(Vue3) → 后端API(FastAPI) → n8n webhook → AI服务(DeepSeek)
                ↓                     ↓
            SQLite            Playwright自动化
                              (发布/检测)
```

---

## 开发路线图

```
阶段0(1天)   阶段1(3天)   阶段2(3天)   阶段3(3天)   阶段4(5天)   阶段5(5天)   阶段6(3天)   阶段7(3天)
修知乎Bug → n8n集成 → 关键词蒸馏 → 文章生成 → AI质检 → 收录检测 → 前端页面 → 定时任务
                                                                           ↓
                                                                      阶段8(3天)
                                                                      数据报表
```

---

## 阶段0：修复知乎发布Bug（1天）

### 目标
修复现有知乎发布功能，确保标题正确填充并发布成功。

### Task 0.1：定位问题
- **检查文件**：`backend/services/playwright/publishers/zhihu.py`
- **检查项**：
  1. 标题填充的selector是否正确
  2. 点击发布按钮的时机是否过早
  3. 是否有等待加载的步骤

### Task 0.2：修复并测试
- **验证标准**：手动测试发布3篇文章，知乎平台能正确显示标题和内容

---

## 阶段1：n8n集成基础设施（3天）

### 目标
建立后端与n8n的通信机制。

### Task 1.1：配置文件
- **新建文件**：`backend/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook"
    DATABASE_URL: str = "sqlite:///./database/auto_geo.db"

settings = Settings()
```

### Task 1.2：n8n客户端
- **新建文件**：`backend/services/n8n_client.py`
```python
import httpx

class N8nClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = 300

    async def call(self, workflow: str, data: dict) -> dict:
        url = f"{self.base_url}/{workflow}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
```

### Task 1.3：n8n测试工作流
- 在n8n创建webhook：`test-connection`
- 返回：`{"status": "ok"}`
- **验证标准**：后端能成功调用并收到响应

---

## 阶段2：关键词蒸馏（3天）

### 目标
用户输入公司信息，AI分析并返回高价值关键词列表。

### Task 2.1：数据库表
```sql
-- 新建文件: backend/database/migrations/001_keywords.sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    description TEXT,
    industry VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    difficulty_score INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE question_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);
```

### Task 2.2：关键词服务
- **新建文件**：`backend/services/keyword_service.py`
```python
from .n8n_client import N8nClient

class KeywordService:
    def __init__(self, n8n: N8nClient):
        self.n8n = n8n

    async def distill(self, company_name: str, industry: str, description: str, count: int = 10):
        return await self.n8n.call("distill-keywords", {
            "company_name": company_name,
            "industry": industry,
            "description": description,
            "count": count
        })

    async def generate_questions(self, keyword: str, count: int = 3):
        result = await self.n8n.call("generate-questions", {
            "keyword": keyword,
            "count": count
        })
        return result.get("questions", [])
```

### Task 2.3：API路由
- **新建文件**：`backend/api/keywords.py`
```python
from fastapi import APIRouter
from services.keyword_service import KeywordService
from services.n8n_client import N8nClient

router = APIRouter(prefix="/api/keywords", tags=["keywords"])
n8n = N8nClient("http://localhost:5678/webhook")

@router.post("/distill")
async def distill_keywords(
    company_name: str,
    industry: str,
    description: str,
    count: int = 10
):
    service = KeywordService(n8n)
    return await service.distill(company_name, industry, description, count)

@router.post("/generate-questions")
async def generate_questions(keyword: str, count: int = 3):
    service = KeywordService(n8n)
    return {"questions": await service.generate_questions(keyword, count)}
```

### Task 2.4：n8n工作流
| 工作流名 | 输入 | 输出 |
|---------|------|------|
| `distill-keywords` | 公司信息 | `{"keywords": [{"keyword": "中小企业CRM", "difficulty_score": 90}]}` |
| `generate-questions` | keyword, count | `{"questions": ["什么是...", "推荐..."]}` |

---

## 阶段3：文章生成（3天）

### Task 3.1：文章表
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    title TEXT,
    content TEXT,
    quality_score DECIMAL(3,2),
    quality_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);
```

### Task 3.2：文章服务
- **新建文件**：`backend/services/article_service.py`
```python
class ArticleService:
    def __init__(self, n8n: N8nClient):
        self.n8n = n8n

    async def generate(self, keyword: str, company: dict, platform: str = "zhihu"):
        prompt = f"请写一篇关于{keyword}的文章，突出{company['name']}的优势..."
        return await self.n8n.call("generate-article", {
            "prompt": prompt,
            "platform": platform
        })
```

### Task 3.3：API路由
- **新建文件**：`backend/api/articles.py`

---

## 阶段4：AI质检（3天）

### Task 4.1：质检服务
- **新建文件**：`backend/services/quality_service.py`
```python
class QualityService:
    async def check(self, article_id: int):
        # 调用n8n检测AI味
        # 返回质检报告
        pass
```

### Task 4.2：n8n工作流：`check-quality`
- 输入：文章content
- 输出：`{"ai_score": 0.3, "readability": 85}`

---

## 阶段5：收录检测（5天）⭐核心

### 目标
使用Playwright自动化检测AI平台收录情况。

### Task 5.1：AI平台检测器基类
- **新建文件**：`backend/services/playwright/ai_platforms/base.py`
```python
from playwright.async_api import async_playwright

class AIPlatformChecker:
    async def check(self, keyword: str, company: str, questions: list[str]) -> dict:
        # 1. 打开AI平台
        # 2. 输入问题
        # 3. 获取回答
        # 4. 检测关键词/公司名
        pass
```

### Task 5.2：豆包检测器
- **新建文件**：`backend/services/playwright/ai_platforms/doubao.py`
```python
from .base import AIPlatformChecker

class DoubaoChecker(AIPlatformChecker):
    URL = "https://www.doubao.com"
    INPUT_SELECTOR = "textarea"
    SUBMIT_SELECTOR = "button[type='submit']"
    ANSWER_SELECTOR = ".answer-content"
```

### Task 5.3：收录记录表
```sql
CREATE TABLE index_check_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    platform VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    keyword_found BOOLEAN,
    company_found BOOLEAN,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);
```

### Task 5.4：验证标准
- 手动测试3个关键词，每个3个问题
- 能正确返回是否包含关键词/公司名

---

## 阶段6：前端页面（5天）

### Task 6.1：关键词管理页面
- **新建文件**：`fronted/src/views/Keywords.vue`
- **功能**：列表展示、添加关键词、查看问题变体

### Task 6.2：文章生成页面
- **新建文件**：`fronted/src/views/Articles.vue`
- **功能**：选择关键词、生成文章、预览

### Task 6.3：收录监控页面
- **新建文件**：`fronted/src/views/Monitor.vue`
- **功能**：显示检测记录、匹配结果

---

## 阶段7：定时任务（3天）

### Task 7.1：定时器服务
- **新建文件**：`backend/services/scheduler_service.py`
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start_daily_check(self, hour: int = 2, minute: int = 0):
        self.scheduler.add_job(
            self.daily_check,
            "cron",
            hour=hour,
            minute=minute
        )

    async def daily_check(self):
        # 获取活跃关键词
        # 并发检测
        # 保存结果
        pass
```

---

## 阶段8：数据报表（3天）

### Task 8.1：统计API
- 计算命中率 = 匹配次数 / 总查询次数
- 趋势分析

### Task 8.2：报表页面
- **新建文件**：`fronted/src/views/Reports.vue`

---

## 文件结构总览

```
backend/
├── config.py                          # 配置
├── services/
│   ├── n8n_client.py                  # n8n客户端
│   ├── keyword_service.py             # 关键词服务
│   ├── article_service.py             # 文章服务
│   ├── quality_service.py             # 质检服务
│   ├── scheduler_service.py           # 定时任务
│   └── playwright/
│       └── ai_platforms/              # AI平台检测器
│           ├── base.py
│           ├── doubao.py
│           ├── qianwen.py
│           └── deepseek.py
├── api/
│   ├── keywords.py                    # 关键词API
│   ├── articles.py                    # 文章API
│   ├── geo.py                         # 收录检测API
│   └── scheduler.py                   # 定时任务API
└── database/
    └── models.py                      # 数据库模型

fronted/src/
├── views/
│   ├── Keywords.vue                   # 关键词管理
│   ├── Articles.vue                   # 文章生成
│   ├── Monitor.vue                    # 收录监控
│   └── Reports.vue                    # 数据报表
└── api/
    └── *.ts                           # API调用
```

---

## 待修复Bug

| Bug | 症状 | 优先级 |
|-----|------|-------|
| 知乎发布 | 标题丢失，内容进入编辑状态 | P0 |

---

## 附录：术语表

| 术语 | 说明 |
|-----|------|
| GEO | Generative Engine Optimization，AI搜索引擎优化 |
| 关键词命中率 | 客户关键词在AI回答中的出现频率 |
| 收录 | AI回答中包含目标关键词或品牌 |
| 掉落 | 之前收录的关键词不再出现 |
| 问题变体 | 基于关键词生成的不同问法 |

---

**开发计划结束**
