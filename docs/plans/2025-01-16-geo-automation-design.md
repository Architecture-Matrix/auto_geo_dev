# AutoGeo GEO全自动化系统 开发计划

**版本**: v2.0
**创建日期**: 2025-01-16
**更新日期**: 2025-01-16
**作者**: 开发者
**状态**: 开发计划

---

## 文档说明

本文档是**可执行的开发计划**，按阶段划分任务，每个任务包含：
- **创建文件**：需要新建/修改的文件路径
- **核心代码**：关键代码框架
- **验证标准**：如何验证完成

---

## 1. 总体架构（简明版）

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AutoGeo 系统架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        前端层 (Electron + Vue3)                       │    │
│  │  ┌──────────┬──────────┬──────────┬──────────┬──────────┬─────────┐  │    │
│  │  │项目看板  │关键词管理│文章生成  │质检中心  │收录监控  │数据报表 │  │    │
│  │  └──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼ HTTP API / WebSocket                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        后端层 (FastAPI)                               │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │                    API 路由层                                  │  │    │
│  │  ├───────────────────────────────────────────────────────────────┤  │    │
│  │  │                    服务层                                      │  │    │
│  │  │  ┌────────────┬────────────┬────────────┬────────────┬──────┐  │  │    │
│  │  │  │文章生成    │质检服务    │收录检测    │竞品分析    │定时器│  │  │    │
│  │  │  └────────────┴────────────┴────────────┴────────────┴──────┘  │  │    │
│  │  ├───────────────────────────────────────────────────────────────┤  │    │
│  │  │                    Playwright 自动化                           │  │    │
│  │  │  ┌────────────┬────────────┬────────────┬────────────────────┐  │  │    │
│  │  │  │知乎发布    │百家号发布  │头条发布    │AI平台收录检测     │  │  │    │
│  │  │  └────────────┴────────────┴────────────┴────────────────────┘  │  │    │
│  │  ├───────────────────────────────────────────────────────────────┤  │    │
│  │  │                    数据层 (SQLite)                             │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼ Webhook                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                   n8n 工作流中间层                                     │    │
│  │  ┌───────────────────────────────────────────────────────────────┐  │    │
│  │  │                    Agent 工作流                                │  │    │
│  │  │  ┌────────────┬────────────┬────────────┬────────────────────┐  │  │    │
│  │  │  │关键词蒸馏  │文章生成    │AI搜索     │竞品分析           │  │  │    │
│  │  │  └────────────┴────────────┴────────────┴────────────────────┘  │  │    │
│  │  └───────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        外部AI服务                                     │    │
│  │  ┌────────────┬────────────┬────────────┬─────────────────────────┐  │    │
│  │  │DeepSeek API│AI搜索      │企业信息API │通知服务 (邮件/IM)       │  │    │    │
│  │  └────────────┴────────────┴────────────┴─────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|------|
| **前端** | Vue 3 + TypeScript + Vite + Element Plus + Pinia | Electron桌面应用 |
| **后端** | FastAPI + SQLAlchemy + Playwright | Python异步框架 |
| **数据库** | SQLite | 轻量级本地数据库 |
| **工作流** | n8n | Agent工作流编排 |
| **AI服务** | DeepSeek API | 性价比最高 |

### 1.3 职责划分

| 功能 | 负责模块 | 原因 |
|-----|---------|------|
| 用户交互 | 前端 | 桌面应用形态 |
| API服务 | 后端 | 业务逻辑中心 |
| Playwright自动化 | 后端 | 资源可控，直接写库 |
| 定时任务 | 后端 APScheduler | 管理方便，可动态配置 |
| AI能力调用 | n8n webhook | 灵活编排，解耦AI服务 |
| 数据持久化 | 后端 | 直接操作SQLite |

---

