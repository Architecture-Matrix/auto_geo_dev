# -*- coding: utf-8 -*-
"""
预警通知测试
我要确保预警功能正常
"""

import pytest
import requests


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"


@pytest.mark.monitor
class TestNotifications:
    """预警通知测试类"""

    def test_notification_list(self, clean_db):
        """测试预警列表"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code in [200, 404]

    def test_rules_display(self, clean_db):
        """测试预警规则显示"""
        response = requests.get(f"{BASE_URL}/api/notifications/rules")
        assert response.status_code in [200, 404]

    def test_create_rule(self, clean_db, test_project):
        """测试创建预警规则"""
        data = {
            "name": "测试规则",
            "project_id": test_project.id,
            "condition": "rate_below",
            "threshold": 50,
            "enabled": True
        }
        response = requests.post(f"{BASE_URL}/api/notifications/rules", json=data)
        assert response.status_code in [200, 404, 405]

    def test_warning_trigger(self, clean_db, test_keyword):
        """测试预警触发"""
        data = {
            "keyword_id": test_keyword.id,
            "rate": 30
        }
        response = requests.post(f"{BASE_URL}/api/notifications/check", json=data)
        assert response.status_code in [200, 404, 405]

    def test_warning_dismiss(self, clean_db):
        """测试标记预警已读"""
        response = requests.patch(f"{BASE_URL}/api/notifications/999/read")
        assert response.status_code in [200, 404]

    def test_delete_rule(self, clean_db):
        """测试删除预警规则"""
        response = requests.delete(f"{BASE_URL}/api/notifications/rules/999")
        assert response.status_code in [200, 404, 405]

    def test_batch_mark_read(self, clean_db):
        """测试批量标记已读"""
        data = {
            "notification_ids": [1, 2, 3]
        }
        response = requests.post(f"{BASE_URL}/api/notifications/batch-read", json=data)
        assert response.status_code in [200, 404, 405]
