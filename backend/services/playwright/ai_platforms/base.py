# -*- coding: utf-8 -*-
"""
AI平台检测器基类
用这个抽象基类定义检测器的统一接口！
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from playwright.async_api import Page, BrowserContext
from loguru import logger
import asyncio
import time
import random


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
        self.retry_count = 3
        self.retry_delay = 2
        self.operation_log = []

    def _log(self, level: str, message: str, **kwargs):
        """
        增强的日志记录方法

        Args:
            level: 日志级别 (info, warning, error, debug)
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "platform": self.name,
            "level": level,
            "message": message,
            **kwargs
        }
        self.operation_log.append(log_entry)

        if level == "info":
            logger.info(f"[{self.name}] {message}")
        elif level == "warning":
            logger.warning(f"[{self.name}] {message}")
        elif level == "error":
            logger.error(f"[{self.name}] {message}")
        elif level == "debug":
            logger.debug(f"[{self.name}] {message}")

    async def _retry_operation(
        self,
        operation,
        operation_name: str,
        max_retries: int = None,
        retry_delay: int = None
    ) -> Dict[str, Any]:
        """
        通用重试机制

        Args:
            operation: 异步操作函数
            operation_name: 操作名称（用于日志）
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            操作结果
        """
        max_retries = max_retries or self.retry_count
        retry_delay = retry_delay or self.retry_delay

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                self._log("info", f"开始执行: {operation_name} (尝试 {attempt}/{max_retries})")
                result = await operation()

                if result.get("success"):
                    self._log("info", f"操作成功: {operation_name}")
                    return result
                else:
                    error_msg = result.get("error_msg", "未知错误")
                    self._log("warning", f"操作失败: {operation_name}, 错误: {error_msg}")

                    if attempt < max_retries:
                        delay = retry_delay + random.uniform(0, 1)
                        self._log("info", f"等待 {delay:.2f} 秒后进行第 {attempt + 1} 次重试")
                        await asyncio.sleep(delay)
                    else:
                        self._log("error", f"操作最终失败: {operation_name}, 错误: {error_msg}")
                        return result

            except Exception as e:
                last_error = str(e)
                self._log("error", f"操作异常: {operation_name}, 错误: {e}")

                if attempt < max_retries:
                    delay = retry_delay + random.uniform(0, 1)
                    self._log("info", f"等待 {delay:.2f} 秒后进行第 {attempt + 1} 次重试")
                    await asyncio.sleep(delay)

        return {
            "success": False,
            "error_msg": last_error or f"操作失败，已重试 {max_retries} 次"
        }

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
        增强的导航到AI平台页面

        Returns:
            是否成功导航
        """
        try:
            self._log("info", f"正在导航到平台页面: {self.url}")

            # 使用更灵活的等待策略
            await page.goto(
                self.url, 
                wait_until="load",  # 改为load，更快速
                timeout=60000  # 增加超时时间
            )

            # 等待页面稳定
            await page.wait_for_load_state("networkidle", timeout=30000)
            
            self._log("info", f"页面加载完成: {self.name}")

            # 增加页面稳定等待时间
            await asyncio.sleep(3)
            
            # 检查是否需要登录（通过检测常见的登录元素）
            login_indicators = [
                "[class*='login']",
                "[id*='login']",
                "[class*='auth']",
                "[id*='auth']",
                "button*='登录'",
                "button*='Sign in'"
            ]
            
            has_login = False
            for indicator in login_indicators:
                try:
                    elements = await page.query_selector_all(indicator)
                    if elements:
                        has_login = True
                        break
                except Exception:
                    continue
            
            if has_login:
                self._log("info", "检测到登录页面，请手动完成登录")
                # 给用户30秒时间完成登录
                await asyncio.sleep(30)
                # 重新等待页面稳定
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)

            return True
        except Exception as e:
            self._log("error", f"导航失败: {e}")
            return False

    async def wait_for_selector(
        self,
        page: Page,
        selectors: List[str],
        timeout: int = 20000
    ) -> tuple:
        """
        增强的智能等待选择器出现（支持多个备选选择器）

        Args:
            page: Playwright Page对象
            selectors: 选择器列表（按优先级排序）
            timeout: 最大等待时间（毫秒）

        Returns:
            (成功标志, 匹配到的选择器)
        """
        start_time = time.time()
        self._log("info", f"等待选择器: {selectors}, 超时时间: {timeout}ms")

        # 增加更多通用选择器
        enhanced_selectors = selectors + [
            "input[type='text']",
            "input[type='textarea']",
            "[contenteditable='true']",
            "[class*='message-input']",
            "[class*='user-input']",
            "[class*='chat-box']",
            "[id*='input']",
            "[name*='input']"
        ]

        # 分批次等待，每批3个选择器
        batch_size = 3
        for i in range(0, len(enhanced_selectors), batch_size):
            batch_selectors = enhanced_selectors[i:i+batch_size]
            batch_timeout = timeout // (len(enhanced_selectors) // batch_size + 1)
            
            self._log("debug", f"尝试选择器批次: {batch_selectors}")
            
            for selector in batch_selectors:
                try:
                    self._log("debug", f"尝试选择器: {selector}")
                    
                    # 先检查元素是否存在
                    elements = await page.query_selector_all(selector)
                    if elements:
                        self._log("info", f"选择器匹配成功: {selector}")
                        return True, selector
                    
                    # 再等待元素出现
                    await page.wait_for_selector(selector, timeout=batch_timeout)
                    
                    self._log("info", f"选择器匹配成功: {selector}")
                    return True, selector

                except Exception as e:
                    self._log("debug", f"选择器 {selector} 未找到: {e}")
                    continue

            # 批次之间短暂休息
            await asyncio.sleep(0.5)

        elapsed_time = (time.time() - start_time) * 1000
        self._log("warning", f"所有选择器都未找到, 耗时: {elapsed_time:.0f}ms")
        return False, None

    async def wait_for_answer_generation(
        self,
        page: Page,
        initial_content: str,
        selector: str = "body",
        timeout: int = 60000,
        check_interval: float = 1.0
    ) -> Dict[str, Any]:
        """
        增强的智能等待AI回答生成完成

        Args:
            page: Playwright Page对象
            initial_content: 初始页面内容
            selector: 要监控的选择器
            timeout: 最大等待时间（毫秒）
            check_interval: 检查间隔（秒）

        Returns:
            等待结果信息
        """
        self._log("info", f"开始智能等待回答生成, 超时时间: {timeout}ms")

        start_time = time.time()
        last_content = initial_content
        stable_count = 0
        required_stable_checks = 3
        min_content_length = 50

        while (time.time() - start_time) < timeout / 1000:
            try:
                current_content = await page.inner_text(selector)

                content_length = len(current_content.strip())

                if content_length > min_content_length and current_content != last_content:
                    self._log("debug", f"检测到内容更新, 长度: {content_length} 字符")

                    stable_count = 0

                    last_content = current_content

                    await asyncio.sleep(check_interval)

                elif content_length > min_content_length and current_content == last_content:
                    stable_count += 1
                    self._log("debug", f"内容稳定检查: {stable_count}/{required_stable_checks}")

                    if stable_count >= required_stable_checks:
                        elapsed_time = (time.time() - start_time) * 1000
                        self._log("info", f"回答生成完成, 耗时: {elapsed_time:.0f}ms, 内容长度: {content_length}")

                        return {
                            "success": True,
                            "content_length": content_length,
                            "elapsed_time": elapsed_time,
                            "stable": True
                        }

                    await asyncio.sleep(check_interval)

                else:
                    await asyncio.sleep(check_interval * 0.5)

            except Exception as e:
                self._log("warning", f"等待回答时发生异常: {e}")
                await asyncio.sleep(check_interval)

        elapsed_time = (time.time() - start_time) * 1000
        current_content = await page.inner_text(selector)
        content_length = len(current_content.strip())

        self._log("warning", f"等待回答超时, 耗时: {elapsed_time:.0f}ms, 内容长度: {content_length}")

        return {
            "success": content_length > min_content_length,
            "content_length": content_length,
            "elapsed_time": elapsed_time,
            "stable": stable_count >= required_stable_checks
        }

    async def get_answer_content(
        self,
        page: Page,
        question: str
    ) -> Dict[str, Any]:
        """
        增强的获取AI回答内容

        Args:
            page: Playwright Page对象
            question: 用户问题（用于过滤）

        Returns:
            获取结果
        """
        self._log("info", "开始获取AI回答内容")

        answer_selectors = [
            "[class*='assistant']",
            "[class*='ai-message']",
            "[data-role='assistant']",
            "[class*='answer-content']",
            "[class*='chat-answer']",
            ".markdown-body",
            "[class*='response']",
            "[class*='result']",
            "[class*='content-body']"
        ]

        answer_text = ""
        matched_selector = None

        for selector in answer_selectors:
            try:
                self._log("debug", f"尝试选择器: {selector}")

                elements = await page.query_selector_all(selector)

                if elements:
                    self._log("debug", f"选择器 {selector} 找到 {len(elements)} 个元素")

                    for element in reversed(elements):
                        try:
                            element_text = await element.inner_text()
                            element_text = element_text.strip()

                            if len(element_text) > 100:
                                if question not in element_text[:50]:
                                    answer_text = element_text
                                    matched_selector = selector
                                    self._log("info", f"找到AI回答, 选择器: {selector}, 长度: {len(answer_text)}")
                                    break

                        except Exception as e:
                            self._log("debug", f"获取元素文本失败: {e}")
                            continue

                    if answer_text:
                        break

            except Exception as e:
                self._log("debug", f"选择器 {selector} 处理失败: {e}")
                continue

        if not answer_text:
            self._log("warning", "标准选择器未找到回答, 尝试备用方法")

            page_text = await page.inner_text("body")
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]

            for line in reversed(lines):
                if len(line) > 100 and question not in line[:30]:
                    answer_text = line
                    matched_selector = "body-text-fallback"
                    self._log("info", f"使用备用方法找到回答, 长度: {len(answer_text)}")
                    break

        if answer_text:
            self._log("info", f"成功获取回答内容, 长度: {len(answer_text)} 字符")
            return {
                "success": True,
                "answer": answer_text[:5000],
                "selector": matched_selector,
                "length": len(answer_text)
            }
        else:
            self._log("warning", "未能获取到回答内容")
            return {
                "success": False,
                "answer": "",
                "selector": None,
                "length": 0
            }

    def check_keywords_in_text(
        self,
        text: str,
        keyword: str,
        company: str
    ) -> Dict[str, Any]:
        """
        检查文本中是否包含关键词和公司名

        Args:
            text: 待检测文本
            keyword: 目标关键词
            company: 公司名称

        Returns:
            检测结果详细信息
        """
        self._log("info", f"开始关键词检测, 文本长度: {len(text)}")

        import re
        cleaned_text = re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        text_lower = cleaned_text.lower()
        keyword_lower = keyword.lower()
        company_lower = company.lower()

        keyword_count = text_lower.count(keyword_lower)
        company_count = text_lower.count(company_lower)

        keyword_positions = [m.start() for m in re.finditer(re.escape(keyword_lower), text_lower)]

        result = {
            "keyword_found": keyword_count > 0,
            "keyword_count": keyword_count,
            "keyword_positions": keyword_positions[:5],
            "company_found": company_count > 0,
            "company_count": company_count,
            "confidence": 0.0,
            "reason": ""
        }

        if keyword_count > 0:
            result["keyword_found"] = True
            result["confidence"] = min(0.5 + keyword_count * 0.1, 0.9)
            result["reason"] = f"关键词'{keyword}'出现{keyword_count}次"

        if company_count > 0:
            result["company_found"] = True
            result["confidence"] = min(result["confidence"] + 0.2, 0.95)
            result["reason"] += f", 公司名'{company}'出现{company_count}次"

        if len(cleaned_text) < 100 and keyword_count > 0:
            result["confidence"] = min(result["confidence"] + 0.1, 0.85)

        self._log("info", f"关键词检测完成: 关键词={result['keyword_found']}({keyword_count}次), "
                         f"公司={result['company_found']}({company_count}次), "
                         f"置信度={result['confidence']:.2f}")

        return result

    async def clear_chat_history(self, page: Page) -> bool:
        """
        清理聊天历史记录（如果支持）

        Returns:
            是否成功清理
        """
        self._log("info", "尝试清理聊天历史")

        try:
            clear_selectors = [
                "[class*='new-chat']",
                "[class*='new-conversation']",
                "[class*='clear-history']",
                "button[title*='新对话']",
                "[class*='refresh'] button"
            ]

            for selector in clear_selectors:
                try:
                    elements = await page.query_selector_all(selector)

                    if elements:
                        for element in elements[:1]:
                            try:
                                await element.click(timeout=3000)
                                await asyncio.sleep(1)
                                self._log("info", f"成功点击清理按钮: {selector}")
                                return True
                            except Exception:
                                continue
                except Exception:
                    continue

            self._log("info", "未找到清理按钮或无需清理")
            return True

        except Exception as e:
            self._log("error", f"清理聊天历史失败: {e}")
            return False

    def get_operation_log(self) -> List[Dict]:
        """
        获取操作日志

        Returns:
            操作日志列表
        """
        return self.operation_log.copy()

    def clear_operation_log(self):
        """
        清空操作日志
        """
        self.operation_log.clear()