## 2. 完整业务流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AutoGeo 完整业务流程                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐                                                      │
│  │ 1. 用户输入     │  公司名 + 关键词 + 公司资料                         │
│  │                │  ▶ 无资料时自动查询（调用n8n AI搜索）               │
│  └────────┬───────┘                                                      │
│           ▼                                                              │
│  ┌────────────────┐   ┌─────────────────┐                               │
│  │ 2. 关键词蒸馏   │   │ 2.1 难度评估    │  竞争度/搜索量分析             │
│  │    AI优化提取  │   │ 2.2 问题变体    │  每个关键词生成3-5个问法       │
│  └────────┬───────┘   └─────────────────┘                               │
│           ▼                                                              │
│  ┌────────────────┐   ┌─────────────────┐                               │
│  │ 3. GEO文章生成 │   │ 3.1 多版本生成  │  每个关键词生成3个版本         │
│  │                │   │ 3.2 风格适配    │  知乎/百家号风格自动调整       │
│  │                │   │ 3.3 提示词自定义 │  用户可自定义模板             │
│  │                │   │ 3.4 自动插图片  │  根据关键词自动插入相关图片    │
│  └────────┬───────┘   └─────────────────┘                               │
│           ▼                                                              │
│  ┌────────────────┐   ┌─────────────────┐                               │
│  │ 4. AI质检      │   │ 4.1 AI味检测    │  AI含量评分                   │
│  │                │   │ 4.2 敏感词检测  │  违禁词/广告词检测             │
│  │                │   │ 4.3 平台合规    │  字数/格式检查                 │
│  │                │   │ 4.4 自动优化    │  不合格则自动重写             │
│  └────────┬───────┘   └─────────────────┘                               │
│           ▼                                                              │
│  ┌────────────────┐                                                       │
│  │ 5. 人工质检     │  ▶ 预览效果 + 一键优化 + 确认发布                    │
│  └────────┬───────┘                                                      │
│           ▼                                                              │
│  ┌────────────────┐                                                       │
│  │ 6. 多平台发布   │  知乎、百家号、搜狐、头条号                          │
│  └────────┬───────┘                                                      │
│           ▼                                                              │
│  ┌────────────────┐   ┌─────────────────┐                               │
│  │ 7. 收录检测     │   │ Playwright自动  │  登录AI平台→输入问题→检测回答 │
│  │                │   │ 化查询收录      │  豆包/千问/DeepSeek          │
│  └────────┬───────┘   └─────────────────┘                               │
│           │                                                              │
│           ├──────────────────┐                                           │
│           ▼                  ▼                                           │
│  ┌────────────────┐   ┌─────────────────┐                               │
│  │ 8. 定时复检     │   │ 9. 数据统计     │  命中率/趋势/竞品对比         │
│  │   每日自动      │   │                 │  智能建议                     │
│  └────────┬───────┘   └────────┬────────┘                               │
│           │                    │                                         │
│           └──────────┬─────────┘                                         │
│                      ▼                                                   │
│           ┌─────────────────────┐                                        │
│           │ 10. 预警通知         │  收录掉落/新增/趋势建议                 │
│           └─────────────────────┘                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件设计

### 3.1 前端页面组件

| 页面 | 组件 | 功能 |
|-----|------|------|
| **项目看板** | ProjectList, StatusCard | 展示所有GEO项目及收录状态概览 |
| **关键词管理** | KeywordList, DistillPanel, QuestionPreview | 管理/添加关键词，查看蒸馏结果和问题变体 |
| **文章生成** | GeneratorForm, PromptEditor, VersionCompare, ArticleEditor, ImageInserter | 选择关键词生成文章，自定义提示词，多版本切换，自动插入图片 |
| **质检中心** | QualityReport, OptimizeSuggestion, OneClickOptimize | AI/人工质检，查看问题点，一键优化 |
| **发布管理** | PlatformSelector, ProgressBar, PublishHistory | 多平台发布，实时进度 |
| **收录监控** | AIPlatformLog, MatchResult, KeywordTag | 显示AI平台查询日志，关键词匹配结果 |
| **数据报表** | ChartView, TrendAnalysis, CompetitorAnalysis | 可视化数据展示，竞品对比 |
| **定时设置** | TimeConfig, ConcurrentConfig, StatusToggle | 配置自动检测任务（时间、并发数、开关） |
| **系统设置** | APIConfig, NotificationConfig, AccountManager | 全局配置 |

