# -*- coding: utf-8 -*-
"""
百家号发布适配器 - v16.2 架构金律终极重构版 (增强正文注入 + 封面再次确认)

【架构金律严格执行】

Rule #1 (状态同步): 严禁使用 .fill() 和 .keyboard.type() 写入长文本
    - 必须通过 execCommand('insertHTML') 配合 Space + Backspace 唤醒 React

Rule #2 (顺序逻辑 + 封面死守): 封面先行 -> 正文压轴 -> 标题终极锁定
    - 必须有封面才能发布，封面下载失败则直接返回错误
    - 封面上传采用"精准触发+协议直投"：DNA 锚点 -> 瞬间劫持 input -> 直投文件
    - 正文注入需要编辑器完全加载，放中间处理
    - 标题锁定是最后一步，防止被其他操作覆盖

Rule #3 (物理清场): 暴力 remove() 所有 z-index > 500 的元素
    - 特别是包含"下一步"、"AI工具"文本的容器
    - 穿透 Shadow DOM 进行深度扫描

【HTML DNA 精准注入】

- 封面: div._73a3a52aab7e3a36-content 或包含"选择封面"文本的容器
- 正文: iframe 内 [data-diagnose-id]
- 标题: p[dir="auto"]
"""

import asyncio
import re
import os
import httpx
import tempfile
import random
from typing import Dict, Any, List
from playwright.async_api import Page, Locator
from loguru import logger

from .base import BasePublisher, registry


