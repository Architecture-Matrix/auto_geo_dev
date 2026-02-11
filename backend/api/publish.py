# -*- coding: utf-8 -*-
"""
发布管理 API
用这个接口来处理文章发布！
"""

import asyncio
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger
from pydantic import BaseModel

from backend.database import get_db
from backend.database.models import PublishRecord, Account, Article, GeoArticle
from backend.schemas import (
    ApiResponse,
    PublishTaskCreate,
    PublishTaskResponse,
    PublishProgressResponse,
    PublishProgressItem,
    PublishStatus,
)
from backend.config import PLATFORMS


router = APIRouter(prefix="/api/publish", tags=["发布管理"])


# ==================== 任务状态管理（内存存储） ====================
class PublishTaskManager:
    """
    发布任务管理器
    用这个来跟踪批量发布任务！
    """
    def __init__(self):
        self._tasks: dict = {}  # task_id -> task_info

    def create_task(self, article_ids: List[int], account_ids: List[int]) -> str:
        """创建批量发布任务"""
        task_id = str(uuid.uuid4())
        # 生成所有子任务组合
        sub_tasks = []
        for article_id in article_ids:
            for account_id in account_ids:
                sub_tasks.append({
                    "article_id": article_id,
                    "account_id": account_id,
                    "status": PublishStatus.PENDING,  # 0=待发布
                    "platform_url": None,
                    "error_msg": None,
                })

        self._tasks[task_id] = {
            "task_id": task_id,
            "total": len(sub_tasks),
            "completed": 0,
            "failed": 0,
            "sub_tasks": sub_tasks,
        }
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def update_sub_task(self, task_id: str, article_id: int, account_id: int,
                       status: int, platform_url: Optional[str] = None,
                       error_msg: Optional[str] = None):
        """更新子任务状态"""
        task = self._tasks.get(task_id)
        if not task:
            return

        for sub_task in task["sub_tasks"]:
            if sub_task["article_id"] == article_id and sub_task["account_id"] == account_id:
                sub_task["status"] = status
                sub_task["platform_url"] = platform_url
                sub_task["error_msg"] = error_msg

                # 更新计数
                if status == PublishStatus.SUCCESS:  # 2=成功
                    task["completed"] += 1
                elif status == PublishStatus.FAILED:  # 3=失败
                    task["failed"] += 1
                break


# 全局任务管理器实例
publish_task_manager = PublishTaskManager()

# WebSocket管理器（由main.py设置）
_ws_manager = None

def set_ws_manager(ws_mgr):
    """设置WebSocket管理器，避免循环导入"""
    global _ws_manager
    _ws_manager = ws_mgr

def get_ws_manager():
    """获取WebSocket管理器"""
    return _ws_manager


# ==================== 导入发布服务 ====================
def get_publish_manager():
    """延迟导入，避免循环依赖"""
    from backend.services.playwright_mgr import PublishManager, playwright_mgr
    return PublishManager(PLATFORMS)


# ==================== API接口 ====================

@router.get("/platforms", response_model=ApiResponse)
async def get_supported_platforms():
    """
    获取支持的发布平台

    用这个接口来告诉前端有哪些平台可以用！
    """
    platforms = []
    for platform_id, config in PLATFORMS.items():
        platforms.append({
            "id": platform_id,
            "name": config.get("name", platform_id),
            "code": config.get("code", ""),
            "color": config.get("color", "#333333"),
            "enabled": True,  # 暂时都启用
        })

    return ApiResponse(data={"platforms": platforms})


@router.post("/create", response_model=ApiResponse)
async def create_publish_task(
    request: PublishTaskCreate,
    db: Session = Depends(get_db),
):
    """
    创建发布任务

    用这个接口来启动批量发布！
    """
    # 1. 验证文章和账号是否存在
    articles = db.query(Article).filter(Article.id.in_(request.article_ids)).all()
    if len(articles) != len(request.article_ids):
        found_ids = [a.id for a in articles]
        missing = set(request.article_ids) - set(found_ids)
        raise HTTPException(status_code=404, detail=f"文章不存在: {missing}")

    accounts = db.query(Account).filter(Account.id.in_(request.account_ids)).all()
    if len(accounts) != len(request.account_ids):
        found_ids = [a.id for a in accounts]
        missing = set(request.account_ids) - set(found_ids)
        raise HTTPException(status_code=404, detail=f"账号不存在: {missing}")

    # 2. 检查账号状态
    disabled_accounts = [a.account_name for a in accounts if a.status != 1]
    if disabled_accounts:
        raise HTTPException(
            status_code=400,
            detail=f"以下账号未授权或已禁用: {', '.join(disabled_accounts)}"
        )

    # 3. 创建批量发布任务
    task_id = publish_task_manager.create_task(request.article_ids, request.account_ids)

    # 4. 创建发布记录（待发布状态）
    for article_id in request.article_ids:
        for account_id in request.account_ids:
            # 检查是否已有发布记录
            existing = db.query(PublishRecord).filter(
                PublishRecord.article_id == article_id,
                PublishRecord.account_id == account_id
            ).first()

            if not existing:
                record = PublishRecord(
                    article_id=article_id,
                    account_id=account_id,
                    publish_status=0,  # 待发布
                )
                db.add(record)

    db.commit()

    # 5. 后台执行发布任务
    # 注意：用asyncio.create_task而不是BackgroundTasks，因为要运行async函数！
    asyncio.create_task(execute_publish_task(task_id, articles, accounts))

    logger.info(f"发布任务已创建: {task_id}, 文章数: {len(articles)}, 账号数: {len(accounts)}")

    return ApiResponse(data={
        "task_id": task_id,
        "total_tasks": len(articles) * len(accounts),
        "message": "发布任务已创建，正在后台执行"
    })


