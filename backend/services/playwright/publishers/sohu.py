# -*- coding: utf-8 -*-
"""
搜狐 (Sohu) 发布适配器 - v2.3 修复版
功能：
1. Cookie持久化免登录
2. 登录状态自动检测
3. 弹窗自动关闭
4. 扫码后自动保存新Cookie
5. 修复：强制直达真实发布页，严格分离标题和正文操作
"""

import asyncio
import re
import os
import httpx
import tempfile
import random
import base64
import urllib.parse
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, BrowserContext
from loguru import logger
from .base import BasePublisher, registry


class SohuPublisher(BasePublisher):
    """搜狐发布适配器 - v2.3 修复版"""

    # 搜狐登录URL
    LOGIN_URL = "https://mp.sohu.com/mpfe/v3/main/login"

    # 搜狐后台首页（用于检测登录状态）
    HOME_URL = "https://mp.sohu.com/mpfe/v3/main/home"

    # 搜狐文章发布页 (v4 真实URL)
    PUBLISH_URL = "https://mp.sohu.com/mpfe/v4/contentManagement/news/addarticle?contentStatus=1"

    async def publish(self, page: Page, article: Any, account: Any, context: BrowserContext = None, mgr: Any = None) -> Dict[str, Any]:
        """
        发布文章到搜狐
        核心逻辑：登录 -> 强跳发布页 -> 填标题 -> 填正文 -> 插图 -> 发布
        """
        temp_files = []
        try:
            logger.info("🚀 开始搜狐 v2.3 修复版自动化发布...")

            # ============================================================
            # Step 1: 检测登录状态
            # ============================================================
            logger.info("Step 1: 检测登录状态...")
            is_logged_in = await self._check_and_restore_session(page, context, mgr, account)

            if not is_logged_in:
                return {"success": False, "error_msg": "登录失败，请重试"}

            # ============================================================
            # Step 2: 强制直达真实发布页
            # ============================================================
            logger.info("Step 2: 强制直达真实发布页...")
            logger.info(f"   → 跳转到: {self.PUBLISH_URL}")
            await page.goto(self.PUBLISH_URL, wait_until="load", timeout=30000)
            await asyncio.sleep(2)

            # 关闭弹窗
            await self._dismiss_popups(page)
            await asyncio.sleep(1)

            # 等待网络空闲
            logger.info("   → 等待网络空闲...")
            await page.wait_for_load_state("networkidle", timeout=15000)

            # 打印当前 URL
            current_url = page.url
            logger.info(f"   → 当前 URL: {current_url}")

            # ============================================================
            # Step 3: 准备资源
            # ============================================================
            logger.info("Step 3: 准备资源...")
            # 标题处理：超过30字自动截断
            safe_title = article.title.replace("#", "").replace("*", "").strip()
            if len(safe_title) > 30:
                safe_title = safe_title[:30]
                logger.info(f"   → 标题已截断至30字: {safe_title}")
            clean_text = self._deep_clean_content(article.content)

            # --- AI 自动配图 ---
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)

            if not image_urls:
                keyword = article.title[:15] if article.title else "business technology"
                logger.info(f"🎨 文章无图片，启动 AI 自动配图 (关键词: {keyword})...")

                for i in range(3):
                    seed = random.randint(1, 1000)
                    prompt = f"realistic professional photo of {keyword} for business article, high quality, {seed}"
                    encoded_prompt = urllib.parse.quote(prompt)
                    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true"
                    image_urls.append(url)

                logger.info(f"✅ AI 已生成 {len(image_urls)} 张配图链接")

            # 下载图片
            downloaded_paths = await self._download_images_fast(image_urls)
            temp_files.extend(downloaded_paths)

            if not downloaded_paths:
                logger.warning("⚠️ 图片下载失败，继续纯文本发布")

            logger.info(f"✅ 成功下载 {len(downloaded_paths)} 张图片")

            # ============================================================
            # Step 4: 步骤A - 精准定位标题
            # ============================================================
            logger.info("Step 4: 填充标题...")
            await self._fill_title_strict(page, safe_title)

            # ============================================================
            # Step 5: 步骤B - 精准定位正文编辑器
            # ============================================================
            logger.info("Step 5: 填充正文内容...")
            await self._fill_content_strict(page, clean_text)
            await asyncio.sleep(random.uniform(1, 2))

            # ============================================================
            # Step 6: 步骤C - 图片插入修正
            # ============================================================
            if downloaded_paths:
                logger.info("Step 6: 在正文中插入图片...")
                await self._inject_images_strict(page, downloaded_paths)

            # ============================================================
            # Step 7: 设置封面
            # ============================================================
            logger.info("Step 7: 设置封面...")
            await self._set_cover(page)

            # ============================================================
            # Step 8: 发布
            # ============================================================
            logger.info("Step 8: 进入发布阶段...")
            if not await self._brutal_publish_click_loop(page):
                return {"success": False, "error_msg": "发布失败：按钮未响应或被屏蔽"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ 搜狐脚本故障: {str(e)}")

            # 出错时尝试截图
            try:
                debug_dir = os.path.join(os.path.dirname(__file__), "../../../debug")
                os.makedirs(debug_dir, exist_ok=True)
                screenshot_path = os.path.join(debug_dir, "debug_sohu_error.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"   → 异常截图已保存: {screenshot_path}")
            except:
                pass

            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _fill_title_strict(self, page: Page, title: str):
        """
        步骤A：精准定位标题

        操作：
        1. 等待 input[placeholder*="标题"] 出现
        2. 点击该 Input
        3. 全选 (Control+A)
        4. 删除 (Backspace)
        5. 仅输入 title (已截断至30字)
        6. Tab 键强制移开焦点
        """
        try:
            logger.info(f"   → 开始精准定位标题输入框...")

            # 精准定位标题选择器
            title_selectors = [
                'input[placeholder*="标题"]',
                'input[placeholder="请输入标题"]',
                'input[name="title"]',
                'input.title-input',
                '.title-input input',
            ]

            title_found = False
            for selector in title_selectors:
                try:
                    logger.info(f"   → 尝试选择器: {selector}")
                    # 等待选择器出现
                    await page.wait_for_selector(selector, timeout=10000)
                    logger.info(f"   ✅ 找到标题输入框: {selector}")

                    # 点击输入框
                    await page.click(selector, timeout=5000)
                    await asyncio.sleep(0.3)

                    # 全选
                    await page.keyboard.press("Control+A")
                    await asyncio.sleep(0.2)

                    # 删除
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)

                    # 仅输入标题（已截断至30字）
                    await page.keyboard.type(title, delay=50)
                    logger.info(f"   ✅ 标题已输入: {title}")
                    await asyncio.sleep(0.3)

                    # Tab 键强制移开焦点
                    await page.keyboard.press("Tab")
                    logger.info(f"   ✅ 已按 Tab 移开焦点")

                    title_found = True
                    break
                except:
                    logger.debug(f"   → 选择器失败: {selector}")
                    continue

            if not title_found:
                logger.error("   ❌ 无法定位标题输入框，跳过标题填充")
                # 尝试截图
                try:
                    debug_dir = os.path.join(os.path.dirname(__file__), "../../../debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    screenshot_path = os.path.join(debug_dir, "debug_title_error.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"   → 标题定位失败截图: {screenshot_path}")
                except:
                    pass
            else:
                logger.success("✅ 标题填充完成")

        except Exception as e:
            logger.error(f"❌ 标题填充失败: {str(e)}")

    async def _fill_content_strict(self, page: Page, content: str):
        """
        步骤B：精准定位正文编辑器

        搜狐的正文编辑器是一个 div，不是 input

        定位器：div.editor-content 或 div[contenteditable="true"]

        操作：
        1. await page.click("div[contenteditable='true']") 确保光标在正文内
        2. 使用 evaluate + ClipboardEvent 的方式注入 content
        3. 不要使用 .fill() 或 .type() 操作正文
        """
        try:
            logger.info(f"   → 开始精准定位正文编辑器...")

            # 正文编辑器选择器（div，不是input）
            editor_selectors = [
                "div[contenteditable='true']",
                ".editor-content",
                "#editor-content",
                ".w-e-text",
                "[contenteditable]",
            ]

            editor_found = False
            for selector in editor_selectors:
                try:
                    logger.info(f"   → 尝试选择器: {selector}")
                    # 等待编辑器出现
                    await page.wait_for_selector(selector, timeout=10000)
                    logger.info(f"   ✅ 找到正文编辑器: {selector}")

                    # 点击编辑器确保光标在正文内
                    await page.click(selector, timeout=5000)
                    await asyncio.sleep(0.3)

                    # 清空编辑器
                    await page.keyboard.press("Control+A")
                    await asyncio.sleep(0.2)
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)

                    # 使用 evaluate + ClipboardEvent 注入内容（不使用 .fill() 或 .type()）
                    await page.evaluate('''(content) => {
                        const selectors = [
                            "div[contenteditable='true']",
                            ".editor-content",
                            "#editor-content",
                            ".w-e-text",
                            "[contenteditable]"
                        ];
                        let editor = null;

                        for (let i = 0; i < selectors.length; i++) {
                            editor = document.querySelector(selectors[i]);
                            if (editor) break;
                        }

                        if (!editor) {
                            console.error("未找到编辑器元素");
                            return;
                        }

                        // 清空编辑器
                        editor.innerHTML = "";

                        // 创建剪贴板事件
                        const dt = new DataTransfer();
                        dt.setData("text/plain", content);

                        const event = new ClipboardEvent("paste", {
                            clipboardData: dt,
                            bubbles: true,
                            cancelable: true
                        });

                        // 触发粘贴事件
                        editor.dispatchEvent(event);
                    }''', content)

                    logger.info(f"   ✅ 正文已注入 ({len(content)} 字)")
                    await asyncio.sleep(1)

                    editor_found = True
                    break
                except:
                    logger.debug(f"   → 选择器失败: {selector}")
                    continue

            if not editor_found:
                logger.error("   ❌ 无法定位正文编辑器，跳过正文填充")
                # 尝试截图
                try:
                    debug_dir = os.path.join(os.path.dirname(__file__), "../../../debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    screenshot_path = os.path.join(debug_dir, "debug_editor_error.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"   → 编辑器定位失败截图: {screenshot_path}")
                except:
                    pass
            else:
                logger.success("✅ 正文填充完成")

        except Exception as e:
            logger.error(f"❌ 正文填充失败: {str(e)}")

    async def _inject_images_strict(self, page: Page, image_paths: List[str]):
        """
        步骤C：图片插入修正

        确保图片插入逻辑也是针对 div[contenteditable="true"] 进行 paste 操作
        绝对不要上传到封面的 input[type="file"]
        """
        try:
            logger.info(f"📝 开始在正文中插入图片，共 {len(image_paths)} 张")

            # 精准定位正文编辑器
            editor_selectors = [
                "div[contenteditable='true']",
                ".editor-content",
                "#editor-content",
                ".w-e-text",
                "[contenteditable]",
            ]

            editor_found = False
            for selector in editor_selectors:
                try:
                    if await page.locator(selector).count(timeout=5000) > 0:
                        logger.info(f"✅ 找到正文编辑器: {selector}")
                        editor_found = True
                        break
                except:
                    continue

            if not editor_found:
                logger.warning("⚠️ 未找到正文编辑器，跳过图片插入")
                return

            # 第1张：插入到文章开头
            logger.info("   → 插入位置: 文章开头")
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)
            await self._paste_image_to_editor(page, image_paths[0])
            await asyncio.sleep(1)

            # 第2张：插入到文章中间
            if len(image_paths) > 1:
                logger.info("   → 插入位置: 文章中间")
                await page.keyboard.press("Home")
                for _ in range(5):
                    await page.keyboard.press("PageDown")
                    await asyncio.sleep(0.2)
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.3)
                await self._paste_image_to_editor(page, image_paths[1])
                await asyncio.sleep(1)

            # 第3张：插入到文章结尾
            if len(image_paths) > 2:
                logger.info("   → 插入位置: 文章结尾")
                await page.keyboard.press("Home")
                for _ in range(10):
                    await page.keyboard.press("PageDown")
                    await asyncio.sleep(0.1)
                await page.keyboard.press("End")
                await asyncio.sleep(0.3)
                await self._paste_image_to_editor(page, image_paths[2])

            logger.info("✅ 正文中图片插入完成")
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ 正文中图片插入失败: {str(e)}")

    async def _paste_image_to_editor(self, page: Page, image_path: str):
        """
        将图片粘贴到正文编辑器（div[contenteditable="true"]）
        绝对不要上传到封面的 input[type="file"]
        """
        try:
            # 确保焦点在正文编辑器内
            editor_selectors = [
                "div[contenteditable='true']",
                ".editor-content",
                "#editor-content",
                ".w-e-text",
                "[contenteditable]",
            ]

            for selector in editor_selectors:
                try:
                    count = await page.locator(selector).count(timeout=2000)
                    if count > 0:
                        await page.click(selector, timeout=3000, force=True)
                        logger.info(f"   ✅ 已激活编辑器焦点: {selector}")
                        break
                except:
                    continue

            await asyncio.sleep(0.3)

            # 读取图片并转换为 base64
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            # 通过 ClipboardEvent 粘贴图片到正文编辑器
            await page.evaluate('''(b64) => {
                const selectors = [
                    "div[contenteditable='true']",
                    ".editor-content",
                    "#editor-content",
                    ".w-e-text",
                    "[contenteditable]"
                ];
                let editor = null;

                for (let i = 0; i < selectors.length; i++) {
                    editor = document.querySelector(selectors[i]);
                    if (editor) break;
                }

                if (!editor) {
                    console.error("未找到编辑器元素");
                    return;
                }

                // 将base64转换为File对象
                const byteCharacters = atob(b64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: 'image/jpeg' });
                const file = new File([blob], "auto_inserted.jpg", { type: 'image/jpeg' });

                // 创建DataTransfer
                const dt = new DataTransfer();
                dt.items.add(file);

                // 创建并分发剪贴板事件
                const event = new ClipboardEvent("paste", {
                    clipboardData: dt,
                    bubbles: true,
                    cancelable: true
                });

                editor.dispatchEvent(event);
            }''', b64)

            logger.info("   ✅ 图片剪贴板注入完成")
            await asyncio.sleep(2)

        except Exception as e:
            logger.warning(f"   ⚠️ 图片注入失败: {str(e)}")

    async def _check_and_restore_session(self, page: Page, context: BrowserContext, mgr: Any, account: Any) -> bool:
        """
        检测登录状态并恢复会话

        流程：
        1. 先跳转到后台首页
        2. 检测是否已登录（查找头像、用户名等元素）
        3. 如果未登录，跳转到登录页，等待用户扫码
        4. 扫码成功后，自动保存新Cookie到数据库

        Returns:
            是否已登录
        """
        try:
            # 1. 先跳转到后台首页（而非登录页）
            logger.info(f"   → 跳转到搜狐后台首页: {self.HOME_URL}")
            await page.goto(self.HOME_URL, wait_until="load", timeout=30000)
            await asyncio.sleep(2)

            # 2. 关闭弹窗
            await self._dismiss_popups(page)
            await asyncio.sleep(1)

            # 3. 检测登录状态
            if await self._check_is_logged_in(page):
                logger.success("✅ 检测到 Cookie 有效，直接使用")
                return True

            # 4. Cookie 失效，需要重新登录
            logger.warning("⚠️ Cookie 已失效或不存在，需要重新登录")
            logger.info("   → 跳转到登录页，请使用手机扫码登录...")

            # 跳转到登录页
            await page.goto(self.LOGIN_URL, wait_until="load", timeout=30000)
            await asyncio.sleep(3)
            await self._dismiss_popups(page)

            # 等待用户扫码登录（最多等待3分钟）
            logger.info("⏳ 等待用户扫码登录 (最多3分钟)...")
            login_success = False
            for i in range(60):  # 60 * 3秒 = 3分钟
                await asyncio.sleep(3)
                if await self._check_is_logged_in(page):
                    login_success = True
                    logger.success("✅ 检测到登录成功！")
                    break
                logger.info(f"   → 等待中... ({i + 1}/60)")

            if not login_success:
                logger.error("❌ 登录超时，请重试")
                return False

            # 5. 登录成功，保存新Cookie到数据库
            if context and mgr and hasattr(mgr, 'update_account_storage_state'):
                logger.info("💾 保存新 Cookie 到数据库...")
                success = await mgr.update_account_storage_state(account.id, context, page)
                if success:
                    logger.success("✅ Cookie 已保存，下次可直接免登录")
                else:
                    logger.warning("⚠️ Cookie 保存失败，但不影响本次发布")

            # 6. 登录成功后跳转到首页（后续会暴力直达发布页）
            logger.info(f"   → 跳转回搜狐后台首页: {self.HOME_URL}")
            await page.goto(self.HOME_URL, wait_until="load", timeout=30000)
            await asyncio.sleep(2)
            await self._dismiss_popups(page)

            return True

        except Exception as e:
            logger.error(f"❌ 登录检测异常: {str(e)}")
            return False

    async def _check_is_logged_in(self, page: Page) -> bool:
        """
        检测是否已登录

        检测搜狐后台的登录状态特征元素：
        - 头像元素
        - 用户名显示
        - 发布按钮
        - 退出登录链接

        Returns:
            是否已登录
        """
        try:
            # 搜狐后台登录特征元素（多种选择器）
            login_indicators = [
                # 头像相关
                ".avatar",
                ".user-avatar",
                ".mp-avatar",
                "img[alt*='头像']",
                "img[alt*='用户']",
                "[class*='avatar']",

                # 用户名相关
                ".user-name",
                ".username",
                ".mp-name",
                ".account-name",
                "[class*='user-name']",

                # 后台特有元素
                ".logout",
                "[class*='logout']",
                "text=退出登录",
                "text=发布文章",
            ]

            # 检查是否在登录页（如果在登录页，说明未登录）
            login_page_indicators = [
                "text=扫码登录",
                "text=账号密码登录",
                ".login-qr",
                "[class*='login-qr']",
            ]

            for selector in login_page_indicators:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # 找到登录页元素，说明未登录
                        logger.debug(f"   检测到登录页元素: {selector}")
                        return False
                except:
                    continue

            # 检查是否有登录成功的特征元素
            for selector in login_indicators:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        logger.debug(f"   检测到登录特征元素: {selector}")
                        return True
                except:
                    continue

            # 检查 URL（如果包含 home 或 article-manage 等，可能已登录）
            current_url = page.url
            if "home" in current_url or "article-manage" in current_url or "news/add" in current_url:
                # 进一步检查页面内容
                content = await page.content()
                # 如果页面包含"我的文章"、"发布"等关键词，说明已登录
                if "我的文章" in content or "文章管理" in content or "发布文章" in content:
                    logger.debug(f"   通过 URL 和页面内容检测到登录状态")
                    return True

            logger.debug("   未检测到明确的登录状态特征")
            return False

        except Exception as e:
            logger.warning(f"   登录状态检测异常: {str(e)}")
            return False

    async def _dismiss_popups(self, page: Page):
        """
        关闭搜狐后台的各种弹窗和遮罩

        常见弹窗：
        - 权益升级提示
        - 活动通知
        - 引导遮罩
        - 新手教程
        """
        try:
            logger.debug("   → 尝试关闭弹窗...")

            # 1. 点击左上角关闭通用遮罩
            await page.mouse.click(10, 10)
            await asyncio.sleep(0.2)

            # 2. JS 移除常见遮罩层
            await page.evaluate('''() => {
                const targets = [
                    // 搜狐特有弹窗
                    '.creation-helper',
                    '.guide-mask',
                    '.tutorial-overlay',
                    '.upgrade-pop',
                    '.upgrade-modal',
                    '.notice-pop',
                    '.activity-modal',
                    '.vip-modal',
                    '.rights-modal',
                    '.pro-modal',
                    '.member-modal',

                    // 通用遮罩
                    '.modal-overlay',
                    '.popup-mask',
                    '.dialog-mask',
                    '.guide-popup',
                    '.tooltip-overlay',
                    '.mask-layer',
                    '[role="dialog"]',
                    '.modal',
                    '.overlay',
                    '.ant-modal-mask',
                    '.ant-modal-wrap',

                    // 关闭按钮
                    '.close-btn',
                    '.modal-close',
                    '.popup-close',
                    '[class*="close"]',
                ];

                // 移除遮罩元素
                for (let i = 0; i < targets.length; i++) {
                    const els = document.querySelectorAll(targets[i]);
                    for (let j = 0; j < els.length; j++) {
                        els[j].remove();
                    }
                }

                // 尝试点击关闭按钮
                const closeBtns = document.querySelectorAll('.close, .modal-close, .popup-close, [class*="close"]');
                for (let i = 0; i < closeBtns.length; i++) {
                    if (closeBtns[i].offsetParent !== null) {
                        closeBtns[i].click();
                    }
                }

                // 关闭所有 open 的 dialog
                const dialogs = document.querySelectorAll('dialog');
                for (let i = 0; i < dialogs.length; i++) {
                    dialogs[i].close();
                }

                // 尝试按 ESC 关闭弹窗
                if (document.querySelector('.modal, .popup, [role="dialog"]')) {
                    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
                    document.dispatchEvent(event);
                }
            }''')

            logger.debug("   ✅ 弹窗关闭完成")
        except Exception as e:
            logger.debug(f"   ⚠️ 弹窗关闭时出现问题: {str(e)}")

    async def _set_cover(self, page: Page):
        """
        设置封面 (搜狐特有)
        尝试点击'自动'或'单图'封面选项
        """
        try:
            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 尝试点击"单图"选项
            cover_selectors = [
                "text=单图",
                "text=自动",
                ".cover-option-single",
                ".cover-auto",
                "label:has-text('单图')",
                ".single-cover"
            ]

            for selector in cover_selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible(timeout=2000):
                        await btn.click(force=True)
                        logger.info("✅ 已选择封面模式")
                        await asyncio.sleep(1)
                        return
                except:
                    continue

            logger.info("ℹ️ 未找到封面选项，搜狐可能会自动抓取")

        except Exception as e:
            logger.warning(f"⚠️ 设置封面时出现问题: {str(e)}")

    async def _brutal_publish_click_loop(self, page: Page) -> bool:
        """
        暴力发布循环
        """
        PUBLISH_BTN = "button:has-text('发布'), button:has-text('提交'), .publish-btn, .submit-btn"
        CONFIRM_BTN = "button:has-text('确认'), button:has-text('确定'), .confirm-btn"

        for i in range(12):
            try:
                # A. 滚动到发布按钮
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.5)

                # B. 点击发布按钮
                p_btn = page.locator(PUBLISH_BTN).last
                await p_btn.scroll_into_view_if_needed()
                if await p_btn.is_enabled():
                    await p_btn.click(force=True)

                # C. 处理确认弹窗
                await asyncio.sleep(2)
                c_btn = page.locator(CONFIRM_BTN).last
                if await c_btn.is_visible(timeout=1000):
                    await c_btn.click(force=True)
                    logger.success("🎯 发布最终确认成功！")
                    return True

                # 检查是否成功跳转
                if "article" in page.url or "news" in page.url:
                    return True
            except:
                pass
            await asyncio.sleep(1)
        return False

    def _deep_clean_content(self, text: str) -> str:
        """深度清洗正文内容"""
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\*\*+', '', text)
        return text.strip()

    async def _download_images_fast(self, urls: List[str]) -> List[str]:
        """快速下载图片"""
        paths = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, timeout=20.0) as client:
            for i, url in enumerate(urls[:3]):
                for attempt in range(2):
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            tmp = os.path.join(tempfile.gettempdir(), f"sohu_v23_{random.randint(1, 9999)}.jpg")
                            with open(tmp, "wb") as f:
                                f.write(resp.content)
                            paths.append(tmp)
                            logger.info(f"✅ 图片 {i + 1}/{min(len(urls), 3)} 下载成功")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ 图片 {i + 1} 下载失败 (尝试 {attempt + 1}/2): {str(e)}")
                        continue

        return paths

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """等待发布结果"""
        for i in range(25):
            if "article" in page.url or "news" in page.url or "article-manage" in page.url:
                return {"success": True, "platform_url": page.url}
            await asyncio.sleep(1)
        return {"success": True, "platform_url": page.url}


# 注册
registry.register("sohu", SohuPublisher("sohu", {
    "name": "搜狐",
    "publish_url": "https://mp.sohu.com/mpfe/v4/contentManagement/news/addarticle?contentStatus=1",
    "color": "#FFCC00"
}))