#### 公共组件

```typescript
// components/KeywordTag.vue
// 关键词标签，显示难度分值
interface KeywordTagProps {
  keyword: string
  difficultyScore: number  // 0-100
  searchIntent: 'informational' | 'commercial' | 'transactional'
}

// components/ArticleCard.vue
// 文章卡片，显示版本号、质检状态
interface ArticleCardProps {
  id: string
  title: string
  version: number  // A/B测试版本号
  qualityStatus: 'pending' | 'pass' | 'fail'
  qualityScore: number
}

// components/AIPlatformLog.vue
// AI平台查询日志
interface AIPlatformLogProps {
  platform: 'doubao' | 'qianwen' | 'deepseek'
  question: string
  answer: string
  keywordFound: boolean
  companyFound: boolean
  timestamp: Date
}
```

### 3.2 后端服务组件

#### 3.2.1 文章生成服务

```python
# backend/services/article_generator.py

class ArticleGenerator:
    """GEO文章生成服务"""

    def __init__(self, n8n_client: N8nClient):
        self.n8n = n8n_client

    async def generate(
        self,
        keyword: str,
        company: dict,
        prompt_template: str,
        target_platform: str = "zhihu",
        versions: int = 3
    ) -> list[Article]:
        """
        生成文章（支持多版本A/B测试）

        Args:
            keyword: 目标关键词
            company: 公司信息 {name, description, industry, ...}
            prompt_template: 提示词模板，支持变量:
                - {{keyword}}: 关键词
                - {{company}}: 公司名称
                - {{description}}: 公司描述
                - {{industry}}: 行业
            target_platform: 目标平台（影响风格）
            versions: 生成版本数量

        Returns:
            文章列表
        """
        articles = []

        # 1. 渲染提示词模板
        rendered_prompt = self._render_template(
            prompt_template,
            keyword,
            company
        )

        # 2. 根据目标平台调整风格
        style_config = self._get_platform_style(target_platform)

        # 3. 生成多个版本
        for i in range(versions):
            article = await self.n8n.call("generate-article", {
                "prompt": rendered_prompt,
                "style": style_config,
                "reduce_ai_flavor": True,
                "temperature": 0.8 + (i * 0.1),  # 每个版本温度不同
                "version": i + 1
            })
            articles.append(article)

        # 4. 自动插入相关图片
        for article in articles:
            article.images = await self._fetch_keyword_images(keyword, max=3)

        return articles

    def _render_template(self, template: str, keyword: str, company: dict) -> str:
        """渲染提示词模板"""
        return template.format(
            keyword=keyword,
            company=company.get("name", ""),
            description=company.get("description", ""),
            industry=company.get("industry", "")
        )

    def _get_platform_style(self, platform: str) -> dict:
        """获取平台风格配置"""
        styles = {
            "zhihu": {"tone": "professional", "length": "long"},
            "baijiahao": {"tone": "casual", "length": "medium"},
            "sohu": {"tone": "neutral", "length": "medium"},
            "toutiao": {"tone": "catchy", "length": "short"}
        }
        return styles.get(platform, styles["zhihu"])

    async def _fetch_keyword_images(self, keyword: str, max: int = 3) -> list[str]:
        """根据关键词获取相关图片URL"""
        # 调用图片搜索API或n8n工作流
        return await self.n8n.call("search-images", {
            "keyword": keyword,
            "max": max
        })
```

#### 3.2.2 收录检测服务

