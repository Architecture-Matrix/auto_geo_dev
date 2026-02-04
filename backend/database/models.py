# -*- coding: utf-8 -*-
"""
数据模型定义 - 工业级完整版
包含基础发布、GEO、监控、知识库及AI招聘所有表结构
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

# 表参数：允许扩展现有表
TABLE_ARGS = {"extend_existing": True}


class Account(Base):
    """账号表"""
    __tablename__ = "accounts"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=True)  # 平台内的用户名
    cookies = Column(Text, nullable=True)
    storage_state = Column(Text, nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(Integer, default=1)
    last_auth_time = Column(DateTime, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    publish_records = relationship("PublishRecord", back_populates="account", cascade="all, delete-orphan")


class ScheduledTask(Base):
    """
    定时任务配置表
    """
    __tablename__ = "scheduled_tasks"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="任务名称")
    task_key = Column(String(50), unique=True, nullable=False, comment="任务标识符(代码中对应key)")
    cron_expression = Column(String(50), nullable=False, comment="Cron表达式")
    is_active = Column(Boolean, default=True, comment="是否启用")
    description = Column(Text, nullable=True, comment="任务描述")

    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task {self.name} : {self.cron_expression}>"


class Candidate(Base):
    """
    AI招聘候选人表
    存储n8n AI招聘流程筛选的候选人数据
    """
    __tablename__ = "candidates"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    uid = Column(String(100), unique=True, nullable=False, index=True, comment="候选人唯一标识（来自招聘平台）")
    detail = Column(Text, nullable=True, comment="候选人详细信息（JSON格式）")

    # 附件相关
    attached = Column(Text, nullable=True, comment="附件信息（JSON格式，存储简历链接等）")

    # 发送状态
    is_send = Column(Boolean, default=False, comment="是否已发送文章/消息")

    # 关联文章（可选：如果发送了文章，记录文章ID）
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, comment="关联的文章ID")

    # 状态
    status = Column(Integer, default=1, comment="状态：1=有效 0=无效 -1=已删除")

    # 备注
    remark = Column(Text, nullable=True, comment="备注信息")

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    sent_at = Column(DateTime, nullable=True, comment="发送时间")

    def __repr__(self):
        return f"<Candidate uid={self.uid} is_send={self.is_send}>"


class Article(Base):
    """
    文章表
    存储文章内容和基本信息
    """
    __tablename__ = "articles"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    title = Column(String(200), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容（Markdown/HTML）")

    # 标签和分类
    tags = Column(String(500), nullable=True, comment="标签，逗号分隔")
    category = Column(String(100), nullable=True, comment="文章分类")

    # 封面图
    cover_image = Column(String(500), nullable=True, comment="封面图片URL")

    # 状态
    status = Column(Integer, default=0, comment="状态：0=草稿 1=已发布")

    # 统计
    view_count = Column(Integer, default=0, comment="查看次数")

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    published_at = Column(DateTime, nullable=True, comment="首次发布时间")

    # 关联关系
    publish_records = relationship("PublishRecord", back_populates="article", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Article {self.title}>"


class PublishRecord(Base):
    """
    发布记录表
    记录文章到各平台的发布状态
    """
    __tablename__ = "publish_records"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    # 外键
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True, comment="文章ID")
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True, comment="账号ID")

    # 发布状态
    publish_status = Column(
        Integer,
        default=0,
        comment="发布状态：0=待发布 1=发布中 2=成功 3=失败"
    )

    # 结果
    platform_url = Column(String(500), nullable=True, comment="发布后的文章链接")
    error_msg = Column(Text, nullable=True, comment="错误信息")

    # 重试
    retry_count = Column(Integer, default=0, comment="重试次数")

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    published_at = Column(DateTime, nullable=True, comment="实际发布时间")

    # 关联关系
    article = relationship("Article", back_populates="publish_records")
    account = relationship("Account", back_populates="publish_records")

    def __repr__(self):
        return f"<PublishRecord article_id={self.article_id} account_id={self.account_id} status={self.publish_status}>"


# ==================== 参考文章表（爆火文章收集）====================

class ReferenceArticle(Base):
    """
    参考文章表
    存储从各平台采集的爆火/热门文章，用于内容创作参考
    """
    __tablename__ = "reference_articles"
    __table_args__ = TABLE_ARGS

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    # 基本信息
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, unique=True, comment="原文链接")
    content = Column(Text, nullable=False, comment="文章正文（已清洗）")
    summary = Column(Text, nullable=True, comment="文章摘要")

    # 来源信息
    platform = Column(String(50), nullable=False, index=True, comment="来源平台：zhihu/toutiao等")
    author = Column(String(200), nullable=True, comment="作者名称")
    publish_time = Column(String(50), nullable=True, comment="原文发布时间")

    # 热度指标
    likes = Column(Integer, default=0, comment="点赞数")
    reads = Column(Integer, default=0, comment="阅读量")
    comments = Column(Integer, default=0, comment="评论数")

    # 采集信息
    keyword = Column(String(200), nullable=True, index=True, comment="采集时使用的关键词")
    collected_at = Column(DateTime, default=func.now(), comment="采集时间")

    # RAGFlow 同步状态
    ragflow_synced = Column(Boolean, default=False, comment="是否已同步到RAGFlow")
    ragflow_doc_id = Column(String(100), nullable=True, comment="RAGFlow文档ID")
    ragflow_sync_time = Column(DateTime, nullable=True, comment="RAGFlow同步时间")

    # 状态
    status = Column(Integer, default=1, comment="状态：1=正常 0=已删除")

    # 时间戳
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<ReferenceArticle {self.title[:30]}... ({self.platform})>"
