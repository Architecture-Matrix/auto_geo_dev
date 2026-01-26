# -*- coding: utf-8 -*-
"""
爆火文章收集整合服务
收集各平台热门文章，为内容创作提供参考！
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from loguru import logger
from sqlalchemy.orm import Session

from backend.services.playwright_mgr import playwright_mgr
from backend.services.playwright.collectors import (
    get_collector,
    list_collectors,
    register_collectors,
    CollectedArticle,
)
from backend.services.ragflow_client import get_ragflow_client
from backend.config import (
    PLATFORMS,
    RAGFLOW_DATASET_ID,
    RAGFLOW_DATASET_NAME,
    RAGFLOW_DUPLICATE_THRESHOLD,
)


class ArticleCollectorService:
    """
    爆火文章收集服务

    功能：
    1. 根据关键词搜索各平台热门文章
    2. 筛选高点赞/高阅读量的爆火文章
    3. 提取文章标题、链接和正文内容
    4. HTML 清洗，去除广告和冗余标签
    5. 存储到数据库
    6. 自动同步到 RAGFlow 进行向量化

    注意：遵循项目的适配器模式设计！
    """

    def __init__(self, db: Optional[Session] = None):
        """
        初始化收集服务

        Args:
            db: 数据库会话（用于保存收集结果）
        """
        self.db = db
        self._initialized = False
        self._ragflow = get_ragflow_client()
        self._dataset_id = RAGFLOW_DATASET_ID

    async def _ensure_initialized(self):
        """确保服务已初始化"""
        if not self._initialized:
            # 注册收集器
            register_collectors(PLATFORMS)
            self._initialized = True

    def _clean_html(self, content: str) -> str:
        """
        清洗 HTML 内容

        去除广告、冗余标签、特殊字符等

        Args:
            content: 原始内容

        Returns:
            清洗后的纯文本内容
        """
        if not content:
            return ""

        # 1. 移除 script 和 style 标签及其内容
        content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content, flags=re.IGNORECASE)

        # 2. 移除 HTML 注释
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

        # 3. 移除常见的广告相关标签和类
        ad_patterns = [
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?</div>',
            r'<div[^>]*class="[^"]*advertisement[^"]*"[^>]*>[\s\S]*?</div>',
            r'<div[^>]*class="[^"]*sponsor[^"]*"[^>]*>[\s\S]*?</div>',
            r'<div[^>]*class="[^"]*promotion[^"]*"[^>]*>[\s\S]*?</div>',
            r'<ins[^>]*>[\s\S]*?</ins>',  # Google AdSense
            r'<aside[^>]*>[\s\S]*?</aside>',  # 侧边栏广告
        ]
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        # 4. 移除所有 HTML 标签，但保留文本
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<p[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<[^>]+>', '', content)

        # 5. 处理 HTML 实体
        html_entities = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
            '&#39;': "'",
            '&ldquo;': '"',
            '&rdquo;': '"',
            '&lsquo;': "'",
            '&rsquo;': "'",
            '&mdash;': '—',
            '&ndash;': '–',
            '&hellip;': '...',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™',
        }
        for entity, char in html_entities.items():
            content = content.replace(entity, char)

        # 6. 移除数字实体
        content = re.sub(r'&#\d+;', '', content)
        content = re.sub(r'&#x[0-9a-fA-F]+;', '', content)

        # 7. 移除多余的空白字符
        content = re.sub(r'\t', ' ', content)
        content = re.sub(r' +', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 8. 移除常见的无意义内容
        noise_patterns = [
            r'点击展开全文',
            r'展开全文',
            r'收起全文',
            r'阅读全文',
            r'查看更多',
            r'相关推荐',
            r'热门推荐',
            r'猜你喜欢',
            r'广告',
            r'推广',
            r'赞助',
            r'分享到',
            r'转发到',
            r'举报',
            r'投诉',
        ]
        for pattern in noise_patterns:
            content = re.sub(pattern, '', content)

        # 9. 去除首尾空白
        content = content.strip()

        return content

    async def _sync_to_ragflow(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步文章到 RAGFlow 进行向量化

        Args:
            article: 文章数据，包含 title, content 等字段

        Returns:
            同步结果：{
                "success": bool,
                "doc_id": str,
                "error_msg": str
            }
        """
        result = {
            "success": False,
            "doc_id": None,
            "error_msg": None
        }

        # 检查 RAGFlow 配置
        if not self._ragflow.is_configured():
            logger.warning("RAGFlow 未配置，跳过向量化同步")
            result["error_msg"] = "RAGFlow 未配置"
            return result

        try:
            # 确保知识库存在
            dataset_id = self._dataset_id
            if not dataset_id:
                dataset_id = self._ragflow.get_or_create_dataset(RAGFLOW_DATASET_NAME)
                if dataset_id:
                    self._dataset_id = dataset_id
                else:
                    result["error_msg"] = "无法获取或创建知识库"
                    return result

            # 构建文档内容
            title = article.get("title", "无标题")
            content = article.get("content", "")
            platform = article.get("platform", "unknown")
            url = article.get("url", "")
            likes = article.get("likes", 0)
            reads = article.get("reads", 0)

            # 添加元信息到内容中
            doc_content = f"""标题：{title}

来源平台：{platform}
原文链接：{url}
点赞数：{likes}
阅读量：{reads}

正文内容：
{content}
"""

            # 上传到 RAGFlow
            upload_result = self._ragflow.upload_document_content(
                dataset_id=dataset_id,
                title=title,
                content=doc_content
            )

            if upload_result.get("code") == 0:
                doc_data = upload_result.get("data", [])
                if doc_data:
                    result["success"] = True
                    result["doc_id"] = doc_data[0].get("id")
                    logger.info(f"文章已同步到 RAGFlow: {title[:30]}...")
            else:
                result["error_msg"] = upload_result.get("message", "上传失败")
                logger.error(f"RAGFlow 同步失败: {result['error_msg']}")

        except Exception as e:
            result["error_msg"] = str(e)
            logger.error(f"RAGFlow 同步异常: {e}")

        return result

    async def _save_to_database(
        self,
        articles: List[Dict[str, Any]],
        keyword: str
    ) -> List[Dict[str, Any]]:
        """
        保存文章到数据库

        Args:
            articles: 文章列表
            keyword: 采集使用的关键词

        Returns:
            保存结果列表
        """
        if not self.db:
            logger.warning("数据库会话未设置，跳过保存")
            return []

        from backend.database.models import ReferenceArticle

        saved_results = []

        for article in articles:
            try:
                # 检查是否已存在（根据 URL 去重）
                url = article.get("url", "")
                existing = self.db.query(ReferenceArticle).filter(
                    ReferenceArticle.url == url
                ).first()

                if existing:
                    logger.debug(f"文章已存在，跳过: {url}")
                    saved_results.append({
                        "url": url,
                        "saved": False,
                        "reason": "already_exists",
                        "article_id": existing.id
                    })
                    continue

                # 清洗内容
                cleaned_content = self._clean_html(article.get("content", ""))

                # 创建新记录
                ref_article = ReferenceArticle(
                    title=article.get("title", "")[:500],
                    url=url,
                    content=cleaned_content,
                    summary=cleaned_content[:500] if cleaned_content else None,
                    platform=article.get("platform", ""),
                    author=article.get("author", ""),
                    publish_time=article.get("publish_time", ""),
                    likes=article.get("likes", 0),
                    reads=article.get("reads", 0),
                    comments=article.get("comments", 0),
                    keyword=keyword,
                    collected_at=datetime.now(),
                    ragflow_synced=False,
                    status=1
                )

                self.db.add(ref_article)
                self.db.commit()
                self.db.refresh(ref_article)

                logger.info(f"文章已保存: {ref_article.title[:30]}... (ID: {ref_article.id})")

                # 同步到 RAGFlow
                sync_result = await self._sync_to_ragflow({
                    "title": ref_article.title,
                    "content": cleaned_content,
                    "platform": ref_article.platform,
                    "url": ref_article.url,
                    "likes": ref_article.likes,
                    "reads": ref_article.reads
                })

                if sync_result["success"]:
                    ref_article.ragflow_synced = True
                    ref_article.ragflow_doc_id = sync_result["doc_id"]
                    ref_article.ragflow_sync_time = datetime.now()
                    self.db.commit()

                saved_results.append({
                    "url": url,
                    "saved": True,
                    "article_id": ref_article.id,
                    "ragflow_synced": sync_result["success"],
                    "ragflow_doc_id": sync_result.get("doc_id")
                })

            except Exception as e:
                logger.error(f"保存文章失败: {e}")
                self.db.rollback()
                saved_results.append({
                    "url": article.get("url", ""),
                    "saved": False,
                    "reason": str(e)
                })

        return saved_results

    async def collect_trending_articles(
        self,
        keyword: str,
        platforms: List[str],
        min_likes: int = 100,
        min_reads: int = 1000,
        max_articles_per_platform: int = 10,
        save_to_db: bool = True,
        sync_to_ragflow: bool = True
    ) -> Dict[str, Any]:
        """
        收集爆火文章

        Args:
            keyword: 搜索关键词
            platforms: 目标平台列表，如 ["zhihu", "toutiao"]
            min_likes: 最低点赞数阈值
            min_reads: 最低阅读量阈值
            max_articles_per_platform: 每个平台最多收集文章数
            save_to_db: 是否保存到数据库
            sync_to_ragflow: 是否同步到 RAGFlow

        Returns:
            收集结果：{
                "success": bool,
                "keyword": str,
                "total_count": int,
                "saved_count": int,
                "ragflow_synced_count": int,
                "results": {
                    "zhihu": [...],
                    "toutiao": [...],
                },
                "save_results": [...],
                "error_msg": str
            }
        """
        await self._ensure_initialized()

        logger.info(f"开始收集爆火文章: keyword={keyword}, platforms={platforms}")

        results = {
            "success": True,
            "keyword": keyword,
            "total_count": 0,
            "saved_count": 0,
            "ragflow_synced_count": 0,
            "results": {},
            "save_results": [],
            "error_msg": None
        }

        try:
            # 启动 Playwright
            await playwright_mgr.start()

            # 并行收集各平台
            tasks = []
            for platform in platforms:
                collector = get_collector(platform)
                if collector:
                    # 更新收集器配置
                    collector.min_likes = min_likes
                    collector.min_reads = min_reads
                    tasks.append(self._collect_from_platform(
                        collector, keyword, max_articles_per_platform
                    ))
                else:
                    logger.warning(f"平台收集器不存在: {platform}")
                    results["results"][platform] = []

            # 等待所有任务完成
            all_articles = []
            if tasks:
                platform_results = await asyncio.gather(*tasks, return_exceptions=True)

                for platform, result in zip(platforms, platform_results):
                    if isinstance(result, Exception):
                        logger.error(f"[{platform}] 收集异常: {result}")
                        results["results"][platform] = []
                    else:
                        # 清洗每篇文章的内容
                        for article in result:
                            article["content"] = self._clean_html(article.get("content", ""))
                        results["results"][platform] = result
                        results["total_count"] += len(result)
                        all_articles.extend(result)

            logger.info(f"收集完成: 共 {results['total_count']} 篇爆火文章")

            # 保存到数据库
            if save_to_db and self.db and all_articles:
                save_results = await self._save_to_database(all_articles, keyword)
                results["save_results"] = save_results
                results["saved_count"] = sum(1 for r in save_results if r.get("saved"))
                results["ragflow_synced_count"] = sum(
                    1 for r in save_results if r.get("ragflow_synced")
                )

        except Exception as e:
            logger.error(f"收集爆火文章失败: {e}")
            results["success"] = False
            results["error_msg"] = str(e)

        return results

    async def _collect_from_platform(
        self,
        collector,
        keyword: str,
        max_articles: int
    ) -> List[Dict[str, Any]]:
        """
        从单个平台收集文章

        Args:
            collector: 平台收集器
            keyword: 搜索关键词
            max_articles: 最大文章数

        Returns:
            文章列表
        """
        try:
            # 创建浏览器上下文
            context = await playwright_mgr._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )

            page = await context.new_page()

            try:
                # 收集文章
                articles = await collector.collect(page, keyword)

                # 限制数量
                articles = articles[:max_articles]

                # 转换为字典
                return [asdict(article) for article in articles]

            finally:
                await page.close()
                await context.close()

        except Exception as e:
            logger.error(f"[{collector.name}] 收集失败: {e}")
            return []

    async def collect_single_platform(
        self,
        keyword: str,
        platform: str,
        min_likes: int = 100,
        min_reads: int = 1000,
        max_articles: int = 10,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        从单个平台收集文章（便捷方法）

        Args:
            keyword: 搜索关键词
            platform: 平台ID
            min_likes: 最低点赞数
            min_reads: 最低阅读量
            max_articles: 最大文章数
            save_to_db: 是否保存到数据库

        Returns:
            收集结果
        """
        result = await self.collect_trending_articles(
            keyword=keyword,
            platforms=[platform],
            min_likes=min_likes,
            min_reads=min_reads,
            max_articles_per_platform=max_articles,
            save_to_db=save_to_db
        )

        return {
            "success": result["success"],
            "keyword": keyword,
            "platform": platform,
            "articles": result["results"].get(platform, []),
            "count": len(result["results"].get(platform, [])),
            "saved_count": result.get("saved_count", 0),
            "ragflow_synced_count": result.get("ragflow_synced_count", 0),
            "error_msg": result["error_msg"]
        }

    async def check_duplicate(
        self,
        content: str,
        threshold: float = None
    ) -> Dict[str, Any]:
        """
        检查内容是否与已有文章重复

        Args:
            content: 待检查的内容
            threshold: 相似度阈值（默认使用配置值）

        Returns:
            检查结果
        """
        if threshold is None:
            threshold = RAGFLOW_DUPLICATE_THRESHOLD

        if not self._ragflow.is_configured():
            return {
                "checked": False,
                "is_duplicate": False,
                "error_msg": "RAGFlow 未配置"
            }

        is_dup, similar_articles = self._ragflow.check_duplicate(
            content=content,
            threshold=threshold
        )

        return {
            "checked": True,
            "is_duplicate": is_dup,
            "similar_articles": similar_articles,
            "threshold": threshold
        }

    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return list(list_collectors().keys())


# 便捷函数
async def collect_trending_articles(
    keyword: str,
    platforms: List[str],
    min_likes: int = 100,
    min_reads: int = 1000,
    db: Session = None
) -> Dict[str, Any]:
    """
    收集爆火文章（便捷函数）

    Example:
        result = await collect_trending_articles(
            keyword="人工智能",
            platforms=["zhihu", "toutiao"],
            min_likes=100,
            db=db_session
        )
    """
    service = ArticleCollectorService(db=db)
    return await service.collect_trending_articles(
        keyword=keyword,
        platforms=platforms,
        min_likes=min_likes,
        min_reads=min_reads
    )
