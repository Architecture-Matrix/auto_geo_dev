# -*- coding: utf-8 -*-
"""
浏览器辅助工具
封装Playwright MCP操作
"""

import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any


class BrowserHelper:
    """
    浏览器辅助类
    我把Playwright MCP封装一下，用起来方便
    """

    def __init__(self, mcp_browser):
        """
        初始化
        :param mcp_browser: MCP浏览器工具实例
        """
        self.browser = mcp_browser
        self.current_url = None

    async def navigate(self, url: str, wait_for: str = "load") -> bool:
        """
        导航到指定URL
        :param url: 目标URL
        :param wait_for: 等待类型 (load/domcontentloaded/networkidle)
        :return: 是否成功
        """
        try:
            await self.browser.browser_navigate(url=url)
            self.current_url = url
            await self.browser_wait_for_stable()
            return True
        except Exception as e:
            print(f"[FAIL] 导航失败: {e}")
            return False

    async def browser_wait_for_stable(self, timeout: float = 2.0):
        """等待页面稳定"""
        await time.sleep(timeout)

    async def get_snapshot(self) -> Optional[dict]:
        """获取页面快照"""
        try:
            result = await self.browser.browser_snapshot()
            if isinstance(result, str):
                # 如果返回的是markdown，解析出结构
                return {"content": result}
            return result
        except Exception as e:
            print(f"[FAIL] 获取快照失败: {e}")
            return None

    async def click_element(self, ref: str, description: str = "") -> bool:
        """
        点击元素
        :param ref: 元素ref
        :param description: 元素描述
        :return: 是否成功
        """
        try:
            await self.browser.browser_click(
                element=description or "元素",
                ref=ref
            )
            await self.browser_wait_for_stable(0.5)
            return True
        except Exception as e:
            print(f"[FAIL] 点击失败 [{description}]: {e}")
            return False

    async def fill_input(self, ref: str, text: str, description: str = "") -> bool:
        """
        填写输入框
        :param ref: 元素ref
        :param text: 填写内容
        :param description: 元素描述
        :return: 是否成功
        """
        try:
            await self.browser.browser_type(
                element=description or "输入框",
                ref=ref,
                text=text
            )
            await self.browser_wait_for_stable(0.3)
            return True
        except Exception as e:
            print(f"[FAIL] 填写失败 [{description}]: {e}")
            return False

    async def select_option(self, ref: str, values: List[str], description: str = "") -> bool:
        """
        选择下拉选项
        :param ref: 元素ref
        :param values: 选项值列表
        :param description: 元素描述
        :return: 是否成功
        """
        try:
            await self.browser.browser_select_option(
                element=description or "下拉框",
                ref=ref,
                values=values
            )
            await self.browser_wait_for_stable(0.3)
            return True
        except Exception as e:
            print(f"[FAIL] 选择失败 [{description}]: {e}")
            return False

    async def get_console_errors(self) -> List[str]:
        """获取控制台错误"""
        try:
            messages = await self.browser.browser_console_messages(level="error")
            return messages if isinstance(messages, list) else []
        except Exception as e:
            print(f"[FAIL] 获取控制台错误失败: {e}")
            return []

    async def take_screenshot(self, filename: str) -> bool:
        """
        截图
        :param filename: 保存文件名
        :return: 是否成功
        """
        try:
            await self.browser.browser_take_screenshot(filename=filename)
            return True
        except Exception as e:
            print(f"[FAIL] 截图失败: {e}")
            return False

    async def wait_for_text(self, text: str, timeout: int = 10) -> bool:
        """
        等待文本出现
        :param text: 目标文本
        :param timeout: 超时秒数
        :return: 是否出现
        """
        for _ in range(timeout * 2):
            snapshot = await self.get_snapshot()
            if snapshot and text in str(snapshot):
                return True
            await time.sleep(0.5)
        return False

    async def find_element_by_text(self, text: str, snapshot: dict = None) -> Optional[str]:
        """
        通过文本查找元素ref
        :param text: 目标文本
        :param snapshot: 页面快照（可选）
        :return: 元素ref或None
        """
        if not snapshot:
            snapshot = await self.get_snapshot()

        if not snapshot:
            return None

        # 这里简化处理，实际需要解析快照结构
        content = str(snapshot)
        if text in content:
            # 返回一个假设的ref，实际实现需要更复杂的解析
            return f"ref-{text}"

        return None

    async def fill_form(self, fields: List[Dict[str, Any]]) -> bool:
        """
        批量填写表单
        :param fields: 字段列表 [{"name": "", "type": "", "ref": "", "value": ""}]
        :return: 是否全部成功
        """
        try:
            await self.browser.browser_fill_form(fields=fields)
            await self.browser_wait_for_stable(0.5)
            return True
        except Exception as e:
            print(f"[FAIL] 批量填写失败: {e}")
            return False