```python
# backend/services/geo_checker.py

class GeoChecker:
    """Playwright自动化检测AI平台收录"""

    PLATFORMS = {
        "doubao": {
            "url": "https://www.doubao.com",
            "input_selector": "textarea",
            "submit_selector": "button[type='submit']",
            "answer_selector": ".answer-content"
        },
        "qianwen": {
            "url": "https://tongyi.aliyun.com",
            "input_selector": "textarea",
            "submit_selector": ".send-btn",
            "answer_selector": ".message-content"
        },
        "deepseek": {
            "url": "https://www.deepseek.com",
            "input_selector": "textarea",
            "submit_selector": "button[type='submit']",
            "answer_selector": ".answer"
        }
    }

    def __init__(self, playwright_manager: PlaywrightManager):
        self.pm = playwright_manager

    async def check_keyword(
        self,
        keyword: str,
        company: str,
        questions: list[str],
        platforms: list[str] = None
    ) -> dict:
        """
        检测关键词在AI平台的收录情况

        Args:
            keyword: 目标关键词
            company: 公司名称
            questions: 问题变体列表
            platforms: 要检测的平台列表

        Returns:
            检测结果
        """
        if platforms is None:
            platforms = list(self.PLATFORMS.keys())

        results = {
            "keyword": keyword,
            "company": company,
            "total_queries": 0,
            "keyword_matched": 0,
            "company_matched": 0,
            "details": []
        }

        for platform_name in platforms:
            platform_result = await self._check_platform(
                platform_name,
                keyword,
                company,
                questions
            )
            results["details"].append(platform_result)
            results["total_queries"] += platform_result["total_queries"]
            results["keyword_matched"] += platform_result["keyword_matched"]
            results["company_matched"] += platform_result["company_matched"]

        # 计算命中率
        results["hit_rate"] = (
            results["keyword_matched"] / results["total_queries"] * 100
            if results["total_queries"] > 0 else 0
        )

        return results

    async def _check_platform(
        self,
        platform_name: str,
        keyword: str,
        company: str,
        questions: list[str]
    ) -> dict:
        """检测单个平台"""
        config = self.PLATFORMS[platform_name]
        queries_result = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 打开AI平台
            await page.goto(config["url"])

            for question in questions:
                # 定位输入框并输入问题
                await page.locator(config["input_selector"]).fill(question)

                # 点击发送
                await page.locator(config["submit_selector"]).click()

                # 等待AI回答生成
                await page.wait_for_selector(config["answer_selector"])
                answer_text = await page.locator(config["answer_selector"]).inner_text()

                # 检测关键词匹配
                query_result = {
                    "platform": platform_name,
                    "question": question,
                    "answer": answer_text,
                    "keyword_found": keyword in answer_text,
                    "company_found": company in answer_text,
                    "timestamp": datetime.now().isoformat()
                }
                queries_result.append(query_result)

            await browser.close()

        # 汇总该平台结果
        return {
            "platform": platform_name,
            "total_queries": len(questions),
            "keyword_matched": sum(1 for q in queries_result if q["keyword_found"]),
            "company_matched": sum(1 for q in queries_result if q["company_found"]),
            "queries": queries_result
        }
```

#### 3.2.3 竞品分析服务

```python
# backend/services/competitor_analyzer.py

class CompetitorAnalyzer:
    """调用AI获取竞品信息"""

    def __init__(self, n8n_client: N8nClient):
        self.n8n = n8n_client

    async def analyze(self, keyword: str, company: str) -> dict:
        """
        分析关键词下的竞品情况

        流程:
        1. 调用n8n webhook
        2. AI搜索获取竞品列表
        3. 分析竞品在AI平台的收录情况
        """
        prompt = f"""
        请分析关键词"{keyword}"下的竞品情况：

        1. 搜索该关键词，找出主要的竞争对手（5个以内）
        2. 分析每个竞品的产品定位、核心卖点
        3. 模拟用户在AI搜索引擎中提问相关问题时，竞品的被提及情况

        目标公司：{company}
        """

        result = await self.n8n.call("analyze-competitors", {
            "keyword": keyword,
            "company": company,
            "prompt": prompt
        })

        return {
            "keyword": keyword,
            "competitors": result.get("competitors", []),
            "analysis_date": datetime.now().isoformat()
        }
```

