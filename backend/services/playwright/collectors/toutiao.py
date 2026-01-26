# -*- coding: utf-8 -*-
"""
今日头条文章收集适配器
爬取头条热门文章！
"""

import asyncio
import re
from typing import Dict, Any, Optional, List
from playwright.async_api import Page
from loguru import logger

from .base import BaseCollector


class ToutiaoCollector(BaseCollector):
    """
    今日头条文章收集适配器

    搜索页面：https://so.toutiao.com/search?keyword={keyword}
    """

    async def search(self, page: Page, keyword: str) -> List[Dict[str, Any]]:
        """搜索头条文章"""
        try:
            # 1. 导航到搜索页
            search_url = f"https://so.toutiao.com/search?keyword={keyword}&pd=information"
            await page.goto(search_url, wait_until="networkidle")
            # 增加延时，等待页面完全加载，防止被检测为爬虫
            await page.wait_for_timeout(3000)
            logger.info(f"[头条] 已导航到搜索页: {keyword}")

            # 2. 滚动加载更多
            await self._scroll_to_load_more(page, scroll_count=3)

            # 3. 提取搜索结果
            articles = await self._extract_search_results(page)

            return articles

        except Exception as e:
            logger.error(f"[头条] 搜索失败: {e}")
            return []

    async def _scroll_to_load_more(self, page: Page, scroll_count: int = 3):
        """滚动页面加载更多"""
        for i in range(scroll_count):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # 增加延时，每次滚动后等待 3 秒，防止被检测为爬虫
            await page.wait_for_timeout(3000)
            logger.debug(f"[头条] 滚动加载 {i + 1}/{scroll_count}")

    async def _extract_search_results(self, page: Page) -> List[Dict[str, Any]]:
        """提取搜索结果"""
        articles = []

        try:
            # 获取搜索结果项
            cards = await page.query_selector_all("[class*='result-content'], .result-item, .article-card")

            for card in cards:
                try:
                    # 提取标题和链接
                    title_elem = await card.query_selector("a[class*='title'], .title a, h3 a")
                    if not title_elem:
                        continue

                    title = await title_elem.text_content()
                    href = await title_elem.get_attribute("href")

                    # 处理相对链接
                    if href and not href.startswith("http"):
                        href = f"https://www.toutiao.com{href}"

                    # 提取阅读量/评论数（头条通常显示阅读量）
                    reads = 0
                    comments = 0

                    # 尝试提取数据
                    meta_elem = await card.query_selector("[class*='read'], [class*='comment'], .meta")
                    if meta_elem:
                        meta_text = await meta_elem.text_content()
                        reads = self._parse_number(meta_text)

                    # 提取作者
                    author = ""
                    author_elem = await card.query_selector("[class*='source'], [class*='author'], .name")
                    if author_elem:
                        author = await author_elem.text_content()

                    if title and href:
                        articles.append({
                            "title": title.strip(),
                            "url": href,
                            "likes": reads // 100,  # 估算点赞数
                            "reads": reads,
                            "comments": comments,
                            "author": author.strip() if author else "",
                        })

                except Exception as e:
                    logger.debug(f"[头条] 提取单条结果失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"[头条] 提取搜索结果失败: {e}")

        return articles

    async def extract_content(self, page: Page, url: str) -> Optional[str]:
        """提取文章正文"""
        try:
            await page.goto(url, wait_until="networkidle")
            # 增加延时，等待页面完全加载
            await page.wait_for_timeout(3000)

            # 尝试多种选择器
            selectors = [
                "article",
                ".article-content",
                ".content",
                "[class*='article-body']",
                ".post-content",
            ]

            for selector in selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        content = await elem.text_content()
                        if content and len(content) > 100:
                            logger.info(f"[头条] 提取正文成功: {len(content)} 字符")
                            return content.strip()
                except Exception:
                    continue

            logger.warning(f"[头条] 未能提取正文: {url}")
            return None

        except Exception as e:
            logger.error(f"[头条] 提取正文失败: {e}")
            return None

    def _parse_number(self, text: str) -> int:
        """解析数字"""
        if not text:
            return 0

        text = text.strip().lower()
        match = re.search(r'([\d.]+)\s*([kwm万])?', text)
        if not match:
            return 0

        num = float(match.group(1))
        unit = match.group(2)

        if unit in ['k', 'K']:
            num *= 1000
        elif unit in ['w', 'W', '万']:
            num *= 10000
        elif unit in ['m', 'M']:
            num *= 1000000

        return int(num)
