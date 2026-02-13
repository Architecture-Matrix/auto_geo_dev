# -*- coding: utf-8 -*-
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.models import ScheduledTask
from backend.services.scheduler_service import get_scheduler_service
from backend.schemas import ApiResponse

router = APIRouter(prefix="/api/scheduler", tags=["定时任务管理"])


# --- Schema ---
class TaskUpdate(BaseModel):
    cron_expression: str
    is_active: bool


class TaskResponse(BaseModel):
    id: int
    name: str
    task_key: str
    cron_expression: str
    is_active: bool
    description: Optional[str] = None

    class Config:
        from_attributes = True


# --- API ---

@router.get("/jobs", response_model=List[TaskResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """获取所有定时任务配置"""
    return db.query(ScheduledTask).all()


@router.put("/jobs/{task_id}", response_model=ApiResponse)
async def update_job(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    """更新任务配置（Cron或开关）"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        return ApiResponse(success=False, message="任务不存在")

    # 更新数据库
    task.cron_expression = data.cron_expression
    task.is_active = data.is_active
    db.commit()

    # 🌟 关键：通知调度器热重载该任务
    scheduler = get_scheduler_service()
    scheduler.reload_task(task_id)

    return ApiResponse(success=True, message="任务配置已更新并生效")


@router.post("/jobs/{job_id}/run", response_model=ApiResponse)
async def trigger_job(job_id: str):
    """
    立即触发任务执行

    参数:
        job_id: APScheduler 的 Job ID (task_key，如 "publish_task")

    实现:
        使用 job.modify(next_run_time=datetime.now()) 将任务下一次运行时间设置为现在，
        调度器会立即捡起并执行，且不影响原来的周期计划。
    """
    scheduler = get_scheduler_service()
    success = scheduler.trigger_job(job_id)

    if success:
        return ApiResponse(success=True, message=f"任务 [{job_id}] 已触发执行")
    else:
        raise HTTPException(status_code=404, detail=f"任务 [{job_id}] 不存在或未运行")