async def execute_publish_task(task_id: str, articles: List[Article],
                               accounts: List[Account]):
    """
    执行发布任务（后台异步任务）

    注意：这个函数在事件循环中运行！
    """
    from backend.services.playwright_mgr import PublishManager, playwright_mgr

    # 获取发布管理器
    publish_mgr = PublishManager(PLATFORMS)

    # 创建所有子任务
    tasks = []
    for article in articles:
        for account in accounts:
            sub_task_id = f"{task_id}_{article.id}_{account.id}"
            task = await publish_mgr.create_task(sub_task_id, article, account)
            tasks.append(task)

    # 进度回调
    async def progress_callback(completed: int, total: int, task):
        """更新进度到数据库和任务管理器"""
        # 更新内存中的任务状态
        article_id = task.article.id
        account_id = task.account.id

        if task.status == "success":
            status = PublishStatus.SUCCESS
            platform_url = task.result.get("platform_url") if task.result else None
            error_msg = None
        elif task.status == "failed":
            status = PublishStatus.FAILED
            platform_url = None
            error_msg = task.error_message or task.result.get("error_msg") if task.result else "未知错误"
        else:
            return

        publish_task_manager.update_sub_task(
            task_id, article_id, account_id, status, platform_url, error_msg
        )

        # 更新数据库记录
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            record = db.query(PublishRecord).filter(
                PublishRecord.article_id == article_id,
                PublishRecord.account_id == account_id
            ).first()

            if record:
                record.publish_status = status
                record.platform_url = platform_url
                record.error_msg = error_msg
                if status == PublishStatus.SUCCESS:
                    from datetime import datetime
                    record.published_at = datetime.now()

                db.commit()

                # 更新文章发布时间（首次发布）
                if status == PublishStatus.SUCCESS:
                    article = db.query(Article).filter(Article.id == article_id).first()
                    if article and not article.published_at:
                        from datetime import datetime
                        article.published_at = datetime.now()
                    if article and article.status == 0:
                        article.status = 1
                    db.commit()

            # 获取账号和文章信息用于推送
            account_obj = db.query(Account).filter(Account.id == account_id).first()
            article_obj = db.query(Article).filter(Article.id == article_id).first()

            if account_obj and article_obj:
                from backend.config import PLATFORMS
                platform_config = PLATFORMS.get(account_obj.platform, {})

                # 推送WebSocket进度更新
                ws_mgr = get_ws_manager()
                if ws_mgr:
                    await ws_mgr.broadcast({
                        "type": "publish_progress",
                        "task_id": task_id,
                        "data": {
                            "article_id": article_id,
                            "article_title": article_obj.title,
                            "account_id": account_id,
                            "account_name": account_obj.account_name,
                            "platform": account_obj.platform,
                            "platform_name": platform_config.get("name", account_obj.platform),
                            "status": status,
                            "platform_url": platform_url,
                            "error_msg": error_msg,
                        }
                    })

        except Exception as e:
            logger.error(f"更新发布记录失败: {e}")
            db.rollback()
        finally:
            db.close()

    # 批量执行
    try:
        await publish_mgr.execute_batch(tasks, progress_callback)
        logger.info(f"发布任务完成: {task_id}")
    except Exception as e:
        logger.error(f"发布任务执行失败: {task_id}, {e}")