#### 3.2.4 定时任务服务

```python
# backend/services/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class GeoScheduler:
    """定时任务调度器"""

    def __init__(self, db: Database, geo_checker: GeoChecker):
        self.scheduler = AsyncIOScheduler()
        self.db = db
        self.geo_checker = geo_checker
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """从数据库加载配置"""
        config = self.db.get_scheduler_config()
        return {
            "check_time": config.get("check_time", "02:00"),
            "concurrent": config.get("concurrent", 3),
            "enabled": config.get("enabled", True)
        }

    def update_config(self, config: dict):
        """更新配置并重新调度"""
        self.config.update(config)
        self.db.save_scheduler_config(self.config)
        self._reschedule()

    def _reschedule(self):
        """重新调度任务"""
        self.scheduler.remove_all_jobs()

        if not self.config.get("enabled"):
            return

        hour, minute = self.config["check_time"].split(":")
        self.scheduler.add_job(
            self._daily_check,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_geo_check"
        )

    async def _daily_check(self):
        """每日收录检测任务"""
        # 获取所有活跃关键词
        active_keywords = self.db.get_active_keywords()

        # 并发检测
        semaphore = asyncio.Semaphore(self.config["concurrent"])

        tasks = [
            self._check_with_semaphore(semaphore, kw)
            for kw in active_keywords
        ]
        results = await asyncio.gather(*tasks)

        # 保存检测结果
        for result in results:
            self.db.save_check_result(result)

        # 生成预警通知
        await self._send_alerts(results)

    async def _check_with_semaphore(self, semaphore: asyncio.Semaphore, keyword: dict):
        """带信号量的检测"""
        async with semaphore:
            return await self.geo_checker.check_keyword(
                keyword=keyword["text"],
                company=keyword["company_name"],
                questions=keyword["questions"]
            )
```

---

## 4. 数据模型设计

### 4.1 数据库表结构

```sql
-- 项目表
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    description TEXT,
    industry VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 关键词表
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    difficulty_score INTEGER,  -- 0-100，难度分数
    search_intent VARCHAR(50),  -- informational/commercial/transactional
    status VARCHAR(20) DEFAULT 'active',  -- active/paused/archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 问题变体表
CREATE TABLE question_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- 文章表
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    version INTEGER NOT NULL,  -- A/B测试版本号
    title TEXT,
    content TEXT,
    images JSON,  -- 图片URL列表
    prompt_template TEXT,  -- 使用的提示词模板
    target_platform VARCHAR(50),
    quality_score DECIMAL(3,2),  -- 质检分数
    ai_flavor_score DECIMAL(3,2),  -- AI含量分数
    quality_status VARCHAR(20),  -- pending/pass/fail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- 发布记录表
CREATE TABLE publish_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_article_id VARCHAR(200),  -- 平台返回的文章ID
    platform_url TEXT,  -- 平台文章链接
    status VARCHAR(20),  -- pending/failed/success
    error_message TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

-- 收录检测记录表
CREATE TABLE index_check_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    platform VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    keyword_found BOOLEAN,
    company_found BOOLEAN,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_scheduled BOOLEAN DEFAULT FALSE,  -- 是否是定时任务检测
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- 定时任务配置表
CREATE TABLE scheduler_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_time VARCHAR(10) NOT NULL,  -- HH:MM格式
    concurrent INTEGER DEFAULT 3,
    enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预警通知表
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type VARCHAR(50),  -- keyword_drop/new_index/hit_rate_change
    keyword_id INTEGER,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);
```

