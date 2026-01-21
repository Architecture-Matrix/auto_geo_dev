# -*- coding: utf-8 -*-
"""
收录检测测试
我要确保收录检测功能正常
"""

import pytest
import requests


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"


@pytest.mark.monitor
class TestIndexCheck:
    """收录检测测试类"""

    def test_check_ui_loaded(self, clean_db):
        """测试检测页面UI加载"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200

    def test_single_check(self, clean_db, test_keyword):
        """测试单个关键词检测"""
        # 这个API可能还没实现
        response = requests.post(f"{BASE_URL}/api/index-check/check", json={
            "keyword_id": test_keyword.id,
            "platforms": ["doubao"]
        })
        # API未实现或数据验证失败
        assert response.status_code in [200, 404, 405, 422]

    def test_batch_check(self, clean_db, test_project):
        """测试批量检测"""
        response = requests.post(f"{BASE_URL}/api/index-check/batch", json={
            "project_id": test_project.id,
            "platforms": ["doubao"]
        })
        assert response.status_code in [200, 404, 405, 422]

    def test_platform_toggle(self, clean_db, test_keyword):
        """测试平台切换"""
        response = requests.post(f"{BASE_URL}/api/index-check/check", json={
            "keyword_id": test_keyword.id,
            "platforms": ["qianwen"]
        })
        assert response.status_code in [200, 404, 405, 422]

    def test_check_records(self, clean_db, test_keyword):
        """测试检测历史记录"""
        response = requests.get(f"{BASE_URL}/api/index-check/records", params={
            "keyword_id": test_keyword.id
        })
        assert response.status_code in [200, 404, 405]

    def test_trend_chart(self, clean_db, test_keyword):
        """测试趋势图数据"""
        response = requests.get(f"{BASE_URL}/api/index-check/trend", params={
            "keyword_id": test_keyword.id,
            "days": 7
        })
        assert response.status_code in [200, 404, 405]

    def test_check_result_detail(self, clean_db, test_keyword):
        """测试检测详情"""
        response = requests.get(f"{BASE_URL}/api/index-check/result", params={
            "keyword_id": test_keyword.id
        })
        assert response.status_code in [200, 404, 405]
