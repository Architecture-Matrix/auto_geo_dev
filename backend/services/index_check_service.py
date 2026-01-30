# -*- coding: utf-8 -*-
"""
收录检测服务
用这个来检测AI平台的收录情况！
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session
from playwright.async_api import async_playwright, Browser
import asyncio

from backend.database.models import IndexCheckRecord, Keyword, QuestionVariant, Project
from backend.config import AI_PLATFORMS
from backend.services.playwright.ai_platforms import DoubaoChecker, QianwenChecker, DeepSeekChecker


class IndexCheckService:
    """
    收录检测服务

    注意：这个服务负责AI平台收录检测！
    """

    def __init__(self, db: Session):
        """
        初始化收录检测服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.checkers = {
            "doubao": DoubaoChecker("doubao", AI_PLATFORMS["doubao"]),
            "qianwen": QianwenChecker("qianwen", AI_PLATFORMS["qianwen"]),
            "deepseek": DeepSeekChecker("deepseek", AI_PLATFORMS["deepseek"]),
        }

    async def check_keyword(
        self,
        keyword_id: int,
        company_name: str,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        检测关键词在所有AI平台的收录情况

        Args:
            keyword_id: 关键词ID
            company_name: 公司名称
            platforms: 要检测的平台列表，默认全部

        Returns:
            检测结果列表
        """
        # 获取关键词信息
        keyword_obj = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword_obj:
            logger.error(f"关键词不存在: {keyword_id}")
            return []

        # 获取问题变体
        questions = self.db.query(QuestionVariant).filter(
            QuestionVariant.keyword_id == keyword_id
        ).all()

        if not questions:
            # 如果没有问题变体，使用默认问题
            questions = [QuestionVariant(
                id=0,
                keyword_id=keyword_id,
                question=f"什么是{keyword_obj.keyword}？推荐哪家公司？"
            )]

        # 确定要检测的平台
        if platforms is None:
            platforms = list(self.checkers.keys())

        results = await self._execute_checks(
            keyword_id=keyword_id,
            keyword_obj=keyword_obj,
            questions=questions,
            company_name=company_name,
            platforms=platforms
        )

        logger.info(f"收录检测完成: 关键词ID={keyword_id}, 检测数={len(results)}")
        return results

    async def check_project_keywords(
        self,
        project_id: int,
        platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        批量检测项目下所有关键词的收录情况
        
        Args:
            project_id: 项目ID
            platforms: 要检测的平台列表，默认全部
            
        Returns:
            检测结果列表
        """
        # 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"项目不存在: {project_id}")
            return []
            
        # 获取项目下所有关键词
        keywords = self.db.query(Keyword).filter(
            Keyword.project_id == project_id
        ).all()
        
        if not keywords:
            logger.error(f"项目下没有关键词: {project_id}")
            return []
            
        all_results = []
        
        # 确定要检测的平台
        if platforms is None:
            platforms = list(self.checkers.keys())
        
        # 使用单个Playwright实例处理所有关键词，提高效率
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                for keyword_obj in keywords:
                    # 获取关键词的问题变体
                    questions = self.db.query(QuestionVariant).filter(
                        QuestionVariant.keyword_id == keyword_obj.id
                    ).all()
                    
                    if not questions:
                        # 如果没有问题变体，使用默认问题
                        questions = [QuestionVariant(
                            id=0,
                            keyword_id=keyword_obj.id,
                            question=f"什么是{keyword_obj.keyword}？推荐哪家公司？"
                        )]
                    
                    # 执行检测
                    results = await self._execute_checks_for_single_keyword(
                        keyword_id=keyword_obj.id,
                        keyword_obj=keyword_obj,
                        questions=questions,
                        company_name=project.company_name,
                        platforms=platforms,
                        page=page
                    )
                    
                    all_results.extend(results)
                    
                    # 短暂休息，避免被平台检测为自动化
                    await asyncio.sleep(2)
                    
            finally:
                await browser.close()
        
        logger.info(f"项目关键词批量检测完成: 项目ID={project_id}, 关键词数={len(keywords)}, 检测数={len(all_results)}")
        return all_results
    
    async def _execute_checks(
        self,
        keyword_id: int,
        keyword_obj: Keyword,
        questions: List[QuestionVariant],
        company_name: str,
        platforms: List[str]
    ) -> List[Dict[str, Any]]:
        """
        执行检测的通用方法
        """
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                results = await self._execute_checks_for_single_keyword(
                    keyword_id=keyword_id,
                    keyword_obj=keyword_obj,
                    questions=questions,
                    company_name=company_name,
                    platforms=platforms,
                    page=page
                )
            finally:
                await browser.close()
        
        return results
    
    async def _execute_checks_for_single_keyword(
        self,
        keyword_id: int,
        keyword_obj: Keyword,
        questions: List[QuestionVariant],
        company_name: str,
        platforms: List[str],
        page: Any
    ) -> List[Dict[str, Any]]:
        """
        为单个关键词执行检测
        """
        results = []
        max_retries = 2
        
        for platform_id in platforms:
            checker = self.checkers.get(platform_id)
            if not checker:
                logger.warning(f"未知的平台: {platform_id}")
                continue

            logger.info(f"开始检测平台: {checker.name}, 关键词: {keyword_obj.keyword}")

            for qv in questions:
                retry_count = 0
                success = False
                check_result = None
                
                while retry_count <= max_retries and not success:
                    try:
                        # 调用检测器
                        check_result = await checker.check(
                            page=page,
                            question=qv.question,
                            keyword=keyword_obj.keyword,
                            company=company_name
                        )
                        
                        success = check_result.get("success", False)
                        if success:
                            logger.debug(f"检测成功: 平台={checker.name}, 问题={qv.question[:30]}...")
                            break
                        
                        retry_count += 1
                        logger.warning(f"检测失败，正在重试 ({retry_count}/{max_retries}): {check_result.get('error_msg', '未知错误')}")
                        
                        # 重试前清理聊天记录和等待
                        await checker.clear_chat_history(page)
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"检测异常，正在重试 ({retry_count}/{max_retries}): {str(e)}")
                        
                        # 重试前等待
                        await asyncio.sleep(5)
                        
                        # 尝试重新导航到页面
                        if retry_count > 1:
                            await checker.navigate_to_page(page)
                
                if not check_result:
                    check_result = {
                        "success": False,
                        "answer": None,
                        "keyword_found": False,
                        "company_found": False,
                        "error_msg": "检测超时或多次失败"
                    }
                
                try:
                    # 保存检测结果
                    record = IndexCheckRecord(
                        keyword_id=keyword_id,
                        platform=platform_id,
                        question=qv.question,
                        answer=check_result.get("answer"),
                        keyword_found=check_result.get("keyword_found", False),
                        company_found=check_result.get("company_found", False)
                    )
                    self.db.add(record)
                    self.db.commit()
                except Exception as db_error:
                    logger.error(f"保存检测结果失败: {str(db_error)}")
                    # 回滚事务
                    self.db.rollback()

                results.append({
                    "keyword_id": keyword_id,
                    "keyword": keyword_obj.keyword,
                    "platform": checker.name,
                    "question": qv.question,
                    "keyword_found": check_result.get("keyword_found", False),
                    "company_found": check_result.get("company_found", False),
                    "success": check_result.get("success", False),
                    "retry_count": retry_count
                })
                
                # 每个问题检测后短暂休息
                await asyncio.sleep(1)
        
        return results

    def get_check_records(
        self,
        keyword_id: Optional[int] = None,
        platform: Optional[str] = None,
        limit: int = 100
    ) -> List[IndexCheckRecord]:
        """
        获取检测记录

        Args:
            keyword_id: 关键词ID筛选
            platform: 平台筛选
            limit: 返回数量限制

        Returns:
            检测记录列表
        """
        query = self.db.query(IndexCheckRecord)

        if keyword_id:
            query = query.filter(IndexCheckRecord.keyword_id == keyword_id)
        if platform:
            query = query.filter(IndexCheckRecord.platform == platform)

        return query.order_by(IndexCheckRecord.check_time.desc()).limit(limit).all()

    def get_hit_rate(self, keyword_id: int) -> Dict[str, Any]:
        """
        计算关键词命中率

        Args:
            keyword_id: 关键词ID

        Returns:
            命中率统计
        """
        records = self.db.query(IndexCheckRecord).filter(
            IndexCheckRecord.keyword_id == keyword_id
        ).all()

        if not records:
            return {"hit_rate": 0, "total": 0, "keyword_found": 0, "company_found": 0}

        total = len(records)
        keyword_found = sum(1 for r in records if r.keyword_found)
        company_found = sum(1 for r in records if r.company_found)

        return {
            "hit_rate": round((keyword_found + company_found) / (total * 2) * 100, 2),
            "total": total,
            "keyword_found": keyword_found,
            "company_found": company_found
        }
    
    def get_keyword_trend(
        self,
        keyword_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取关键词收录趋势
        
        Args:
            keyword_id: 关键词ID
            days: 统计天数
            
        Returns:
            趋势数据
        """
        from datetime import datetime, timedelta
        
        # 获取起始时间
        start_date = datetime.now() - timedelta(days=days)
        
        # 获取关键词信息
        keyword = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
        if not keyword:
            return {"keyword": None, "trend": []}
        
        # 按天分组统计
        trend_data = []
        
        for day_offset in range(days, 0, -1):
            day_start = datetime.now() - timedelta(days=day_offset)
            day_end = day_start + timedelta(days=1)
            
            # 获取当天的检测记录
            records = self.db.query(IndexCheckRecord).filter(
                IndexCheckRecord.keyword_id == keyword_id,
                IndexCheckRecord.check_time >= day_start,
                IndexCheckRecord.check_time < day_end
            ).all()
            
            if not records:
                continue
            
            # 计算当天的统计数据
            total = len(records)
            keyword_found = sum(1 for r in records if r.keyword_found)
            company_found = sum(1 for r in records if r.company_found)
            
            # 计算命中率
            hit_rate = round((keyword_found + company_found) / (total * 2) * 100, 2) if total > 0 else 0
            
            trend_data.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "total": total,
                "keyword_found": keyword_found,
                "company_found": company_found,
                "hit_rate": hit_rate,
                "keyword_pct": round((keyword_found / total) * 100, 2) if total > 0 else 0,
                "company_pct": round((company_found / total) * 100, 2) if total > 0 else 0
            })
        
        return {
            "keyword": keyword.keyword,
            "trend": trend_data,
            "total_days": days
        }
    
    def get_project_analytics(
        self,
        project_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取项目的综合分析
        
        Args:
            project_id: 项目ID
            days: 统计天数
            
        Returns:
            项目分析数据
        """
        from datetime import datetime, timedelta
        
        # 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "项目不存在"}
        
        # 获取关键词列表
        keywords = self.db.query(Keyword).filter(
            Keyword.project_id == project_id,
            Keyword.status == "active"
        ).all()
        
        if not keywords:
            return {
                "project_name": project.name,
                "company_name": project.company_name,
                "total_keywords": 0,
                "analytics": [],
                "summary": {
                    "total_checks": 0,
                    "avg_hit_rate": 0,
                    "keyword_avg": 0,
                    "company_avg": 0
                }
            }
        
        start_date = datetime.now() - timedelta(days=days)
        
        keyword_analytics = []
        total_checks = 0
        total_hit_rate = 0
        total_keyword_avg = 0
        total_company_avg = 0
        
        for keyword in keywords:
            # 获取该关键词的检测记录
            records = self.db.query(IndexCheckRecord).filter(
                IndexCheckRecord.keyword_id == keyword.id,
                IndexCheckRecord.check_time >= start_date
            ).all()
            
            if not records:
                continue
            
            total = len(records)
            keyword_found = sum(1 for r in records if r.keyword_found)
            company_found = sum(1 for r in records if r.company_found)
            
            hit_rate = round((keyword_found + company_found) / (total * 2) * 100, 2) if total > 0 else 0
            keyword_pct = round((keyword_found / total) * 100, 2) if total > 0 else 0
            company_pct = round((company_found / total) * 100, 2) if total > 0 else 0
            
            keyword_analytics.append({
                "keyword_id": keyword.id,
                "keyword": keyword.keyword,
                "total_checks": total,
                "hit_rate": hit_rate,
                "keyword_pct": keyword_pct,
                "company_pct": company_pct,
                "status": "good" if hit_rate > 60 else "warning" if hit_rate > 30 else "critical"
            })
            
            # 累计统计
            total_checks += total
            total_hit_rate += hit_rate
            total_keyword_avg += keyword_pct
            total_company_avg += company_pct
        
        # 计算平均值
        keyword_count = len(keyword_analytics)
        summary = {
            "total_checks": total_checks,
            "avg_hit_rate": round(total_hit_rate / keyword_count, 2) if keyword_count > 0 else 0,
            "keyword_avg": round(total_keyword_avg / keyword_count, 2) if keyword_count > 0 else 0,
            "company_avg": round(total_company_avg / keyword_count, 2) if keyword_count > 0 else 0
        }
        
        return {
            "project_name": project.name,
            "company_name": project.company_name,
            "total_keywords": len(keywords),
            "active_keywords": keyword_count,
            "analytics": keyword_analytics,
            "summary": summary
        }
    
    def get_platform_performance(
        self,
        project_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取各平台的表现分析
        
        Args:
            project_id: 项目ID（可选）
            days: 统计天数
            
        Returns:
            平台表现数据
        """
        from datetime import datetime, timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 构建查询条件
        query = self.db.query(IndexCheckRecord)
        
        if project_id:
            # 通过关键词关联到项目
            from sqlalchemy import and_
            query = query.join(Keyword).filter(
                and_(
                    IndexCheckRecord.check_time >= start_date,
                    Keyword.project_id == project_id,
                    Keyword.status == "active"
                )
            )
        else:
            query = query.filter(IndexCheckRecord.check_time >= start_date)
        
        records = query.all()
        
        if not records:
            return {"platforms": [], "summary": {"total_checks": 0}}
        
        # 按平台分组统计
        platform_data = {}
        
        for record in records:
            platform = record.platform
            if platform not in platform_data:
                platform_data[platform] = {
                    "platform": platform,
                    "total": 0,
                    "keyword_found": 0,
                    "company_found": 0,
                    "success_count": 0
                }
            
            platform_data[platform]["total"] += 1
            if record.keyword_found:
                platform_data[platform]["keyword_found"] += 1
            if record.company_found:
                platform_data[platform]["company_found"] += 1
            
            # 成功检测（有回答）
            if record.answer and record.answer.strip():
                platform_data[platform]["success_count"] += 1
        
        # 计算各平台的命中率和成功率
        platforms = []
        total_checks = 0
        total_success = 0
        
        for platform, data in platform_data.items():
            hit_rate = round((data["keyword_found"] + data["company_found"]) / (data["total"] * 2) * 100, 2) if data["total"] > 0 else 0
            keyword_pct = round((data["keyword_found"] / data["total"]) * 100, 2) if data["total"] > 0 else 0
            company_pct = round((data["company_found"] / data["total"]) * 100, 2) if data["total"] > 0 else 0
            success_rate = round((data["success_count"] / data["total"]) * 100, 2) if data["total"] > 0 else 0
            
            platforms.append({
                "platform": platform,
                "platform_name": self.checkers.get(platform, {}).name if platform in self.checkers else platform,
                "total_checks": data["total"],
                "hit_rate": hit_rate,
                "keyword_pct": keyword_pct,
                "company_pct": company_pct,
                "success_rate": success_rate,
                "status": "good" if hit_rate > 60 else "warning" if hit_rate > 30 else "critical"
            })
            
            total_checks += data["total"]
            total_success += data["success_count"]
        
        # 按命中率排序
        platforms.sort(key=lambda x: x["hit_rate"], reverse=True)
        
        summary = {
            "total_platforms": len(platforms),
            "total_checks": total_checks,
            "avg_success_rate": round((total_success / total_checks) * 100, 2) if total_checks > 0 else 0
        }
        
        return {
            "platforms": platforms,
            "summary": summary
        }
