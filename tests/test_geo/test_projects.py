# -*- coding: utf-8 -*-
"""
项目管理测试
我要确保项目CRUD功能正常
"""

import pytest
import requests
from tests.helpers.mock_data import MockData


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"
# ！注意项目API在 /api/geo/projects 路径下
PROJECTS_API = f"{BASE_URL}/api/geo/projects"


@pytest.mark.geo
class TestProjects:
    """项目管理测试类"""

    def test_create_project(self, clean_db):
        """测试创建项目"""
        # 准备数据
        data = MockData.project()

        # 发送请求
        response = requests.post(PROJECTS_API, json=data)

        # 验证
        assert response.status_code == 201, f"创建项目失败: {response.text}"
        result = response.json()
        assert result["name"] == data["name"]
        assert result["company_name"] == data["company_name"]
        assert "id" in result

    def test_list_projects(self, clean_db):
        """测试列出项目"""
        # 先创建几个项目
        for _ in range(3):
            data = MockData.project()
            requests.post(PROJECTS_API, json=data)

        # 获取列表
        response = requests.get(PROJECTS_API)

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 3

    def test_get_project(self, clean_db):
        """测试获取单个项目"""
        # 创建项目
        data = MockData.project()
        create_resp = requests.post(PROJECTS_API, json=data)
        project_id = create_resp.json()["id"]

        # 获取项目
        response = requests.get(f"{PROJECTS_API}/{project_id}")

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == project_id
        assert result["name"] == data["name"]

    def test_get_project_keywords(self, clean_db, test_project):
        """测试获取项目的关键词"""
        # 添加关键词
        from backend.database.models import Keyword
        kw = Keyword(project_id=test_project.id, keyword="测试关键词")
        clean_db.add(kw)
        clean_db.commit()

        # 获取项目关键词
        response = requests.get(f"{PROJECTS_API}/{test_project.id}/keywords")

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_project_model_fields(self, clean_db):
        """测试项目模型字段"""
        data = MockData.project()
        response = requests.post(PROJECTS_API, json=data)
        result = response.json()

        # 验证所有必需字段
        assert "id" in result
        assert "name" in result
        assert "company_name" in result
        assert "status" in result
        assert "created_at" in result

    def test_project_with_optional_fields(self, clean_db):
        """测试带可选字段的项目创建"""
        data = MockData.project()
        data["description"] = "详细的项目描述"
        data["industry"] = "科技"

        response = requests.post(PROJECTS_API, json=data)

        # 验证
        assert response.status_code == 201
        result = response.json()
        assert result["description"] == data["description"]
        assert result["industry"] == data["industry"]

    def test_project_filter_by_status(self, clean_db):
        """测试按状态筛选项目"""
        # 创建活跃项目
        data = MockData.project()
        data["status"] = 1
        requests.post(PROJECTS_API, json=data)

        # API默认只返回活跃项目(status=1)
        response = requests.get(PROJECTS_API)
        result = response.json()

        # 验证所有返回的项目都是活跃状态
        for project in result:
            assert project["status"] == 1

    def test_project_ordering(self, clean_db):
        """测试项目排序"""
        # 创建多个项目
        for _ in range(3):
            data = MockData.project()
            requests.post(PROJECTS_API, json=data)

        # 获取列表
        response = requests.get(PROJECTS_API)
        result = response.json()

        # 验证：结果按ID升序排列（当前API实现）
        if len(result) >= 2:
            assert result[0]["id"] < result[-1]["id"]
