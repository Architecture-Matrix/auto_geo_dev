# -*- coding: utf-8 -*-
"""
文章收集适配器基类
用适配器模式实现各平台收集，遵循开闭原则！
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from playwright.async_api import Page, BrowserContext
from loguru import logger


@dataclass
class CollectedArticle:
    """收集到的文章数据结构"""
    title: str
    url: str
    content: str
    likes: int = 0
    reads: int = 0
    comments: int = 0
    author: str = ""
    platform: str = ""
    publish_time: str = ""


class BaseCollector(ABC):
    """
    基础文章收集适配器
    注意：所有平台收集器都要继承这个类！
    """

    def __init__(self, platform_id: str, config: Dict[str, Any]):
        self.platform_id = platform_id
        self.config = config
        self.name = config.get("name", platform_id)
        self.search_url = config.get("search_url", "")
        self.min_likes = config.get("min_likes", 100)
        self.min_reads = config.get("min_reads", 1000)

    @abstractmethod
    async def search(self, page: Page, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索关键词相关文章

        Args:
            page: Playwright Page对象
            keyword: 搜索关键词

        Returns:
            搜索结果列表：[{title, url, likes, reads, ...}, ...]
        """
        pass

    @abstractmethod
    async def extract_content(self, page: Page, url: str) -> Optional[str]:
        """
        提取文章正文内容

        Args:
            page: Playwright Page对象
            url: 文章URL

        Returns:
            文章正文内容
        """
        pass

    async def collect(self, page: Page, keyword: str) -> List[CollectedArticle]:
        """
        收集爆火文章（主流程）

        Args:
            page: Playwright Page对象
            keyword: 搜索关键词

        Returns:
            符合条件的文章列表
        """
        try:
            # 1. 搜索文章
            search_results = await self.search(page, keyword)
            logger.info(f"[{self.name}] 搜索到 {len(search_results)} 篇文章")

            # 2. 筛选爆火文章
            trending_articles = self._filter_trending(search_results)
            logger.info(f"[{self.name}] 筛选出 {len(trending_articles)} 篇爆火文章")

            # 3. 提取正文内容
            collected = []
            for article in trending_articles:
                content = await self.extract_content(page, article["url"])
                if content:
                    collected.append(CollectedArticle(
                        title=article.get("title", ""),
                        url=article.get("url", ""),
                        content=content,
                        likes=article.get("likes", 0),
                        reads=article.get("reads", 0),
                        comments=article.get("comments", 0),
                        author=article.get("author", ""),
                        platform=self.platform_id,
                        publish_time=article.get("publish_time", "")
                    ))

            return collected

        except Exception as e:
            logger.error(f"[{self.name}] 收集文章失败: {e}")
            return []

    def _filter_trending(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        筛选爆火文章

        筛选逻辑：点赞数 > min_likes 或 阅读量 > min_reads
        """
        trending = []
        for article in articles:
            likes = article.get("likes", 0)
            reads = article.get("reads", 0)

            if likes > self.min_likes or reads > self.min_reads:
                trending.append(article)
                logger.debug(f"[{self.name}] 爆火: {article.get('title', '')[:30]}... "
                           f"(👍{likes}, 👁{reads})")

        return trending

    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        """等待选择器出现"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"等待选择器超时: {selector}, {e}")
            return False

    async def navigate_to_search(self, page: Page, keyword: str) -> bool:
        """导航到搜索页面"""
        try:
            search_url = self.search_url.format(keyword=keyword)
            await page.goto(search_url, wait_until="networkidle")
            logger.info(f"[{self.name}] 已导航到搜索页: {keyword}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] 导航搜索页失败: {e}")
            return False


class CollectorRegistry:
    """
    收集器注册表
    用这个来管理所有平台的收集器！
    """

    def __init__(self):
        self._collectors: Dict[str, BaseCollector] = {}

    def register(self, platform_id: str, collector: BaseCollector):
        """注册收集器"""
        self._collectors[platform_id] = collector
        logger.info(f"收集器已注册: {platform_id}")

    def get(self, platform_id: str) -> Optional[BaseCollector]:
        """获取收集器"""
        return self._collectors.get(platform_id)

    def list_all(self) -> Dict[str, BaseCollector]:
        """列出所有收集器"""
        return self._collectors.copy()


# 全局注册表
collector_registry = CollectorRegistry()


def get_collector(platform_id: str) -> Optional[BaseCollector]:
    """获取平台收集器"""
    return collector_registry.get(platform_id)


def list_collectors() -> Dict[str, BaseCollector]:
    """列出所有收集器"""
    return collector_registry.list_all()
