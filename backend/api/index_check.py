# -*- coding: utf-8 -*-
"""
收录检测API
写的收录检测API，简单明了！
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.index_check_service import IndexCheckService
from backend.database.models import IndexCheckRecord
from backend.schemas import ApiResponse
from loguru import logger


router = APIRouter(prefix="/api/index-check", tags=["收录检测"])


# ==================== 请求/响应模型 ====================

class CheckRequest(BaseModel):
    """收录检测请求"""
    keyword_id: int
    company_name: str
    platforms: Optional[List[str]] = None


class CheckResultResponse(BaseModel):
    """检测结果响应"""
    platform: str
    question: str
    keyword_found: bool
    company_found: bool
    success: bool


class RecordResponse(BaseModel):
    """检测记录响应"""
    id: int
    keyword_id: int
    platform: str
    question: str
    answer: Optional[str]
    keyword_found: Optional[bool]
    company_found: Optional[bool]
    check_time: str

    class Config:
        from_attributes = True


class HitRateResponse(BaseModel):
    """命中率响应"""
    hit_rate: float
    total: int
    keyword_found: int
    company_found: int


# ==================== 收录检测API ====================

@router.post("/check", response_model=ApiResponse)
async def check_index(
    request: CheckRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    执行收录检测

    调用Playwright自动化检测AI平台收录情况。
    注意：这是一个耗时操作，建议异步执行！
    """
    # 验证关键词存在
    from backend.database.models import Keyword
    keyword = db.query(Keyword).filter(Keyword.id == request.keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    service = IndexCheckService(db)

    # 执行检测
    try:
        results = await service.check_keyword(
            keyword_id=request.keyword_id,
            company_name=request.company_name,
            platforms=request.platforms
        )

        return ApiResponse(
            success=True,
            message=f"检测完成，共{len(results)}条记录",
            data={"results": results}
        )
    except Exception as e:
        logger.error(f"收录检测失败: {e}")
        return ApiResponse(success=False, message=f"检测失败: {str(e)}")


@router.get("/records", response_model=List[RecordResponse])
async def get_records(
    keyword_id: Optional[int] = Query(None, description="关键词ID筛选"),
    platform: Optional[str] = Query(None, description="平台筛选"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    获取检测记录

    注意：返回值按检测时间倒序！
    """
    service = IndexCheckService(db)
    records = service.get_check_records(keyword_id, platform, limit)
    return records


@router.get("/keywords/{keyword_id}/hit-rate", response_model=HitRateResponse)
async def get_hit_rate(keyword_id: int, db: Session = Depends(get_db)):
    """
    获取关键词命中率

    注意：命中率越高，SEO效果越好！
    """
    # 验证关键词存在
    from backend.database.models import Keyword as KwModel
    keyword = db.query(KwModel).filter(KwModel.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    service = IndexCheckService(db)
    return service.get_hit_rate(keyword_id)


@router.get("/records/{record_id}", response_model=RecordResponse)
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """获取检测记录详情"""
    record = db.query(IndexCheckRecord).filter(IndexCheckRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.delete("/records/{record_id}", response_model=ApiResponse)
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    """
    删除检测记录

    注意：删除操作不可恢复！
    """
    record = db.query(IndexCheckRecord).filter(IndexCheckRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(record)
    db.commit()

    logger.info(f"检测记录已删除: {record_id}")
    return ApiResponse(success=True, message="记录已删除")
