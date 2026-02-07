# -*- coding: utf-8 -*-
"""
知乎发布适配器 - v5.0 鲁棒暴力版
重构重点：
1. 封面上传 - 物理坐标+隐藏注入双杀方案
2. 正文同步 - 状态固化组合拳（End->Enter->Backspace->Tab）
3. 话题流程加固 - 双重Escape清理 + 强制点击遮罩
"""

import asyncio
import re
import os
import httpx
import tempfile
import base64
import random
import urllib.parse
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class ZhihuPublisher(BasePublisher):
    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 开始知乎发布 (v5.0 鲁棒暴力版)...")

            # 1. 导航
            await page.goto(self.config["publish_url"], wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)

            # 2. 图像准备
            # A. 提取正文链接
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)
            # B. 清洗正文
            clean_content = re.sub(r'!\[.*?\]\(.*?\)', '', article.content)

            # C. 强制补图策略
            if not image_urls:
                keyword = article.title[:10] if article.title else "technology"
                # 生成3张不同的图
                for i in range(3):
                    seed = random.randint(1, 1000)
                    encoded_kw = urllib.parse.quote(f"high quality realistic photo of {keyword} {seed}")
                    url = f"https://image.pollinations.ai/prompt/{encoded_kw}?width=800&height=600&nologo=true"
                    image_urls.append(url)
                logger.info(f"🎨 已自动生成 {len(image_urls)} 张配图链接")

            # D. 下载图片
            downloaded_paths = await self._download_images(image_urls)
            temp_files.extend(downloaded_paths)

            if not downloaded_paths:
                return {"success": False, "error_msg": "图片下载失败，无法满足强制配图需求"}

            # 3. 填充标题
            await self._fill_title(page, article.title)

            # 4. 填充正文
            await self._fill_content_and_clean_ui(page, clean_content)

            # 5. 设置 AI 声明
            await self._set_ai_declaration(page)

            # 6. 执行多图排版上传
            await self._handle_multi_image_upload(page, downloaded_paths)

            # 7. 发布流程
            topic_word = getattr(article, 'keyword_text', article.title[:4])
            if not await self._handle_publish_process(page, topic_word):
                return {"success": False, "error_msg": "发布确认环节失败"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ 知乎脚本致命故障: {str(e)}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _download_images(self, urls: List[str]) -> List[str]:
        paths = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True) as client:
            for i, url in enumerate(urls[:3]):
                for attempt in range(2):
                    try:
                        resp = await client.get(url, timeout=20.0)
                        if resp.status_code == 200:
                            if len(resp.content) < 1000: continue
                            tmp_path = os.path.join(tempfile.gettempdir(), f"zh_v50_{random.randint(1000, 9999)}.jpg")
                            with open(tmp_path, "wb") as f:
                                f.write(resp.content)
                            paths.append(tmp_path)
                            logger.info(f"✅ 图片 {i + 1} 下载成功")
                            break
                    except:
                        pass
        return paths

    async def _handle_multi_image_upload(self, page: Page, paths: List[str]):
        """多图排版逻辑"""
        try:
            # Step 1: 彻底重写的封面上传 - 物理坐标+隐藏注入双杀方案
            if not await self._set_zhihu_cover(page, paths[0]):
                logger.warning("⚠️ 封面上传失败，继续处理正文图片")

            # Step 2: 遍历插入正文
            editor = page.locator(".public-DraftEditor-content").first
            await editor.click()

            for i, image_path in enumerate(paths):
                logger.info(f"📝 正在插入第 {i + 1}/{len(paths)} 张图片...")

                if i == 0:
                    await page.keyboard.press("Control+Home")
                    await page.keyboard.press("Enter")
                    await page.keyboard.press("ArrowUp")
                else:
                    for _ in range(4):
                        await page.keyboard.press("PageDown")
                        await asyncio.sleep(0.2)
                    await page.keyboard.press("Enter")

                await self._paste_image_via_js(page, image_path)
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"多图上传流程部分失败: {e}")

    async def _set_zhihu_cover(self, page: Page, cover_path: str) -> bool:
        """
        知乎封面上传 v5.0 - 物理坐标+隐藏注入双杀方案

        执行步骤：
        1. 滚动到底部：window.scrollTo(0, document.body.scrollHeight)
        2. 劫持并显形：input.UploadPicture-input 设为 block，fixed 定位到左上角 (0,0)，宽度 200px
        3. 直接注入：page.set_input_files 注入路径
        4. 物理点击弹窗：(640, 400) 和 (850, 600) 位置各执行一次物理点击
        """
        try:
            logger.info("🖼️ [封面] 开始执行物理坐标+隐藏注入双杀方案...")

            # ========================================
            # 1. 滚动到底部 - 确保封面区域进入视口
            # ========================================
            logger.info("🖼️ [封面] 滚动到底部...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # ========================================
            # 2. 劫持并显形 - DOM Hijacking
            # ========================================
            logger.info("🖼️ [封面] 劫持 Input 并强制显形...")

            # JS 脚本：将隐藏的 input 挪到页面左上角并强制显示，宽度 200px
            hijack_success = await page.evaluate('''() => {
                const input = document.querySelector('input.UploadPicture-input');

                if (!input) {
                    console.error('[封面] 未找到 input.UploadPicture-input');
                    return { success: false, error: 'Input not found' };
                }

                // 强制显示配置 - fixed 定位到左上角 (0,0)，宽度 200px
                input.style.cssText = "display:block !important; visibility:visible !important; position:fixed !important; top:0 !important; left:0 !important; width:200px !important; height:100px !important; z-index:99999 !important; opacity:1 !important;";

                console.log('[封面] DOM 劫持成功 - Input 已强制显示 (200px width)');
                return { success: true };
            }''')

            if not hijack_success.get("success"):
                logger.error("❌ [封面] DOM 劫持失败: " + hijack_success.get("error"))
                return False

            await asyncio.sleep(0.5)

            # ========================================
            # 3. 直接注入 - 底层文件流注入
            # ========================================
            logger.info(f"🖼️ [封面] 直接注入文件: {cover_path}")
            cover_input = page.locator("input.UploadPicture-input").first
            await cover_input.set_input_files(cover_path)
            logger.info("🖼️ [封面] 文件注入完成")

            # ========================================
            # 4. 物理点击弹窗 - 暴力点击可能的位置
            # ========================================
            logger.info("🖼️ [封面] 等待3秒后执行物理坐标点击...")
            await asyncio.sleep(3)

            # 暴力点击：(640, 400) 和 (850, 600) 位置各执行一次物理点击
            # 基于 1280x800 视口
            for coords in [(640, 400), (850, 600)]:
                try:
                    x, y = coords
                    logger.info(f"🖼️ [封面] 物理点击坐标: ({x}, {y})")
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.5)
                except:
                    pass

            # 再次暴力点击，确保裁剪框关闭
            logger.info("🖼️ [封面] 执行追加暴力点击...")
            for coords in [(640, 500), (640, 550), (640, 600)]:
                try:
                    x, y = coords
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.2)
                except:
                    pass

            await asyncio.sleep(2)

            # ========================================
            # 5. 状态校验 - 检查封面是否真的挂载成功
            # ========================================
            logger.info("🖼️ [封面] 执行状态校验...")

            cover_mounted = await page.evaluate('''() => {
                const coverElement = document.querySelector('.PublishPanel-coverImage');
                if (coverElement) {
                    const img = coverElement.querySelector('img');
                    if (img && img.src && img.src.length > 10) {
                        return { mounted: true, hasImage: true, src: img.src.substring(0, 50) + '...' };
                    }
                    return { mounted: true, hasImage: false };
                }
                return { mounted: false };
            }''')

            if cover_mounted.get("mounted") and cover_mounted.get("hasImage"):
                logger.success(f"✅ [封面] 封面挂载成功: {cover_mounted.get('src')}")
                return True
            elif cover_mounted.get("mounted"):
                logger.warning("⚠️ [封面] 封面元素存在但未加载图片")
                return False
            else:
                logger.error("❌ [封面] 封面元素未找到，挂载失败")
                return False

        except Exception as e:
            logger.exception(f"❌ [封面] 封面上传异常: {str(e)}")
            return False

    async def _paste_image_via_js(self, page: Page, image_path: str):
        """剪贴板注入技术"""
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')

        await page.evaluate('''(data) => {
            const { b64 } = data;
            const byteCharacters = atob(b64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'image/jpeg' });
            const file = new File([blob], "auto_inserted.jpg", { type: 'image/jpeg' });

            const dt = new DataTransfer();
            dt.items.add(file);

            const editor = document.querySelector(".public-DraftEditor-content");
            const event = new ClipboardEvent("paste", {
                clipboardData: dt,
                bubbles: true,
                cancelable: true
            });
            editor.dispatchEvent(event);
        }''', {"b64": b64_data})

    async def _fill_title(self, page: Page, title: str):
        sel = "input[placeholder*='标题'], .WriteIndex-titleInput textarea"
        await page.wait_for_selector(sel)
        await page.fill(sel, title)

    async def _fill_content_and_clean_ui(self, page: Page, content: str):
        """
        填充正文 - 状态固化组合拳

        执行步骤：
        1. 粘贴文字后，禁止直接等待
        2. 执行物理按键：End -> Enter -> Backspace
        3. 执行 page.keyboard.press("Tab")

        原理：必须通过物理按键让编辑器认为"有人在打字"，React 状态才会更新
        """
        editor = ".public-DraftEditor-content"
        await page.wait_for_selector(editor)
        await page.click(editor)

        # 粘贴内容
        await page.evaluate('''(text) => {
            const dt = new DataTransfer();
            dt.setData("text/plain", text);
            const ev = new ClipboardEvent("paste", { clipboardData: dt, bubbles: true });
            document.querySelector(".public-DraftEditor-content").dispatchEvent(ev);
        }''', content)

        # ========================================
        # 状态固化组合拳 - 禁止直接等待
        # ========================================
        logger.info("📝 [正文] 执行状态固化组合拳...")

        # 执行物理按键：End -> Enter -> Backspace
        await asyncio.sleep(1)  # 等待粘贴完成
        await page.keyboard.press("End")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Backspace")
        await asyncio.sleep(0.3)

        # 执行 Tab 键 - 强制触发 React 状态更新
        logger.info("📝 [正文] 按 Tab 键触发状态更新...")
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)

        # 处理可能的解析确认弹窗
        try:
            confirm = page.locator("button:has-text('确认并解析')").first
            if await confirm.is_visible(timeout=3000):
                await confirm.click()
                logger.info("✅ [正文] 已点击确认并解析")
                await asyncio.sleep(1)
        except:
            pass

    async def _set_ai_declaration(self, page: Page):
        """设置 AI 创作声明"""
        try:
            logger.info("正在设置 AI 声明...")
            # 查找并点击 AI 助手按钮
            ai_btn = page.locator("button:has-text('AI助手'), .ToolbarButton:has-text('AI')").first
            if await ai_btn.is_visible(timeout=3000):
                await ai_btn.click()
                await asyncio.sleep(1)
                # 选择 AI 辅助创作
                option = page.locator("text=AI辅助创作, [role='menuitem']:has-text('AI')").first
                if await option.is_visible(timeout=2000):
                    await option.click()
                    logger.info("✅ 已勾选 AI 辅助创作声明")
        except:
            logger.warning("未找到 AI 声明入口，跳过此步")

    async def _handle_publish_process(self, page: Page, topic: str) -> bool:
        """
        话题流程加固

        执行步骤：
        1. 滚动到底部
        2. 点击"添加话题"前，先按两次 Escape 键清理所有遮挡
        3. 输入话题后，增加 await page.keyboard.press("Enter")
        4. 在检查 final_btn.is_enabled() 前，先执行一次 page.mouse.click(10, 10) 点掉可能存在的透明遮罩
        """
        # 滚动到底部
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)

        # ========================================
        # 1. 双重 Escape 清理 - 移除所有遮挡
        # ========================================
        logger.info("🏷️ [话题] 执行双重 Escape 清理...")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)

        # 添加话题
        try:
            add_topic = page.locator("button:has-text('添加话题')").first
            if await add_topic.is_visible(timeout=2000):
                await add_topic.click()
                logger.info("✅ [话题] 已点击添加话题按钮")

                # 输入话题
                topic_input = page.locator("input[placeholder*='话题']").first
                await topic_input.fill(topic)
                await asyncio.sleep(2)

                # 点击建议
                suggestion = page.locator(".Suggestion-item, .PublishPanel-suggestionItem").first
                if await suggestion.is_visible(timeout=2000):
                    await suggestion.click()
                    logger.info(f"✅ [话题] 已选择话题: {topic}")
                else:
                    # 增加 Enter 键确认
                    logger.info("🏷️ [话题] 未找到建议，按 Enter 确认...")
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(1)
            else:
                logger.warning("⚠️ [话题] 未找到添加话题按钮")
        except Exception as e:
            logger.warning(f"⚠️ [话题] 添加话题流程异常: {e}")

        await asyncio.sleep(1)

        # ========================================
        # 2. 强制点击透明遮罩 - 点掉可能存在的遮罩
        # ========================================
        logger.info("🖱️ [发布] 强制点击透明遮罩...")
        try:
            await page.mouse.click(10, 10)
            await asyncio.sleep(0.5)
        except:
            pass

        # ========================================
        # 3. 等待并点击发布按钮
        # ========================================
        logger.info("🚀 [发布] 等待发布按钮可用...")

        final_btn = page.locator(
            "button.PublishPanel-submitButton, .WriteIndex-publishButton, button:has-text('发布')").last

        # 增加重试次数和等待时间
        for i in range(8):  # 从5次增加到8次
            try:
                if await final_btn.is_enabled(timeout=1000):
                    logger.info(f"✅ [发布] 发布按钮已可用，正在点击 (第{i+1}次尝试)...")
                    await final_btn.click(force=True)
                    return True
            except:
                pass

            # 如果按钮未启用，继续等待
            logger.info(f"⏳ [发布] 等待发布按钮... ({i+1}/8)")
            await asyncio.sleep(2)

        logger.error("❌ [发布] 发布按钮始终未启用")
        return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        for i in range(30):  # 增加到30秒
            if "/p/" in page.url and "/edit" not in page.url:
                logger.success(f"✅ [发布] 发布成功: {page.url}")
                return {"success": True, "platform_url": page.url}
            await asyncio.sleep(1)
        logger.error("❌ [发布] 发布超时")
        return {"success": False, "error_msg": "发布超时"}


# 注册
ZHIHU_CONFIG = {"name": "知乎", "publish_url": "https://zhuanlan.zhihu.com/write", "color": "#0084FF"}
registry.register("zhihu", ZhihuPublisher("zhihu", ZHIHU_CONFIG))
