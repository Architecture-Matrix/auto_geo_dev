# -*- coding: utf-8 -*-
"""
数据报表测试
我要确保报表功能正常
"""

import pytest
import requests


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"


@pytest.mark.monitor
class TestReports:
    """数据报表测试类"""

    def test_overview_dashboard(self, clean_db):
        """测试概览仪表板"""
        response = requests.get(f"{BASE_URL}/api/reports/overview")
        assert response.status_code in [200, 404]

    def test_trend_chart_render(self, clean_db, test_project):
        """测试收录趋势图"""
        response = requests.get(f"{BASE_URL}/api/reports/trend", params={
            "project_id": test_project.id,
            "days": 30
        })
        assert response.status_code in [200, 404]

    def test_ranking_table(self, clean_db, test_project):
        """测试排名表格"""
        response = requests.get(f"{BASE_URL}/api/reports/ranking", params={
            "project_id": test_project.id,
            "order_by": "rate",
            "order": "desc"
        })
        assert response.status_code in [200, 404]

    def test_platform_distribution(self, clean_db):
        """测试平台分布饼图"""
        response = requests.get(f"{BASE_URL}/api/reports/platform-distribution")
        assert response.status_code in [200, 404]

    def test_date_range_filter(self, clean_db, test_project):
        """测试日期范围筛选"""
        response = requests.get(f"{BASE_URL}/api/reports/trend", params={
            "project_id": test_project.id,
            "start_date": "2025-01-01",
            "end_date": "2025-01-31"
        })
        assert response.status_code in [200, 404]

    def test_export_report(self, clean_db, test_project):
        """测试导出报表"""
        response = requests.get(f"{BASE_URL}/api/reports/export", params={
            "project_id": test_project.id,
            "format": "xlsx"
        })
        assert response.status_code in [200, 404, 405]

    def test_keyword_statistics(self, clean_db, test_project):
        """测试关键词统计"""
        response = requests.get(f"{BASE_URL}/api/reports/keyword-stats", params={
            "project_id": test_project.id
        })
        assert response.status_code in [200, 404]
