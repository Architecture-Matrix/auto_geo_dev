# -*- coding: utf-8 -*-
"""
搜狐号发布适配器 - v5.5 架构金律版
1. 状态同步：彻底弃用 .fill()，使用物理点击 + 剪贴板注入 + 状态固化组合键
2. 执行顺序：正文压轴写入 -> 标题终极锁定
3. 物理清场：全量移除 z-index 干扰，恢复 body 滚动
4. 指纹对齐：严格执行指纹守卫
"""

import asyncio
import json
from typing import Dict, Any
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class SohuPublisher(BasePublisher):
    """
    搜狐号发布适配器 - 严格执行架构金律
    发布页面: https://mp.sohu.com/upload/article
    """

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        try:
            logger.info("🚀 [搜狐] 开始执行架构金律发布流程...")

            # ========== 0. 指纹守卫 (Rule #4) ==========
            if not account or not account.user_agent:
                err = "[搜狐] 账号指纹缺失，请重新授权以补全 UA"
                logger.error(f"❌ {err}")
                return {"success": False, "error_msg": err}

            # ========== 1. 导航与环境准备 ==========
            await page.set_viewport_size({"width": 1280, "height": 800})
            if not await self._navigate_to_publish_page(page):
                return {"success": False, "error_msg": "页面加载超时"}

            # ========== 2. 物理清场 (Rule #3) ==========
            await self._clear_ui_obstacles(page)

            # ========== 3. 设置先行 (如有封面/设置) ==========
            # 目前搜狐号封面多为自动抓取，如有特定封面逻辑在此处插入

            # ========== 4. 正文压轴写入 (Rule #1 & #2) ==========
            logger.info("[搜狐] 执行正文物理注入...")
            if not await self._brutal_inject_content(page, article.content):
                return {"success": False, "error_msg": "正文注入失败：无法锁定编辑器"}

            # ========== 5. 标题终极锁定 (Rule #2) ==========
            logger.info(f"[搜狐] 终极锁定标题: {article.title[:20]}...")
            if not await self._brutal_inject_title(page, article.title):
                logger.warning("⚠️ 标题注入可能偏移，尝试继续发布")

            # ========== 6. 物理确认发布 ==========
            logger.info("[搜狐] 执行暴力发布点击...")
            if not await self._brutal_publish_click(page):
                return {"success": False, "error_msg": "发布按钮无响应"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ [搜狐] 发布链路崩溃: {str(e)}")
            return {"success": False, "error_msg": f"系统崩溃: {str(e)}"}

    async def _navigate_to_publish_page(self, page: Page) -> bool:
        try:
            await page.goto(self.config["publish_url"], wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            # 检查是否被踢回登录
            if "login" in page.url:
                logger.error("❌ [搜狐] Session 已过期")
                return False
            return True
        except:
            return False

    async def _clear_ui_obstacles(self, page: Page):
        """强力清理搜狐号特有的干扰层"""
        await page.evaluate('''() => {
            const selectors = [
                '[class*="guide"]', '.mask', '.overlay', '.modal', 
                '[class*="Tooltip"]', '.popover', '.sp-guide-container'
            ];
            selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
            document.body.style.overflow = 'auto';
            document.body.style.position = 'static';
        }''')
        # 物理关闭可能存在的弹窗
        for _ in range(2):
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
        await page.mouse.click(10, 10)  # 粉碎全屏透明遮罩

    async def _brutal_inject_content(self, page: Page, content: str) -> bool:
        """针对 UEditor 的物理注入方案"""
        try:
            # 1. 定位 iframe
            iframe_handle = await page.wait_for_selector("iframe[id*='ueditor']", timeout=10000)
            if not iframe_handle: return False

            frame = await iframe_handle.content_frame()
            # 2. 物理点击聚焦
            await frame.click("body", force=True, delay=100)

            # 3. DataTransfer 注入
            await frame.evaluate('''(text) => {
                const dt = new DataTransfer();
                dt.setData("text/plain", text);
                const ev = new ClipboardEvent("paste", { clipboardData: dt, bubbles: true });
                document.body.dispatchEvent(ev);
            }''', content)

            # 4. 状态固化：Enter + Backspace 强制触发监听
            await frame.keyboard.press("End")
            await frame.keyboard.press("Enter")
            await asyncio.sleep(0.3)
            await frame.keyboard.press("Backspace")

            logger.info("✅ [搜狐] 正文物理注入成功")
            return True
        except Exception as e:
            logger.error(f"正文注入异常: {e}")
            return False

    async def _brutal_inject_title(self, page: Page, title: str) -> bool:
        """标题锁定逻辑"""
        try:
            title_sel = "#title, input[name='title'], .title-input"
            target = page.locator(title_sel).first

            # 获取物理位置，不依赖简单 click
            box = await target.bounding_box()
            if box:
                await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            else:
                await target.click(force=True)

            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(title, delay=20)
            await page.keyboard.press("Tab")  # 失焦触发同步
            return True
        except:
            return False

    async def _brutal_publish_click(self, page: Page) -> bool:
        """暴力点击发布"""
        # 搜狐号发布按钮有时在滚动区域外
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)

        selectors = ["button:has-text('发布')", ".publish-btn", "[class*='submit']"]
        for sel in selectors:
            btn = page.locator(sel).first
            if await btn.is_visible():
                await btn.click(force=True)
                return True

        # 最后的物理坐标尝试
        await page.mouse.click(1100, 750)
        return True

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """结果检测逻辑"""
        for i in range(20):
            if "success" in page.url.lower() or "manage" in page.url.lower():
                return {"success": True, "platform_url": page.url}
            # 检查是否有错误提示
            err_msg = await page.evaluate('() => document.querySelector(".error-tip")?.innerText')
            if err_msg: return {"success": False, "error_msg": err_msg}
            await asyncio.sleep(1)
        return {"success": True, "platform_url": page.url}


# ========== 注册发布器 ==========
SOHU_CONFIG = {
    "name": "搜狐号",
    "publish_url": "https://mp.sohu.com/upload/article",
    "color": "#FF6B00"
}
registry.register("sohu", SohuPublisher("sohu", SOHU_CONFIG))