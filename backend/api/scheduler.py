# -*- coding: utf-8 -*-
"""
定时任务API
写的定时任务API，管理定时检测！
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.scheduler_service import get_scheduler_service
from backend.schemas import ApiResponse
from loguru import logger


router = APIRouter(prefix="/api/scheduler", tags=["定时任务"])


# ==================== 响应模型 ====================

class JobInfo(BaseModel):
    """任务信息"""
    id: str
    name: str
    next_run_time: str | None


# 全局服务实例
_scheduler_service = None


def get_scheduler():
    """获取定时任务服务"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = get_scheduler_service()
        # 设置数据库工厂
        _scheduler_service.set_db_factory(lambda: get_db().__next__())
    return _scheduler_service


# ==================== 定时任务API ====================

@router.get("/jobs", response_model=List[JobInfo])
async def get_scheduled_jobs():
    """
    获取所有定时任务

    注意：返回所有已配置的定时任务！
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_scheduled_jobs()
    return jobs


@router.post("/trigger-check", response_model=ApiResponse)
async def trigger_index_check(background_tasks: BackgroundTasks):
    """
    手动触发收录检测任务

    注意：用于立即执行检测，无需等到定时时间！
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.trigger_check_now)
    return ApiResponse(success=True, message="收录检测任务已触发")


@router.post("/trigger-alert", response_model=ApiResponse)
async def trigger_alert_check(background_tasks: BackgroundTasks):
    """
    手动触发预警检查任务

    注意：用于立即检查预警！
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.trigger_alert_now)
    return ApiResponse(success=True, message="预警检查任务已触发")


@router.get("/status")
async def get_scheduler_status():
    """
    获取定时任务服务状态

    注意：检查服务是否正在运行！
    """
    scheduler = get_scheduler()
    return {
        "running": scheduler.scheduler.running if scheduler else False,
        "job_count": len(scheduler.get_scheduled_jobs()) if scheduler else 0
    }


@router.post("/start", response_model=ApiResponse)
async def start_scheduler():
    """
    启动定时任务服务

    注意：服务会在应用启动时自动启动！
    """
    scheduler = get_scheduler()
    if scheduler.scheduler.running:
        return ApiResponse(success=True, message="服务已在运行中")

    try:
        scheduler.start()
        return ApiResponse(success=True, message="定时任务服务已启动")
    except Exception as e:
        logger.error(f"启动定时任务服务失败: {e}")
        return ApiResponse(success=False, message=f"启动失败: {str(e)}")


@router.post("/stop", response_model=ApiResponse)
async def stop_scheduler():
    """
    停止定时任务服务

    注意：停止后定时任务将不再执行！
    """
    scheduler = get_scheduler()
    if not scheduler.scheduler.running:
        return ApiResponse(success=True, message="服务已停止")

    try:
        scheduler.stop()
        return ApiResponse(success=True, message="定时任务服务已停止")
    except Exception as e:
        logger.error(f"停止定时任务服务失败: {e}")
        return ApiResponse(success=False, message=f"停止失败: {str(e)}")
