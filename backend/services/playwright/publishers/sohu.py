# -*- coding: utf-8 -*-
import asyncio
import random
from typing import Dict, Any
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher


class SohuPublisher(BasePublisher):
    """
    搜狐号发布适配器 - v16.0 全新 UI 适配版
    适配基于 Vue.js 的新版后台与 Quill 编辑器
    """

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        try:
            # 0. 抹除 Playwright 特征 (针对 Sohu WAF)
            await self._apply_stealth_strategy(page)

            # 1. 导航至后台主页并点击"发布内容"
            logger.info("正在通过后台主页导航至发布页面...")
            await self._navigate_to_editor(page)

            # 2. 暴力移除干扰层
            await self._clear_overlays(page)

            # --- 架构金律：顺序执行 ---

            # 3. 标题先行 (Quill 编辑器中标题输入可能位于编辑器外)
            if not await self._fill_title_physical(page, article.title):
                return {"success": False, "error_msg": "标题注入失败"}

            # 4. 封面上传 (位于正文之前)
            if hasattr(article, 'cover_path') and article.cover_path:
                if not await self._handle_cover_v2(page, article.cover_path):
                    logger.warning("封面上传失败，继续后续流程")

            # 5. 正文注入 (Quill 编辑器)
            if not await self._fill_content_quill(page, article.content):
                return {"success": False, "error_msg": "正文注入失败"}

            # 6. 发布
            return await self._execute_publish(page)

        except Exception as e:
            logger.error(f"搜狐号发布异常: {e}")
            return {"success": False, "error_msg": str(e)}

    async def _apply_stealth_strategy(self, page: Page):
        """深度抹除自动化特征"""
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        """)

    async def _clear_overlays(self, page: Page):
        """物理清场：移除所有阻碍点击的层"""
        await page.evaluate("""
            () => {
                const selectors = ['.introjs-overlay', '.introjs-helperLayer', '.wp-guide-mask', '.p-guide', '.v-modal', '.el-overlay'];
                selectors.forEach(s => {
                    const el = document.querySelector(s);
                    if(el) el.remove();
                });
            }
        """)

    async def _navigate_to_editor(self, page: Page) -> bool:
        """
        导航至后台主页并点击"发布内容"按钮
        工作流：访问后台主页 -> 定位"发布内容"按钮 -> 点击进入编辑器 -> 等待编辑器加载
        """
        try:
            # 访问后台主页 (假设用户已登录，页面已处于后台)
            # 如果当前不在后台，可根据需要调整 URL
            base_url = "https://mp.sohu.com/mpfe/v4/contentManagement/firstpage"
            logger.info(f"访问后台主页: {base_url}")
            await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            # 尝试多种选择器定位"发布内容"按钮
            publish_selectors = [
                'button:has-text("发布内容")',
                '.publish-btn',
                'span:has-text("发布内容")',
                'a:has-text("发布内容")',
                '[class*="publish"]:has-text("发布")',
            ]

            button = None
            for selector in publish_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        button = element
                        logger.info(f"使用选择器找到按钮: {selector}")
                        break
                except:
                    continue

            if not button:
                logger.error("未找到'发布内容'按钮")
                return False

            # 点击按钮
            await button.click()
            logger.info("已点击'发布内容'按钮，等待编辑器加载...")

            # 等待编辑器加载完成 (等待 Quill 编辑器出现)
            await page.wait_for_selector(".ql-editor", timeout=15000)
            logger.info("编辑器加载完成")
            return True

        except Exception as e:
            logger.error(f"导航至编辑器失败: {e}")
            return False

    async def _fill_title_physical(self, page: Page, title: str) -> bool:
        """
        标题物理锁定
        使用新版选择器：input[placeholder="请输入标题（5-72字）"]
        """
        selector = 'input[placeholder="请输入标题（5-72字）"]'
        try:
            await page.wait_for_selector(selector, timeout=10000)
            logger.info("定位到标题输入框")

            # 暴力清空
            await page.click(selector, click_count=3)
            await page.keyboard.press("Backspace")

            # 模拟真人输入
            for char in title:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.01, 0.05))

            # 架构金律：唤醒状态
            await page.keyboard.press("Space")
            await page.keyboard.press("Backspace")
            logger.info(f"标题注入完成: {title}")
            return True
        except Exception as e:
            logger.error(f"标题注入异常: {e}")
            return False

    async def _fill_content_quill(self, page: Page, content: str) -> bool:
        """
        Quill 编辑器注入内容
        定位到 .ql-editor 元素并模拟真实输入
        """
        selector = ".ql-editor"
        try:
            logger.info("等待 Quill 编辑器加载...")
            await page.wait_for_selector(selector, timeout=15000)

            # 激活编辑器
            await page.click(selector)
            logger.info("编辑器已激活，开始注入内容...")

            # 清空编辑器 (Ctrl+A + Delete)
            await page.keyboard.press("Control+A")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.5)

            # 模拟真实输入注入内容
            # 注意：长文本直接使用 type() 可能较慢，可考虑分段注入
            await page.keyboard.type(content)

            logger.info("正文注入完成")
            return True

        except Exception as e:
            logger.error(f"Quill 编辑器注入异常: {e}")
            return False

    async def _handle_cover_v2(self, page: Page, cover_path: str) -> bool:
        """
        封面上传
        使用 Playwright 的 filechooser 事件监听器处理文件选择

        Args:
            page: Playwright 页面对象
            cover_path: 封面图片的本地文件路径

        Returns:
            bool: 上传是否成功
        """
        selector = "div.upload-file.mp-upload"
        try:
            logger.info(f"开始上传封面，文件路径: {cover_path}")

            # 等待封面上传区域可见
            await page.wait_for_selector(selector, timeout=10000)
            logger.info("定位到封面上传区域")

            # 注册 filechooser 事件监听器
            async def handle_file_chooser(file_chooser):
                await file_chooser.set_files(cover_path)
                logger.info("文件选择器已设置文件")

            page.on('filechooser', handle_file_chooser)

            # 点击上传区域触发文件选择器
            await page.click(selector)
            logger.info("已点击上传区域")

            # 等待文件上传完成
            # 方式 1: 固定等待 (简单)
            await asyncio.sleep(3)

            # 方式 2: 等待上传加载指示器消失 (更优，可根据实际情况调整选择器)
            # await page.wait_for_selector(".upload-loading", state="detached", timeout=30000)

            # 移除事件监听器
            page.remove_listener('filechooser', handle_file_chooser)

            logger.info("封面上传完成")
            return True

        except Exception as e:
            logger.error(f"封面上传异常: {e}")
            return False

    async def _execute_publish(self, page: Page) -> Dict[str, Any]:
        """
        发布确认
        使用新版发布按钮选择器 (li 元素)
        """
        # 使用精准的新版发布按钮选择器
        publish_selectors = [
            'li.publish-report-btn.active.positive-button:has-text("发布")',
        ]

        for selector in publish_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=10000)
                if btn:
                    logger.info(f"找到发布按钮: {selector}")
                    await btn.click()

                    # 等待可能的确认弹窗
                    await asyncio.sleep(2)
                    confirm_selectors = [
                        "button:has-text('确定')",
                        "button.el-button--primary:has-text('确定')",
                    ]
                    for confirm_selector in confirm_selectors:
                        try:
                            confirm_btn = await page.wait_for_selector(confirm_selector, timeout=3000)
                            if confirm_btn:
                                await confirm_btn.click()
                                logger.info("已点击确认按钮")
                                break
                        except:
                            continue

                    logger.info("发布成功")
                    return {
                        "success": True,
                        "platform_url": page.url,
                        "error_msg": None
                    }
            except Exception as e:
                logger.error(f"使用选择器 {selector} 点击发布失败: {e}")
                continue

        return {"success": False, "error_msg": "未找到发布按钮或点击失败"}
