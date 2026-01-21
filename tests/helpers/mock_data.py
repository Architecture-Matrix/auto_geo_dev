# -*- coding: utf-8 -*-
"""
Mock数据生成器
生成测试用的模拟数据
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any


class MockData:
    """
    Mock数据生成器
    我准备的测试数据，够用就行
    """

    # ==================== GEO模块数据 ====================

    @staticmethod
    def project() -> Dict[str, Any]:
        """生成Mock项目数据"""
        return {
            "name": f"测试项目_{random.randint(1000, 9999)}",
            "company_name": f"测试公司_{random.randint(1000, 9999)}",
            "description": "这是一个自动化测试项目",
            "industry": random.choice(["互联网", "教育", "金融", "医疗", "电商"]),
            "status": 1
        }

    @staticmethod
    def keywords(count: int = 5) -> List[str]:
        """生成Mock关键词列表"""
        base_keywords = [
            "SEO优化", "AI写作", "内容营销", "关键词工具",
            "长尾关键词挖掘", "搜索引擎优化技巧", "关键词排名工具",
            "AI内容生成", "文章自动发布", "自媒体运营"
        ]
        return random.sample(base_keywords, min(count, len(base_keywords)))

    @staticmethod
    def distill_result() -> List[str]:
        """生成Mock蒸馏结果"""
        return [
            "长尾关键词挖掘技巧",
            "SEO关键词分析方法",
            "搜索引擎优化实战指南",
            "关键词排名监控工具推荐"
        ]

    @staticmethod
    def question_variants(keyword: str) -> List[str]:
        """生成问题变体"""
        templates = [
            f"什么是{keyword}？",
            f"{keyword}怎么用？",
            f"{keyword}的优势是什么？",
            f"如何学习{keyword}？",
            f"{keyword}的注意事项"
        ]
        return templates

    # ==================== 监控模块数据 ====================

    @staticmethod
    def index_result() -> Dict[str, Any]:
        """生成Mock收录检测结果"""
        platforms = ["doubao", "qianwen", "deepseek"]
        result = {}
        for platform in platforms:
            if random.random() > 0.3:  # 70%概率被收录
                result[platform] = {
                    "indexed": True,
                    "rank": random.randint(1, 10),
                    "url": f"https://{platform}.example.com/article/{random.randint(1000, 9999)}"
                }
            else:
                result[platform] = {
                    "indexed": False,
                    "rank": None,
                    "url": None
                }
        return result

    @staticmethod
    def trend_data(days: int = 7) -> List[Dict[str, Any]]:
        """生成Mock趋势数据"""
        data = []
        base_date = datetime.now() - timedelta(days=days)
        for i in range(days):
            date = base_date + timedelta(days=i)
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "rate": round(random.uniform(50, 95), 1)
            })
        return data

    @staticmethod
    def notification() -> Dict[str, Any]:
        """生成Mock预警通知"""
        types = ["warning", "info", "success"]
        messages = [
            "命中率下降超过20%",
            "关键词排名提升",
            "新文章收录成功",
            "账号Cookie即将过期"
        ]
        return {
            "type": random.choice(types),
            "message": random.choice(messages),
            "keyword_id": random.randint(1, 100),
            "created_at": datetime.now().isoformat(),
            "read": False
        }

    # ==================== 发布模块数据 ====================

    @staticmethod
    def article() -> Dict[str, Any]:
        """生成Mock文章数据"""
        return {
            "title": f"测试文章_{random.randint(1000, 9999)}",
            "content": "这是一篇自动化测试文章的内容。包含了各种测试文本，用于验证文章编辑和发布功能。",
            "tags": "测试,自动化,AI",
            "category": random.choice(["技术", "教程", "资讯"]),
            "status": 0
        }

    @staticmethod
    def account() -> Dict[str, Any]:
        """生成Mock账号数据"""
        platforms = ["zhihu", "baijiahao", "sohu", "toutiao"]
        return {
            "platform": random.choice(platforms),
            "account_name": f"测试账号_{random.randint(1000, 9999)}",
            "username": f"test_user_{random.randint(1000, 9999)}",
            "status": 1
        }

    @staticmethod
    def publish_result() -> Dict[str, Any]:
        """生成Mock发布结果"""
        platforms = ["zhihu", "baijiahao"]
        result = {}
        for platform in platforms:
            if random.random() > 0.2:  # 80%成功率
                result[platform] = {
                    "status": "success",
                    "url": f"https://{platform}.com/article/{random.randint(10000, 99999)}"
                }
            else:
                result[platform] = {
                    "status": "failed",
                    "error": random.choice(["Cookie已过期", "网络错误", "发布受限"])
                }
        return result

    # ==================== 通用数据 ====================

    @staticmethod
    def email() -> str:
        """生成随机邮箱"""
        return f"test_{random.randint(1000, 9999)}@example.com"

    @staticmethod
    def phone() -> str:
        """生成随机手机号"""
        return f"1{random.choice([3, 5, 7, 8, 9])}{random.randint(100000000, 999999999)}"

    @staticmethod
    def url() -> str:
        """生成随机URL"""
        return f"https://example.com/page/{random.randint(1000, 9999)}"

    @staticmethod
    def timestamp() -> str:
        """生成时间戳字符串"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
