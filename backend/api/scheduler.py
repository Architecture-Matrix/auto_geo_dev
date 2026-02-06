# -*- coding: utf-8 -*-
"""
调度器 API - 支持任务管理和执行日志查询
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database import get_db
from backend.database.models import ScheduledTask, TaskExecutionLog
from backend.services.scheduler_service import get_scheduler_service
from backend.schemas import ApiResponse

router = APIRouter(prefix="/api/scheduler", tags=["定时任务管理"])


# ==================== Schemas ====================

class TaskUpdate(BaseModel):
    """任务更新请求"""
    cron_expression: str
    is_active: bool


class TaskResponse(BaseModel):
    """任务响应（包含执行状态）"""
    id: int
    name: str
    task_key: str
    cron_expression: str
    is_active: bool
    description: Optional[str] = None
    last_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutionLogResponse(BaseModel):
    """执行日志响应"""
    id: int
    task_key: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[str] = None
    error_traceback: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LogsResponse(BaseModel):
    """日志列表响应（带分页）"""
    total: int
    page: int
    page_size: int
    logs: List[ExecutionLogResponse]


# ==================== API Endpoints ====================

@router.get("/jobs", response_model=List[TaskResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """
    获取所有定时任务配置
    包含 last_run_time 和 last_run_status 字段，用于前端看板展示
    """
    tasks = db.query(ScheduledTask).all()
    return tasks


@router.get("/jobs/{task_id}", response_model=TaskResponse)
async def get_job(task_id: int, db: Session = Depends(get_db)):
    """获取单个定时任务详情"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/jobs/{task_id}", response_model=ApiResponse)
async def update_job(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    """
    更新任务配置（Cron 或开关）
    更新后会自动通知调度器热重载该任务
    """
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 更新数据库
    task.cron_expression = data.cron_expression
    task.is_active = data.is_active
    db.commit()

    # 通知调度器热重载该任务
    scheduler = get_scheduler_service()
    scheduler.reload_task(task_id)

    return ApiResponse(success=True, message="任务配置已更新并生效")


@router.get("/logs", response_model=LogsResponse)
async def get_execution_logs(
    task_key: Optional[str] = Query(None, description="按任务标识过滤"),
    status: Optional[str] = Query(None, description="按状态过滤：success/failed/running"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取任务执行日志（支持分页和过滤）

    参数说明:
        task_key: 任务标识符，如 "publish_task"
        status: 执行状态过滤
        page: 页码（从1开始）
        page_size: 每页数量（最大100）

    返回: 分页的执行日志列表
    """
    query = db.query(TaskExecutionLog)

    # 按任务标识过滤
    if task_key:
        query = query.filter(TaskExecutionLog.task_key == task_key)

    # 按状态过滤
    if status:
        query = query.filter(TaskExecutionLog.status == status)

    # 获取总数
    total = query.count()

    # 分页查询（按创建时间倒序）
    logs = query.order_by(desc(TaskExecutionLog.start_time)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return LogsResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=logs
    )


@router.get("/logs/{log_id}", response_model=ExecutionLogResponse)
async def get_execution_log_detail(log_id: int, db: Session = Depends(get_db)):
    """
    获取单条执行日志详情
    包含完整的错误堆栈信息
    """
    log = db.query(TaskExecutionLog).filter(TaskExecutionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return log


@router.get("/logs/latest/{task_key}", response_model=Optional[ExecutionLogResponse])
async def get_latest_execution_log(task_key: str, db: Session = Depends(get_db)):
    """
    获取指定任务最新的执行日志
    用于前端看板快速展示最近一次执行结果
    """
    log = db.query(TaskExecutionLog).filter(
        TaskExecutionLog.task_key == task_key
    ).order_by(desc(TaskExecutionLog.start_time)).first()
    return log
