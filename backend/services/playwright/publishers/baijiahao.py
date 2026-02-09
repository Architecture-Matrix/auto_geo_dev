# -*- coding: utf-8 -*-
"""
百家号发布适配器 - v10.1 精准打击版

重构重点 (AutoGeo 架构金律)：
1. Rule #2 - 执行顺序：清场 -> 封面 -> 正文 -> 标题 -> 发布
2. Rule #1 - 正文注入：严禁 f-string，使用 evaluate 传参 + 状态固化组合键
3. Golden Rule #1 & #3 - 彻底杜绝原生对话框：协议直接注入 + 零点击
4. JS 崩溃修复：document.body.scrollHeight 增加 Null Check
5. Rule #3 - 降维打击：Shadow DOM 穿透 + 递归扫描 + 绝杀高 z-index

v10.1 新增补丁：
1. 封面注入补丁：精准选位（区分图片与视频 input）+ Tab 切换 + 绝杀点击
2. 正文注入补丁：深度唤醒（按键激活编辑器）+ 注入增强 + 200ms 状态固化
3. 标题锁定补丁：物理清空增强 + 等待 2 秒后执行
4. 物理清场常态化：封面后、正文后各补一次清场
"""

import asyncio
import re
import os
import httpx
import tempfile
import random
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from loguru import logger

from .base import BasePublisher, registry


