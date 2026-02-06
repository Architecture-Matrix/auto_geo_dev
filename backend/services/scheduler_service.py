# -*- coding: utf-8 -*-
"""
自动化调度服务 - 工业加固版 v2.0
重构目标：
1. 装饰器注册模式取代字典硬编码
2. 全链路执行监控（TaskExecutionLog）
3. 执行守卫（Execution Guard）防崩溃
4. 依赖注入优化（自动DB Session管理）
5. 并发控制（Semaphore限流）
"""

import asyncio
import json
import traceback
from functools import wraps
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
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
from backend.database.models import ScheduledTask, TaskExecutionLog, GeoArticle

# ==================== 装饰器注册系统 ====================

class JobRegistry:
    """任务注册表 - 单例模式管理所有装饰器注册的任务"""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def register(self, key: str, name: str, description: str = ""):
        """
        装饰器工厂函数
        用法: @register_job(key="publish_task", name="文章发布")
        """
        def decorator(func: Callable):
            self._jobs[key] = {
                "func": func,
                "name": name,
                "description": description
            }
            return func
        return decorator

    def get_job(self, key: str) -> Optional[Callable]:
        """获取任务函数"""
        job = self._jobs.get(key)
        return job["func"] if job else None

    def get_job_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取任务元信息"""
        return self._jobs.get(key)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有已注册的任务"""
        return [
            {"key": key, **info}
            for key, info in self._jobs.items()
        ]

    def update_job(self, key: str, name: str, description: str = ""):
        """更新任务元信息"""
        if key in self._jobs:
            self._jobs[key]["name"] = name
            self._jobs[key]["description"] = description


# 全局注册表实例
_registry = JobRegistry()


def register_job(key: str, name: str, description: str = ""):
    """
    任务注册装饰器
    装饰后的函数会被自动注册到调度器，并享受执行守卫保护

    Args:
        key: 任务唯一标识符
        name: 任务显示名称
        description: 任务描述

    用法示例:
        @register_job(key="publish_task", name="文章发布")
        async def my_job(db: Session):
            # 业务逻辑，db 由执行守卫自动注入
            ...
    """
    return _registry.register(key, name, description)


# ==================== 执行守卫 (Execution Guard) ====================

class ExecutionGuard:
    """执行守卫 - 负责全链路任务生命周期管理"""

    def __init__(self, db_factory):
        self.db_factory = db_factory
        # 并发控制：限制同时运行的任务数
        self.semaphore = asyncio.Semaphore(3)

    async def wrap_execution(self, task_key: str, job_func: Callable):
        """
        执行包装器
        负责完整生命周期：记录开始 -> 执行 -> 记录结束 -> 错误处理
        """
        log = logger.bind(module="调度器", task=task_key)
        log_id = None

        # 独立的 DB Session 用于记录日志
        db = self.db_factory()

        try:
            # 1. 创建运行中记录
            start_time = datetime.now()
            log_record = TaskExecutionLog(
                task_key=task_key,
                status="running",
                start_time=start_time
            )
            db.add(log_record)
            db.commit()
            db.refresh(log_record)
            log_id = log_record.id

            log.info(f"🚀 任务开始执行 [log_id={log_id}]")

            # 2. 执行任务（注入新的 DB Session）
            # 任务函数会接收到一个独立的 DB Session
            task_db = self.db_factory()
            try:
                # 执行任务函数，传入 db session
                result = await job_func(task_db)
                # 任务完成后关闭 session
                task_db.close()
            except Exception as task_error:
                task_db.close()
                raise task_error

            # 3. 记录成功结果
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 处理返回结果
            result_str = None
            if result is not None:
                if isinstance(result, (dict, list)):
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(result)

            # 更新日志记录
            log_record.status = "success"
            log_record.end_time = end_time
            log_record.duration = duration
            log_record.result = result_str

            # 更新 ScheduledTask 的上次运行状态
            scheduled_task = db.query(ScheduledTask).filter(
                ScheduledTask.task_key == task_key
            ).first()
            if scheduled_task:
                scheduled_task.last_run_time = end_time
                scheduled_task.last_run_status = "success"

            db.commit()
            log.success(f"✅ 任务执行成功 [log_id={log_id}] 耗时={duration:.2f}s 结果={result_str}")

        except Exception as e:
            # 4. 错误处理：捕获所有异常，确保调度器不崩溃
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_traceback = traceback.format_exc()

            # 更新日志记录为失败
            if log_record:
                log_record.status = "failed"
                log_record.end_time = end_time
                log_record.duration = duration
                log_record.error_traceback = error_traceback

            # 更新 ScheduledTask 的上次运行状态
            scheduled_task = db.query(ScheduledTask).filter(
                ScheduledTask.task_key == task_key
            ).first()
            if scheduled_task:
                scheduled_task.last_run_time = end_time
                scheduled_task.last_run_status = "failed"

            db.commit()
            log.error(f"❌ 任务执行失败 [log_id={log_id}]: {e}\n{error_traceback}")

        finally:
            db.close()


