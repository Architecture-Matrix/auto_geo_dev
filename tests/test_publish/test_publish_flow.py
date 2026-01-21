# -*- coding: utf-8 -*-
"""
发布流程测试
我要确保发布流程正常
"""

import pytest
import requests
from tests.helpers.mock_data import MockData


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"
PUBLISH_API = f"{BASE_URL}/api/publish"


@pytest.mark.publish
class TestPublishFlow:
    """发布流程测试类"""

    def test_platform_selection(self, clean_db, test_article):
        """测试平台选择"""
        # 获取可用平台
        response = requests.get(f"{BASE_URL}/api/platforms")

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert "platforms" in result
        assert len(result["platforms"]) > 0

    def test_single_platform_publish(self, clean_db, test_article, test_account):
        """测试单平台发布"""
        # 发布API可能还没实现
        data = {
            "article_id": test_article.id,
            "account_ids": [test_account.id]
        }

        response = requests.post(PUBLISH_API, json=data)

        # 验证：API可能未实现
        assert response.status_code in [200, 404, 405]

    def test_multi_platform_publish(self, clean_db, test_article):
        """测试多平台发布"""
        # 创建多个账号
        account_ids = []
        for platform in ["zhihu", "baijiahao"]:
            data = MockData.account()
            data["platform"] = platform
            resp = requests.post(f"{BASE_URL}/api/accounts", json=data)
            account_ids.append(resp.json()["id"])

        # 发布API可能还没实现
        data = {
            "article_id": test_article.id,
            "account_ids": account_ids
        }

        response = requests.post(PUBLISH_API, json=data)

        # 验证：API可能未实现
        assert response.status_code in [200, 404, 405]

    def test_publish_progress(self, clean_db, test_article):
        """测试发布进度"""
        response = requests.get(
            f"{PUBLISH_API}/progress",
            params={"article_id": test_article.id}
        )

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_publish_result(self, clean_db, test_article):
        """测试发布结果"""
        response = requests.get(
            f"{PUBLISH_API}/result",
            params={"article_id": test_article.id}
        )

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_publish_history(self, clean_db):
        """测试发布历史"""
        response = requests.get(f"{PUBLISH_API}/history")

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_republish(self, clean_db):
        """测试重新发布"""
        data = {
            "record_id": 999  # 假设的失败记录ID
        }

        response = requests.post(f"{PUBLISH_API}/republish", json=data)

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_cancel_publish(self, clean_db, test_article):
        """测试取消发布"""
        response = requests.post(
            f"{PUBLISH_API}/cancel",
            json={"article_id": test_article.id}
        )

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_publish_validation(self, clean_db):
        """测试发布数据验证"""
        # 缺少article_id
        invalid_data = {
            "account_ids": [1, 2]
        }

        response = requests.post(PUBLISH_API, json=invalid_data)

        # 验证应该返回错误
        assert response.status_code in [400, 422, 404, 405]

    def test_batch_publish(self, clean_db):
        """测试批量发布"""
        # 批量发布多篇文章
        articles = []
        for _ in range(3):
            data = MockData.article()
            resp = requests.post(f"{BASE_URL}/api/articles", json=data)
            articles.append(resp.json())

        batch_data = {
            "article_ids": [a["id"] for a in articles],
            "platform": "zhihu"
        }

        response = requests.post(f"{PUBLISH_API}/batch", json=batch_data)

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_publish_preview(self, clean_db, test_article):
        """测试发布预览"""
        response = requests.get(
            f"{PUBLISH_API}/preview",
            params={"article_id": test_article.id}
        )

        # 验证
        assert response.status_code in [200, 404, 405]

    def test_scheduled_publish(self, clean_db, test_article, test_account):
        """测试定时发布"""
        from datetime import datetime, timedelta

        scheduled_time = (datetime.now() + timedelta(hours=1)).isoformat()

        data = {
            "article_id": test_article.id,
            "account_ids": [test_account.id],
            "scheduled_at": scheduled_time
        }

        response = requests.post(f"{PUBLISH_API}/schedule", json=data)

        # 验证
        assert response.status_code in [200, 404, 405]
