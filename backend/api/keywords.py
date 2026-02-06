# -*- coding: utf-8 -*-
"""
关键词管理API - 架构修正版
1. 修复路由双重嵌套导致的 404 错误
2. 实现软删除机制，保护关联文章不丢失
"""

from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database.models import Project, Keyword, QuestionVariant
from backend.services.keyword_service import KeywordService
from backend.schemas import ApiResponse
from loguru import logger

# 🌟 路由前缀已经是 /api/keywords 了
router = APIRouter(prefix="/api/keywords", tags=["关键词管理"])


# ==================== 请求/响应模型 ====================

class ProjectCreate(BaseModel):
    name: str
    company_name: str
    domain_keyword: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    company_name: str
    domain_keyword: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KeywordCreate(BaseModel):
    project_id: int
    keyword: str
    difficulty_score: Optional[int] = None


class KeywordResponse(BaseModel):
    id: int
    project_id: int
    keyword: str
    difficulty_score: Optional[int] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuestionVariantResponse(BaseModel):
    id: int
    keyword_id: int
    question: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DistillRequest(BaseModel):
    project_id: int
    core_kw: Optional[str] = None
    target_info: Optional[str] = None
    prefixes: Optional[str] = None
    suffixes: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    count: int = 10


class GenerateQuestionsRequest(BaseModel):
    keyword_id: int
    count: int = 3


# ==================== 项目API ====================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.status != 0).order_by(Project.created_at.desc()).all()
    return projects


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=project_data.name,
        company_name=project_data.company_name,
        domain_keyword=project_data.domain_keyword,
        description=project_data.description,
        industry=project_data.industry,
        status=1
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info(f"项目已创建: {project.name}")
    return project


@router.get("/projects/{project_id}/keywords", response_model=List[KeywordResponse])
async def get_project_keywords(project_id: int, db: Session = Depends(get_db)):
    """获取项目关键词（排除已软删除的）"""
    keywords = db.query(Keyword).filter(
        Keyword.project_id == project_id,
        Keyword.status != "deleted"  # 🌟 关键：不显示回收站里的词
    ).order_by(Keyword.created_at.desc()).all()
    return keywords


# ==================== 关键词业务API ====================

@router.post("/distill", response_model=ApiResponse)
async def distill_keywords(request: DistillRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    service = KeywordService(db)
    core_kw = (request.core_kw or "").strip() or (project.domain_keyword or "").strip()
    target_info = (request.target_info or "").strip() or (request.company_name or "").strip() or (
                project.company_name or "").strip()

    result = await service.distill(
        core_kw=core_kw,
        target_info=target_info,
        prefixes=(request.prefixes or "").strip(),
        suffixes=(request.suffixes or "").strip(),
        company_name=(request.company_name or "").strip(),
        industry=(request.industry or "").strip(),
        description=(request.description or "").strip(),
        count=request.count,
    )

    if result.get("status") == "error":
        return ApiResponse(success=False, message=result.get("message", "蒸馏失败"))

    keywords_data = result.get("keywords", [])
    saved_keywords = []
    for kw_data in keywords_data:
        keyword = service.add_keyword(
            project_id=request.project_id,
            keyword=kw_data.get("keyword", ""),
            difficulty_score=kw_data.get("difficulty_score")
        )
        saved_keywords.append({"id": keyword.id, "keyword": keyword.keyword})

    return ApiResponse(success=True, message=f"成功蒸馏{len(saved_keywords)}个词", data={"keywords": saved_keywords})


@router.post("/generate-questions", response_model=ApiResponse)
async def generate_questions(request: GenerateQuestionsRequest, db: Session = Depends(get_db)):
    keyword = db.query(Keyword).filter(Keyword.id == request.keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    service = KeywordService(db)
    questions = await service.generate_questions(keyword=keyword.keyword, count=request.count)

    saved_questions = []
    for question in questions:
        qv = service.add_question_variant(keyword_id=request.keyword_id, question=question)
        saved_questions.append({"id": qv.id, "question": qv.question})

    return ApiResponse(success=True, message="生成完成", data={"questions": saved_questions})


@router.post("/projects/{project_id}/keywords", response_model=KeywordResponse, status_code=201)
async def create_keyword(project_id: int, keyword_data: KeywordCreate, db: Session = Depends(get_db)):
    keyword = Keyword(
        project_id=project_id,
        keyword=keyword_data.keyword,
        difficulty_score=keyword_data.difficulty_score,
        status="active"
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


# 🌟 修复：去掉多余的 /keywords，路径变为 /api/keywords/{id}/questions
@router.get("/{keyword_id}/questions", response_model=List[QuestionVariantResponse])
async def get_keyword_questions(keyword_id: int, db: Session = Depends(get_db)):
    questions = db.query(QuestionVariant).filter(
        QuestionVariant.keyword_id == keyword_id
    ).order_by(QuestionVariant.created_at.desc()).all()
    return questions


# 🌟 修复：去掉多余的 /keywords，路径变为 /api/keywords/{id}
@router.delete("/{keyword_id}", response_model=ApiResponse)
async def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """
    [软删除] 删除关键词
    路径修正为: DELETE /api/keywords/{id}
    """
    logger.info(f"收到软删除请求，关键词ID: {keyword_id}")
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 软删除逻辑：修改状态，保留数据，防止文章关联丢失
    keyword.status = "deleted"
    db.commit()

    logger.success(f"关键词已软删除，ID: {keyword_id} (关联文章已安全保留)")
    return ApiResponse(success=True, message="关键词已移至回收站")