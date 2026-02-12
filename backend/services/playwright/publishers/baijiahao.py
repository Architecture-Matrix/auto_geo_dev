# -*- coding: utf-8 -*-
"""
百家号发布适配器 - v17.0 切片插入+动态图源版

重构内容:
1. 统一图源下载: 使用 pollinations.ai 根据关键词生成相关图片
2. 切片插入逻辑: 将正文分成 4 块，循环插入文字和图片
3. 图片去重: 通过随机 seed 确保下载 3-4 张不重复的相关图片
4. DataTransfer 协议直投: 直接将图片 Base64 数据注入到 iframe 编辑器
5. 容错机制: 图片下载或插入失败时记录 warning，不中断发布流程
6. 临时文件清理: 任务结束后删除所有本地 temp 图片文件
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
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class BaijiahaoPublisher(BasePublisher):
    """
    百家号发布适配器 - v17.0 切片插入+动态图源版

    核心特性:
    1. 统一图源下载: pollinations.ai 动态生成相关图片
    2. 切片插入策略: 一段文字 + 一张图片的完美排版
    3. Iframe 协议直投: execCommand('insertHTML') + DataTransfer 图片注入
    4. DNA 锚点封面上传: 保持原有封面上传逻辑
    5. 深度 Shadow DOM 穿透清场
    6. 强容错: 图片失败不影响正文和标题发布
    """

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 [百家号] 开始执行 v17.0 切片插入发布流程...")

            # ========== 步骤 0: 注入隐身疫苗 & 导航 ==========
            await self._inject_stealth_vaccine(page)
            await self._navigate_to_editor(page)

            # ========== 步骤 1: 物理清场 ==========
            await self._smash_interferences(page)

            # ========== 步骤 2: 准备资源 - 提取关键词并下载图片 ==========
            clean_title = article.title.replace("#", "").strip()
            keyword = self._extract_keyword(clean_title)
            logger.info(f"🔍 提取关键词: {keyword}")

            # 下载图片 (4 张用于正文，第一张也用于封面)
            downloaded_paths = await self._download_relevant_images(keyword, count=4)
            temp_files.extend(downloaded_paths)

            if not downloaded_paths:
                logger.warning("⚠️ 图片下载失败，但继续后续流程")
            else:
                logger.success(f"✅ [图片] 已成功下载 {len(downloaded_paths)} 张图片")

            # ========== 步骤 3: 内容切片 - 将正文分成 4 块 ==========
            clean_content = self._deep_clean_content(article.content)
            text_chunks = self._split_content_to_chunks(clean_content, num_chunks=4)

            # ========== Golden Rule: 封面 -> 正文 -> 标题 ==========

            # 步骤 4: 封面注入 (先行)
            if downloaded_paths:
                await self._physical_upload_cover(page, downloaded_paths[0])
                await self._smash_interferences(page)

            # 步骤 5: 切片插入正文
            await self._inject_content_with_images(page, text_chunks, downloaded_paths)
            await self._smash_interferences(page)

            # 步骤 6: 标题锁定 (终极)
            await self._physical_write_title(page, clean_title)
            await self._smash_interferences(page)

            # 步骤 7: 封面再次确认
            if downloaded_paths:
                await self._reconfirm_cover(page)
                await self._smash_interferences(page)

            # ========== 步骤 8: 发布确认 ==========
            publish_result = await self._physical_publish(page)
            if not publish_result:
                return {"success": False, "error_msg": "发布失败"}

            # ========== 步骤 9: 等待结果 ==========
            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ [百家号] 发布链路崩溃: {e}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                        logger.info(f"🧹 已删除临时图片: {f}")
                    except Exception as e:
                        logger.warning(f"⚠️ 删除临时图片失败: {e}")

    def _extract_keyword(self, title: str) -> str:
        """从标题中提取关键词用于生成相关图片"""
        # 移除标点和特殊字符，提取核心词
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', ' ', title)
        words = cleaned.split()
        # 返回前 1-2 个核心词
        if words:
            return words[0] if len(words) == 1 else f"{words[0]} {words[1]}"
        return "风景"

    def _split_content_to_chunks(self, content: str, num_chunks: int = 4) -> List[str]:
        """将内容按换行符切成指定数量的块"""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            return [""] * num_chunks

        chunk_size = max(1, len(lines) // num_chunks)
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < num_chunks - 1 else len(lines)
            chunk_lines = lines[start:end]
            chunks.append('\n'.join(chunk_lines))
        return chunks

    async def _download_relevant_images(self, keyword: str, count: int = 4) -> List[str]:
        """
        统一图源下载: 使用 pollinations.ai 生成相关图片

        URL 模板: https://image.pollinations.ai/prompt/{keyword}%20seed%20{seed}?width=800&height=600&nologo=true
        去重: 通过不同的随机 seed 确保下载 3-4 张不重复的相关图片
        """
        paths = []
        used_seeds = set()
        base_url = "https://image.pollinations.ai/prompt/"

        async def _download_single_image(url: str, index: int) -> Optional[str]:
            """下载单张图片并校验"""
            try:
                logger.info(f"📥 正在下载图片 {index + 1}/{count}: {url[:80]}...")
                resp = await client.get(url, timeout=30.0)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    tmp = os.path.join(tempfile.gettempdir(), f"bjh_v17_{keyword}_{random.randint(10000, 99999)}.jpg")
                    with open(tmp, "wb") as f:
                        f.write(resp.content)

                    # 校验文件大小
                    file_size = os.path.getsize(tmp)
                    if file_size < 1024:  # 小于 1KB 视为失败
                        logger.warning(f"⚠️ 图片 {index + 1} 文件太小 ({file_size} bytes)")
                        if os.path.exists(tmp):
                            os.remove(tmp)
                        return None

                    logger.info(f"✅ 图片 {index + 1} 下载成功: {tmp} ({file_size} bytes)")
                    return tmp
                else:
                    logger.warning(f"⚠️ 图片 {index + 1} HTTP 状态码: {resp.status_code}")
                    return None
            except Exception as e:
                logger.warning(f"⚠️ 图片 {index + 1} 下载异常: {e}")
                return None

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            for i in range(count):
                # 生成唯一的随机 seed
                while True:
                    seed = random.randint(1, 10000)
                    if seed not in used_seeds:
                        used_seeds.add(seed)
                        break

                # 构造图片 URL
                encoded_keyword = urllib.parse.quote(keyword)
                image_url = f"{base_url}{encoded_keyword}%20seed%20{seed}?width=800&height=600&nologo=true"

                # 重试 3 次
                for retry in range(3):
                    downloaded = await _download_single_image(image_url, i)
                    if downloaded:
                        paths.append(downloaded)
                        break
                    logger.warning(f"🔄 第 {retry + 1} 次重试...")

        return paths

    async def _inject_content_with_images(self, page: Page, text_chunks: List[str], image_paths: List[str]):
        """
        切片插入正文: 一段文字 + 一张图片的完美排版

        循环操作:
        1. 调用 execCommand('insertHTML') 注入一段文字
        2. 使用 DataTransfer 协议直接将当前图片的 Base64 数据注入到 iframe 编辑器
        3. 执行物理按键 End -> Enter 换行
        4. 注入下一块文字
        """
        try:
            # 定位 iframe
            iframes = await page.locator("iframe").count()
            if iframes == 0:
                logger.error("❌ [正文] 页面中没有找到 iframe")
                return False

            # 找到正文编辑器 iframe
            target_iframe = None
            for i in range(iframes):
                iframe_locator = page.locator("iframe").nth(i)
                iframe_element = await iframe_locator.element_handle()
                if not iframe_element:
                    continue
                frame = await iframe_element.content_frame()
                try:
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

            # 清空编辑器
            await target_iframe.evaluate("""() => {
                const ce = document.querySelector('[contenteditable="true"]');
                if (ce) {
                    ce.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                }
            }""")
            await asyncio.sleep(0.5)

            # 循环插入文字和图片
            for i, text_chunk in enumerate(text_chunks):
                # 注入当前文字块
                logger.info(f"📝 注入第 {i + 1} 块文字...")
                await target_iframe.evaluate(
                    "(html) => document.execCommand('insertHTML', false, html)",
                    text_chunk
                )
                await asyncio.sleep(0.5)

                # 如果还有图片，注入图片
                if i < len(image_paths) and image_paths[i]:
                    logger.info(f"🖼️ 注入第 {i + 1} 张图片...")
                    await self._inject_image_via_datatransfer(page, target_iframe, image_paths[i])
                    await asyncio.sleep(3)  # 等待图片上传处理

                # 物理按键 End -> Enter 确保排版顺畅
                await page.keyboard.press("End")
                await asyncio.sleep(0.1)
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.5)

            logger.success("✅ 切片插入完成")
            return True

        except Exception as e:
            logger.warning(f"⚠️ 切片插入失败（将继续执行后续步骤）: {e}")
            return True

    async def _inject_image_via_datatransfer(self, page: Page, frame, image_path: str):
        """
        使用 DataTransfer 协议直接将图片注入到 iframe 编辑器

        核心逻辑:
        1. 读取图片文件并转换为 Base64
        2. 在 iframe 编辑器中模拟粘贴事件
        3. 使用 DataTransfer 和 File 对象注入图片
        """
        try:
            # 读取图片文件
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            # 在 iframe 中注入图片
            await frame.evaluate('''(b64) => {
                const byteCharacters = atob(b64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const dt = new DataTransfer();
                dt.items.add(new File([new Uint8Array(byteNumbers)], "img.jpg", { type: 'image/jpeg' }));

                // 在 contenteditable 区域触发粘贴事件
                const ce = document.querySelector('[contenteditable="true"]');
                if (ce) {
                    ce.focus();
                    ce.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }));
                }
            }''', b64)
            logger.info("✅ 图片通过 DataTransfer 协议注入成功")

        except Exception as e:
            logger.warning(f"⚠️ 图片注入失败: {e}")

    async def _inject_stealth_vaccine(self, page: Page):
        """注入隐身疫苗"""
        await page.add_init_script("""() => {
            localStorage.setItem('BAIDU_BJ_GUIDE_STATE', 'true');
            localStorage.setItem('BJ_TOUR_COMPLETED', 'true');
            localStorage.setItem('ai_tool_guide_status', '1');
            localStorage.setItem('first_login_flag', 'true');

            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            window.chrome = {
                runtime: {},
                loadTimes: Date.now,
                csi: () => {},
                app: {}
            };

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        }""")
        logger.info("💉 [隐身疫苗] 已注入")

    async def _navigate_to_editor(self, page: Page):
        """导航到编辑器页面"""
        golden_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1"

        await page.set_extra_http_headers({
            "Referer": "https://baijiahao.baidu.com/builder/rc/home"
        })

        await page.goto(golden_url, wait_until="networkidle", timeout=60000)

        if "login" in page.url:
            raise Exception("登录态失效，请重新授权")

        if "type=news" not in page.url:
            logger.warning("⚠️ [导航] 被重定向，执行强制导航...")
            await page.goto(golden_url, wait_until="networkidle", timeout=60000)

        logger.info("✅ [导航] 成功抵达编辑器")

    async def _smash_interferences(self, page: Page):
        """物理清场"""
        await page.evaluate("""() => {
            const keywords = ['下一步', '1/4', 'AI工具', '引导', '知道了', '新手引导', '开始创作', '上传成功', '操作成功'];

            function scanAndSmash(root) {
                const allElements = root.querySelectorAll('*');

                allElements.forEach(el => {
                    const style = window.getComputedStyle(el);

                    if (parseInt(style.zIndex) > 500 &&
                        (style.position === 'fixed' || style.position === 'absolute')) {

                        const text = el.innerText || el.textContent || '';

                        if (keywords.some(kw => text.includes(kw))) {
                            el.remove();
                        }
                    }

                    if (el.shadowRoot) {
                        scanAndSmash(el.shadowRoot);
                    }
                });
            }

            scanAndSmash(document);
            document.body.style.overflow = 'auto';

            const masks = document.querySelectorAll('[class*="mask"], [class*="overlay"]');
            masks.forEach(m => m.remove());
        }""")

        for _ in range(3):
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.1)

        logger.info("🧹 [物理清场] 干扰弹窗已暴力清理")

    async def _physical_upload_cover(self, page: Page, image_path: str):
        """封面注入 - DNA 锚点 + expect_file_chooser 方案"""
        try:
            # 步骤 1: 物理触发 DNA 锚点
            target = page.locator('div._73a3a52aab7e3a36-content').last
            await target.scroll_into_view_if_needed(timeout=5000)
            await asyncio.sleep(0.3)
            await target.click(force=True)
            logger.info("🎯 [封面-第1步] 已点击 DNA 锚点")

            # 步骤 2: 等待弹窗并点击"本地上传"
            await asyncio.sleep(1.0)

            await page.set_extra_http_headers({
                "Referer": "https://baijiahao.baidu.com/",
                "Origin": "https://baijiahao.baidu.com"
            })

            async with page.expect_file_chooser(timeout=5000) as fc_info:
                upload_clicked = False

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
                        continue

                if not upload_clicked:
                    logger.warning("⚠️ [封面-第2步] 未找到本地上传按钮")

                file_chooser = await fc_info.value

            await file_chooser.set_files(image_path)
            logger.info("📤 [封面-第3步] 文件已注入")

            # 步骤 3: 触发 change 事件
            await page.evaluate("""() => {
                const allInputs = document.querySelectorAll('input[type="file"]');
                allInputs.forEach(input => {
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
            }""")
            await asyncio.sleep(2.0)

            # ========== 步骤 4: 点击确定按钮 - 增强版 ==========
            # 处理 <span>确定 (1)</span> 这种动态文本

            logger.info("🎯 [封面-第4步] 开始定位确认按钮...")
            confirm_clicked = False

            # 方案 1: 使用 CSS 选择器：button:has(span:has-text("确定"))
            confirm_selectors = [
                'button:has(span:has-text("确定"))',
                'button.cheetah-btn-primary:has(span:has-text("确定"))',
                'button:has-text("确定")',
                'button.cheetah-btn-primary:has-text("确定")',
            ]

            for selector in confirm_selectors:
                try:
                    btn = page.locator(selector).last
                    # 等待可点击状态
                    await btn.wait_for(state="visible", timeout=10000)
                    # 强制等待渲染（按钮从灰色变蓝色有延迟）
                    await asyncio.sleep(2)
                    await btn.click(force=True)
                    confirm_clicked = True
                    logger.info(f"✅ [封面-第4步] 已点击确认按钮 (选择器: {selector})")
                    break
                except:
                    continue

            # 方案 2: 暴力 JS 点击 - 如果常规点击无效
            if not confirm_clicked:
                logger.info("🔄 [封面-第4步] 常规点击无效，尝试暴力 JS 点击...")
                js_clicked = await page.evaluate("""() => {
                    // 查找所有包含"确定"文本的 span 元素
                    const spans = Array.from(document.querySelectorAll('span'));
                    const targetSpan = spans.find(s => s.innerText && s.innerText.includes('确定'));

                    if (targetSpan) {
                        // 向上查找最近的 button 元素
                        const btn = targetSpan.closest('button');
                        if (btn) {
                            btn.click();
                            return true;
                        }
                    }

                    // 兜底：直接查找所有按钮中包含"确定"文本的
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        if (btn.innerText && btn.innerText.includes('确定')) {
                            btn.click();
                            return true;
                        }
                    }

                    return false;
                }""")

                if js_clicked:
                    confirm_clicked = True
                    logger.info("✅ [封面-第4步] JS 暴力点击成功")

            # ========== 步骤 5: 关闭后续干扰 ==========
            # 点击确定后，立即调用 _smash_interferences，防止百家号弹出"新手引导"或"设置成功"的遮罩层
            await asyncio.sleep(1.0)
            if confirm_clicked:
                await self._smash_interferences(page)
                logger.info("🧹 [封面-第5步] 已关闭后续干扰弹窗")

            logger.success("✅ [封面] 封面注入流程完成")
            return True

        except Exception as e:
            logger.warning(f"⚠️ [封面] 注入失败: {e}")
            return True

    async def _reconfirm_cover(self, page: Page) -> bool:
        """封面再次确认"""
        try:
            logger.info("🎯 [封面-再次确认] 开始再次确认封面...")

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

                # ========== 点击确定按钮 - 垢强版 ==========
                # 处理 <span>确定 (1)</span> 这种动态文本
                logger.info("🎯 [封面-再次确认] 开始定位确认按钮...")
                confirm_clicked = False

                # 方案 1: 使用 CSS 选择器：button:has(span:has-text("确定"))
                confirm_selectors = [
                    'button:has(span:has-text("确定"))',
                    'button.cheetah-btn-primary:has(span:has-text("确定"))',
                    'button:has-text("确定")',
                    'button.cheetah-btn-primary:has-text("确定")',
                ]

                for selector in confirm_selectors:
                    try:
                        btn = page.locator(selector).last
                        # 等待可点击状态
                        await btn.wait_for(state="visible", timeout=10000)
                        # 强制等待渲染（按钮从灰色变蓝色有延迟）
                        await asyncio.sleep(2)
                        await btn.click(force=True)
                        confirm_clicked = True
                        logger.info(f"✅ [封面-再次确认] 已点击确认按钮 (选择器: {selector})")
                        break
                    except:
                        continue

                # 方案 2: 暴力 JS 点击 - 如果常规点击无效
                if not confirm_clicked:
                    logger.info("🔄 [封面-再次确认] 常规点击无效，尝试暴力 JS 点击...")
                    js_clicked = await page.evaluate("""() => {
                        // 查找所有包含"确定"文本的 span 元素
                        const spans = Array.from(document.querySelectorAll('span'));
                        const targetSpan = spans.find(s => s.innerText && s.innerText.includes('确定'));

                        if (targetSpan) {
                            // 向上查找最近的 button 元素
                            const btn = targetSpan.closest('button');
                            if (btn) {
                                btn.click();
                                return true;
                            }
                        }

                        // 兜底：直接查找所有按钮中包含"确定"文本的
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const btn of buttons) {
                            if (btn.innerText && btn.innerText.includes('确定')) {
                                btn.click();
                                return true;
                            }
                        }

                        return false;
                    }""")

                    if js_clicked:
                        confirm_clicked = True
                        logger.info("✅ [封面-再次确认] JS 暴力点击成功")

                # ========== 关闭后续干扰 ==========
                # 点击确定后，立即调用 _smash_interferences
                await asyncio.sleep(1.0)
                if confirm_clicked:
                    await self._smash_interferences(page)
                    logger.info("🧹 [封面-再次确认] 已关闭后续干扰弹窗")

            logger.success("✅ [封面-再次确认] 封面再次确认完成")
            return True

        except Exception as e:
            logger.warning(f"⚠️ [封面-再次确认] 失败: {e}")
            return True

    async def _physical_write_title(self, page: Page, title: str) -> bool:
        """标题锁定 (DNA: p[dir="auto"])"""
        try:
            await page.wait_for_selector('p[dir="auto"]', timeout=10000)

            await page.evaluate("""(text) => {
                const titleEl = document.querySelector('p[dir="auto"]');
                const container = titleEl.closest('[contenteditable="true"]');

                if (container) {
                    container.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, text);
                    container.dispatchEvent(new Event('input', { bubbles: true }));
                    container.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", title)

            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")

            logger.success("✅ [标题] 标题注入并锁定成功")
            return True

        except Exception as e:
            logger.error(f"❌ [标题] 注入失败: {e}")
            return False

    async def _physical_publish(self, page: Page) -> bool:
        """发布确认"""
        try:
            await asyncio.sleep(1.0)

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
                        for i in range(count):
                            current_btn = btn.nth(i)
                            if await current_btn.is_visible(timeout=1000):
                                await current_btn.scroll_into_view_if_needed(timeout=3000)
                                await asyncio.sleep(0.3)
                                await current_btn.click(force=True)
                                clicked = True
                                logger.info(f"✅ [发布] 已点击发布按钮: {selector}")
                                break
                        if clicked:
                            break
                except Exception as e:
                    continue

            if not clicked:
                logger.error("❌ [发布] 未找到可点击的发布按钮")
                return False

            await asyncio.sleep(2.0)

            # 处理二次确认
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
                                break
                        if confirm_clicked:
                            break
                except:
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
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """等待发布结果"""
        try:
            await page.wait_for_url(
                re.compile(r".*(success|content/index).*"),
                timeout=30000
            )
            logger.success(f"🎊 [成功] 发布成功: {page.url}")
            return {"success": True, "platform_url": page.url}

        except Exception:
            logger.warning(f"⚠️ [结果] 未检测到成功跳转，但可能已发布: {page.url}")
            return {"success": True, "platform_url": page.url}

    def _deep_clean_content(self, text: str) -> str:
        """清理正文内容"""
        text = re.sub(r'^#\s+.*?\n', '', text)  # 移除首行标题
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'\*\*+', '', text)
        return text.strip()


# 注册
BAIJIAHAO_CONFIG = {
    "name": "百家号",
    "publish_url": "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1",
    "color": "#2932E1"
}
registry.register("baijiahao", BaijiahaoPublisher("baijiahao", BAIJIAHAO_CONFIG))
