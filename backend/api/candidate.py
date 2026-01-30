# -*- coding: utf-8 -*-
"""
候选人管理API
用这个来管理AI招聘候选人数据！
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from backend.database import get_db
from backend.database.models import Candidate, Article
from backend.schemas import ApiResponse


router = APIRouter(prefix="/api/candidates", tags=["候选人管理"])


@router.get("", response_model=dict)
async def get_candidates(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[int] = Query(None, description="状态筛选"),
    is_send: Optional[bool] = Query(None, description="是否已发送"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: Session = Depends(get_db)
):
    """
    获取候选人列表

    支持分页、状态筛选、发送状态筛选、关键词搜索
    """
    query = db.query(Candidate)

    if status is not None:
        query = query.filter(Candidate.status == status)

    if is_send is not None:
        query = query.filter(Candidate.is_send == is_send)

    if keyword:
        query = query.filter(Candidate.uid.contains(keyword))

    # 统计总数
    total = query.count()

    # 分页查询
    candidates = query.order_by(Candidate.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    # 序列化结果
    items = []
    for c in candidates:
        item = {
            "id": c.id,
            "uid": c.uid,
            "detail": json.loads(c.detail) if c.detail else None,
            "attached": json.loads(c.attached) if c.attached else None,
            "is_send": c.is_send,
            "article_id": c.article_id,
            "status": c.status,
            "remark": c.remark,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
        }
        items.append(item)

    return {
        "success": True,
        "total": total,
        "items": items,
        "page": page,
        "limit": limit
    }


@router.get("/{candidate_id}", response_model=dict)
async def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """获取候选人详情"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    return {
        "success": True,
        "data": {
            "id": candidate.id,
            "uid": candidate.uid,
            "detail": json.loads(candidate.detail) if candidate.detail else None,
            "attached": json.loads(candidate.attached) if candidate.attached else None,
            "is_send": candidate.is_send,
            "article_id": candidate.article_id,
            "status": candidate.status,
            "remark": candidate.remark,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
            "sent_at": candidate.sent_at.isoformat() if candidate.sent_at else None,
        }
    }


@router.post("/sync", response_model=ApiResponse)
async def sync_candidate(data: dict, db: Session = Depends(get_db)):
    """
    同步候选人数据（n8n webhook调用）

    n8n 工作流筛选候选人后调用此接口保存数据
    """
    uid = data.get("uid")
    if not uid:
        raise HTTPException(status_code=400, detail="缺少 uid")

    # 检查是否已存在
    candidate = db.query(Candidate).filter(Candidate.uid == uid).first()

    try:
        if candidate:
            # 更新
            candidate.detail = json.dumps(data.get("detail"), ensure_ascii=False)
            candidate.attached = json.dumps(data.get("attached"), ensure_ascii=False)
            logger.info(f"候选人已更新: {uid}")
        else:
            # 新建
            candidate = Candidate(
                uid=uid,
                detail=json.dumps(data.get("detail"), ensure_ascii=False),
                attached=json.dumps(data.get("attached"), ensure_ascii=False),
                is_send=data.get("is_send", False)
            )
            db.add(candidate)
            logger.info(f"新候选人已创建: {uid}")

        db.commit()
        db.refresh(candidate)

        return ApiResponse(success=True, message="同步成功", data={"candidate_id": candidate.id})

    except Exception as e:
        db.rollback()
        logger.error(f"同步候选人失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/{candidate_id}/send", response_model=ApiResponse)
async def send_to_candidate(
    candidate_id: int,
    article_id: int,
    db: Session = Depends(get_db)
):
    """
    发送文章给候选人

    标记候选人为已发送，并关联文章
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    # 验证文章存在
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    try:
        candidate.is_send = True
        candidate.article_id = article_id
        candidate.sent_at = func.now()

        db.commit()
        db.refresh(candidate)

        logger.info(f"已发送文章 {article_id} 给候选人 {candidate_id}")
        return ApiResponse(
            success=True,
            message="发送成功",
            data={
                "candidate_id": candidate.id,
                "article_id": article_id,
                "article_title": article.title
            }
        )

    except Exception as e:
        db.rollback()
        logger.error(f"发送失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")


@router.put("/{candidate_id}", response_model=ApiResponse)
async def update_candidate(
    candidate_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    """更新候选人信息"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    # 更新字段
    if "detail" in data:
        candidate.detail = json.dumps(data["detail"], ensure_ascii=False)
    if "attached" in data:
        candidate.attached = json.dumps(data["attached"], ensure_ascii=False)
    if "is_send" in data:
        candidate.is_send = data["is_send"]
    if "article_id" in data:
        candidate.article_id = data["article_id"]
    if "status" in data:
        candidate.status = data["status"]
    if "remark" in data:
        candidate.remark = data["remark"]

    db.commit()
    db.refresh(candidate)

    logger.info(f"候选人已更新: {candidate_id}")
    return ApiResponse(success=True, message="更新成功")


@router.delete("/{candidate_id}", response_model=ApiResponse)
async def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """删除候选人"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="候选人不存在")

    db.delete(candidate)
    db.commit()

    logger.info(f"候选人已删除: {candidate_id}")
    return ApiResponse(success=True, message="删除成功")


@router.get("/stats/overview", response_model=dict)
async def get_stats(db: Session = Depends(get_db)):
    """获取候选人统计信息"""
    total = db.query(Candidate).count()
    sent = db.query(Candidate).filter(Candidate.is_send == True).count()
    pending = total - sent

    return {
        "success": True,
        "data": {
            "total": total,
            "sent": sent,
            "pending": pending,
            "send_rate": round(sent / total * 100, 2) if total > 0 else 0
        }
    }
