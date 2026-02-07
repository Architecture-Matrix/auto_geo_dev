# -*- coding: utf-8 -*-
"""
自动化调度服务 - 工业鲁棒加固版
负责：定时扫描待发布文章、自动触发收录检测、失败重试、动态任务加载
重构点：
1. 引入 Semaphore 控制最大并发数为 3
2. 添加执行日志记录 (SchedulerExecutionLog)
3. 任务自愈机制 (cleanup_stuck_tasks)
4. 指数退避重试策略
5. 执行守卫模式 (wrap_execution)
"""

import asyncio
import random
import traceback
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

# 尝试导入时区，防止环境缺失报错
try:
    from pytz import timezone
except ImportError:
    timezone = None

from backend.services.geo_article_service import GeoArticleService
from backend.database.models import (
    ScheduledTask, GeoArticle, Project, Keyword,
    SchedulerExecutionLog
)

# 🌟 统一日志绑定
log = logger.bind(module="调度中心")

# ==================== 执行守卫装饰器 ====================

def wrap_execution(task_key: str):
    """
    执行守卫装饰器
    负责记录执行开始/结束/错误堆栈到 SchedulerExecutionLog
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 提取 article_id
            article_id = kwargs.get('article_id') or (args[0] if args else None)

            if not self.db_factory:
                return await func(self, *args, **kwargs)

            # 获取执行日志记录函数
            async def log_execution(status: str, error_stack: str = None, result_summary: str = None):
                db = self.db_factory()
                try:
                    log_entry = db.query(SchedulerExecutionLog).filter(
                        SchedulerExecutionLog.task_key == task_key,
                        SchedulerExecutionLog.article_id == article_id,
                        SchedulerExecutionLog.finished_at == None
                    ).first()

                    if log_entry:
                        log_entry.finished_at = datetime.now()
                        log_entry.duration_ms = int((log_entry.finished_at - log_entry.started_at).total_seconds() * 1000)
                        log_entry.status = status
                        if error_stack:
                            log_entry.error_stack_trace = error_stack
                        if result_summary:
                            log_entry.result_summary = result_summary
                        db.commit()
                except Exception as e:
                    logger.error(f"记录执行日志失败: {e}")
                finally:
                    db.close()

            # 创建运行中日志
            db = self.db_factory()
            try:
                execution_log = SchedulerExecutionLog(
                    task_key=task_key,
                    article_id=article_id,
                    started_at=datetime.now(),
                    status="running"
                )
                db.add(execution_log)
                db.commit()
                db.refresh(execution_log)
            except Exception as e:
                logger.error(f"创建执行日志失败: {e}")
            finally:
                db.close()

            # 执行被装饰函数
            try:
                result = await func(self, *args, **kwargs)
                # 记录成功
                result_summary = f"发布成功，返回: {result}"
                await log_execution("success", result_summary=result_summary)
                return result
            except Exception as e:
                # 记录失败
                error_stack = traceback.format_exc()
                await log_execution("failed", error_stack=error_stack, result_summary=f"执行异常: {str(e)}")
                logger.error(f"执行失败: {e}\n{error_stack}")
                raise
        return wrapper
    return decorator


# 指数退避时间配置（分钟）
RETRY_DELAYS = [5, 30, 120]  # 第1次5分钟，第2次30分钟，第3次2小时


class SchedulerService:
    def __init__(self):
        tz = timezone('Asia/Shanghai') if timezone else None
        # 配置调度器，设置较长的误火容忍时间
        self.scheduler = AsyncIOScheduler(
            timezone=tz,
            job_defaults={
                'misfire_grace_time': 60, # 🌟 允许错过时间后60秒内重试
                'coalesce': True,         # 积压的任务只跑一次
                'max_instances': 1        # 同一个Job同时只能跑一个实例
            }
        )
        self.db_factory = None

        # 🌟 并发控制：最大同时执行3个发布任务
        self._publish_semaphore = asyncio.Semaphore(3)

        # 🌟 任务映射表
        self.task_registry = {
            "publish_task": self.check_and_publish_scheduled_articles,
            "monitor_task": self.auto_check_indexing_job
        }

    def set_db_factory(self, db_factory):
        self.db_factory = db_factory

    def init_default_tasks(self):
        """初始化默认定时扫描任务"""
        if not self.db_factory: return
        db = self.db_factory()
        try:
            if db.query(ScheduledTask).count() == 0:
                defaults = [
                    ScheduledTask(
                        name="文章自动发布引擎",
                        task_key="publish_task",
                        cron_expression="*/1 * * * *",  # 每分钟扫描一次
                        description="扫描待发布文章并触发浏览器自动化脚本",
                        is_active=True
                    ),
                    ScheduledTask(
                        name="全网收录实时监测",
                        task_key="monitor_task",
                        cron_expression="*/5 * * * *",  # 每5分钟监测一次
                        description="通过AI搜索引擎检查已发布文章的收录状态",
                        is_active=True
                    )
                ]
                db.add_all(defaults)
                db.commit()
                log.info("✅ 默认定时扫描任务初始化完成")
        except Exception as e:
            log.error(f"初始化任务失败: {e}")
        finally:
            db.close()

    def _schedule_job(self, task: ScheduledTask):
        """内部方法：注册/更新单个 Job"""
        func = self.task_registry.get(task.task_key)
        if not func:
            log.warning(f"⚠️ 未找到处理函数: {task.task_key}")
            return

        if self.scheduler.get_job(task.task_key):
            self.scheduler.remove_job(task.task_key)

        if task.is_active:
            try:
                self.scheduler.add_job(
                    func,
                    CronTrigger.from_crontab(task.cron_expression),
                    id=task.task_key,
                    replace_existing=True,
                    misfire_grace_time=60 # 🌟 加固保护
                )
                log.info(f"📅 任务装载成功: [{task.name}] -> {task.cron_expression}")
            except Exception as e:
                log.error(f"❌ Cron 表达式解析错误 [{task.name}]: {e}")

    def load_jobs_from_db(self):
        """从数据库加载并注册所有任务"""
        if not self.db_factory: return
        db = self.db_factory()
        try:
            tasks = db.query(ScheduledTask).all()
            for t in tasks:
                self._schedule_job(t)
        finally:
            db.close()

    async def cleanup_stuck_tasks(self):
        """
        任务自愈：清理卡死的任务
        将停留在 publishing 状态超过阈值（默认30分钟）的文章重置为 failed
        """
        if not self.db_factory:
            return

        db = self.db_factory()
        try:
            threshold = datetime.now() - timedelta(minutes=30)
            stuck_articles = db.query(GeoArticle).filter(
                GeoArticle.publish_status == "publishing",
                GeoArticle.updated_at < threshold
            ).all()

            if stuck_articles:
                log.warning(f"🔧 [自愈] 发现 {len(stuck_articles)} 篇卡死文章，正在重置状态...")
                for article in stuck_articles:
                    article.publish_status = "failed"
                    article.error_msg = "任务执行超时，自动重置"
                    log.warning(f"  -> 文章 {article.id} 已从 publishing 重置为 failed")

                    # 记录超时日志
                    log_entry = SchedulerExecutionLog(
                        task_key="publish_task",
                        article_id=article.id,
                        started_at=article.updated_at,
                        finished_at=datetime.now(),
                        status="timeout",
                        result_summary="任务执行超时，自动重置"
                    )
                    db.add(log_entry)

                db.commit()
                log.success(f"✅ [自愈] 已重置 {len(stuck_articles)} 篇卡死文章")
        except Exception as e:
            log.error(f"任务自愈失败: {e}")
        finally:
            db.close()

    def start(self):
        """启动调度引擎"""
        if not self.scheduler.running:
            # 启动任务自愈（必须在加载任务前执行）
            asyncio.create_task(self.cleanup_stuck_tasks())
            self.init_default_tasks()
            self.load_jobs_from_db()
            self.scheduler.start()
            log.success("🚀 [Scheduler] 动态调度引擎已全面启动")

    def stop(self):
        """安全停止"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            log.info("🛑 [Scheduler] 调度引擎已安全关闭")

    def reload_task(self, task_id: int):
        """用户修改配置后，手动热更新"""
        if not self.db_factory: return
        db = self.db_factory()
        try:
            task = db.query(ScheduledTask).get(task_id)
            if task:
                self._schedule_job(task)
                return True
        finally:
            db.close()
        return False

    # ================= 🚀 核心业务逻辑 Job =================

    async def _publish_articles_internal(self, articles: List[GeoArticle]):
        """
        内部方法：使用 Semaphore 控制并发发布
        确保最多同时执行 3 个发布任务
        """
        async def publish_with_semaphore(article: GeoArticle):
            async with self._publish_semaphore:
                try:
                    service = GeoArticleService(self.db_factory())
                    await service.execute_publish(article.id)
                finally:
                    # 释放 db 连接
                    self.db_factory().close()

        # 创建所有任务，但通过 Semaphore 限制并发
        tasks = [publish_with_semaphore(article) for article in articles]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def check_and_publish_scheduled_articles(self):
        """
        [Job] 自动扫描并发布
        增强功能：
        1. 使用 Semaphore 限制最大并发数为 3
        2. 支持指数退避重试策略
        """
        if not self.db_factory: return
        db = self.db_factory()
        try:
            now = datetime.now()
            # 搜索：待发布(scheduled) 或 失败重试(failed 且 时间已到)
            pending = db.query(GeoArticle).filter(
                ((GeoArticle.publish_status == "scheduled") |
                 ((GeoArticle.publish_status == "failed") & (GeoArticle.publish_time <= now))),
                GeoArticle.retry_count < len(RETRY_DELAYS)  # 未超过最大重试次数
            ).all()

            if pending:
                log.info(f"🔍 [发布扫描] 发现 {len(pending)} 篇待发布文章，准备触发脚本...")
                # 使用内部方法进行并发控制
                await self._publish_articles_internal(pending)
        except Exception as e:
            log.error(f"发布 Job 运行异常: {e}")
        finally:
            db.close()

    async def auto_check_indexing_job(self):
        """
        [Job] 自动监测收录
        """
        if not self.db_factory: return
        db = self.db_factory()
        try:
            # 搜索：已发布 但 未被确认收录的文章
            pending = db.query(GeoArticle).filter(
                GeoArticle.publish_status == "published",
                GeoArticle.index_status != "indexed"
            ).all()

            if pending:
                log.info(f"📡 [收录扫描] 发现 {len(pending)} 篇已发布文章需要检测效果...")
                service = GeoArticleService(db)
                for article in pending:
                    asyncio.create_task(service.check_article_index(article.id))
        except Exception as e:
            log.error(f"监测 Job 运行异常: {e}")
        finally:
            db.close()

# 单例模式
_instance = SchedulerService()

def get_scheduler_service():
    return _instance