---

## 5. API接口设计

### 5.1 关键词相关

```python
# POST /api/keywords/distill
# 蒸馏关键词
Request:
{
    "company_name": "某某科技",
    "industry": "CRM软件",
    "description": "提供中小企业CRM解决方案...",
    "base_keywords": ["CRM", "客户管理"],
    "count": 10
}

Response:
{
    "keywords": [
        {
            "keyword": "中小企业CRM",
            "difficulty_score": 90,
            "search_intent": "commercial",
            "questions": [
                "什么是中小企业CRM",
                "推荐一款中小企业CRM",
                "中小企业CRM怎么选"
            ]
        },
        ...
    ]
}

# POST /api/keywords/generate-questions
# 生成问题变体
Request:
{
    "keyword": "中小企业CRM",
    "count": 5
}

Response:
{
    "questions": [
        "什么是中小企业CRM系统",
        "推荐一款中小企业CRM",
        "中小企业CRM怎么选",
        "中小企业CRM哪家好",
        "中小企业CRM价格"
    ]
}
```

### 5.2 文章相关

```python
# POST /api/articles/generate
# 生成文章（多版本）
Request:
{
    "keyword_id": 1,
    "prompt_template": "请写一篇关于{{keyword}}的文章，公司是{{company}}...",
    "target_platform": "zhihu",
    "versions": 3,
    "insert_images": true
}

Response:
{
    "articles": [
        {
            "id": 1,
            "version": 1,
            "title": "...",
            "content": "...",
            "images": ["url1", "url2"],
            "quality_preview": {
                "ai_score": 0.3,
                "readability": 85
            }
        },
        ...
    ]
}

# POST /api/articles/check-quality
# 质检文章
Request:
{
    "article_id": 1,
    "target_platform": "zhihu"
}

Response:
{
    "overall_score": 4.2,
    "can_publish": true,
    "details": {
        "keyword_density": {"score": 85, "status": "pass"},
        "ai_detection": {"score": 35, "status": "pass"},
        "originality": {"score": 82, "status": "pass"},
        "sensitive_words": {"found": [], "status": "pass"},
        "platform_compliance": {"status": "pass"}
    }
}

# POST /api/articles/optimize
# 自动优化文章
Request:
{
    "article_id": 1,
    "issues": ["ai_flavor_high", "keyword_density_low"]
}

Response:
{
    "optimized_content": "...",
    "improvements": ["降低AI味", "增加关键词密度"]
}
```

### 5.3 收录检测相关

```python
# POST /api/geo/check
# 手动触发收录检测
Request:
{
    "keyword_ids": [1, 2, 3],
    "platforms": ["doubao", "qianwen", "deepseek"],
    "use_questions": true  # 是否使用问题变体
}

Response:
{
    "check_id": "check_xxx",
    "summary": {
        "total_queries": 45,
        "keyword_matched": 27,
        "company_matched": 18,
        "hit_rate": 60.0
    },
    "details": [...]
}

# GET /api/geo/check/history?keyword_id=1
# 获取收录检测历史
Response:
{
    "keyword_id": 1,
    "keyword": "中小企业CRM",
    "history": [
        {
            "date": "2025-01-15",
            "hit_rate": 60.0,
            "platforms": {"doubao": 66, "qianwen": 55, "deepseek": 70}
        },
        ...
    ]
}
```

### 5.4 定时任务相关

```python
# GET /api/scheduler/config
# 获取定时任务配置
Response:
{
    "check_time": "02:00",
    "concurrent": 3,
    "enabled": true,
    "last_run": "2025-01-15 02:00:00",
    "next_run": "2025-01-16 02:00:00"
}

# PUT /api/scheduler/config
# 更新定时任务配置
Request:
{
    "check_time": "03:00",
    "concurrent": 5,
    "enabled": true
}

# POST /api/scheduler/trigger
# 手动触发定时任务
Response:
{
    "task_id": "task_xxx",
    "status": "running"
}

# GET /api/scheduler/status
# 获取当前任务状态
Response:
{
    "status": "running",  # idle/running/completed/failed
    "progress": "60/100",
    "started_at": "2025-01-16 02:00:00",
    "estimated_finish": "2025-01-16 03:30:00"
}
```

