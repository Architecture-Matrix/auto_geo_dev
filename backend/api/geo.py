# -*- coding: utf-8 -*-
"""
GEO文章管理 API - 工业加固版
处理文章生成、质检、列表、收录检测触发等
"""

from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db, SessionLocal
from backend.services.geo_article_service import GeoArticleService
from backend.database.models import GeoArticle, Project
from backend.schemas import ApiResponse
from backend.config import N8N_CALLBACK_URL
from loguru import logger

router = APIRouter(prefix="/api/geo", tags=["GEO文章"])


# ==================== 请求/响应模型 ====================

class GenerateArticleRequest(BaseModel):
    """文章生成请求模型"""
    keyword_id: int
    company_name: str


class ArticleCallbackRequest(BaseModel):
    """
    n8n异步回调请求模型
    n8n生成完成后将结果通过此接口回调
    """
    article_id: int = Field(..., description="文章ID，用于关联更新对应记录")
    title: Optional[str] = Field(None, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")
    seo_score: Optional[int] = Field(None, description="SEO评分")
    quality_score: Optional[int] = Field(None, description="质量评分")
    error: Optional[str] = Field(None, description="错误信息，如果生成失败")
    status: Optional[str] = Field("success", description="生成状态")


class ArticleResponse(BaseModel):
    """
    🌟 核心模型：解决前端列表显示的所有字段需求
    """
    id: int
    keyword_id: int
    title: Optional[str] = None
    content: Optional[str] = None

    # 状态字段
    quality_status: Optional[str] = "pending"
    publish_status: Optional[str] = "draft"
    index_status: Optional[str] = "uncheck"
    platform: Optional[str] = "zhihu"

    # 评分字段
    quality_score: Optional[int] = None
    ai_score: Optional[int] = None
    readability_score: Optional[int] = None

    # 记录与日志
    retry_count: Optional[int] = 0
    error_msg: Optional[str] = None
    publish_logs: Optional[str] = None
    platform_url: Optional[str] = None  # 🌟 发布成功后的真实链接
    index_details: Optional[str] = None

    # 时间戳
    publish_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # 兼容 SQLAlchemy 对象
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: int
    name: str
    company_name: str
    model_config = ConfigDict(from_attributes=True)


# ==================== 异步辅助逻辑 ====================

async def run_generate_task(keyword_id: int, company_name: str):
    """后台执行生成任务的闭包"""
    db = SessionLocal()
    try:
        service = GeoArticleService(db)
        await service.generate(keyword_id, company_name)
    except Exception as e:
        logger.error(f"❌ 后台生成任务失败: {str(e)}")
    finally:
        db.close()


# ==================== 接口实现 ====================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """获取所有活跃项目列表"""
    return db.query(Project).filter(Project.status == 1).all()


@router.post("/generate", response_model=ApiResponse)
async def generate_article(request: GenerateArticleRequest, background_tasks: BackgroundTasks):
    """
    提交文章生成任务
    使用 BackgroundTasks 实现非阻塞响应
    """
    background_tasks.add_task(
        run_generate_task,
        request.keyword_id,
        request.company_name
    )
    return ApiResponse(success=True, message="生成任务已提交，请在列表查看进度")


@router.get("/articles", response_model=List[ArticleResponse])
async def list_articles(
    limit: int = Query(100),
    publish_status: Optional[str] = Query(None, description="发布状态过滤: generating/scheduled/publishing/published/failed"),
    db: Session = Depends(get_db)
):
    """
    获取文章列表（按创建时间倒序）
    支持按 publish_status 过滤，用于批量发布时只获取待发布的文章
    """
    query = db.query(GeoArticle).order_by(desc(GeoArticle.created_at))

    # 如果指定了状态，进行过滤
    if publish_status:
        query = query.filter(GeoArticle.publish_status == publish_status)

    # 应用分页限制
    if limit:
        query = query.limit(limit)

    articles = query.all()
    return articles


@router.post("/articles/{article_id}/check-quality", response_model=ApiResponse)
async def check_quality(article_id: int, db: Session = Depends(get_db)):
    """
    🌟 [修复] 手动触发文章质检评分
    """
    service = GeoArticleService(db)
    try:
        result = await service.check_quality(article_id)
        if result.get("success"):
            return ApiResponse(success=True, message="质检完成", data=result)
        return ApiResponse(success=False, message=result.get("message", "质检失败"))
    except Exception as e:
        logger.error(f"质检异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/{article_id}/check-index", response_model=ApiResponse)
async def manual_check_index(article_id: int, db: Session = Depends(get_db)):
    """手动触发单篇文章的收录监测"""
    service = GeoArticleService(db)
    try:
        result = await service.check_article_index(article_id)
        if result.get("status") == "error":
            return ApiResponse(success=False, message=result.get("message"))
        return ApiResponse(success=True, message=f"检测完成，当前状态：{result.get('index_status')}")
    except Exception as e:
        logger.error(f"收录检测异常: {str(e)}")
        return ApiResponse(success=False, message="检测服务暂时不可用")


@router.delete("/articles/{article_id}", response_model=ApiResponse)
async def delete_article(article_id: int, db: Session = Depends(get_db)):
    """删除文章记录"""
    article = db.query(GeoArticle).filter(GeoArticle.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    try:
        db.delete(article)
        db.commit()
        return ApiResponse(success=True, message="文章已成功删除")
    except Exception as e:
        db.rollback()
        return ApiResponse(success=False, message=f"删除失败: {str(e)}")


@router.post("/callback", response_model=ApiResponse)
async def handle_n8n_callback(request: ArticleCallbackRequest, db: Session = Depends(get_db)):
    """
    接收 n8n 异步回调接口
    n8n生成完成后调用此接口更新文章内容
    """
    logger.info(f"📨 收到 n8n 回调: article_id={request.article_id}, status={request.status}")

    # 1. 查找文章记录
    article = db.query(GeoArticle).filter(GeoArticle.id == request.article_id).first()
    if not article:
        logger.warning(f"⚠️ 回调文章不存在: article_id={request.article_id}")
        raise HTTPException(status_code=404, detail=f"文章 ID {request.article_id} 不存在")

    # 2. 根据回调状态更新文章
    if request.status == "success" or request.error is None:
        # 生成成功：更新内容和状态
        if request.title:
            article.title = request.title
            logger.info(f"✅ 更新标题: {request.title}")

        if request.content:
            article.content = request.content
            logger.info(f"✅ 更新内容 (长度: {len(request.content)})")

        # 更新评分（如果有）
        if request.quality_score:
            article.quality_score = request.quality_score
            article.quality_status = "passed"
            logger.info(f"✅ 更新质量评分: {request.quality_score}")

        if request.seo_score:
            article.ai_score = request.seo_score
            logger.info(f"✅ 更新SEO评分: {request.seo_score}")

        # 将状态改为 scheduled（待发布），等待用户手动触发发布或调度器处理
        article.publish_status = "scheduled"
        article.error_msg = None
        article.publish_time = datetime.now()

        db.commit()
        logger.success(f"✅ 文章 {article.id} 生成完成，状态已更新为 scheduled")

    else:
        # 生成失败：记录错误信息
        article.publish_status = "failed"
        article.error_msg = request.error or "n8n生成失败"
        db.commit()
        logger.error(f"❌ 文章 {article.id} 生成失败: {request.error}")

    return ApiResponse(success=True, message="回调处理完成")