@router.get("/progress/{task_id}", response_model=ApiResponse)
async def get_publish_progress(task_id: str, db: Session = Depends(get_db)):
    """
    获取发布进度

    用这个接口来查询发布状态！
    """
    task_info = publish_task_manager.get_task(task_id)

    if not task_info:
        # 尝试从数据库获取历史记录
        records = db.query(PublishRecord).order_by(
            PublishRecord.created_at.desc()
        ).limit(100).all()

        # 如果找不到任务，返回空
        return ApiResponse(
            success=False,
            message="任务不存在或已过期",
            data={"task_id": task_id, "total": 0, "completed": 0, "failed": 0, "items": []}
        )

    # 获取详细信息
    items = []
    for sub_task in task_info["sub_tasks"]:
        article = db.query(Article).filter(Article.id == sub_task["article_id"]).first()
        account = db.query(Account).filter(Account.id == sub_task["account_id"]).first()

        if not article or not account:
            continue

        platform_config = PLATFORMS.get(account.platform, {})
        items.append(PublishProgressItem(
            id=sub_task.get("id", 0),
            article_id=article.id,
            article_title=article.title,
            account_id=account.id,
            account_name=account.account_name,
            platform=account.platform,
            platform_name=platform_config.get("name", account.platform),
            status=sub_task["status"],
            platform_url=sub_task.get("platform_url"),
            error_msg=sub_task.get("error_msg"),
            created_at=article.created_at,
            published_at=None,
        ))

    return ApiResponse(data={
        "task_id": task_id,
        "total": task_info["total"],
        "completed": task_info["completed"],
        "failed": task_info["failed"],
        "items": items,
    })


