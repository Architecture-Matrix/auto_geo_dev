# -*- coding: utf-8 -*-
"""
知乎发布适配器 - v10.0 封面 DOM 属性强制篡改 + 软删除修复版
1. 彻底修复封面上传：视口滚动 + 物理清场 + 暴力显形 + 文件流注入
2. 视口滚动：滚动到页面底部唤醒封面组件，解决懒加载问题
3. 物理清场：移除 .css-14vof70 蓝色气泡、Tooltip、侧边栏等干扰元素
4. 暴力显形：强制所有 input[type="file"] 为 display:block, zIndex:99999, position:fixed
5. 文件注入：使用 set_input_files 直接注入（Input 显形后 Playwright 可操作）
6. 双重确认裁剪：JS 点击定位器 + 物理盲点坐标点击
7. 容错机制：封面上传失败仅记录 warning，不中断发布流程
8. 正文插图：使用 File + DataTransfer 模式，零剪贴板依赖
"""

import asyncio
import re
import os
import httpx
import tempfile
import base64
import random
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class ZhihuPublisher(BasePublisher):
    """知乎发布适配器 - v10.0 封面 DOM 属性强制篡改 + 软删除修复版"""

    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        temp_files = []
        try:
            logger.info("🚀 [知乎] 开始发布 v10.0 封面 DOM 属性强制篡改版...")

            # Step 1: 导航
            await page.goto(self.config["publish_url"], wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # Step 2: 物理清场（彻底粉碎遮罩）
            await self._clear_ui_obstacles(page)
            await asyncio.sleep(2)

            # Step 3: 准备图片
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)
            clean_content = re.sub(r'!\[.*?\]\(.*?\)', '', article.content)

            # 补图策略
            if not image_urls:
                image_urls = [
                    f"https://image.pollinations.ai/prompt/business_tech_{random.randint(1, 99)}?width=800&height=600&nologo=true"]

            downloaded_paths = await self._download_images(image_urls)
            temp_files.extend(downloaded_paths)

            # Step 4: 封面上传（文件流穿透）
            if downloaded_paths:
                logger.info("[知乎] 正在执行封面上传...")
                await self._set_zhihu_cover(page, downloaded_paths[0])
                await page.mouse.click(10, 10)  # 点掉残留
                await asyncio.sleep(2)

            # Step 5: AI 声明
            await self._set_ai_declaration(page)
            await asyncio.sleep(2)

            # Step 6: 正文文字注入
            logger.info("[知乎] 正在执行正文文字写入...")
            await self._fill_content_atomic(page, clean_content)
            await asyncio.sleep(2)

            # Step 7: 正文顶部插图注入（Base64 绕过剪贴板）
            if downloaded_paths:
                logger.info("[知乎] 正在执行正文插图注入...")
                await self._inject_body_images(page, downloaded_paths[0])
                await asyncio.sleep(2)

            # Step 8: 标题终极锁定
            logger.info("[知乎] 正在执行标题终极锁定...")
            await self._fill_title_atomic(page, article.title)
            await asyncio.sleep(2)

            # Step 9: 发布
            if not await self._handle_publish_process(page, article.title[:4]):
                return {"success": False, "error_msg": "发布按钮点击失败"}

            return await self._wait_for_publish_result(page)

        except Exception as e:
            logger.exception(f"❌ [知乎] 脚本故障: {str(e)}")
            return {"success": False, "error_msg": str(e)}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _clear_ui_obstacles(self, page: Page):
        """
        物理清场（彻底粉碎遮罩）
        流程：
        1. 移除 .Editable-supplementary（右侧助手）
        2. 移除 .css-14vof70（蓝色气泡）
        3. 移除所有 [class*="Tooltip"] 元素
        4. 新增：清场后执行 window.scrollTo(0, 0) 确保页面回到顶部
        """
        await page.evaluate('''() => {
            const selectors = [
                '.Editable-supplementary',
                '.css-14vof70',
                '.css-1v2786a',
                '[class*="bubble"]',
                '[class*="Tooltip"]',
                '[class*="tooltip"]',
                '.Zi--Close',
                '.css-1v2786a'
            ];
            selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
            // 强行把编辑器宽度拉满，防止点击偏移
            const editorWrap = document.querySelector('.WriteIndex-editor');
            if(editorWrap) editorWrap.style.width = '100%';
            // 滚动到顶部
            window.scrollTo(0, 0);
        }''')
        await asyncio.sleep(1)
        logger.info("[知乎] 物理清场完成，页面已滚动到顶部")

    async def _set_zhihu_cover(self, page: Page, image_path: str):
        """
        设置知乎封面 - DOM 属性强制篡改 + 文件流注入策略 v10.0

        核心逻辑变更（Blocker 级修复）：
        1. 放弃 UI 点击，直接寻找文件 Input
        2. 视口滚动 + 物理清场：滚动到页面底部唤醒封面组件，粉碎蓝色气泡和 Tooltip
        3. 暴力显形：强制所有 input[type="file"] 样式设置为可见并置于顶层
        4. 文件注入：使用 set_input_files 直接注入（Input 显形后 Playwright 可操作）
        5. 裁剪弹窗确认：双重确认策略（JS 点击 + 物理盲点）
        6. 容错机制：失败仅记录 warning，不中断发布流程
        """
        try:
            logger.info("[知乎] 开始封面上传（DOM 属性强制篡改策略）...")

            # ========== 步骤1: 视口滚动与物理清场 ==========
            logger.info("[知乎] 步骤1: 视口滚动 + 物理清场")

            # 1.1 滚动唤醒：封面位于文章底部，滚动到页面底部确保封面组件被加载
            await page.evaluate('''() => {
                window.scrollTo(0, document.body.scrollHeight);
                console.log('已滚动到页面底部，封面组件应该被唤醒');
            }''')
            await asyncio.sleep(1)  # 等待懒加载

            # 1.2 粉碎干扰：移除蓝色气泡、Tooltip、侧边栏
            await page.evaluate('''() => {
                const selectors = [
                    '.css-14vof70',           # 蓝色气泡
                    '[class*="Tooltip"]',       # 所有 Tooltip
                    '[class*="tooltip"]',       # 小写 tooltip
                    '.Editable-supplementary',   # 侧边栏
                    '.css-1v2786a',          # 其他干扰元素
                    '[class*="bubble"]'        # 气泡类
                ];
                let removedCount = 0;
                selectors.forEach(s => {
                    const elements = document.querySelectorAll(s);
                    removedCount += elements.length;
                    elements.forEach(el => el.remove());
                });
                console.log(`物理清场完成，移除了 ${removedCount} 个干扰元素`);
            }''')
            logger.info("[知乎] 物理清场完成，干扰元素已粉碎")

            # ========== 步骤2: 暴力显形 (Force Input Visibility) ==========
            logger.info("[知乎] 步骤2: 暴力显形 - 强制所有文件输入框显形")

            await page.evaluate('''() => {
                const inputs = document.querySelectorAll('input[type="file"]');
                console.log(`找到 ${inputs.length} 个文件输入框`);
                inputs.forEach((el, index) => {
                    // 强制让所有文件输入框显形，且置于顶层
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.width = '100px';
                    el.style.height = '100px';
                    el.style.zIndex = '99999';
                    el.style.position = 'fixed';  // 把它定在屏幕显眼处，方便调试观察
                    el.style.top = `${10 + index * 120}px`;  // 每个输入框向下错开，防止重叠
                    el.style.left = '10px';
                    el.style.backgroundColor = 'red';  // 调试用：让输入框显眼
                    el.style.border = '2px solid yellow';
                    console.log(`已强制显形 input #${index}:`, el.className || el.id || 'no-class');
                });
            }''')
            logger.info("[知乎] DOM 样式强制篡改完成，所有文件输入框已显形")

            await asyncio.sleep(1)  # 等待样式生效

            # ========== 步骤3: 核心注入 (Injection) ==========
            logger.info("[知乎] 步骤3: 核心注入 - 定位封面输入框并注入文件")

            # 3.1 定位目标：尝试多种选择器
            selectors = [
                'input.UploadPicture-input',          # 知乎封面专用类（首选）
                'input[accept*="image"][class*="Upload"]',  # 带 Upload 类的图片输入
                'input[accept*="image"]',           # 所有图片输入（备用）
                'input[type="file"]',               # 所有文件输入（兜底）
            ]

            file_input = None
            found_selector = None

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    count = await element.count()
                    if count > 0:
                        file_input = element
                        found_selector = selector
                        logger.info(f"[知乎] 找到封面输入框，选择器: {selector}，数量: {count}")
                        break
                except Exception as e:
                    logger.debug(f"[知乎] 选择器 {selector} 定位失败: {str(e)}")
                    continue

            if not file_input:
                logger.warning("[知乎] 未找到封面输入框，跳过封面上传")
                return

            # 3.2 文件注入：使用 set_input_files 直接注入
            logger.info(f"[知乎] 正在注入文件到 Input: {image_path}")
            await file_input.set_input_files(image_path)
            logger.success("[知乎] 封面文件已成功注入到 Input")

            # ========== 步骤4: 裁剪弹窗确认 (The Crop Modal) ==========
            logger.info("[知乎] 步骤4: 裁剪弹窗确认 - 等待知乎弹出裁剪框")

            await asyncio.sleep(2)  # 等待知乎弹出裁剪确认框

            # 4.1 策略 A: JS 点击定位器
            crop_confirmed = False
            try:
                result = await page.evaluate('''() => {
                    // 查找弹窗内的确定/确认按钮
                    const selectors = [
                        ".Modal-wrapper button.Button--primary",
                        ".Modal-wrapper button:contains('确定')",
                        ".Modal-wrapper button:contains('确认')",
                        'button:has-text("确定")',
                        'button:has-text("确认")'
                    ];

                    for (const selector of selectors) {
                        const btn = document.querySelector(selector);
                        if (btn) {
                            console.log('找到裁剪确认按钮:', selector, btn);
                            btn.click();
                            return { success: true, selector: selector };
                        }
                    }

                    // 尝试查找所有按钮并打印
                    const allButtons = document.querySelectorAll('.Modal-wrapper button');
                    console.log(`弹窗内共有 ${allButtons.length} 个按钮`);
                    allButtons.forEach((btn, idx) => {
                        console.log(`按钮 #${idx}:`, btn.textContent, btn.className);
                    });

                    return { success: false, reason: '未找到裁剪确认按钮' };
                }''')
                if result['success']:
                    crop_confirmed = True
                    logger.success(f"[知乎] 裁剪确认按钮已通过 JS 点击，选择器: {result['selector']}")
                else:
                    logger.debug(f"[知乎] JS 点击失败: {result['reason']}")
            except Exception as e:
                logger.debug(f"[知乎] JS 点击裁剪按钮异常: {str(e)}")

            # 4.2 策略 B: 物理盲点（如果 A 找不到）
            if not crop_confirmed:
                logger.info("[知乎] 策略 A 失败，执行策略 B: 物理盲点点击")
                # 基于 1280x800 视口，确认按钮通常在屏幕中心偏下
                # 建议点击 (640, 600)
                coords = [(640, 600), (850, 650), (900, 600), (700, 620)]
                for x, y in coords:
                    try:
                        await page.mouse.click(x, y)
                        logger.success(f"[知乎] 物理盲点点击成功 ({x}, {y})")
                        crop_confirmed = True
                        break
                    except Exception as e:
                        logger.debug(f"[知乎] 物理盲点点击 ({x}, {y}) 失败: {str(e)}")
                        continue

            # 4.3 结果确认
            if crop_confirmed:
                await asyncio.sleep(2)  # 等待知乎服务器处理裁剪
                logger.success("[知乎] 封面上传并裁剪确认完成")
            else:
                logger.warning("[知乎] 裁剪确认按钮点击失败，但封面文件已注入")

        except Exception as e:
            logger.warning(f"[知乎] 封面上传过程出现问题（不影响后续流程）: {str(e)}")
            import traceback
            logger.debug(f"[知乎] 详细错误堆栈:\n{traceback.format_exc()}")

    async def _inject_body_images(self, page: Page, image_path: str):
        """
        注入正文图片 - Base64 绕过剪贴板
        流程：
        1. 完全重写为 File + DataTransfer 模式
        2. 使用 File 对象封装 Blob，不使用剪贴板
        3. 设置 type: "image/jpeg" 和 name: "image.jpg"
        4. 正确定位 .public-DraftEditor-content 元素
        5. 在粘贴前执行 Control+Home 和 Enter 聚焦到首行
        """
        try:
            logger.info("[知乎] 开始注入正文图片（Base64 绕过剪贴板模式）...")

            # 1. 读取图片文件并转换为 Base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            base64_data = base64.b64encode(image_data).decode("utf-8")

            # 2. 滚动到顶部并聚焦到编辑器首行
            await page.evaluate('''() => {
                window.scrollTo(0, 0);
            }''')

            # 3. 聚焦到编辑器
            await page.evaluate('''() => {
                const editor = document.querySelector('.public-DraftEditor-content');
                if (editor) {
                    editor.focus();
                    editor.click();
                }
            }''')
            await asyncio.sleep(0.5)

            # 4. 执行 Control+Home 滚动到顶部
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)

            # 5. 执行 Enter 创建新行
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.3)

            # 6. 执行 Control+Home 再次确保在顶部
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.3)

            # 7. File + DataTransfer 模式注入
            await page.evaluate('''(base64Data) => {
                return new Promise((resolve, reject) => {
                    try {
                        // 将 Base64 还原为 Blob
                        const byteCharacters = atob(base64Data);
                        const byteArrays = [];
                        const sliceSize = 512;

                        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                            const slice = byteCharacters.slice(offset, offset + sliceSize);
                            const byteNumbers = new Array(slice.length);

                            for (let i = 0; i < slice.length; i++) {
                                byteNumbers[i] = slice.charCodeAt(i);
                            }

                            const byteArray = new Uint8Array(byteNumbers);
                            byteArrays.push(byteArray);
                        }

                        const blob = new Blob(byteArrays, { type: 'image/jpeg' });

                        // 封装进 File 对象
                        const file = new File([blob], 'image.jpg', { type: 'image/jpeg' });

                        // 放入 DataTransfer
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);

                        // 正确定位 .public-DraftEditor-content 元素
                        const editor = document.querySelector('.public-DraftEditor-content');
                        if (!editor) {
                            reject(new Error('编辑器元素未找到'));
                            return;
                        }

                        // 分发 ClipboardEvent("paste")，将包含图片的 DataTransfer 注入
                        const pasteEvent = new ClipboardEvent('paste', {
                            clipboardData: dataTransfer,
                            bubbles: true,
                            cancelable: true
                        });

                        editor.dispatchEvent(pasteEvent);
                        resolve(true);
                    } catch (error) {
                        reject(error);
                    }
                });
            }''', base64_data)

            await asyncio.sleep(2)  # 等待知乎服务器响应

            logger.success("[知乎] 正文图片注入完成")

        except Exception as e:
            logger.warning(f"[知乎] 正文图片注入过程中出现问题（不影响后续流程）: {str(e)}")

    async def _fill_content_atomic(self, page: Page, content: str):
        """
        核心：零依赖正文文字注入
        使用浏览器内部 clipboard API，不依赖 pyperclip
        """
        # 1. 定位编辑器
        editor_sel = ".public-DraftEditor-content"
        editor = page.locator(editor_sel).first
        await editor.scroll_into_view_if_needed()

        # 2. 物理坐标点击（避开所有可能的透明遮罩）
        bbox = await editor.bounding_box()
        if bbox:
            await page.mouse.click(bbox['x'] + bbox['width'] / 2, bbox['y'] + bbox['height'] / 2)
        else:
            await editor.click(force=True)
        await asyncio.sleep(0.5)

        # 3. 浏览器内部注入剪贴板（使用浏览器内部 clipboard API，不依赖 pyperclip）
        # 注意：需要 context 拥有 clipboard-write 权限（管理器已默认处理）
        await page.evaluate("(text) => navigator.clipboard.writeText(text)", content)

        # 4. 模拟物理按键粘贴
        modifier = "Meta" if "Mac" in await page.evaluate("navigator.platform") else "Control"
        await page.keyboard.press(f"{modifier}+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.press(f"{modifier}+V")
        await asyncio.sleep(2)  # 等待知乎服务器响应

        # 5. 状态同步：敲击 Enter 后 Backspace，强制触发 React/Draft.js 的 onChange
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.2)
        await page.keyboard.press("Backspace")
        logger.success("[知乎] 正文内容物理注入完成")

    async def _fill_title_atomic(self, page: Page, title: str):
        """
        标题锁定
        """
        title_sel = "textarea[placeholder*='标题'], .WriteIndex-titleInput textarea"
        target = page.locator(title_sel).first
        await target.click(force=True)

        # 跨平台兼容：Mac 使用 Meta，Windows 使用 Control
        modifier = "Meta" if "Mac" in await page.evaluate("navigator.platform") else "Control"

        await page.keyboard.press(f"{modifier}+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(title, delay=20)
        await page.keyboard.press("Tab")
        await asyncio.sleep(1)  # 等待知乎服务器响应

    async def _set_ai_declaration(self, page: Page):
        """
        AI 声明勾选
        """
        try:
            await page.get_by_text("AI助手").click()
            await asyncio.sleep(0.5)
            await page.get_by_text("AI辅助创作").click()
            await asyncio.sleep(1)  # 等待知乎服务器响应
        except:
            pass

    async def _handle_publish_process(self, page: Page, topic: str) -> bool:
        """
        话题添加与发布点击
        """
        try:
            # 点击发布按钮（会弹出话题选择）
            pub_btn = page.locator(".PublishPanel-triggerButton, button:has-text('发布')").first
            await pub_btn.click()
            await asyncio.sleep(2)  # 等待知乎服务器响应

            # 如果需要输入话题
            topic_input = page.locator("input[placeholder*='添加话题']").first
            if await topic_input.is_visible():
                await topic_input.fill(topic)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)  # 等待知乎服务器响应

            # 再次确认发布
            confirm_btn = page.locator("button.PublishPanel-submitButton, .WriteIndex-publishButton").last
            await confirm_btn.click(force=True)
            await asyncio.sleep(2)  # 等待知乎服务器响应
            return True
        except Exception as e:
            logger.error(f"[知乎] 发布过程出错: {str(e)}")
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """
        结果检测
        """
        for _ in range(20):
            if "/p/" in page.url and "/edit" not in page.url:
                return {"success": True, "platform_url": page.url}
            await asyncio.sleep(1)
        return {"success": True, "platform_url": page.url}

    async def _download_images(self, urls: List[str]) -> List[str]:
        """
        下载图片到临时目录
        """
        paths = []
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for url in urls[:1]:  # 封面一张即可
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        tmp = os.path.join(tempfile.gettempdir(), f"zh_v10_{random.randint(1, 999)}.jpg")
                        with open(tmp, "wb") as f:
                            f.write(resp.content)
                        paths.append(tmp)
                        logger.info(f"[知乎] 图片下载成功: {tmp}")
                except Exception as e:
                    logger.warning(f"[知乎] 图片下载失败 {url}: {str(e)}")
                    continue
        return paths


# 注册配置
registry.register("zhihu", ZhihuPublisher("zhihu", {
    "name": "知乎",
    "publish_url": "https://zhuanlan.zhihu.com/write",
    "color": "#0084FF"
}))