### 5.5 竞品分析相关

```python
# POST /api/competitors/analyze
# 竞品分析
Request:
{
    "keyword": "中小企业CRM",
    "company": "某某科技"
}

Response:
{
    "keyword": "中小企业CRM",
    "competitors": [
        {
            "name": "竞品A",
            "positioning": "面向大型企业的CRM系统",
            "selling_points": ["功能强大", "可定制"],
            "ai_mention_rate": 75.0  # AI提及率
        },
        ...
    ],
    "analysis_date": "2025-01-16"
}
```

---

## 6. 待修复Bug列表

### 6.1 知乎发布Bug

| 项目 | 详情 |
|-----|------|
| **平台** | 知乎 |
| **症状** | Playwright发布后，知乎平台找不到文章；详情页是编辑状态，**有内容但标题丢失** |
| **影响范围** | 知乎平台发布功能 |
| **优先级** | P0（高） |
| **根因（推测）** | 脚本可能没有正确填入标题字段，或点击发布时机不对 |
| **修复计划** | 检查 `backend/services/playwright/publishers/zhihu.py` |

```python
# 需要检查的关键代码位置
# backend/services/playwright/publishers/zhihu.py

class ZhihuPublisher(BasePublisher):
    async def publish(self, article: Article) -> dict:
        # TODO: 检查标题填充逻辑
        # TODO: 检查发布按钮点击时机
        pass
```

---

## 7. 开发计划

### 7.1 功能优先级

| 功能模块 | 优先级 | 预计工期 | 依赖 |
|---------|-------|---------|------|
| 修复知乎发布Bug | P0 | 1天 | - |
| 关键词蒸馏+问题变体 | P0 | 1周 | n8n webhook |
| 文章生成（多版本+自定义提示词+图片） | P0 | 1周 | 关键词蒸馏 |
| AI质检 | P0 | 3天 | 文章生成 |
| 收录检测（Playwright） | P0 | 2周 | 技术验证 |
| 定时任务系统 | P0 | 1周 | 收录检测 |
| 数据统计报表 | P1 | 1周 | 收录检测 |
| 竞品分析 | P1 | 3天 | AI搜索 |
| 预警通知 | P1 | 2天 | 数据统计 |

### 7.2 技术验证任务

| 验证项 | 成功标准 | 负责人 | 完成时间 |
|-------|---------|--------|---------|
| Playwright检测豆包 | 成功获取回答并检测关键词 | - | Week 1 Day 1 |
| Playwright检测千问 | 同上 | - | Week 1 Day 2 |
| Playwright检测DeepSeek | 同上 | - | Week 1 Day 3 |
| 并发检测稳定性 | 5个并发不出错 | - | Week 1 Day 4 |
| n8n webhook集成 | 成功调用并返回结果 | - | Week 1 Day 5 |

---

## 8. 附录

### 8.1 术语表

| 术语 | 说明 |
|-----|------|
| GEO | Generative Engine Optimization，AI搜索引擎优化 |
| 关键词命中率 | 客户关键词在AI回答中的出现频率 |
| 收录 | AI回答中包含目标关键词或品牌 |
| 掉落 | 之前收录的关键词不再出现在AI回答中 |
| 问题变体 | 基于关键词生成的不同问法，用于多角度检测收录 |
| AI味 | 文章内容看起来像AI生成的程度 |
| n8n | 开源工作流自动化工具 |

### 8.2 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|-----|------|----------|--------|
| v1.0 | 2025-01-16 | 初始设计文档 | 开发者 |

---

**文档结束**