@router.get("/records", response_model=List[dict])
async def get_publish_records(
    article_id: Optional[int] = Query(None, description="文章ID"),
    account_id: Optional[int] = Query(None, description="账号ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    获取发布记录

    用这个接口来查看历史发布记录！
    """
    query = db.query(PublishRecord)

    if article_id is not None:
        query = query.filter(PublishRecord.article_id == article_id)
    if account_id is not None:
        query = query.filter(PublishRecord.account_id == account_id)

    records = query.order_by(PublishRecord.created_at.desc()).limit(limit).all()

    # 转换为字典列表
    result = []
    for record in records:
        article = db.query(Article).filter(Article.id == record.article_id).first()
        account = db.query(Account).filter(Account.id == record.account_id).first()

        platform_name = ""
        if account:
            platform_config = PLATFORMS.get(account.platform, {})
            platform_name = platform_config.get("name", account.platform)

        result.append({
            "id": record.id,
            "article_id": record.article_id,
            "article_title": article.title if article else "",
            "account_id": record.account_id,
            "account_name": account.account_name if account else "",
            "platform": account.platform if account else "",
            "platform_name": platform_name,
            "status": record.publish_status,
            "platform_url": record.platform_url,
            "error_msg": record.error_msg,
            "retry_count": record.retry_count,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "published_at": record.published_at.isoformat() if record.published_at else None,
        })

    return result


@router.post("/retry/{record_id}", response_model=ApiResponse)
async def retry_publish(
    record_id: int,
    db: Session = Depends(get_db),
):
    """
    重试发布

    用这个接口来重新发布失败的任务！
    """
    # 1. 查找发布记录
    record = db.query(PublishRecord).filter(PublishRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="发布记录不存在")

    # 2. 检查是否已经成功
    if record.publish_status == 2:  # 2=成功
        return ApiResponse(success=False, message="该记录已发布成功，无需重试")

    # 3. 获取文章和账号
    article = db.query(Article).filter(Article.id == record.article_id).first()
    account = db.query(Account).filter(Account.id == record.account_id).first()

    if not article or not account:
        raise HTTPException(status_code=404, detail="文章或账号不存在")

    # 4. 检查账号状态
    if account.status != 1:
        raise HTTPException(status_code=400, detail="账号未授权或已禁用")

    # 5. 更新重试次数
    record.retry_count += 1
    record.publish_status = 0  # 重置为待发布
    record.error_msg = None
    db.commit()

    # 6. 创建重试任务
    task_id = publish_task_manager.create_task([article.id], [account.id])

    # 7. 后台执行
    asyncio.create_task(execute_publish_task(task_id, [article], [account]))

    logger.info(f"重试发布任务已创建: {task_id}, 记录ID: {record_id}")

    return ApiResponse(data={
        "task_id": task_id,
        "record_id": record_id,
        "retry_count": record.retry_count,
        "message": "重试任务已创建"
    })


# ==================== 批量发布接口（针对 GeoArticle） ====================

class BatchPublishRequest(BaseModel):
    """批量发布请求模型（针对 GeoArticle）"""
    article_ids: List[int]
    account_ids: List[int]
    # 每篇文章可以指定不同的平台和账号组合
    # 格式: [{"article_id": 1, "platform": "zhihu", "account_id": 2}, ...]
    # 简化版：直接使用 account_ids，平台由账号决定
    scheduled_time: Optional[str] = None


@router.post("/batch", response_model=ApiResponse)
async def batch_publish_geo_articles(
    request: BatchPublishRequest,
    db: Session = Depends(get_db),
):
    """
    批量发布 GEO 文章

    文章生成阶段已与平台解耦，发布时需要为每篇文章选择平台和账号
    """
    # 1. 验证文章和账号是否存在
    geo_articles = db.query(GeoArticle).filter(GeoArticle.id.in_(request.article_ids)).all()
    if len(geo_articles) != len(request.article_ids):
        found_ids = [a.id for a in geo_articles]
        missing = set(request.article_ids) - set(found_ids)
        raise HTTPException(status_code=404, detail=f"文章不存在: {missing}")

    accounts = db.query(Account).filter(Account.id.in_(request.account_ids)).all()
    if len(accounts) != len(request.account_ids):
        found_ids = [a.id for a in accounts]
        missing = set(request.account_ids) - set(found_ids)
        raise HTTPException(status_code=404, detail=f"账号不存在: {missing}")

    # 2. 检查账号状态和文章状态
    disabled_accounts = [a.account_name for a in accounts if a.status != 1]
    invalid_articles = [a.title for a in geo_articles if a.publish_status != "scheduled"]

    if disabled_accounts:
        raise HTTPException(
            status_code=400,
            detail=f"以下账号未授权或已禁用: {', '.join(disabled_accounts)}"
        )

    if invalid_articles:
        raise HTTPException(
            status_code=400,
            detail=f"以下文章尚未生成完成: {', '.join(invalid_articles[:3])}{'...' if len(invalid_articles) > 3 else ''}"
        )

    # 3. 为每篇文章绑定选中的平台和账号，更新状态为 publishing
    # 同时创建发布记录
    publish_records = []
    task_subtasks = []

    for article in geo_articles:
        for account in accounts:
            # 更新文章状态和平台
            article.platform = account.platform
            article.publish_status = "publishing"

            # 检查是否已有发布记录
            existing = db.query(PublishRecord).filter(
                PublishRecord.article_id == article.id,
                PublishRecord.account_id == account.id
            ).first()

            if not existing:
                record = PublishRecord(
                    article_id=article.id,
                    account_id=account.id,
                    publish_status=0,  # 待发布
                )
                db.add(record)
                publish_records.append(record)

            # 添加到任务子任务列表
            task_subtasks.append({
                "article_id": article.id,
                "account_id": account.id,
                "platform": account.platform,
                "status": 0,  # 待发布
                "platform_url": None,
                "error_msg": None,
            })

    db.commit()

    # 4. 创建发布任务
    task_id = publish_task_manager.create_task(request.article_ids, request.account_ids)

    # 5. 创建异步进度更新函数
    async def update_task_progress(completed: int, total: int):
        await update_publish_progress(task_id, completed, total, task_subtasks[completed] if completed < len(task_subtasks) else None)

    # 6. 后台执行发布任务
    try:
        await publish_mgr.execute_batch(task_subtasks, update_task_progress)
        logger.info(f"批量发布任务完成: {task_id}")
    except Exception as e:
        logger.error(f"批量发布任务执行失败: {task_id}, {e}")
        # 更新失败状态
        for article in geo_articles:
            if article.publish_status == "publishing":
                article.publish_status = "failed"
                article.error_msg = str(e)
        db.commit()


async def update_publish_progress(task_id: str, completed: int, total: int, task: dict):
    """
    更新发布进度并推送 WebSocket 消息
    """
    # 更新任务管理器中的进度
    if task is None:
        return

    # 更新数据库中的发布记录
    from backend.database import SessionLocal
    from datetime import datetime

    db = SessionLocal()
    try:
        record = db.query(PublishRecord).filter(
            PublishRecord.article_id == task["article_id"],
            PublishRecord.account_id == task["account_id"]
        ).first()

        if record:
            # 更新记录状态
            if completed >= total:
                # 全部完成
                record.publish_status = 2  # 成功
                record.published_at = datetime.now()
            else:
                record.publish_status = 0  # 待发布
            db.commit()

            # 更新文章状态
            article = db.query(GeoArticle).filter(GeoArticle.id == task["article_id"]).first()
            if article:
                article.publish_status = "published" if completed >= total else "publishing"
                article.published_at = datetime.now() if completed >= total else None
                if task.get("platform_url"):
                    article.platform_url = task["platform_url"]
                if task.get("error_msg"):
                    article.error_msg = task["error_msg"]
                db.commit()

                # 推送 WebSocket 进度更新
                ws_mgr = get_ws_manager()
                if ws_mgr:
                    await ws_mgr.broadcast({
                        "type": "publish_progress",
                        "task_id": task_id,
                        "data": {
                            "article_id": task["article_id"],
                            "article_title": article.title,
                            "account_id": task["account_id"],
                            "platform": task.get("platform"),
                            "status": record.publish_status,
                            "platform_url": task.get("platform_url"),
                            "error_msg": task.get("error_msg"),
                            "completed": completed,
                            "total": total,
                        }
                    })
    finally:
        db.close()
