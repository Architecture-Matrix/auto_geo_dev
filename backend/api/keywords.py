# -*- coding: utf-8 -*-
"""
关键词管理API
写的关键词API，简单明了！
"""

from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_serializer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database.models import Project, Keyword, QuestionVariant
from backend.services.keyword_service import KeywordService
from backend.schemas import ApiResponse
from loguru import logger


router = APIRouter(prefix="/api/keywords", tags=["关键词管理"])


# ==================== 请求/响应模型 ====================

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str
    company_name: str
    domain_keyword: Optional[str] = None  # 领域关键词，用于关键词蒸馏
    description: Optional[str] = None
    industry: Optional[str] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    id: int
    name: str
    company_name: str
    domain_keyword: Optional[str] = None  # 领域关键词
    description: Optional[str]
    industry: Optional[str]
    status: int
    created_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() if dt else ""

    class Config:
        from_attributes = True


class KeywordCreate(BaseModel):
    """创建关键词请求"""
    project_id: int
    keyword: str
    difficulty_score: Optional[int] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: int
    project_id: int
    keyword: str
    difficulty_score: Optional[int]
    status: str
    created_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() if dt else ""

    class Config:
        from_attributes = True


class QuestionVariantCreate(BaseModel):
    """创建问题变体请求"""
    keyword_id: int
    question: str


class QuestionVariantResponse(BaseModel):
    """问题变体响应"""
    id: int
    keyword_id: int
    question: str
    created_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime) -> str:
        return dt.isoformat() if dt else ""

    class Config:
        from_attributes = True


class DistillRequest(BaseModel):
    """关键词蒸馏请求"""
    project_id: int
    company_name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    count: int = 10


class GenerateQuestionsRequest(BaseModel):
    """生成问题变体请求"""
    keyword_id: int
    count: int = 3


# ==================== 项目API ====================

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """
    获取项目列表

    注意：返回所有活跃项目！
    """
    projects = db.query(Project).filter(Project.status == 1).order_by(Project.created_at.desc()).all()
    return projects


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)):
    """
    创建项目

    注意：项目是关键词的容器！
    """
    project = Project(
        name=project_data.name,
        company_name=project_data.company_name,
        domain_keyword=project_data.domain_keyword,  # 保存领域关键词
        description=project_data.description,
        industry=project_data.industry
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info(f"项目已创建: {project.name}")
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/projects/{project_id}/keywords", response_model=List[KeywordResponse])
async def get_project_keywords(project_id: int, db: Session = Depends(get_db)):
    """
    获取项目的所有关键词

    注意：只返回活跃状态的关键词！
    """
    keywords = db.query(Keyword).filter(
        Keyword.project_id == project_id,
        Keyword.status == "active"
    ).order_by(Keyword.created_at.desc()).all()
    return keywords


# ==================== 关键词API ====================

@router.post("/distill", response_model=ApiResponse)
async def distill_keywords(
    request: DistillRequest,
    db: Session = Depends(get_db)
):
    """
    蒸馏关键词

    调用n8n工作流分析公司信息，返回高价值关键词列表。
    注意：这是AI驱动的核心功能！
    """
    # 验证项目存在
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 调用关键词服务
    service = KeywordService(db)
    result = await service.distill(
        company_name=request.company_name,
        industry=request.industry or "",
        description=request.description or "",
        count=request.count
    )

    if result.get("status") == "error":
        return ApiResponse(success=False, message=result.get("message", "蒸馏失败"))

    # 保存关键词到数据库
    keywords = result.get("keywords", [])
    saved_keywords = []
    for kw_data in keywords:
        keyword = service.add_keyword(
            project_id=request.project_id,
            keyword=kw_data.get("keyword", ""),
            difficulty_score=kw_data.get("difficulty_score")
        )
        saved_keywords.append({
            "id": keyword.id,
            "keyword": keyword.keyword,
            "difficulty_score": keyword.difficulty_score
        })

    return ApiResponse(
        success=True,
        message=f"成功蒸馏{len(saved_keywords)}个关键词",
        data={"keywords": saved_keywords}
    )


@router.post("/generate-questions", response_model=ApiResponse)
async def generate_questions(
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db)
):
    """
    生成问题变体

    基于关键词生成不同的问法，用于后续AI平台收录检测。
    注意：问题变体越多，检测结果越准确！
    """
    # 验证关键词存在
    keyword = db.query(Keyword).filter(Keyword.id == request.keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 调用关键词服务
    service = KeywordService(db)
    questions = await service.generate_questions(
        keyword=keyword.keyword,
        count=request.count
    )

    # 保存问题变体到数据库
    saved_questions = []
    for question in questions:
        qv = service.add_question_variant(
            keyword_id=request.keyword_id,
            question=question
        )
        saved_questions.append({
            "id": qv.id,
            "question": qv.question
        })

    return ApiResponse(
        success=True,
        message=f"成功生成{len(saved_questions)}个问题变体",
        data={"questions": saved_questions}
    )


@router.get("/keywords/{keyword_id}/questions", response_model=List[QuestionVariantResponse])
async def get_keyword_questions(keyword_id: int, db: Session = Depends(get_db)):
    """
    获取关键词的所有问题变体

    注意：返回值用于AI平台收录检测！
    """
    # 验证关键词存在
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    questions = db.query(QuestionVariant).filter(
        QuestionVariant.keyword_id == keyword_id
    ).order_by(QuestionVariant.created_at.desc()).all()
    return questions


@router.delete("/keywords/{keyword_id}", response_model=ApiResponse)
async def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """
    删除关键词（软删除）

    注意：这是软删除，数据不会真正删除！
    """
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    keyword.status = "inactive"
    db.commit()

    logger.info(f"关键词已停用: {keyword_id}")
    return ApiResponse(success=True, message="关键词已停用")


@router.post("/projects/{project_id}/keywords", response_model=KeywordResponse, status_code=201)
async def create_keyword(
    project_id: int,
    keyword_data: KeywordCreate,
    db: Session = Depends(get_db)
):
    """
    创建关键词

    注意：为指定项目添加新关键词！
    """
    # 验证项目存在
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    keyword = Keyword(
        project_id=project_id,
        keyword=keyword_data.keyword,
        difficulty_score=keyword_data.difficulty_score
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    logger.info(f"关键词已创建: {keyword.keyword}")
    return keyword


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    更新项目

    注意：更新项目信息！
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.name = project_data.name
    project.company_name = project_data.company_name
    project.domain_keyword = project_data.domain_keyword  # 更新领域关键词
    project.description = project_data.description
    project.industry = project_data.industry
    db.commit()
    db.refresh(project)

    logger.info(f"项目已更新: {project.name}")
    return project


@router.delete("/projects/{project_id}", response_model=ApiResponse)
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    删除项目（软删除）

    注意：这是软删除，数据不会真正删除！
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.status = 0
    db.commit()

    logger.info(f"项目已停用: {project_id}")
    return ApiResponse(success=True, message="项目已停用")


@router.delete("/questions/{question_id}", response_model=ApiResponse)
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """
    删除问题变体

    注意：这是永久删除！
    """
    question = db.query(QuestionVariant).filter(QuestionVariant.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="问题变体不存在")

    db.delete(question)
    db.commit()

    logger.info(f"问题变体已删除: {question_id}")
    return ApiResponse(success=True, message="问题变体已删除")