# ==================== 调度器服务 ====================

class SchedulerService:
    """
    调度器服务 - 基于 APScheduler 的任务调度引擎
    """

    def __init__(self):
        tz = timezone('Asia/Shanghai') if timezone else None
        self.scheduler = AsyncIOScheduler(
            timezone=tz,
            job_defaults={
                'misfire_grace_time': 60,  # 允许错过时间后60秒内重试
                'coalesce': True,           # 积压的任务只跑一次
                'max_instances': 1          # 同一个Job同时只能跑一个实例
            }
        )
        self.db_factory = None
        self.execution_guard = None

    def set_db_factory(self, db_factory):
        """设置数据库工厂函数"""
        self.db_factory = db_factory
        self.execution_guard = ExecutionGuard(db_factory)

    def init_default_tasks(self):
        """初始化默认定时任务配置"""
        if not self.db_factory:
            return

        db = self.db_factory()
        try:
            # 检查是否已有默认任务
            existing_keys = {t.task_key for t in db.query(ScheduledTask.task_key).all()}

            # 从注册表获取所有已注册的任务
            registered_jobs = _registry.list_jobs()

            for job in registered_jobs:
                if job["key"] not in existing_keys:
                    # 根据任务key选择合适的默认cron表达式
                    if job["key"] == "publish_task":
                        cron_expr = "*/1 * * * *"  # 每分钟
                    elif job["key"] == "monitor_task":
                        cron_expr = "*/5 * * * *"  # 每5分钟
                    else:
                        cron_expr = "*/10 * * * *"  # 默认每10分钟

                    default_task = ScheduledTask(
                        name=job["name"],
                        task_key=job["key"],
                        cron_expression=cron_expr,
                        description=job.get("description", ""),
                        is_active=True
                    )
                    db.add(default_task)

            db.commit()
            logger.info(f"✅ 默认定时任务配置初始化完成，共注册 {len(registered_jobs)} 个任务")
        except Exception as e:
            logger.error(f"初始化任务失败: {e}")
        finally:
            db.close()

    def _schedule_job(self, task: ScheduledTask):
        """
        内部方法：注册/更新单个 Job
        使用执行守卫包装所有任务函数
        """
        job_func = _registry.get_job(task.task_key)
        if not job_func:
            logger.warning(f"⚠️ 未找到任务函数: {task.task_key}")
            return

        # 移除已存在的任务
        if self.scheduler.get_job(task.task_key):
            self.scheduler.remove_job(task.task_key)

        if task.is_active:
            try:
                # 使用执行守卫包装任务函数
                async def wrapped_job():
                    await self.execution_guard.wrap_execution(task.task_key, job_func)

                self.scheduler.add_job(
                    wrapped_job,
                    CronTrigger.from_crontab(task.cron_expression),
                    id=task.task_key,
                    replace_existing=True,
                    misfire_grace_time=60
                )
                logger.info(f"📅 任务装载成功: [{task.name}] -> {task.cron_expression}")
            except Exception as e:
                logger.error(f"❌ Cron 表达式解析错误 [{task.name}]: {e}")

    def load_jobs_from_db(self):
        """从数据库加载并注册所有任务"""
        if not self.db_factory:
            return

        db = self.db_factory()
        try:
            tasks = db.query(ScheduledTask).all()
            for t in tasks:
                self._schedule_job(t)
        finally:
            db.close()

    def start(self):
        """启动调度引擎"""
        if not self.scheduler.running:
            self.init_default_tasks()
            self.load_jobs_from_db()
            self.scheduler.start()
            logger.success("🚀 [Scheduler] 动态调度引擎已全面启动")

    def stop(self):
        """安全停止"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("🛑 [Scheduler] 调度引擎已安全关闭")

    def reload_task(self, task_id: int) -> bool:
        """用户修改配置后，手动热更新"""
        if not self.db_factory:
            return False

        db = self.db_factory()
        try:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if task:
                self._schedule_job(task)
                return True
        finally:
            db.close()
        return False

    def get_task_registry(self) -> JobRegistry:
        """获取任务注册表（用于API等外部调用）"""
        return _registry


# ==================== 业务逻辑 Job 定义 ====================
# 使用装饰器注册的任务会被自动注册到调度器

@register_job(key="publish_task", name="文章自动发布引擎",
             description="扫描待发布文章并触发浏览器自动化脚本（含指数退避重试）")
async def check_and_publish_scheduled_articles(db: Session):
    """
    [Job] 自动扫描并发布待发布文章
    使用 Semaphore 限制并发，防止一次性拉起大量浏览器
    实现指数退避重试：第一次失败5分钟后重试，第二次30分钟后，第三次2小时后

    Args:
        db: 由执行守卫自动注入的数据库会话

    Returns:
        dict: 执行结果统计，会被自动记录到日志
    """
    log = logger.bind(module="发布Job")

    # 并发控制：限制同时运行的任务数
    semaphore = asyncio.Semaphore(3)

    async def publish_with_limit(article_id: int):
        async with semaphore:
            try:
                service = GeoArticleService(db)
                await service.execute_publish(article_id)
            except Exception as e:
                log.error(f"发布文章 {article_id} 失败: {e}")

    now = datetime.now()

    # 指数退避时间配置（分钟）
    RETRY_DELAYS = {
        0: 5,    # 第一次失败：5分钟后重试
        1: 30,   # 第二次失败：30分钟后重试
        2: 120   # 第三次失败：2小时（120分钟）后重试
    }

    # 搜索待发布文章
    # 1. 正常待发布：scheduled 且 publish_time <= now
    scheduled_articles = db.query(GeoArticle).filter(
        GeoArticle.publish_status == "scheduled",
        GeoArticle.publish_time <= now
    ).all()

    # 2. 失败重试：failed 且 retry_count < 3 且 指数退避时间已到
    failed_articles = db.query(GeoArticle).filter(
        GeoArticle.publish_status == "failed",
        GeoArticle.retry_count < 3
    ).all()

    # 过滤出符合退避时间的失败文章
    retry_articles = []
    for article in failed_articles:
        delay_minutes = RETRY_DELAYS.get(article.retry_count, 5)
        retry_time = article.updated_at + timedelta(minutes=delay_minutes)
        if retry_time <= now:
            retry_articles.append(article)
            log.info(f"🔄 文章 {article.id} 符合重试条件（重试次数={article.retry_count}，延迟={delay_minutes}分钟）")

    # 合并待发布列表
    pending = scheduled_articles + retry_articles

    if pending:
        log.info(f"🔍 [发布扫描] 发现 {len(pending)} 篇待发布文章，准备触发脚本...")

        # 创建并发任务
        tasks = [publish_with_limit(article.id) for article in pending]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = db.query(GeoArticle).filter(
            GeoArticle.id.in_([a.id for a in pending]),
            GeoArticle.publish_status == "published"
        ).count()

        return {
            "processed": len(pending),
            "success": success_count,
            "failed": len(pending) - success_count
        }

    return {
        "processed": 0,
        "success": 0,
        "failed": 0
    }


@register_job(key="monitor_task", name="全网收录实时监测",
             description="通过AI搜索引擎检查已发布文章的收录状态")
async def auto_check_indexing_job(db: Session):
    """
    [Job] 自动监测收录
    Args:
        db: 由执行守卫自动注入的数据库会话

    Returns:
        dict: 执行结果统计
    """
    log = logger.bind(module="收录Job")

    # 并发控制：限制同时运行的任务数
    semaphore = asyncio.Semaphore(3)

    async def check_with_limit(article_id: int):
        async with semaphore:
            try:
                service = GeoArticleService(db)
                await service.check_article_index(article_id)
            except Exception as e:
                log.error(f"检测收录 {article_id} 失败: {e}")

    # 搜索：已发布 但 未被确认收录的文章
    pending = db.query(GeoArticle).filter(
        GeoArticle.publish_status == "published",
        GeoArticle.index_status != "indexed"
    ).all()

    if pending:
        log.info(f"📡 [收录扫描] 发现 {len(pending)} 篇已发布文章需要检测效果...")

        # 创建并发任务
        tasks = [check_with_limit(article.id) for article in pending]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        indexed_count = db.query(GeoArticle).filter(
            GeoArticle.id.in_([a.id for a in pending]),
            GeoArticle.index_status == "indexed"
        ).count()

        return {
            "processed": len(pending),
            "indexed": indexed_count,
            "pending": len(pending) - indexed_count
        }

    return {
        "processed": 0,
        "indexed": 0,
        "pending": 0
    }


# ==================== 单例模式 ====================

_instance = SchedulerService()


def get_scheduler_service() -> SchedulerService:
    """获取调度器服务单例"""
    return _instance


def get_job_registry() -> JobRegistry:
    """获取任务注册表单例"""
    return _registry
