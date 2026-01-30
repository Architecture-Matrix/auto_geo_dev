# -*- coding: utf-8 -*-
"""
豆包AI检测器
用这个来检测豆包的收录情况！
"""

from typing import Dict, Any
from playwright.async_api import Page
import asyncio

from .base import AIPlatformChecker


class DoubaoChecker(AIPlatformChecker):
    """
    豆包AI检测器

    URL: https://www.doubao.com
    """

    SELECTORS = {
        "input_box": [
            "textarea[placeholder*='输入']",
            "textarea[data-placeholder*='输入']",
            "textarea[class*='input']",
            "textarea[class*='chat-input']",
            "textarea[role='textbox']"
        ],
        "submit_button": [
            "button[type='submit']",
            "button[aria-label*='发送']",
            "button[class*='send']",
            "[class*='submit'] button"
        ],
        "new_chat": [
            "[class*='new-chat']",
            "[class*='new-conversation']",
            "[class*='new-dialog']",
            "a[href='/chat']",
            "[class*='create-chat']"
        ]
    }

    async def check(
        self,
        page: Page,
        question: str,
        keyword: str,
        company: str
    ) -> Dict[str, Any]:
        """
        检测豆包收录情况

        Returns:
            检测结果详细信息
        """
        self._log("info", f"开始检测, 问题: {question[:50]}...")
        self._log("info", f"目标关键词: {keyword}, 公司: {company}")

        try:
            # 跳过导航操作，使用已经打开的页面
            self._log("info", "跳过导航操作，使用已经打开的页面")
            nav_result = {"success": True}

            async def clear_operation():
                if await self.clear_chat_history(page):
                    return {"success": True}
                return {"success": False, "error_msg": "清理失败"}

            await self._retry_operation(
                clear_operation,
                "清理聊天历史",
                max_retries=1
            )

            input_selectors = self.SELECTORS["input_box"]

            success, matched_selector = await self.wait_for_selector(
                page,
                input_selectors,
                timeout=20000
            )

            if not success:
                self._log("error", "未找到输入框")
                return {
                    "success": False,
                    "answer": None,
                    "keyword_found": False,
                    "company_found": False,
                    "error_msg": "输入框未找到"
                }

            self._log("info", f"找到输入框: {matched_selector}")

            await page.fill(matched_selector, question)
            await asyncio.sleep(0.5)
            self._log("info", f"已输入问题: {question[:30]}...")

            initial_content = await page.inner_text("body")

            await page.keyboard.press("Enter")
            self._log("info", "已提交问题")

            wait_result = await self.wait_for_answer_generation(
                page,
                initial_content,
                timeout=60000,
                check_interval=2.0
            )

            if wait_result["success"]:
                self._log("info", f"回答生成成功, 长度: {wait_result['content_length']} 字符")
            else:
                self._log("warning", f"回答生成未完成, 长度: {wait_result.get('content_length', 0)} 字符")

            answer_result = await self.get_answer_content(page, question)

            if not answer_result["success"]:
                self._log("warning", "未能获取到AI回答内容")

            answer_text = answer_result.get("answer", "")

            if not answer_text.strip():
                answer_text = await page.inner_text("body")
                self._log("info", f"使用页面全文作为回答, 长度: {len(answer_text)}")

            check_result = self.check_keywords_in_text(answer_text, keyword, company)

            self._log("info", "检测完成")
            self._log("info", f"关键词 '{keyword}' 检测结果: {check_result['keyword_found']}")
            self._log("info", f"公司名 '{company}' 检测结果: {check_result['company_found']}")

            operation_logs = self.get_operation_log()

            return {
                "success": True,
                "answer": answer_text[:5000],
                "keyword_found": check_result["keyword_found"],
                "company_found": check_result["company_found"],
                "keyword_count": check_result.get("keyword_count", 0),
                "company_count": check_result.get("company_count", 0),
                "confidence": check_result.get("confidence", 0.0),
                "answer_length": len(answer_text),
                "wait_info": wait_result,
                "answer_selector": answer_result.get("selector"),
                "operation_logs": operation_logs,
                "error_msg": None
            }

        except Exception as e:
            self._log("error", f"检测过程发生异常: {e}")
            return {
                "success": False,
                "answer": None,
                "keyword_found": False,
                "company_found": False,
                "error_msg": str(e)
            }