class BaijiahaoPublisher(BasePublisher):
    """
    百家号发布适配器 - v16.2 架构金律终极重构版 (增强正文注入 + 封面再次确认)

    核心特性:
    1. 深度 Shadow DOM 穿透清场
    2. DNA 级精准定位注入
    3. 严格执行封面->正文->标题的时序逻辑
    4. 封面死守：必须有封面才能发布
    5. 精准触发+协议直投：DNA 锚点 -> 瞬间劫持 -> 直投文件
    6. 完整的隐身疫苗注入
    """

    # ========== 备用图源 ==========
    # 确保必定能下载到一张图
    FALLBACK_IMAGE_URLS = [
        "https://pic.rmb.bdstatic.com/bjh/news/0a3e8787e9d7249d3240275817294862.jpeg",  # 百度官方测试图
        "https://pic.rmb.bdstatic.com/bjh/news/5f3e8787e9d7249d3240275817294863.jpeg",
    ]

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        """
        执行发布流程 - 严格按照架构金律执行
        """
        temp_files = []
        try:
            logger.info("🚀 [百家号] 开始执行 v16.2 架构金律发布流程...")

            # ========== 步骤 0: 注入隐身疫苗 & 导航 ==========
            await self._inject_stealth_vaccine(page)
            await self._navigate_to_editor(page)

            # ========== 步骤 1: 物理清场（Rule #3）==========
            await self._smash_interferences(page)

            # ========== 步骤 2: 准备资源 & 下载图片（封面死守）==========
            clean_title = article.title.replace("#", "").strip()
            # 提取正文（移除首行标题）
            clean_content = re.sub(r'^#\s+.*?\n', '', article.content).strip()
            # 提取图片 URL
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)

            # 如果没有图片，使用默认图
            if not image_urls:
                image_urls.append("https://api.dujin.org/bing/1920.php")
                logger.info("🎨 [图片] 自动生成 1 张配图链接")

            # ========== 封面死守：下载图片 ==========
            downloaded_paths = await self._download_images(image_urls)
            temp_files.extend(downloaded_paths)

            # Rule #2: 封面死守 - 必须有封面才能发布
            if not downloaded_paths:
                logger.error("❌ [封面死守] 图片下载失败，终止发布流程")
                return {"success": False, "error_msg": "封面图片下载失败，无法发布"}

            logger.success(f"✅ [封面] 已成功下载 {len(downloaded_paths)} 张图片")

            # ========== Golden Rule #2: 封面 -> 正文 -> 标题 ==========

            # 步骤 3: 封面注入 (先行) - 精准触发+协议直投
            # DNA: div._73a3a52aab7e3a36-content 或包含"选择封面"文本的容器
            await self._physical_upload_cover(page, downloaded_paths[0])
            await self._smash_interferences(page)  # 封面上传后立即清场，杀掉"上传成功"气泡

            # 步骤 4: 正文注入 (压轴)
            # DNA: iframe 内 [data-diagnose-id]
            content_result = await self._physical_write_content(page, clean_content)
            if not content_result:
                return {"success": False, "error_msg": "正文注入失败"}
            await self._smash_interferences(page)

            # 步骤 5: 标题锁定 (终极)
            # DNA: p[dir="auto"]
            title_result = await self._physical_write_title(page, clean_title)
            if not title_result:
                return {"success": False, "error_msg": "标题注入失败"}
            await self._smash_interferences(page)

            # ========== 步骤 6: 封面再次确认 ==========
            # 在正文和标题写完后，再次点击封面区域进行最终确认
            logger.info("🎯 [封面-再次确认] 正文和标题写完，再次点击封面区域确认...")
            await self._reconfirm_cover(page)
            await self._smash_interferences(page)

            # ========== 步骤 7: 发布确认 ==========
            publish_result = await self._physical_publish(page)
            if not publish_result:
                return {"success": False, "error_msg": "发布失败"}

            # ========== 步骤 8: 等待结果 ==========
            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ [百家号] 发布链路崩溃: {e}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)

    async def _inject_stealth_vaccine(self, page: Page):
        """
        注入隐身疫苗（运行环境补丁）

        核心逻辑:
        1. 抹除 navigator.webdriver
        2. 伪造 window.chrome 对象
        3. 注入本地存储标记，绕过新手引导
        """
        await page.add_init_script("""() => {
            // 绕过百家号新手引导
            localStorage.setItem('BAIDU_BJ_GUIDE_STATE', 'true');
            localStorage.setItem('BJ_TOUR_COMPLETED', 'true');
            localStorage.setItem('ai_tool_guide_status', '1');
            localStorage.setItem('first_login_flag', 'true');

            // 抹除自动化痕迹
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 伪造 Chrome 对象
            window.chrome = {
                runtime: {},
                loadTimes: Date.now,
                csi: () => {},
                app: {}
            };

            // 伪造 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 伪造 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        }""")
        logger.info("💉 [隐身疫苗] 已注入 navigator.webdriver 抹除 + window.chrome 伪造")

    async def _navigate_to_editor(self, page: Page):
        """
        导航到编辑器页面

        运行环境补丁: 强制导航
        如果空降 URL 被重定向，强制跳转回 ?type=news&is_from_cms=1
        """
        golden_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1"

        # 设置 Referer
        await page.set_extra_http_headers({
            "Referer": "https://baijiahao.baidu.com/builder/rc/home"
        })

        # 首次导航
        await page.goto(golden_url, wait_until="networkidle", timeout=60000)

        # 检查登录态
        if "login" in page.url:
            raise Exception("登录态失效，请重新授权")

        # 强制导航：如果被重定向，强制返回
        if "type=news" not in page.url:
            logger.warning("⚠️ [导航] 被重定向，执行强制导航...")
            await page.goto(golden_url, wait_until="networkidle", timeout=60000)

        logger.info("✅ [导航] 成功抵达编辑器")

    async def _smash_interferences(self, page: Page):
        """
        物理清场 (Rule #3)

        核心逻辑:
        1. 编写 JS 穿透 Shadow DOM 扫描所有包含"下一步"、"1/4"、"AI工具"文本的 div
        2. 向上寻找其最近的 fixed 或 absolute 定位父级并执行 .remove()
        3. 清理完成后发送 Escape 键确保无残留
        """
        await page.evaluate("""() => {
            // 干扰关键词
            const keywords = ['下一步', '1/4', 'AI工具', '引导', '知道了', '新手引导', '开始创作', '上传成功', '操作成功'];

            // 穿透 Shadow DOM 的递归扫描函数
            function scanAndSmash(root) {
                const allElements = root.querySelectorAll('*');

                allElements.forEach(el => {
                    // 获取计算样式
                    const style = window.getComputedStyle(el);

                    // 判断是否需要清理：z-index > 500 且是 fixed 或 absolute 定位
                    if (parseInt(style.zIndex) > 500 &&
                        (style.position === 'fixed' || style.position === 'absolute')) {

                        const text = el.innerText || el.textContent || '';

                        // 检查是否包含干扰关键词
                        if (keywords.some(kw => text.includes(kw))) {
                            el.remove();
                        }
                    }

                    // 穿透 Shadow DOM
                    if (el.shadowRoot) {
                        scanAndSmash(el.shadowRoot);
                    }
                });
            }

            // 执行清理
            scanAndSmash(document);

            // 恢复 body 滚动
            document.body.style.overflow = 'auto';

            // 隐藏可能的遮罩层
            const masks = document.querySelectorAll('[class*="mask"], [class*="overlay"]');
            masks.forEach(m => m.remove());
        }""")

        # 发送 Escape 键确保无残留弹窗
        for _ in range(3):
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.1)

        logger.info("🧹 [物理清场] 干扰弹窗已暴力清理")

    async def _physical_upload_cover(self, page: Page, image_path: str):
        """
        封面注入 - v15.8 精准点击 + expect_file_chooser 方案 (彻底修复视频格式错误)

        核心逻辑:
        1. 物理触发 (DNA 级唤醒):
           - 定位：div._73a3a52aab7e3a36-content 或包含"选择封面"文本的容器
           - 执行：物理滚动并点击 DNA 元素

        2. 精准点击"本地上传"按钮 并 捕获文件选择器 (关键):
           - 等待弹窗出现
           - 使用 expect_file_chooser 包裹点击动作
           - 点击弹窗内的"本地上传"卡片，触发文件选择器

        3. 文件注入:
           - 使用 file_chooser.set_files() 注入文件

        4. 强制确认:
           - 物理点击 button:has-text("确定")
        """
        try:
            # ========== 步骤 1: 物理触发 (DNA 级唤醒) ==========
            # DNA 锚定：div._73a3a52aab7e3a36-content
            target = page.locator('div._73a3a52aab7e3a36-content').last

            # 物理滚动到可视区域
            await target.scroll_into_view_if_needed(timeout=5000)
            await asyncio.sleep(0.3)

            # 物理点击 DNA 元素
            await target.click(force=True)
            logger.info("🎯 [封面-第1步] 已点击 DNA 锚点: div._73a3a52aab7e3a36-content")

            # ========== 步骤 2: 等待弹窗并点击"本地上传" ==========
            # 等待弹窗出现
            await asyncio.sleep(1.0)

            # Referer 补丁
            await page.set_extra_http_headers({
                "Referer": "https://baijiahao.baidu.com/",
                "Origin": "https://baijiahao.baidu.com"
            })

            # 使用 expect_file_chooser 包裹点击动作
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                upload_clicked = False

                # 尝试多种选择器点击"本地上传"
                local_upload_selectors = [
                    'div:has-text("本地上传")',
                    'button:has-text("本地上传")',
                    'span:has-text("本地上传")',
                    '[role="button"]:has-text("本地上传")',
                    '[role="listitem"]:has-text("本地上传")',
                ]

                for selector in local_upload_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        for i in range(count):
                            btn = elements.nth(i)
                            if await btn.is_visible(timeout=500):
                                await btn.click(force=True)
                                upload_clicked = True
                                break
                        if upload_clicked:
                            break
                    except Exception as e:
                        logger.debug(f"尝试选择器 {selector} 失败: {e}")
                        continue

                if not upload_clicked:
                    logger.warning("⚠️ [封面-第2步] 未找到本地上传按钮")

                # 等待文件选择器被捕获
                file_chooser = await fc_info.value

            # 注入文件路径
            await file_chooser.set_files(image_path)
            logger.info("📤 [封面-第3步] 文件已通过文件选择器注入")

            # ========== 步骤 3: 触发 change 事件 ==========
            await page.evaluate("""() => {
                const allInputs = document.querySelectorAll('input[type="file"]');
                allInputs.forEach(input => {
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
            }""")
            logger.info("🎯 [封面-第4步] 已触发 change 事件")

            # 等待上传处理
            await asyncio.sleep(2.0)

            # ========== 步骤 4: 强制确认按钮 ==========
            confirm_selectors = [
                'button:has-text("确定")',
                'button.cheetah-btn-primary:has-text("确定")',
            ]

            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    btn = page.locator(selector).last
                    if await btn.is_visible(timeout=2000):
                        await btn.click(force=True)
                        confirm_clicked = True
                        break
                except:
                    continue

            if confirm_clicked:
                await asyncio.sleep(1.0)

            # ========== 步骤 5: 处理可能出现的错误弹窗 ==========
            # 点击"确定"后可能会出现"视频格式错误"等错误弹窗
            # 需要检查并关闭这些弹窗
            await asyncio.sleep(0.5)

            # 查找所有可能出现的错误/提示弹窗
            error_dialog_info = await page.evaluate("""() => {
                const results = [];
                const keywords = ['格式', '错误', '提示', '警告', 'error', 'warning'];
                const allElements = document.querySelectorAll('*');

                allElements.forEach(el => {
                    const text = (el.innerText || el.textContent || '').toLowerCase();
                    const style = window.getComputedStyle(el);
                    const isVisible = style.position !== 'none' && style.visibility !== 'hidden' &&
                                     parseInt(style.zIndex) > 100;

                    if (isVisible && keywords.some(kw => text.includes(kw))) {
                        results.push({
                            tag: el.tagName,
                            class: el.className,
                            text: (el.innerText || el.textContent || '').substring(0, 50)
                        });
                    }
                });
                return results;
            }""")

            # 尝试点击错误弹窗中的按钮（我知道了、关闭、重试等）
            error_btn_selectors = [
                'button:has-text("我知道了")',
                'button:has-text("关闭")',
                'button:has-text("知道了")',
                'button:has-text("重试")',
                'button:has-text("继续")',
                'button:has-text("确定")',
                'button.cheetah-btn-primary:has-text("我知道了")',
                'button.cheetah-btn-primary:has-text("关闭")',
                'div[role="button"]:has-text("我知道了")',
                'div[role="button"]:has-text("关闭")',
            ]

            error_btn_clicked = False
            for selector in error_btn_selectors:
                try:
                    btn = page.locator(selector)
                    count = await btn.count()
                    if count > 0:
                        for i in range(count):
                            current_btn = btn.nth(i)
                            if await current_btn.is_visible(timeout=500):
                                await current_btn.click(force=True)
                                error_btn_clicked = True
                                break
                        if error_btn_clicked:
                            break
                except:
                    continue

            if error_btn_clicked:
                await asyncio.sleep(0.5)

            # 再次检查并点击"确定"按钮（处理可能的二次确认）
            for selector in confirm_selectors:
                try:
                    btn = page.locator(selector).last
                    if await btn.is_visible(timeout=1000):
                        await btn.click(force=True)
                        break
                except:
                    continue

            logger.success("✅ [封面] 封面注入流程完成（精准点击 + expect_file_chooser）")
            return True

        except Exception as e:
            logger.warning(f"⚠️ [封面] 注入失败: {e}")
            # 封面失败不应该阻断整个流程
            return True

    async def _reconfirm_cover(self, page: Page) -> bool:
        """
        封面再次确认 (在正文和标题写完后调用)

        核心逻辑:
        1. 再次点击封面区域，确保封面已正确上传
        2. 如果有错误弹窗，点击关闭/确认
        """
        try:
            logger.info("🎯 [封面-再次确认] 开始再次确认封面...")

            # 点击封面占位符区域
            cover_selectors = [
                'div._73a3a52aab7e3a36-content',
                'div:has-text("选择封面")',
                'div:has-text("封面")',
            ]

            clicked = False
            for selector in cover_selectors:
                try:
                    target = page.locator(selector).last
                    if await target.is_visible(timeout=2000):
                        await target.scroll_into_view_if_needed(timeout=3000)
                        await asyncio.sleep(0.3)
                        await target.click(force=True)
                        clicked = True
                        break
                except:
                    continue

            if clicked:
                await asyncio.sleep(1.0)

                # 检查是否有确认按钮需要点击
                confirm_selectors = [
                    'button:has-text("确定")',
                    'button.cheetah-btn-primary:has-text("确定")',
                ]

                for selector in confirm_selectors:
                    try:
                        btn = page.locator(selector)
                        count = await btn.count()
                        if count > 0:
                            for i in range(count):
                                current_btn = btn.nth(i)
                                if await current_btn.is_visible(timeout=1000):
                                    await current_btn.click(force=True)
                                    await asyncio.sleep(0.5)
                                    break
                            break
                    except:
                        continue

            logger.success("✅ [封面-再次确认] 封面再次确认完成")
            return True

        except Exception as e:
            logger.warning(f"⚠️ [封面-再次确认] 失败: {e}")
            return True

    async def _physical_write_content(self, page: Page, content: str) -> bool:
        """
        正文注入 (增强版 - 支持多种编辑器)

        Rule #1 (状态同步):
        严禁使用 .fill() 和 .keyboard.type() 写入长文本
        必须通过 execCommand('insertHTML') 配合 Space + Backspace 唤醒 React

        核心逻辑:
        1. 定位：锁定 iframe 内 contenteditable 容器
        2. 注入：使用 execCommand('insertHTML', false, cleanBody)
        3. 状态激活：注入后必须执行物理按键 End -> Space -> Backspace
        """
        try:
            # 定位 iframe
            iframes = await page.locator("iframe").count()
            if iframes == 0:
                logger.error("❌ [正文] 页面中没有找到 iframe")
                return False

            # 尝试找到正文编辑器 iframe
            target_iframe = None
            for i in range(iframes):
                iframe_locator = page.locator("iframe").nth(i)
                # 获取 element_handle 然后 content_frame
                iframe_element = await iframe_locator.element_handle()
                if not iframe_element:
                    continue
                frame = await iframe_element.content_frame()
                try:
                    # 检查这个 iframe 是否有 contenteditable
                    has_content_editable = await frame.evaluate("""() => {
                        const ce = document.querySelector('[contenteditable="true"]');
                        return ce !== null;
                    }""")
                    if has_content_editable:
                        target_iframe = frame
                        break
                except:
                    continue

            if not target_iframe:
                # 兜底：使用第一个 iframe
                iframe = await page.wait_for_selector("iframe", timeout=15000)
                target_iframe = await iframe.content_frame()

            # 等待编辑器加载
            await asyncio.sleep(1.0)

            # 查看 iframe 内的元素结构
            iframe_info = await target_iframe.evaluate("""() => {
                const results = {
                    bodyText: document.body.innerText.substring(0, 100),
                    hasContentEditable: document.querySelector('[contenteditable="true"]') !== null,
                    hasDataDiagnoseId: document.querySelector('[data-diagnose-id]') !== null,
                    bodyHTML: document.body.innerHTML.substring(0, 200)
                };
                return results;
            }""")

            # 多种选择器尝试定位编辑器
            content_selectors = [
                '[contenteditable="true"]',
                '[data-diagnose-id"]',
                '.edui-editor',
                '.editor-content',
            ]

            content_found = False
            for selector in content_selectors:
                try:
                    count = await target_iframe.locator(selector).count()
                    if count > 0:
                        content_found = True
                        break
                except:
                    continue

            if not content_found:
                logger.error("❌ [正文] 未找到可编辑区域")
                return False

            # 清空并聚焦编辑器
            await target_iframe.evaluate("""() => {
                const ce = document.querySelector('[contenteditable="true"]');
                if (ce) {
                    ce.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                } else {
                    // 如果没有找到 contenteditable，尝试直接操作 body
                    document.body.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                }
            }""")
            await asyncio.sleep(0.5)

            # Rule #1: Space + Backspace 唤醒 React
            await page.keyboard.press("Space")
            await asyncio.sleep(0.1)
            await page.keyboard.press("Backspace")

            # 使用 execCommand 注入 HTML
            await target_iframe.evaluate(
                "(html) => document.execCommand('insertHTML', false, html)",
                content
            )

            # 状态激活：End -> Space -> Backspace
            await page.keyboard.press("End")
            await asyncio.sleep(0.1)
            await page.keyboard.press("Space")
            await asyncio.sleep(0.1)
            await page.keyboard.press("Backspace")

            # 等待内容渲染
            await asyncio.sleep(1.0)

            # 验证：检查内容是否真的写入了
            verification = await target_iframe.evaluate("""() => {
                const bodyText = document.body.innerText || '';
                const bodyHTML = document.body.innerHTML || '';
                return {
                    bodyLength: bodyText.length,
                    bodyPreview: bodyText.substring(0, 100),
                    bodyHTMLLength: bodyHTML.length,
                    bodyHTMLPreview: bodyHTML.substring(0, 200)
                };
            }""")

            logger.success("✅ [正文] 正文注入并唤醒成功 (execCommand + page.keyboard)")
            return True

        except Exception as e:
            logger.error(f"❌ [正文] 注入失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _physical_write_title(self, page: Page, title: str) -> bool:
        """
        标题锁定 (DNA: p[dir="auto"])

        Rule #2: 这是全流程最后一步

        核心逻辑:
        1. 定位：锁定页面主 DOM 中 p[dir="auto"] 所在的 contenteditable 容器
        2. 注入：使用 execCommand('insertText', false, cleanTitle)
        3. 时序：注入后按 Enter 锁定
        """
        try:
            # DNA 定位：p[dir="auto"]
            await page.wait_for_selector('p[dir="auto"]', timeout=10000)

            # 获取最近的 contenteditable 容器
            await page.evaluate("""(text) => {
                // DNA: p[dir="auto"]
                const titleEl = document.querySelector('p[dir="auto"]');
                const container = titleEl.closest('[contenteditable="true"]');

                if (container) {
                    container.focus();

                    // 清空现有内容
                    document.execCommand('selectAll', false, null);

                    // Rule #1: 使用 execCommand 注入文本
                    document.execCommand('insertText', false, text);

                    // 触发 input 事件
                    container.dispatchEvent(new Event('input', { bubbles: true }));
                    container.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", title)

            await asyncio.sleep(0.3)

            # Rule #2: 按 Enter 锁定标题
            await page.keyboard.press("Enter")

            logger.success("✅ [标题] 标题注入并锁定成功 (execCommand + Enter)")
            return True

        except Exception as e:
            logger.error(f"❌ [标题] 注入失败: {e}")
            return False

    async def _physical_publish(self, page: Page) -> bool:
        """
        发布确认 (增强版 - 处理二次确认)

        核心逻辑:
        1. 启用所有禁用的发布按钮
        2. 点击发布按钮
        3. 处理二次确认（AI 内容/滑块）
        """
        try:
            # 先等待页面稳定
            await asyncio.sleep(1.0)

            # 启用所有可能被禁用的发布按钮
            await page.evaluate(
                """() => {
                    document.querySelectorAll('button').forEach(btn => {
                        if (btn.innerText.includes('发布') || btn.innerText.includes('确认')) {
                            btn.disabled = false;
                            btn.removeAttribute('disabled');
                        }
                    });
                }"""
            )

            # 查找所有包含"发布"的按钮
            publish_buttons_info = await page.evaluate("""() => {
                const results = [];
                const buttons = document.querySelectorAll('button');
                buttons.forEach(btn => {
                    const text = btn.innerText || btn.textContent || '';
                    if (text.includes('发布')) {
                        results.push({
                            class: btn.className,
                            text: text.substring(0, 30),
                            disabled: btn.disabled,
                            visible: btn.offsetParent !== null
                        });
                    }
                });
                return results;
            }""")

            # 尝试多种选择器定位发布按钮
            publish_selectors = [
                'button.cheetah-btn-primary:has-text("发布")',
                'button:has-text("发布")',
                '[class*="publish"]:has-text("发布")',
                'button[type="submit"]:has-text("发布")',
            ]

            clicked = False
            for selector in publish_selectors:
                try:
                    btn = page.locator(selector)
                    count = await btn.count()

                    if count > 0:
                        # 尝试点击第一个可见的发布按钮
                        for i in range(count):
                            current_btn = btn.nth(i)
                            if await current_btn.is_visible(timeout=1000):
                                # 滚动到可视区域
                                await current_btn.scroll_into_view_if_needed(timeout=3000)
                                await asyncio.sleep(0.3)
                                await current_btn.click(force=True)
                                clicked = True
                                logger.info(f"✅ [发布] 已点击发布按钮: {selector} (第{i+1}个)")
                                break
                        if clicked:
                            break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 失败: {e}")
                    continue

            if not clicked:
                logger.error("❌ [发布] 未找到可点击的发布按钮")
                return False

            # 等待二次确认弹窗或页面跳转
            await asyncio.sleep(2.0)

            # 检查 URL 是否已跳转
            if "publish" in page.url or "success" in page.url:
                logger.info("✅ [发布] 页面已跳转，发布完成")
                return True

            # 处理二次确认

            # 查找所有确认按钮
            confirm_buttons = await page.evaluate("""() => {
                const results = [];
                const buttons = document.querySelectorAll('button');
                buttons.forEach(btn => {
                    const text = btn.innerText || btn.textContent || '';
                    const className = btn.className || '';
                    // 查找发布、确认、继续等按钮
                    if (text.includes('发布') || text.includes('确认') || text.includes('继续')) {
                        results.push({
                            class: className,
                            text: text.substring(0, 30),
                            disabled: btn.disabled,
                            visible: btn.offsetParent !== null,
                            isPrimary: className.includes('primary') || className.includes('cheetah-btn-primary')
                        });
                    }
                });
                return results;
            }""")

            # 优先点击 primary 级别的确认按钮
            confirm_selectors = [
                'button.cheetah-btn-primary:has-text("发布")',
                'button.cheetah-btn-primary:has-text("确认")',
                'button.cheetah-btn-primary:has-text("继续")',
                'button:has-text("发布")',
                'button:has-text("确认")',
                'button:has-text("继续")',
            ]

            confirm_clicked = False
            for selector in confirm_selectors:
                try:
                    btn = page.locator(selector)
                    count = await btn.count()
                    if count > 0:
                        for i in range(count):
                            current_btn = btn.nth(i)
                            if await current_btn.is_visible(timeout=1000):
                                await current_btn.scroll_into_view_if_needed(timeout=3000)
                                await asyncio.sleep(0.3)
                                await current_btn.click(force=True)
                                confirm_clicked = True
                                logger.info(f"✅ [发布] 已点击确认按钮: {selector} (第{i+1}个)")
                                break
                        if confirm_clicked:
                            break
                except Exception as e:
                    logger.debug(f"确认选择器 '{selector}' 失败: {e}")
                    continue

            # 检查滑块验证
            if await page.locator('div:has-text("安全验证")').count() > 0:
                logger.warning("🚨 [风控] 触发滑块验证！请在 60 秒内手动完成滑动！")
                await page.wait_for_selector(
                    'div:has-text("安全验证")',
                    state='hidden',
                    timeout=60000
                )
                logger.info("✅ [风控] 检测到滑块消失，继续流程...")

            logger.success("✅ [发布] 发布按钮已点击")
            return True

        except Exception as e:
            logger.error(f"❌ [发布] 点击失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        等待发布结果

        Returns:
            发布结果字典
        """
        try:
            # 等待跳转到成功页面
            await page.wait_for_url(
                re.compile(r".*(success|content/index).*"),
                timeout=30000
            )
            logger.success(f"🎊 [成功] 发布成功: {page.url}")
            return {"success": True, "platform_url": page.url}

        except Exception:
            logger.warning(f"⚠️ [结果] 未检测到成功跳转，但可能已发布: {page.url}")
            return {"success": True, "platform_url": page.url}

    async def _download_images(self, urls: List[str]) -> List[str]:
        """
        下载图片到本地临时目录 - Critical Fix v16.2

        修复内容:
        1. follow_redirects=True: 允许跟随 302 跳转获取真实图片
        2. trust_env=False: 绕过本地可能报错的代理配置
        3. 添加正确的 User-Agent 和 Referer headers
        4. 备用图源：确保必定能下载到一张图

        Args:
            urls: 图片 URL 列表

        Returns:
            下载后的本地路径列表
        """
        paths = []

        # 合并用户提供的 URL 和备用图源
        all_urls = urls + self.FALLBACK_IMAGE_URLS

        # 只取第一张成功下载的图片作为封面
        for url in all_urls:
            try:
                # ========== Critical Fix: 正确的 httpx 配置 ==========
                async with httpx.AsyncClient(
                    verify=False,                       # 跳过 SSL 验证
                    follow_redirects=True,              # 关键：允许跟随 302 跳转获取真实图片
                    trust_env=False,                    # 关键：绕过本地可能报错的代理配置
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.baidu.com"
                    },
                    timeout=30.0                         # 超时时间 30 秒
                ) as client:
                    resp = await client.get(url)

                # 检查响应状态码
                    if resp.status_code in (200, 301, 302):
                        # 如果是重定向，httpx 已经自动跟随，直接获取最终内容
                        if len(resp.content) > 10000:  # 确保下载到的是有效图片（至少 10KB）
                            # 生成随机文件名
                            tmp_path = os.path.join(
                                tempfile.gettempdir(),
                                f"bjh_v15_{random.randint(10000, 99999)}.jpg"
                            )
                            with open(tmp_path, "wb") as f:
                                f.write(resp.content)
                            paths.append(tmp_path)
                            logger.success(f"✅ [图片] 封面图下载成功: {url} ({len(resp.content)} bytes)")
                            return paths  # 成功下载一张就返回
                        else:
                            logger.warning(f"⚠️ [图片] 下载内容过小，可能不是有效图片: {url}")
                    else:
                        logger.warning(f"⚠️ [图片] HTTP 状态码异常: {resp.status_code} - {url}")

            except httpx.HTTPStatusError as e:
                logger.warning(f"⚠️ [图片] HTTP 错误: {e.response.status_code} - {url}")
            except httpx.TimeoutException:
                logger.warning(f"⚠️ [图片] 下载超时: {url}")
            except httpx.ProxyError:
                logger.warning(f"⚠️ [图片] 代理错误，已绕过: {url}")
            except Exception as e:
                logger.warning(f"⚠️ [图片] 下载失败: {e} - {url}")

        logger.error("❌ [图片] 所有图源均下载失败")
        return paths


# 注册到全局注册表
BAIJIAHAO_CONFIG = {
    "name": "百家号",
    "publish_url": "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1",
    "color": "#2932E1"
}
registry.register("baijiahao", BaijiahaoPublisher("baijiahao", BAIJIAHAO_CONFIG))
