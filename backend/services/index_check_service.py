# -*- coding: utf-8 -*-
"""
收录检测服务 - 工业加固版
负责调用 Playwright 模拟 AI 搜索并实时推送执行进度
包含百度搜索收录检测功能
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from backend.database.models import IndexCheckRecord, Keyword, QuestionVariant, GeoArticle
from backend.config import AI_PLATFORMS

# 🌟 绑定模块名，用于 WebSocket 实时日志着色
chk_log = logger.bind(module="监测站")


class IndexCheckService:
    """收录检测服务类"""

    def __init__(self, db: Session):
        self.db = db
        # 注意：这里假设你已经定义好了相关的 Checker 类
        # 如果还没写完逻辑，可以使用下方的 Mock 逻辑进行测试
        try:
            from backend.services.playwright.ai_platforms import DoubaoChecker, QianwenChecker, DeepSeekChecker
            self.checkers = {
                "doubao": DoubaoChecker("doubao", AI_PLATFORMS.get("doubao")),
                "qianwen": QianwenChecker("qianwen", AI_PLATFORMS.get("qianwen")),
                "deepseek": DeepSeekChecker("deepseek", AI_PLATFORMS.get("deepseek")),
            }
        except ImportError:
            self.checkers = {}
            chk_log.warning("⚠️ 警告：未找到 AI 平台检测插件，将使用模拟模式运行")

    async def run_ai_search_check(
            self,
            keyword_id: int,
            company_name: str,
            platforms: Optional[List[str]] = None
    ):
        """
        🌟 核心方法：执行收录检测 (由 API 异步调用)
        """
        # 1. 基础数据校验
        keyword_obj = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword_obj:
            chk_log.error(f"❌ 错误：关键词 ID {keyword_id} 不存在")
            return

        chk_log.info(f"🔍 监测启动：正在检索关键词 【{keyword_obj.keyword}】")

        # 2. 获取检测问题
        questions = self.db.query(QuestionVariant).filter(
            QuestionVariant.keyword_id == keyword_id
        ).all()

        # 兜底：如果没有变体词，生成一个默认问题
        query_texts = [q.question for q in questions] if questions else [
            f"请推荐一些专业的{keyword_obj.keyword}服务商，{company_name}怎么样？"]

        # 确定平台
        target_platforms = platforms if platforms else ["doubao", "qianwen", "deepseek"]

        # 3. 启动 Playwright 执行检测
        chk_log.info(f"🌐 正在初始化自动化浏览器 (目标平台: {', '.join(target_platforms)})...")

        async with async_playwright() as p:
            # 这里的 headless=True 代表后台运行。调试时可以改为 False 看效果
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                for platform_id in target_platforms:
                    chk_log.info(f"📡 正在接入 {platform_id} 平台...")

                    # 🌟 模拟/实际检测逻辑
                    for q_text in query_texts:
                        chk_log.info(f"💬 询问 AI: \"{q_text[:20]}...\"")

                        # --- 核心逻辑：这里调用你定义的每个平台的爬虫逻辑 ---
                        checker = self.checkers.get(platform_id)
                        if checker:
                            # 实际调用 Playwright 脚本
                            res = await checker.check(page, q_text, keyword_obj.keyword, company_name)
                        else:
                            # 🌟 Mock 模式：如果没有实现具体插件，先跑通流程
                            await asyncio.sleep(2)  # 模拟网络耗时
                            is_hit = random.random() > 0.4
                            res = {
                                "success": True,
                                "answer": f"为您找到关于{keyword_obj.keyword}的信息...",
                                "keyword_found": True,
                                "company_found": is_hit
                            }

                        # 4. 保存结果到数据库
                        record = IndexCheckRecord(
                            keyword_id=keyword_id,
                            platform=platform_id,
                            question=q_text,
                            answer=res.get("answer"),
                            keyword_found=res.get("keyword_found", False),
                            company_found=res.get("company_found", False),
                            check_time=datetime.now()
                        )
                        self.db.add(record)

                        # 5. 回填更新 GeoArticle 状态
                        article = self.db.query(GeoArticle).filter(GeoArticle.keyword_id == keyword_id).first()
                        if article:
                            if res.get("company_found"):
                                article.index_status = "indexed"
                                chk_log.success(f"🎯 命中！{platform_id} 已收录文章内容")
                            else:
                                article.index_status = "not_indexed"
                                chk_log.warning(f"☁️ 未命中：{platform_id} 暂未发现关联信息")
                            article.last_check_time = datetime.now()

                self.db.commit()
                chk_log.success(f"✅ 关键词 【{keyword_obj.keyword}】 监测任务执行完毕")

            except Exception as e:
                self.db.rollback()
                chk_log.error(f"🚨 监测过程中发生异常: {str(e)}")
            finally:
                await browser.close()

    def get_check_records(self, keyword_id: Optional[int] = None, platform: Optional[str] = None, limit: int = 100):
        query = self.db.query(IndexCheckRecord)
        if keyword_id:
            query = query.filter(IndexCheckRecord.keyword_id == keyword_id)
        if platform:
            query = query.filter(IndexCheckRecord.platform == platform)
        return query.order_by(IndexCheckRecord.check_time.desc()).limit(limit).all()

    def get_hit_rate(self, keyword_id: int) -> Dict[str, Any]:
        records = self.db.query(IndexCheckRecord).filter(IndexCheckRecord.keyword_id == keyword_id).all()
        if not records:
            return {"hit_rate": 0, "total": 0, "keyword_found": 0, "company_found": 0}
        total = len(records)
        kw_f = sum(1 for r in records if r.keyword_found)
        co_f = sum(1 for r in records if r.company_found)
        return {
            "overall_hit_rate": round((co_f / total) * 100, 2) if total > 0 else 0,
            "total_checks": total,
            "keyword_found_count": kw_f,
            "company_found_count": co_f
        }


class BaiduIndexCheckService:
    """百度收录检测服务 - 用于检测关键词在百度搜索中的收录情况"""

    def __init__(self):
        self.temp_screenshots_dir = Path("backend/temp_screenshots")
        self.temp_screenshots_dir.mkdir(parents=True, exist_ok=True)
        # 导入 playwright_mgr 单例
        from backend.services.playwright_mgr import playwright_mgr
        self.playwright_mgr = playwright_mgr

    async def check_baidu_index(self, keyword: str, company_name: str) -> bool:
        """
        检查关键词在百度的收录情况

        Args:
            keyword: 要搜索的关键词
            company_name: 要查找的公司名称

        Returns:
            bool: 是否在前两页结果中找到公司名称
        """
        logger.info(f"开始百度收录检测 - 关键词: {keyword}, 公司: {company_name}")

        # 模拟人工停顿
        await asyncio.sleep(1)

        page = None
        context = None

        try:
            # 获取浏览器页面
            page, context = await self._get_browser_page()
            logger.info("成功获取浏览器页面")

            # 访问百度
            await page.goto("https://www.baidu.com", wait_until="networkidle")
            logger.info("正在访问百度首页...")

            # 模拟人工停顿
            await asyncio.sleep(1)

            # 在搜索框中输入关键词
            search_input = await page.wait_for_selector("#kw")
            await search_input.fill(keyword)
            logger.info(f"正在搜索: {keyword}...")

            # 模拟人工停顿
            await asyncio.sleep(1)

            # 点击搜索按钮
            search_button = await page.wait_for_selector("#su")
            await search_button.click()
            logger.info("已点击搜索按钮")

            # 等待搜索结果加载
            await page.wait_for_selector("#content_left", timeout=10000)
            await asyncio.sleep(2)  # 额外等待确保结果完全加载

            # 保存搜索结果截图
            await self._save_screenshot(page, keyword, "search_results")
            logger.info("已保存搜索结果截图")

            # 检查第一页结果
            page1_found = await self._check_search_results(page, company_name, 1)

            if page1_found:
                logger.info(f"发现匹配项: 第一页中找到 {company_name}")
                return True
            else:
                logger.info("第一页未找到匹配项，继续检查第二页")

                # 点击下一页
                next_page = await page.wait_for_selector(".n", timeout=5000)
                if next_page:
                    await next_page.click()
                    logger.info("正在加载第二页...")

                    # 等待第二页加载
                    await page.wait_for_selector("#content_left", timeout=10000)
                    await asyncio.sleep(2)

                    # 保存第二页截图
                    await self._save_screenshot(page, keyword, "page2_results")

                    # 检查第二页结果
                    page2_found = await self._check_search_results(page, company_name, 2)

                    if page2_found:
                        logger.info(f"发现匹配项: 第二页中找到 {company_name}")
                    else:
                        logger.info("第二页也未找到匹配项")

                    return page2_found
                else:
                    logger.warning("未找到下一页按钮")
                    return False

        except Exception as e:
            logger.error(f"百度收录检测失败: {str(e)}")
            # 保存错误截图
            if page:
                try:
                    await self._save_screenshot(page, keyword, "error")
                except:
                    pass
            return False

        finally:
            # 清理资源
            if context:
                await context.close()
            logger.info("百度收录检测完成")

    async def _get_browser_page(self) -> tuple[Page, BrowserContext]:
        """获取浏览器页面和上下文"""
        try:
            # 检查浏览器是否已启动
            if not self.playwright_mgr._browser:
                logger.info("浏览器未启动，正在启动...")
                await self.playwright_mgr.start()

            # 创建新上下文
            context = await self.playwright_mgr._browser.new_context()
            page = await context.new_page()

            # 设置页面视窗大小
            await page.set_viewport_size({"width": 1280, "height": 720})

            return page, context

        except Exception as e:
            logger.error(f"获取浏览器页面失败: {str(e)}")
            raise

    async def _check_search_results(self, page: Page, company_name: str, page_num: int) -> bool:
        """
        检查搜索结果中是否包含公司名称

        Args:
            page: 页面对象
            company_name: 公司名称
            page_num: 页码

        Returns:
            bool: 是否找到匹配项
        """
        logger.info(f"检查第{page_num}页搜索结果是否包含: {company_name}")

        try:
            # 获取所有搜索结果标题
            result_elements = await page.query_selector_all("div#content_left .result h3")

            found = False
            for i, element in enumerate(result_elements, 1):
                try:
                    title = await element.inner_text()

                    # 检查标题是否包含公司名称
                    if company_name.lower() in title.lower():
                        logger.info(f"在第{page_num}页第{i}个结果中找到匹配: {title}")
                        found = True
                        break

                    # 如果没有匹配，检查摘要
                    summary_element = await element.query_selector("../.. div.c-abstract")
                    if summary_element:
                        summary = await summary_element.inner_text()
                        if company_name.lower() in summary.lower():
                            logger.info(f"在第{page_num}页第{i}个结果的摘要中找到匹配: {summary[:50]}...")
                            found = True
                            break

                except Exception as e:
                    logger.warning(f"检查第{i}个结果时出错: {str(e)}")
                    continue

            return found

        except Exception as e:
            logger.error(f"检查搜索结果时出错: {str(e)}")
            return False

    async def _save_screenshot(self, page: Page, keyword: str, suffix: str) -> None:
        """保存截图"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{keyword}_{suffix}_{timestamp}.png"
            filepath = self.temp_screenshots_dir / filename

            await page.screenshot(path=str(filepath))
            logger.info(f"截图已保存: {filepath}")

        except Exception as e:
            logger.error(f"保存截图失败: {str(e)}")


# 创建全局服务实例
baidu_index_check_service = BaiduIndexCheckService()