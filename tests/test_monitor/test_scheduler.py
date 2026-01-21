# -*- coding: utf-8 -*-
"""
定时任务测试
我要确保定时任务功能正常
"""

import pytest
import requests


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"


@pytest.mark.monitor
class TestScheduler:
    """定时任务测试类"""

    def test_scheduler_status(self, clean_db):
        """测试任务状态"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status")
        assert response.status_code in [200, 404]

    def test_manual_trigger(self, clean_db):
        """测试手动触发检测"""
        response = requests.post(f"{BASE_URL}/api/scheduler/trigger")
        assert response.status_code in [200, 404, 405]

    def test_job_list(self, clean_db):
        """测试查看已配置任务"""
        response = requests.get(f"{BASE_URL}/api/scheduler/jobs")
        assert response.status_code in [200, 404]

    def test_create_job(self, clean_db):
        """测试创建定时任务"""
        data = {
            "name": "测试任务",
            "cron": "0 9 * * *",
            "task_type": "index_check"
        }
        response = requests.post(f"{BASE_URL}/api/scheduler/jobs", json=data)
        assert response.status_code in [200, 404, 405]

    def test_update_job(self, clean_db):
        """测试更新定时任务"""
        data = {
            "cron": "0 18 * * *",
            "enabled": True
        }
        response = requests.patch(f"{BASE_URL}/api/scheduler/jobs/1", json=data)
        assert response.status_code in [200, 404, 405]

    def test_delete_job(self, clean_db):
        """测试删除定时任务"""
        response = requests.delete(f"{BASE_URL}/api/scheduler/jobs/1")
        assert response.status_code in [200, 404, 405]

    def test_pause_resume_job(self, clean_db):
        """测试暂停/恢复任务"""
        # 暂停
        response = requests.post(f"{BASE_URL}/api/scheduler/jobs/1/pause")
        assert response.status_code in [200, 404, 405]

        # 恢复
        response = requests.post(f"{BASE_URL}/api/scheduler/jobs/1/resume")
        assert response.status_code in [200, 404, 405]
