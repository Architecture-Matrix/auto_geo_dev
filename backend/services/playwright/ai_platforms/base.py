# -*- coding: utf-8 -*-
"""
AI平台检测器基类
用这个抽象基类定义检测器的统一接口！
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
from loguru import logger
import asyncio


class AIPlatformChecker(ABC):
    """
    AI平台检测器基类

    注意：所有AI平台检测器都要继承这个类！
    """

    def __init__(self, platform_id: str, config: Dict[str, Any]):
        """
        初始化检测器

        Args:
            platform_id: 平台ID
            config: 平台配置
        """
        self.platform_id = platform_id
        self.config = config
        self.name = config.get("name", platform_id)
        self.url = config.get("url", "")
        self.color = config.get("color", "#333333")

    @abstractmethod
    async def check(
        self,
        page: Page,
        question: str,
        keyword: str,
        company: str
    ) -> Dict[str, Any]:
        """
        检测AI平台收录情况

        Args:
            page: Playwright Page对象
            question: 检测使用的问题
            keyword: 目标关键词
            company: 公司名称

        Returns:
            检测结果：
            {
                "success": bool,
                "answer": str,
                "keyword_found": bool,
                "company_found": bool,
                "error_msg": str
            }
        """
        pass

    async def navigate_to_page(self, page: Page) -> bool:
        """
        导航到AI平台页面

        Returns:
            是否成功导航
        """
        try:
            await page.goto(self.url, wait_until="networkidle")
            logger.info(f"导航到AI平台: {self.name}")
            await asyncio.sleep(2)  # 等待页面完全加载
            return True
        except Exception as e:
            logger.error(f"导航失败: {self.name}, {e}")
            return False

    async def wait_for_selector(
        self,
        page: Page,
        selector: str,
        timeout: int = 10000
    ) -> bool:
        """
        等待选择器出现

        注意：AI平台加载慢，需要耐心等待！
        """
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            logger.warning(f"等待选择器超时: {selector}")
            return False

    def check_keywords_in_text(
        self,
        text: str,
        keyword: str,
        company: str
    ) -> Dict[str, bool]:
        """
        检查文本中是否包含关键词和公司名

        Args:
            text: 待检测文本
            keyword: 关键词
            company: 公司名称

        Returns:
            {keyword_found: bool, company_found: bool}
        """
        text_lower = text.lower()
        return {
            "keyword_found": keyword.lower() in text_lower,
            "company_found": company.lower() in text_lower
        }