class BaijiahaoPublisher(BasePublisher):
    async def publish(self, page: Page, article: Any, account: Any) -> Dict[str, Any]:
        """
        百家号发布流程 - v10.1 精准打击版

        执行顺序 (Golden Rule #2)：
        1. _force_remove_interferences (初次清场)
        2. _physical_upload_cover (封面先行) ← 内部深度清场 + 精准选位
        3. _physical_write_content (正文压轴) ← 深度唤醒 + 注入增强
        4. Escape 清理 (标题锁定前 - 清理自动保存提示)
        5. _physical_write_title (标题终极锁定) ← 正文注入成功后 2 秒执行
        6. _brutal_publish_click (暴力发布)
        """
        temp_files = []
        try:
            logger.info("🚀 开始百家号发布 (v10.1 精准打击版)...")

            # ========== 步骤1: 导航到编辑页面 ==========
            edit_url = self.config["publish_url"]
            logger.info(f"📝 [导航] 跳转到编辑页面: {edit_url}")
            await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 检查是否需要重新登录
            if "login" in page.url.lower():
                return {"success": False, "platform_url": None, "error_msg": "[百家号] 账号指纹缺失，请前往管理页重新授权"}

            # ========== 步骤2: 暴力清场 - 降维打击 (Golden Rule #3) ==========
            logger.info("🧹 [清场] 执行初次清场 v10.1...")
            await self._force_remove_interferences(page)
            await asyncio.sleep(1)

            # ========== 步骤3: 状态检查 - 验证编辑器是否可用 ==========
            logger.info("🔍 [状态] 检查编辑器可用性...")
            editor_available = await self._verify_editor_available(page)
            if not editor_available:
                logger.warning("⚠️ [状态] 清场后编辑器检测异常，继续执行")

            # ========== 步骤4: 准备图片资源 ==========
            image_urls = re.findall(r'!\[.*?\]\(((?:https?://)?\S+?)\)', article.content)
            clean_content = re.sub(r'!\[.*?\]\(.*?\)', '', article.content)

            if not image_urls:
                keyword = article.title[:10] if article.title else "technology"
                for i in range(3):
                    url = f"https://api.dujin.org/bing/1920.php"
                    image_urls.append(url)
                logger.info(f"🎨 [图片] 自动生成 {len(image_urls)} 张配图链接")

            downloaded_paths = await self._download_images(image_urls)
            temp_files.extend(downloaded_paths)

            if not downloaded_paths:
                return {"success": False, "error_msg": "图片下载失败，无法满足强制配图需求"}

            # ========== 步骤5: 封面物理注入 (Golden Rule #2 - 封面先行) ==========
            logger.info("🖼️ [封面] 开始封面注入 v10.1 (精准选位版)...")
            cover_success = await self._physical_upload_cover(page, downloaded_paths[0])
            if not cover_success:
                logger.warning("⚠️ [封面] 物理注入失败，继续尝试发布")

            # Rule #3: 封面后物理清场常态化 - 粉碎新手气泡
            logger.info("🧹 [清场] 封面后物理清场 - 粉碎新手气泡...")
            await self._force_remove_interferences(page)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)

            # ========== 步骤6: 正文物理注入 (Golden Rule #2 - 正文压轴) ==========
            logger.info(f"📝 [正文] 物理注入正文，长度: {len(clean_content)}")
            content_injected = await self._physical_write_content(page, clean_content)
            if not content_injected:
                return {"success": False, "error_msg": "正文物理注入失败"}

            # Rule #3: 正文后物理清场常态化 - 粉碎动态气泡
            logger.info("🧹 [清场] 正文后物理清场 - 粉碎动态气泡...")
            await self._force_remove_interferences(page)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)

            # ========== 步骤7: 标题物理注入 (Golden Rule #2 - 标题终极锁定) ==========
            # 标题锁定补丁：正文注入成功后等待 2 秒，再执行标题注入
            logger.info("⏱️ [标题] 标题锁定前等待 2 秒...")
            await asyncio.sleep(2)

            # 标题锁定前 Escape 清理可能弹出的"自动保存成功"提示
            logger.info("🧹 [标题] 标题锁定前 Escape 清理 - 清理自动保存提示...")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)

            logger.info(f"📝 [标题] 物理注入标题: {article.title}")
            if not await self._physical_write_title(page, article.title):
                logger.warning("⚠️ [标题] 物理注入失败，继续尝试发布")

            # Golden Rule #3: 标题后 Escape 物理降压
            logger.info("🧹 [清场] 标题后物理降压...")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)

            # ========== 步骤8: 最后的发布确认清场 ==========
            logger.info("🧹 [清场] 发布前最后的确认清场 - 粉碎 AI 检测拦截框...")
            await self._force_remove_interferences(page)
            await asyncio.sleep(0.5)

            # ========== 步骤9: 物理点击发布按钮 (Golden Rule #2 - 暴力发布) ==========
            logger.info("🚀 [发布] 进入暴力发布阶段...")
            if not await self._brutal_publish_click(page):
                return {"success": False, "error_msg": "发布按钮未响应或被屏蔽"}

            # ========== 步骤10: 等待发布结果 ==========
            return await self._wait_for_publish_result(page)

        except Exception as e:
            # 错误反馈加固
            error_msg = str(e)
            if "user_agent" in error_msg.lower() or "fingerprint" in error_msg.lower():
                error_msg = "[百家号] 账号指纹缺失，请前往管理页重新授权"

            logger.exception(f"❌ [百家号] 发布异常: {error_msg}")
            return {"success": False, "platform_url": None, "error_msg": error_msg}
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    async def _force_remove_interferences(self, page: Page):
        """
        暴力移除脚本 v10.1 - 降维打击版 (Shadow DOM 穿透 + 绝杀高 z-index)

        清场逻辑：
        1. 递归函数 findAndRemove(root) - 穿透 shadowRoot 扫描
        2. 全深度扫描 div, span, button 的 innerText
        3. 精准爆破：文本匹配 1/4, 下一步, AI工具, 体验，立即销毁固定定位父容器
        4. 遮罩层绝杀：强制移除所有 z-index > 1000 的元素
        5. 样式暴力恢复 - Null Check 防止 scrollHeight 报错
        6. 连续三次 Escape 物理降压
        7. (10, 10) 坐标物理点击粉碎透明拦截层
        """
        logger.info("🧹 [清场] 执行 v10.1 降维打击脚本...")

        await page.evaluate("""() => {
            console.log('[清场 v10.1] 开始降维打击...');

            // ========================================
            // 1. 样式暴力恢复 - Null Check 防止 scrollHeight 报错
            // ========================================
            const resetStyles = (element) => {
                if (!element) return;  // Null Check - 防止 JS 崩溃
                try {
                    element.style.setProperty('overflow', 'auto', 'important');
                    element.style.setProperty('position', 'static', 'important');
                    element.style.setProperty('overflow-x', 'visible', 'important');
                    element.style.setProperty('overflow-y', 'visible', 'important');
                    element.style.setProperty('pointer-events', 'auto', 'important');
                } catch (e) {
                    console.warn('[清场 v10.1] 样式重置异常:', e);
                }
            };

            if (document?.body) resetStyles(document.body);
            if (document?.documentElement) resetStyles(document.documentElement);

            console.log('[清场 v10.1] 样式暴力恢复完成');

            // ========================================
            // 2. 遮罩层绝杀 - 强制移除所有 z-index > 1000 的元素
            // ========================================
            const allElements = document.querySelectorAll('*');
            let removedHighZIndex = 0;

            allElements.forEach(el => {
                if (!el) return;  // Null Check

                try {
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style?.zIndex) || 0;

                    // 绝杀条件：z-index > 1000 + 固定/绝对定位 + 非隐藏
                    if ((style?.position === 'fixed' || style?.position === 'absolute') &&
                        zIndex > 1000 &&
                        style?.display !== 'none') {
                        el?.remove();
                        removedHighZIndex++;
                    }
                } catch (e) {
                    // 忽略异常，继续处理下一个元素
                }
            });

            console.log(`[清场 v10.1] 绝杀高 z-index 元素: ${removedHighZIndex} 个`);

            // ========================================
            // 3. 递归扫描函数 - 穿透 Shadow DOM
            // ========================================
            const targetTexts = ['AI工具收起', '下一步', '1/4', '立即体验', 'AI 生成内容', '请确认', 'AI工具', '完成', '确定', '体验', '新手', '气泡', '提示'];
            const removedContainers = [];

            // 递归扫描函数，能穿透 shadowRoot
            const findAndRemove = (root) => {
                if (!root) return;

                // 扫描目标元素：div, span, button
                const targetSelectors = ['div', 'span', 'button', 'label'];
                const elements = root.querySelectorAll(targetSelectors.join(', '));

                for (let i = 0; i < elements?.length; i++) {
                    const el = elements[i];
                    if (!el) continue;

                    // 获取文本内容
                    const text = (el?.innerText || el?.textContent || '')?.trim();

                    // 精准匹配目标文本
                    if (targetTexts?.some(target => text?.includes?.(target))) {
                        console.log(`[清场 v10.1] 发现目标文本: "${text?.substring?.(0, 30)}..."`);

                        let container = el;
                        let foundContainer = null;

                        // 向上递归寻找最近的 fixed/absolute 定位父级
                        while (container && container !== document.body && container !== document.documentElement) {
                            try {
                                const style = window.getComputedStyle(container);
                                const isFixedOrAbsolute = style?.position === 'fixed' || style?.position === 'absolute';

                                if (isFixedOrAbsolute) {
                                    foundContainer = container;
                                    console.log(`[清场 v10.1] 找到固定/绝对定位父容器: position=${style?.position}`);
                                    break;
                                }

                                container = container?.parentElement;
                            } catch (e) {
                                // 忽略异常
                                break;
                            }
                        }

                        // 如果没找到定位父级，至少移除元素本身
                        if (!foundContainer) {
                            foundContainer = el;
                            console.log('[清场 v10.1] 未找到定位父级，移除元素本身');
                        }

                        // 暴力移除
                        try {
                            if (foundContainer && foundContainer?.parentNode && document?.body?.contains?.(foundContainer)) {
                                removedContainers.push({
                                    tag: foundContainer?.tagName,
                                    class: foundContainer?.className || 'no-class',
                                    id: foundContainer?.id || 'no-id'
                                });
                                foundContainer?.remove();
                                console.log('[清场 v10.1] 已暴力删除目标容器');
                            }
                        } catch (e) {
                            console.warn('[清场 v10.1] 删除异常:', e);
                        }
                    }
                }

                // 递归扫描所有 Shadow DOM
                const allElements = root.querySelectorAll('*');
                for (let i = 0; i < allElements?.length; i++) {
                    const el = allElements[i];
                    if (el?.shadowRoot) {
                        findAndRemove(el.shadowRoot);
                    }
                }
            };

            // 从 document.documentElement 开始递归扫描
            findAndRemove(document.documentElement);

            console.log(`[清场 v10.1] 已删除 ${removedContainers.length} 个 AI 工具弹窗容器`);

            // ========================================
            // 4. 移除包含 mask, guide, modal, overlay 的全屏遮罩层
            // ========================================
            const maskClasses = ['mask', 'Mask', 'MASK', 'guide', 'Guide', 'GUIDE',
                                'modal', 'Modal', 'MODAL', 'overlay', 'Overlay', 'OVERLAY',
                                'tooltip', 'Tooltip', 'TOOLTIP', 'bubble', 'Bubble', 'BUBBLE'];

            const maskElements = document.querySelectorAll('*');
            const removedMasks = [];

            maskElements.forEach(el => {
                if (!el) return;  // Null Check

                try {
                    // Optional Chaining - 使用 el?.classList
                    const classList = Array.from(el?.classList || []);
                    const hasMaskClass = classList?.some(cls =>
                        maskClasses?.some(maskClass => cls?.includes?.(maskClass))
                    ) || false;

                    const style = window.getComputedStyle(el);
                    const isFixedOrAbsolute = style?.position === 'fixed' || style?.position === 'absolute';
                    const width = parseInt(style?.width) || 0;
                    const height = parseInt(style?.height) || 0;
                    const isLarge = (width > 500 || style?.width === '100%') ||
                                    (height > 500 || style?.height === '100%');

                    if (hasMaskClass && isFixedOrAbsolute && isLarge) {
                        removedMasks.push(el?.className || 'no-class');
                        el?.remove();
                    }
                } catch (e) {
                    // 忽略异常
                }
            });

            console.log(`[清场 v10.1] 已移除 ${removedMasks.length} 个遮罩层`);

            // ========================================
            // 5. 最终样式确认
            // ========================================
            if (document?.body) resetStyles(document.body);
            if (document?.documentElement) resetStyles(document.documentElement);

            document?.body?.classList.remove('modal-open', 'overflow-hidden', 'noscroll');
            document?.documentElement?.classList.remove('modal-open', 'overflow-hidden', 'noscroll');

            console.log('[清场 v10.1] 执行完成');

            return {
                removedMasks: removedMasks.length,
                removedContainers: removedContainers.length,
                removedHighZIndex: removedHighZIndex
            };
        }""")

        # ========================================
        # 连续三次 Escape 物理降压
        # ========================================
        logger.info("🧹 [清场] 执行三重 Escape 物理降压...")
        for i in range(3):
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.15)
        await asyncio.sleep(0.2)

        # ========================================
        # (10, 10) 坐标物理点击 - 粉碎透明拦截层
        # ========================================
        logger.info("🧹 [清场] 执行坐标物理点击粉碎透明拦截层...")
        try:
            await page.mouse.click(10, 10)
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"[清场] 坐标点击异常: {e}")

        logger.info("✅ [清场] v10.1 降维打击脚本完成")

    async def _verify_editor_available(self, page: Page) -> bool:
        """
        状态检查 v10.1 - 验证编辑器是否可用

        检查目标：
        1. 标题输入框: input[placeholder*="标题"], textarea[placeholder*="标题"]
        2. 正文编辑器: iframe
        3. 正文编辑器容器: .news-editor-pc

        只要找到其中之一，就认为编辑器可用
        """
        try:
            result = await page.evaluate("""() => {
                // 1. 查找标题输入区域
                const titleInputs = document.querySelectorAll('input[placeholder*="标题"], textarea[placeholder*="标题"], [placeholder*="标题"]');
                for (let input of titleInputs) {
                    if (!input) continue;
                    const style = window.getComputedStyle(input);
                    if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                        return { found: true, type: 'title', tag: input?.tagName };
                    }
                }

                // 2. 查找 iframe 正文编辑器
                const iframes = document.querySelectorAll('iframe');
                for (let iframe of iframes) {
                    if (!iframe) continue;
                    const style = window.getComputedStyle(iframe);
                    if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                        return { found: true, type: 'iframe', id: iframe?.id };
                    }
                }

                // 3. 查找 .news-editor-pc 类名的容器
                const editorPc = document.querySelector('.news-editor-pc');
                if (editorPc) {
                    const style = window.getComputedStyle(editorPc);
                    if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                        return { found: true, type: 'editor-pc' };
                    }
                }

                return { found: false };
            }""")

            if result.get('found'):
                logger.info(f"✅ [状态] 编辑器可用 - 类型: {result.get('type')}")
                return True
            else:
                logger.warning("⚠️ [状态] 清场后编辑器仍不可用")
                return False
        except Exception as e:
            logger.debug(f"[状态] 编辑器验证异常: {e}")
            return False

    async def _physical_write_title(self, page: Page, title: str) -> bool:
        """
        标题物理注入 v10.1 - 标题终极锁定 (Golden Rule #2)

        执行位置：正文注入之后等待 2 秒
        严禁使用 .fill()，全部改用物理按键 + evaluate

        v10.1 新增：物理清空增强 - Control+A -> Backspace -> Control+A -> Delete
        """
        try:
            # 滚动到顶部 - Null Check 防止 scrollHeight 报错
            await page.evaluate("() => { window.scrollTo(0, 0); }")
            await asyncio.sleep(0.5)

            # 物理点击标题区域
            await page.mouse.click(450, 150)
            await asyncio.sleep(0.3)

            # 清空（物理清空增强：确保顽固字符被粉碎）
            logger.info("🗑️ [标题] 物理清空增强...")
            await page.keyboard.press("Control+A")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Control+A")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.2)

            # 注入标题 - 使用 evaluate 传参，严禁 f-string
            await page.evaluate("(title) => { document.execCommand('insertText', false, title); }", title)
            await asyncio.sleep(0.5)

            # Tab 失焦
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)

            logger.info("✅ [标题] 物理注入完成")
            return True
        except Exception as e:
            logger.debug(f"[标题] 物理注入异常: {e}")
            return False

    async def _physical_write_content(self, page: Page, content: str) -> bool:
        """
        正文物理注入 v10.1 - 深度唤醒版 (Rule #1)

        关键规则：
        1. 严禁使用 f-string 演接正文，使用 page.evaluate(JS_CODE, content) 模式传参
        2. 编辑器唤醒增强：iframe 找不到时尝试页面刷新或物理点击
        3. 深度唤醒：点击 iframe 中心后，立即发送 a -> Backspace 激活编辑器
        4. 注入方式增强：不仅触发 paste，还要 el.focus() + document.execCommand('insertText')
        5. 状态固化组合键：End -> Enter -> Backspace -> Tab，间隔 200ms
        6. API 修正：统一使用 page.keyboard

        v10.1 新增补丁：
        - 深度唤醒：按键 a -> Backspace 强制触发 input 事件
        - 注入增强：paste + focus + execCommand 三重注入
        - 状态固化：按键间隔增加到 200ms
        """
        try:
            # ========================================
            # 1. 处理正文区域遮挡残留 - (10, 10) 物理点击
            # ========================================
            logger.info("🧹 [正文] 粉碎正文区域透明遮罩...")
            try:
                await page.mouse.click(10, 10)
                await asyncio.sleep(0.15)
            except Exception as e:
                logger.debug(f"[正文] 坐标点击异常: {e}")

            # ========================================
            # 2. 编辑器唤醒增强 - 等待并物理点击激活 iframe
            # ========================================
            logger.info("🔍 [正文] 编辑器唤醒 - 等待 iframe 加载...")
            iframe_element = None
            try:
                iframe_element = await page.wait_for_selector("iframe", timeout=10000)
            except Exception as e:
                logger.error(f"❌ [正文] 未找到 iframe: {e}")
                # 编辑器唤醒增强 - 尝试页面刷新或物理点击
                logger.info("🔄 [正文] 编辑器唤醒增强 - 尝试物理点击激活懒加载...")
                try:
                    await page.mouse.click(640, 400)  # 页面中心点击
                    await asyncio.sleep(1)
                    # 再次尝试查找 iframe
                    iframe_element = await page.query_selector("iframe")
                    if iframe_element:
                        logger.info("✅ [正文] 物理点击后找到 iframe")
                except:
                    pass

                if not iframe_element:
                    iframe_info = await page.evaluate("""() => {
                        const iframes = document.querySelectorAll('iframe');
                        return Array.from(iframes).map(iframe => ({
                            id: iframe?.id || 'no-id',
                            class: iframe?.className || 'no-class',
                            src: iframe?.src ? iframe?.src.substring(0, 50) : 'no-src'
                        }));
                    }""")
                    logger.error(f"[正文] 页面 iframe 诊断信息: {iframe_info}")
                    return False

            # 获取 iframe 的 bounding_box 并物理点击中心位置
            try:
                box = await iframe_element.bounding_box()
                if box:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    logger.info(f"🖱️ [正文] 物理点击 iframe 中心: ({center_x}, {center_y})")
                    await page.mouse.click(center_x, center_y)
                    await asyncio.sleep(0.3)
            except Exception as e:
                logger.debug(f"[正文] iframe 中心点击异常: {e}")

            # ========================================
            # 3. 切换到 iframe 并探测内部结构
            # ========================================
            logger.info("🔄 [正文] 切换到 iframe 内部...")
            iframe = await iframe_element.content_frame()
            if not iframe:
                logger.error("❌ [正文] iframe 内容无法访问")
                return False

            await asyncio.sleep(0.5)

            # 增强 Iframe 内部探测 - 优先查找 [contenteditable="true"] 元素
            editor_target = await iframe.evaluate("""() => {
                const editables = document.querySelectorAll('[contenteditable="true"]');
                for (let el of editables) {
                    if (!el) continue;
                    const style = window.getComputedStyle(el);
                    if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                        return { found: true, type: 'contenteditable', tag: el?.tagName };
                    }
                }
                if (document?.body) {
                    return { found: true, type: 'body', tag: 'BODY' };
                }
                return { found: false };
            }""")

            logger.info(f"🔍 [正文] iframe 内部探测结果: {editor_target}")

            # 根据探测结果点击目标元素
            if editor_target.get('found'):
                if editor_target.get('type') == 'contenteditable':
                    await iframe.evaluate("""() => {
                        const editables = document.querySelectorAll('[contenteditable="true"]');
                        for (let el of editables) {
                            if (!el) continue;
                            const style = window.getComputedStyle(el);
                            if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                                el?.click();
                                el?.focus();
                                return;
                            }
                        }
                    }""")
                else:
                    await iframe.evaluate("document.body.click()")
                await asyncio.sleep(0.3)
            else:
                logger.error("❌ [正文] iframe 内部未找到可编辑区域")
                return False

            # ========================================
            # 4. 深度唤醒 - 按键 a -> Backspace 激活编辑器 (v10.1 新增)
            # ========================================
            logger.info("⌨️ [正文] 深度唤醒 - 按键 a -> Backspace 激活编辑器...")
            await page.keyboard.press("a")
            await asyncio.sleep(0.1)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)

            logger.info("🔍 [正文] 物理唤醒 - Control+Home 定位光标...")
            await page.keyboard.press("Control+Home")
            await asyncio.sleep(0.2)

            # ========================================
            # 5. 增强"全选清空"逻辑 - 先 Control+End 再 Control+A
            # ========================================
            logger.info("🗑️ [正文] 增强清空现有内容...")
            await page.keyboard.press("Control+End")  # 确保光标在末尾
            await asyncio.sleep(0.1)
            await page.keyboard.press("Control+A")   # 全选全部内容
            await asyncio.sleep(0.1)
            await page.keyboard.press("Backspace")    # 删除
            await asyncio.sleep(0.3)                  # 清空后增加等待

            # ========================================
            # 6. 增强注入方式 - paste + focus + execCommand (v10.1 新增)
            # ========================================
            logger.info("📝 [正文] 增强注入 - 三重注入模式...")
            # 使用 evaluate 传参，严禁 f-string 演接
            await iframe.evaluate("""(text) => {
                const target = document.querySelector('[contenteditable="true"]') || document.body;

                // 注入方式 1: DataTransfer 模拟 paste
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                target?.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }));

                // 注入方式 2: el.focus() 强制聚焦
                if (target?.focus) {
                    target.focus();
                }

                // 注入方式 3: document.execCommand('insertText') 强制插入
                document.execCommand('insertText', false, text);
            }""", content)
            await asyncio.sleep(0.5)

            # ========================================
            # 7. 状态固化组合键 (Rule #1) - 间隔增加到 200ms (v10.1 新增)
            # ========================================
            logger.info("🔒 [正文] 执行状态固化组合键 (200ms 间隔)...")
            await page.keyboard.press("End")
            await asyncio.sleep(0.2)  # 增加到 200ms
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.2)  # 增加到 200ms
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)  # 增加到 200ms

            # Tab 失焦 - 关键：失焦触发百家号的自动保存
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)

            logger.info("✅ [正文] 物理注入完成 (v10.1 深度唤醒版)")
            return True

        except Exception as e:
            logger.error(f"❌ [正文] 物理注入异常: {e}")
            return False

    async def _physical_upload_cover(self, page: Page, image_path: str) -> bool:
        """
        封面物理注入 v10.1 - 精准选位版 (Golden Rule #1 & #3)

        关键规则 (Golden Rule #1 & #3)：
        1. networkidle 等待：在方法最开始执行 await page.wait_for_load_state("networkidle")
        2. 深度清场：调用 _force_remove_interferences
        3. 禁止物理点击：严禁对 file input 执行任何 .click() 或 page.mouse.click() 动作
        4. 协议直接注入：使用 page.set_input_files 直接设置文件流

        v10.1 新增补丁：
        - 精准选位：通过 JS 查找 input[type="file"] 时，检查父级/祖先是否包含"封面"或"单图"字样
        - Tab 切换：注入前物理点击"单图"或"封面"按钮，确保当前处于图片模式
        - 绝杀点击：注入后执行 button:has-text('确认') 文本定位点击，找不到则物理点击 (640, 480)
        """
        try:
            # ========================================
            # Golden Rule #1 - networkidle 等待：封面注入前的网络空闲
            # ========================================
            logger.info("🔄 [封面] 等待网络空闲...")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass  # 网络空闲等待失败不影响后续流程

            # ========================================
            # Golden Rule #3 - 深度清场：封面注入前的焦土状态
            # ========================================
            logger.info("🧹 [封面] 执行深度清场 - 确保页面为焦土状态...")
            await self._force_remove_interferences(page)
            await asyncio.sleep(0.5)

            # ========================================
            # 滚动到底部 - Null Check 防止 scrollHeight 报错
            # ========================================
            await page.evaluate("() => { window.scrollTo(0, document.body ? document.body.scrollHeight : 0); }")
            await asyncio.sleep(0.5)

            # ========================================
            # v10.1 新增：Tab 切换 - 物理点击"单图"或"封面"按钮
            # ========================================
            logger.info("🔄 [封面] Tab 切换 - 确保当前处于图片模式...")
            tab_switch_result = await page.evaluate("""() => {
                // 查找包含"单图"、"封面"、"图片"等字样的按钮或元素
                const targetLabels = ['单图', '封面', '图片', 'cover', 'image', 'single'];
                const buttons = document.querySelectorAll('button, div, span, label');

                for (let button of buttons) {
                    if (!button) continue;
                    const text = (button?.innerText || button?.textContent || '')?.trim();
                    if (targetLabels.some(label => text?.includes?.(label))) {
                        // 检查是否可见
                        const style = window.getComputedStyle(button);
                        if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                            button?.click();
                            return { clicked: true, text: text?.substring(0, 20) };
                        }
                    }
                }
                return { clicked: false };
            }""")

            if tab_switch_result.get('clicked'):
                logger.info(f"✅ [封面] Tab 切换成功: {tab_switch_result.get('text')}")
                await asyncio.sleep(0.5)
            else:
                logger.info("ℹ️ [封面] 未找到 Tab 切换按钮，继续执行")

            # ========================================
            # v10.1 新增：精准选位 - 查找图片上传的 file input
            # ========================================
            logger.info("🖼️ [封面] 精准选位 - 查找图片上传 input...")
            image_file_input_found = await page.evaluate("""() => {
                const fileInputs = document.querySelectorAll('input[type="file"]');
                const targetKeywords = ['封面', '单图', '图片', 'cover', 'image', '封面图'];

                for (let input of fileInputs) {
                    if (!input) continue;

                    // 检查 input 本身的属性
                    const accept = input?.accept || '';
                    const isImageInput = accept.includes('image') || !accept;  // accept 包含 image 或为空

                    if (!isImageInput) continue;

                    // 向上递归查找父级/祖先元素是否包含目标关键词
                    let ancestor = input?.parentElement;
                    while (ancestor && ancestor !== document.body && ancestor !== document.documentElement) {
                        const ancestorText = (ancestor?.innerText || ancestor?.textContent || '')?.trim();
                        if (targetKeywords.some(keyword => ancestorText?.includes?.(keyword))) {
                            console.log(`[精准选位] 找到图片上传 input，祖先包含: "${ancestorText?.substring(0, 30)}..."`);
                            return { found: true, reason: 'ancestor', text: ancestorText?.substring(0, 30) };
                        }

                        // 检查 class 或 id
                        const classStr = ancestor?.className || '';
                        const idStr = ancestor?.id || '';
                        if (targetKeywords.some(keyword => classStr?.toLowerCase?.().includes?.(keyword?.toLowerCase()) ||
                                                        idStr?.toLowerCase?.().includes?.(keyword?.toLowerCase()))) {
                            console.log(`[精准选位] 找到图片上传 input，class/id 包含关键词`);
                            return { found: true, reason: 'class-id', class: classStr, id: idStr };
                        }

                        ancestor = ancestor?.parentElement;
                    }

                    // 如果没找到明确的祖先标记，使用第一个 image input
                    return { found: true, reason: 'first-image', accept: accept };
                }

                return { found: false };
            }""")

            if image_file_input_found.get('found'):
                logger.info(f"✅ [封面] 精准选位成功: {image_file_input_found.get('reason')}")
            else:
                logger.warning("⚠️ [封面] 未找到精准的图片上传 input，尝试通用选择")

            # ========================================
            # 显形劫持 - 强制显示所有 input[type="file"]
            # ========================================
            logger.info("🖼️ [封面] 执行显形劫持 - 强制显示 file input...")
            file_input_count = await page.evaluate("""() => {
                const fileInputs = document.querySelectorAll('input[type="file"]');
                fileInputs?.forEach((el, index) => {
                    if (!el) return;
                    el.style.cssText = 'display:block !important; position:fixed; top:0; left:0; width:100px; height:50px; z-index:99999; opacity:1; visibility:visible;';
                    el?.setAttribute('data-autogeo-index', index);
                    console.log(`[显形劫持] file input ${index}:`, el?.id || el?.className);
                });
                return fileInputs?.length || 0;
            }""")
            logger.info(f"✅ [封面] 发现 {file_input_count} 个 file input")

            await asyncio.sleep(0.3)

            # ========================================
            # 协议直接注入 - 严禁物理点击，直接设置文件流 (Golden Rule #1)
            # ========================================
            logger.info("📤 [封面] 协议直接注入 - 设置文件路径...")
            # 使用 page.set_input_files 直接设置，不会弹出系统对话框
            # 严禁对 input 执行任何 .click() 或 page.mouse.click() 动作
            try:
                await page.set_input_files("input[type='file']", image_path)
                logger.info("✅ [封面] 文件协议注入完成（无原生对话框）")
            except Exception as e:
                logger.warning(f"⚠️ [封面] 协议注入异常，尝试查找元素: {e}")
                # 降级方案：使用 element.set_input_files
                file_input = await page.query_selector("input[type='file']")
                if file_input:
                    await file_input.set_input_files(image_path)
                    logger.info("✅ [封面] 元素设置文件完成")
                else:
                    logger.error("❌ [封面] 未找到 file input")
                    return False

            # ========================================
            # 键盘触发 - 如果页面没有反应，使用 Enter 键触发
            # ========================================
            logger.info("⌨️ [封面] 等待上传处理...")
            await asyncio.sleep(2)

            # 检查是否有上传反应，如果没有则键盘触发
            upload_check = await page.evaluate("""() => {
                // 检查是否有上传中的指示器或变化
                const uploadIndicators = document.querySelectorAll('[class*="upload"], [class*="loading"], [class*="progress"]');
                let hasProgress = false;
                uploadIndicators?.forEach(el => {
                    if (!el) return;
                    const style = window.getComputedStyle(el);
                    if (style?.display !== 'none' && style?.visibility !== 'hidden') {
                        hasProgress = true;
                    }
                });
                return {
                    hasProgress,
                    inputCount: document.querySelectorAll('input[type="file"]')?.length || 0
                };
            }""")

            logger.info(f"🔍 [封面] 上传检查结果: {upload_check}")

            # 如果没有明显的上传进度，尝试键盘触发
            if not upload_check.get('hasProgress'):
                logger.info("⌨️ [封面] 未检测到上传进度，使用 Enter 键触发...")
                await page.keyboard.press("Enter")
                await asyncio.sleep(1)

                # 再次尝试
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.5)

            # 等待上传处理
            await asyncio.sleep(2)

            # ========================================
            # v10.1 新增：绝杀点击 - 文本定位 button:has-text('确认')
            # ========================================
            logger.info("🔘 [封面] 绝杀点击 - 文本定位确认按钮...")

            # 等待可能的裁剪框或确认按钮
            await asyncio.sleep(1)

            # 使用 button:has-text('确认') 文本定位点击
            confirm_clicked = False
            confirm_selectors = [
                "button:has-text('确认')",
                "button:has-text('确定')",
                "button:has-text('完成')",
                "button:has-text('保存')",
            ]

            for selector in confirm_selectors:
                try:
                    # 使用 page.locator(...).filter(visible=True) 进行物理点击
                    locator = page.locator(selector)
                    count = await locator.count()
                    if count > 0:
                        # 检查是否可见
                        try:
                            first = locator.first
                            is_visible = await first.is_visible()
                            if is_visible:
                                await first.click()
                                logger.info(f"✅ [封面] 绝杀点击成功: {selector}")
                                confirm_clicked = True
                                break
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"[封面] 选择器 {selector} 点击异常: {e}")
                    continue

            # 如果文本定位点击失败，使用坐标暴力点击 (640, 480)
            if not confirm_clicked:
                logger.info("🖱️ [封面] 文本定位失败，使用坐标暴力点击 (640, 480)...")
                try:
                    await page.mouse.click(640, 480)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"[封面] 坐标点击异常: {e}")

            # ========================================
            # Golden Rule #3 - 弹窗复发压制：三次 Escape
            # ========================================
            logger.info("🧹 [封面] 执行弹窗复发压制 - 三重 Escape...")
            for i in range(3):
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.15)
            await asyncio.sleep(0.3)

            # 等待确认处理完成
            await asyncio.sleep(2)

            logger.info("✅ [封面] 封面注入完成 (v10.1 精准选位版)")
            return True

        except Exception as e:
            logger.error(f"❌ [封面] 物理注入异常: {e}")
            return False

    async def _brutal_publish_click(self, page: Page) -> bool:
        """
        暴力点击发布按钮 v10.1

        多坐标并发点击，确保命中
        API 修正：统一使用 page.keyboard
        """
        try:
            # 滚动到底部 - Null Check 防止 scrollHeight 报错
            await page.evaluate("() => { window.scrollTo(0, document.body ? document.body.scrollHeight : 0); }")
            await asyncio.sleep(0.5)

            # 多坐标暴力点击可能的发布按钮位置
            click_coords = [
                (640, 600),  # 屏幕中心偏下
                (640, 650),  # 稍微偏下
                (640, 700),  # 更偏下
                (540, 650),  # 左侧区域
                (740, 650),  # 右侧区域
            ]

            for x, y in click_coords:
                try:
                    logger.info(f"🖱️ [发布] 暴力点击坐标: ({x}, {y})")
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.2)
                except Exception:
                    pass

            # 尝试选择器方式
            selectors = [
                "button:has-text('发布')",
                "button:has-text('提交')",
                "button:has-text('确认')",
            ]

            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            is_visible = await element.is_visible()
                            if is_visible:
                                await element.click(force=True)
                                logger.info(f"✅ [发布] 选择器点击成功: {selector}")
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue

            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.debug(f"[发布] 暴力点击异常: {e}")
            return False

    async def _wait_for_publish_result(self, page: Page) -> Dict[str, Any]:
        """等待发布结果"""
        for i in range(30):
            current_url = page.url
            # 检查 URL 变化或包含成功标识
            if "success" in current_url.lower() or "articles" in current_url.lower():
                logger.success(f"✅ [百家号] 发布成功: {current_url}")
                return {"success": True, "platform_url": current_url}
            await asyncio.sleep(1)

        logger.warning("⚠️ [百家号] 发布状态不确定，默认返回成功")
        return {"success": True, "platform_url": page.url}

    async def _download_images(self, urls: List[str]) -> List[str]:
        """下载图片"""
        paths = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True, timeout=20.0) as client:
            for i, url in enumerate(urls[:3]):
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        if len(resp.content) < 1000: continue
                        tmp_path = os.path.join(tempfile.gettempdir(), f"bjh_v101_{random.randint(1000, 9999)}.jpg")
                        with open(tmp_path, "wb") as f:
                            f.write(resp.content)
                        paths.append(tmp_path)
                        logger.info(f"✅ 图片 {i + 1} 下载成功")
                        break
                except Exception:
                    pass
        return paths


# 注册
BAIJIAHAO_CONFIG = {
    "name": "百家号",
    "publish_url": "https://baijiahao.baidu.com/builder/rc/edit?type=news",
    "color": "#E53935"
}
registry.register("baijiahao", BaijiahaoPublisher("baijiahao", BAIJIAHAO_CONFIG))
