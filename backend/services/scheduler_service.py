# -*- coding: utf-8 -*-
"""
定时任务服务
用这个来管理定时收录检测任务！
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from backend.config import INDEX_CHECK_HOUR, INDEX_CHECK_MINUTE
from backend.services.index_check_service import IndexCheckService
from backend.services.notification_service import get_notification_service, WebSocketNotificationChannel
from backend.database.models import Keyword, Project


class SchedulerService:
    """
    定时任务服务

    注意：这个服务负责管理所有定时任务！
    """

    def __init__(self):
        """初始化定时任务服务"""
        self.scheduler = AsyncIOScheduler()
        self.db_factory = None
        self.ws_callback = None

    def set_db_factory(self, db_factory):
        """设置数据库工厂"""
        self.db_factory = db_factory

    def set_ws_callback(self, callback: Callable):
        """设置WebSocket回调"""
        self.ws_callback = callback

    def start(self):
        """启动定时任务"""
        # 添加每日收录检测任务
        self.scheduler.add_job(
            self.daily_index_check,
            CronTrigger(hour=INDEX_CHECK_HOUR, minute=INDEX_CHECK_MINUTE),
            id="daily_index_check",
            name="每日收录检测",
            replace_existing=True
        )

        # 添加预警检查任务（每天检查一次，在收录检测后1小时）
        alert_hour = (INDEX_CHECK_HOUR + 1) % 24
        self.scheduler.add_job(
            self.daily_alert_check,
            CronTrigger(hour=alert_hour, minute=INDEX_CHECK_MINUTE),
            id="daily_alert_check",
            name="每日预警检查",
            replace_existing=True
        )

        # 添加失败重试任务（每6小时检查一次）
        self.scheduler.add_job(
            self.retry_failed_checks,
            CronTrigger(hour="*/6"),
            id="retry_failed_checks",
            name="失败重试任务",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"定时任务服务已启动，收录检测: {INDEX_CHECK_HOUR:02d}:{INDEX_CHECK_MINUTE:02d}, 预警检查: {alert_hour:02d}:{INDEX_CHECK_MINUTE:02d}")

    def stop(self):
        """停止定时任务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务服务已停止")

    async def daily_index_check(self):
        """
        每日收录检测任务

        注意：这个任务会检测所有活跃关键词！
        """
        logger.info("开始执行每日收录检测任务")

        if not self.db_factory:
            logger.error("数据库工厂未设置，无法执行检测任务")
            return

        db = self.db_factory()
        try:
            service = IndexCheckService(db)

            # 获取所有活跃项目
            projects = db.query(Project).filter(Project.status == 1).all()

            total_keywords = 0
            total_checks = 0

            for project in projects:
                # 获取项目的活跃关键词
                keywords = db.query(Keyword).filter(
                    Keyword.project_id == project.id,
                    Keyword.status == "active"
                ).all()

                if not keywords:
                    continue

                logger.info(f"开始检测项目: {project.name}, 关键词数: {len(keywords)}")

                for keyword in keywords:
                    try:
                        # 执行检测
                        results = await service.check_keyword(
                            keyword_id=keyword.id,
                            company_name=project.company_name
                        )

                        total_keywords += 1
                        total_checks += len(results)

                        # 发送WebSocket通知
                        if self.ws_callback:
                            await self.ws_callback({
                                "type": "index_check_progress",
                                "data": {
                                    "project_name": project.name,
                                    "keyword": keyword.keyword,
                                    "results_count": len(results)
                                }
                            })

                    except Exception as e:
                        logger.error(f"关键词检测失败: {keyword.keyword}, {e}")

            logger.info(f"每日收录检测任务完成: 检测{total_keywords}个关键词, 共{total_checks}条记录")

            # 发送完成通知
            if self.ws_callback:
                await self.ws_callback({
                    "type": "index_check_complete",
                    "data": {
                        "total_keywords": total_keywords,
                        "total_checks": total_checks
                    }
                })

        except Exception as e:
            logger.error(f"每日收录检测任务失败: {e}")
        finally:
            db.close()

    async def trigger_check_now(self):
        """
        立即触发一次检测任务（用于测试）

        注意：这个方法用于手动触发检测！
        """
        logger.info("手动触发收录检测任务")
        await self.daily_index_check()

    async def daily_alert_check(self):
        """
        每日预警检查任务

        注意：检测完成后检查SEO健康状况！
        """
        logger.info("开始执行每日预警检查任务")

        if not self.db_factory:
            logger.error("数据库工厂未设置，无法执行预警检查")
            return

        db = self.db_factory()
        try:
            # 创建通知服务
            notification_service = get_notification_service(db)

            # 添加WebSocket通知渠道
            if self.ws_callback:
                notification_service.add_channel(WebSocketNotificationChannel(self.ws_callback))

            # 执行预警检查
            alerts = await notification_service.check_and_alert()

            logger.info(f"每日预警检查完成: 触发{len(alerts)}条预警")

            # 发送预警汇总
            if self.ws_callback:
                summary = notification_service.get_alert_summary()
                await self.ws_callback({
                    "type": "alert_summary",
                    "data": summary
                })

        except Exception as e:
            logger.error(f"每日预警检查任务失败: {e}")
        finally:
            db.close()

    async def retry_failed_checks(self):
        """
        失败重试任务

        注意：重试最近检测失败的关键词！
        """
        logger.info("开始执行失败重试任务")

        if not self.db_factory:
            logger.error("数据库工厂未设置，无法执行重试任务")
            return

        db = self.db_factory()
        try:
            service = IndexCheckService(db)

            # 获取最近24小时内没有检测记录的关键词
            from datetime import datetime, timedelta
            from backend.database.models import IndexCheckRecord

            yesterday = datetime.now() - timedelta(days=1)

            # 获取所有活跃关键词
            keywords = db.query(Keyword).filter(Keyword.status == "active").all()

            retry_count = 0

            for keyword in keywords:
                # 检查最近是否有检测记录
                latest_check = db.query(IndexCheckRecord).filter(
                    IndexCheckRecord.keyword_id == keyword.id
                ).order_by(IndexCheckRecord.check_time.desc()).first()

                # 如果没有检测记录或记录已过期，重新检测
                if not latest_check or latest_check.check_time < yesterday:
                    # 获取关键词所属项目
                    project = db.query(Project).filter(Project.id == keyword.project_id).first()
                    if project:
                        try:
                            await service.check_keyword(
                                keyword_id=keyword.id,
                                company_name=project.company_name
                            )
                            retry_count += 1
                            logger.info(f"重试检测成功: {keyword.keyword}")

                        except Exception as e:
                            logger.error(f"重试检测失败: {keyword.keyword}, {e}")

            logger.info(f"失败重试任务完成: 重试{retry_count}个关键词")

        except Exception as e:
            logger.error(f"失败重试任务失败: {e}")
        finally:
            db.close()

    async def trigger_alert_now(self):
        """
        立即触发一次预警检查（用于测试）

        注意：这个方法用于手动触发预警检查！
        """
        logger.info("手动触发预警检查任务")
        await self.daily_alert_check()

    def get_scheduled_jobs(self) -> list[Dict[str, Any]]:
        """
        获取当前所有定时任务

        注意：返回所有已配置的定时任务！
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })
        return jobs


# 全局单例
scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """
    获取定时任务服务单例

    注意：这是对外暴露的主要接口！
    """
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService()
    return scheduler_service
