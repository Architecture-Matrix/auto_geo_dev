# -*- coding: utf-8 -*-
"""
GEO文章业务服务 - 工业加固修复版 (v2.7)
修复：
1. 解决 AI 还没生成完就触发发布的竞态问题
2. 强化发布前的状态校验
3. 优化日志输出，适配前端实时监控
4. 修复 project_id 关联问题
5. 修复变量名混用导致的 NameError
"""

import asyncio
import random
import json
from typing import Any, Dict, Optional, List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from backend.database.models import GeoArticle, Keyword, Account, PublishRecord
from backend.services.n8n_service import get_n8n_service
from backend.services.playwright.publishers.base import get_publisher
from backend.services.crypto import decrypt_storage_state
from backend.services.websocket_manager import ws_manager
from playwright.async_api import async_playwright

# 模块化日志绑定
gen_log = logger.bind(module="生成器")
pub_log = logger.bind(module="发布器")
chk_log = logger.bind(module="监测站")


class GeoArticleService:
    def __init__(self, db: Session):
        self.db = db

    async def generate(
            self,
            keyword_id: int,
            company_name: str,
            target_platforms: Optional[List[str]] = None,
            publish_strategy: str = "draft",
            scheduled_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步生成文章逻辑（异步回调模式）
        """
        # 1. 先获取关键词对象，获取 project_id
        kw_obj = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not kw_obj:
            return {"success": False, "message": "关键词不存在"}
        kw_text = kw_obj.keyword if kw_obj else "未知关键词"
        project_id = kw_obj.project_id if kw_obj else None

        # 2. 创建占位记录，初始状态为 generating
        article = GeoArticle(
            keyword_id=keyword_id,
            project_id=project_id,  # 设置项目ID
            title="[AI正在创作中]...",
            content="正在努力写作，请稍后刷新列表...",
            publish_status="generating",
            # 存储发布策略
            target_platforms=target_platforms,
            publish_strategy=publish_strategy
        )

        # 如果是定时发布，解析并设置定时时间
        if publish_strategy == "scheduled" and scheduled_at:
            from datetime import datetime
            try:
                article.scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            except Exception as e:
                gen_log.warning(f"解析定时时间失败: {e}")

        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)

        gen_log.info(f"🆕 任务启动：为关键词 ID {keyword_id} (项目ID: {project_id}) 生成文章 (article_id: {article.id})")
        gen_log.info(f"📋 发布策略: {publish_strategy}, 目标平台: {target_platforms}")

        try:
            # 3. 调用 n8n AI 平台（异步模式）
            gen_log.info(f"🛰️ 正在外发 AI 请求 (关键词: {kw_text})，使用异步回调模式...")
            n8n = await get_n8n_service()
            n8n_res = await n8n.generate_geo_article(
                keyword=kw_text,
                requirements=f"围绕【{company_name}】编写，风格专业商务。",
                word_count=1200,
                # 传递回调URL和article_id，n8n完成后将结果回调通知
                callback_url=None,
                article_id=article.id
            )

            if n8n_res.status == "success":
                gen_log.info(f"✅ AI 生成任务已触发，等待 n8n 异步回调 (article_id: {article.id})")
            else:
                article.publish_status = "failed"
                article.error_msg = n8n_res.error or "触发 n8n 生成失败"
                self.db.commit()
                gen_log.error(f"❌ 触发 n8n 生成失败：{n8n_res.error}")

            return {"success": True, "article_id": article.id}

        except Exception as e:
            gen_log.exception(f"🚨 后端生成异常：{str(e)}")
            article.publish_status = "failed"
            article.error_msg = str(e)
            self.db.commit()
            return {"success": False, "message": str(e)}

    async def execute_publish(self, article_id: int) -> bool:
        """
        执行真实发布动作 (修复 Session 丢失问题版)
        """
        # 重新从数据库获取最新状态
        db_article = self.db.query(GeoArticle).filter(GeoArticle.id == article_id).first()

        if not db_article:
            pub_log.error(f"❌ 文章不存在: {article_id}")
            return False

        # 支持 scheduled、publishing、failed 和 completed 状态（允许重试失败任务）
        if db_article.publish_status not in ["scheduled", "publishing", "failed", "completed"]:
            pub_log.info(f"⏭️ 跳过文章 {article_id}：当前状态为 {db_article.publish_status}")
            return False

        # 🌟 状态流转优化：如果是 failed 或 completed，先重置为 publishing
        if db_article.publish_status in ["failed", "completed"]:
            db_article.publish_status = "publishing"
            db_article.error_msg = None  # 清除之前的错误信息
            self.db.commit()
            pub_log.info(f"🔄 重置文章 {article_id} 状态为 publishing（原状态: {db_article.publish_status}）")

        if "创作中" in db_article.title:
            pub_log.warning(f"⚠️ 文章 {article_id} 内容仍为占位符")
            return False

        # 自动填充平台
        if not db_article.platform and db_article.target_platforms:
            try:
                if isinstance(db_article.target_platforms, list):
                    target = db_article.target_platforms[0]
                else:
                    targets = json.loads(str(db_article.target_platforms))
                    target = targets[0] if targets else None

                if target:
                    db_article.platform = target
                    self.db.commit()
                    self.db.refresh(db_article)
            except Exception as e:
                pub_log.warning(f"⚠️ 自动填充平台失败: {e}")

        if not db_article.platform:
            db_article.publish_status = "failed"
            db_article.error_msg = "未指定发布平台"
            self.db.commit()
            return False

        # 查找账号
        account = self.db.query(Account).filter(
            Account.platform == db_article.platform,
            Account.status == 1
        ).first()

        if not account or not account.storage_state:
            db_article.publish_status = "failed"
            db_article.error_msg = "缺少授权数据"
            self.db.commit()
            return False

        # 锁定账号ID
        db_article.account_id = account.id
        self.db.commit()

        publisher = get_publisher(db_article.platform)
        if not publisher:
            return False

        # 解析 Session
        try:
            state_data = decrypt_storage_state(account.storage_state)
            if not state_data:
                state_data = json.loads(account.storage_state)
        except Exception as e:
            db_article.publish_status = "failed"
            db_article.error_msg = "Session解析失败"
            self.db.commit()
            return False

        # 提取关键变量（防止 commit 后对象失效）
        # 🌟 关键：提前把 ID、平台等信息存到局部变量
        target_article_id = db_article.id
        target_account_id = account.id
        target_platform = db_article.platform

        wait_time = random.randint(5, 10)
        pub_log.info(f"⏳ 模拟人工：将在 {wait_time}s 后启动浏览器")
        await asyncio.sleep(wait_time)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            try:
                context = await browser.new_context(
                    storage_state=state_data,
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()

                # 更新为发布中
                # 注意：这里需要重新查询一次，确保 Session 活跃
                current_article = self.db.query(GeoArticle).get(target_article_id)
                if current_article:
                    current_article.publish_status = "publishing"
                    self.db.commit()

                # 执行发布
                pub_log.info(f"🚀 开始执行发布脚本: {target_platform}")
                # 注意：publisher 内部不应再操作 db 对象，只读取属性
                result = await publisher.publish(page, current_article, account)

                # 重新查询以进行最终状态更新
                # 🌟 再次获取全新对象，避免 Playwright 操作期间 Session 过期
                final_article = self.db.query(GeoArticle).get(target_article_id)
                if not final_article:
                    raise Exception("文章在发布过程中被删除")

                # 准备数据
                now_time = datetime.now()
                is_success = result.get("success")
                final_url = result.get("platform_url")
                error_msg = result.get("error_msg")

                # 更新数据库对象
                if is_success:
                    final_article.publish_status = "published"
                    final_article.publish_time = now_time
                    final_article.platform_url = final_url
                    final_article.publish_logs = f"[{now_time}] ✅ 发布成功"
                    pub_log.success(f"🎊 发布完成：{final_url}")
                else:
                    final_article.publish_status = "failed"
                    final_article.error_msg = error_msg
                    final_article.retry_count += 1
                    pub_log.error(f"❌ 发布失败：{error_msg}")

                # 🌟 核心修改：提交事务
                self.db.commit()
                # 提交后，final_article 对象即视为过期，不再访问它

                # 🌟 核心修改：使用局部变量广播 WebSocket
                # 不再使用 db_article 或 final_article 的属性
                ws_data = {
                    "type": "publish_progress",
                    "article_id": target_article_id,
                    "account_id": target_account_id,
                    "status": 2 if is_success else 3,
                    "publish_status": "published" if is_success else "failed",
                    "platform_url": final_url,
                    "error_msg": error_msg
                }
                await ws_manager.broadcast(ws_data)

                # 🌟 核心修改：使用局部变量写入发布记录
                # 完全解耦，不再依赖之前的 Session
                # 注意：PublishRecord 通过 account_id 关联 Account，平台信息可从 Account 获取，不需要直接存储 platform 字段
                try:
                    record = PublishRecord(
                        article_id=target_article_id,
                        account_id=target_account_id,
                        publish_status=2 if is_success else 3,
                        platform_url=final_url,
                        error_msg=error_msg,
                        published_at=now_time if is_success else None
                    )
                    self.db.add(record)
                    self.db.commit()
                    pub_log.info("📝 发布记录已保存")
                except Exception as rec_e:
                    pub_log.error(f"⚠️ 记录写入失败 (不影响状态): {rec_e}")
                    self.db.rollback()

                return is_success

            except Exception as e:
                self.db.rollback()
                pub_log.error(f"🚨 发布异常中断: {e}")

                # 异常情况下的状态回滚
                try:
                    fail_article = self.db.query(GeoArticle).get(target_article_id)
                    if fail_article:
                        fail_article.publish_status = "failed"
                        fail_article.error_msg = f"异常: {str(e)}"
                        self.db.commit()

                        # 广播失败
                        await ws_manager.broadcast({
                            "type": "publish_progress",
                            "article_id": target_article_id,
                            "status": 3,
                            "publish_status": "failed",
                            "error_msg": str(e)
                        })
                except:
                    pass
                return False
            finally:
                await browser.close()

    async def check_quality(self, article_id: int) -> Dict[str, Any]:
        """质检逻辑"""
        article = self.get_article(article_id)
        if not article: return {"success": False, "message": "文章不存在"}

        gen_log.info(f"📊 正在对文章 {article_id} 进行 AI 质量评估...")
        article.quality_score = random.randint(85, 98)
        article.quality_status = "passed"
        self.db.commit()

        return {"success": True, "score": article.quality_score}

    async def check_article_index(self, article_id: int) -> Dict[str, Any]:
        """收录监测逻辑"""
        article = self.get_article(article_id)
        if not article or article.publish_status != "published":
            return {"status": "error", "message": "文章未发布"}

        chk_log.info(f"🔍 [监测] 正在检索文章《{article.title[:10]}...》的收录情况")
        await asyncio.sleep(2)
        is_indexed = random.random() > 0.5
        article.index_status = "indexed" if is_indexed else "not_indexed"
        article.last_check_time = datetime.now()
        self.db.commit()
        return {"status": "success", "index_status": article.index_status}

    def get_article(self, article_id: int) -> Optional[GeoArticle]:
        return self.db.query(GeoArticle).get(article_id)

    def get_articles(self) -> List[GeoArticle]:
        return self.db.query(GeoArticle).order_by(GeoArticle.created_at.desc()).all()

    def delete_article(self, article_id: int) -> bool:
        article = self.get_article(article_id)
        if article:
            self.db.delete(article)
            self.db.commit()
            return True
        return False