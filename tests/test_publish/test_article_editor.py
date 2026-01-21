# -*- coding: utf-8 -*-
"""
文章编辑测试
我要确保文章编辑功能正常
"""

import pytest
import requests
from tests.helpers.mock_data import MockData


# 测试基础URL
BASE_URL = "http://127.0.0.1:8001"
ARTICLES_API = f"{BASE_URL}/api/articles"


@pytest.mark.publish
class TestArticleEditor:
    """文章编辑测试类"""

    def test_editor_ui_loaded(self, clean_db):
        """测试编辑器UI加载"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200

    def test_create_article(self, clean_db):
        """测试创建文章"""
        data = MockData.article()

        response = requests.post(ARTICLES_API, json=data)

        # 验证：201是创建成功的标准状态码
        assert response.status_code in [200, 201], f"创建文章失败: {response.text}"
        result = response.json()
        assert result["title"] == data["title"]
        assert result["content"] == data["content"]

    def test_title_input(self, clean_db):
        """测试标题输入"""
        data = MockData.article()
        data["title"] = "测试标题内容"

        response = requests.post(ARTICLES_API, json=data)

        # 验证：201是创建成功的标准状态码
        assert response.status_code in [200, 201]
        result = response.json()
        assert result["title"] == "测试标题内容"

    def test_content_edit(self, clean_db):
        """测试内容编辑"""
        data = MockData.article()
        data["content"] = "# 测试标题\n\n这是测试内容，包含**加粗**和*斜体*。"

        response = requests.post(ARTICLES_API, json=data)

        # 验证：201是创建成功的标准状态码
        assert response.status_code in [200, 201]
        result = response.json()
        assert "测试内容" in result["content"]

    def test_save_draft(self, clean_db):
        """测试保存草稿"""
        data = MockData.article()
        data["status"] = 0  # 草稿

        response = requests.post(ARTICLES_API, json=data)

        # 验证：201是创建成功的标准状态码
        assert response.status_code in [200, 201]
        result = response.json()
        assert result["status"] == 0

    def test_load_draft(self, clean_db):
        """测试加载草稿"""
        # 创建草稿
        data = MockData.article()
        data["status"] = 0
        create_resp = requests.post(ARTICLES_API, json=data)
        article_id = create_resp.json()["id"]

        # 加载草稿
        response = requests.get(f"{ARTICLES_API}/{article_id}")

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == article_id
        assert result["status"] == 0

    def test_update_article(self, clean_db):
        """测试更新文章"""
        # 创建文章
        data = MockData.article()
        create_resp = requests.post(ARTICLES_API, json=data)
        article_id = create_resp.json()["id"]

        # 更新
        update_data = {
            "title": "更新后的标题",
            "content": "更新后的内容"
        }
        response = requests.put(
            f"{ARTICLES_API}/{article_id}",
            json=update_data
        )

        # 验证
        assert response.status_code == 200
        result = response.json()
        assert result["title"] == "更新后的标题"

    def test_delete_article(self, clean_db):
        """测试删除文章"""
        # 创建文章
        data = MockData.article()
        create_resp = requests.post(ARTICLES_API, json=data)
        article_id = create_resp.json()["id"]

        # 删除
        response = requests.delete(f"{ARTICLES_API}/{article_id}")

        # 验证
        assert response.status_code == 200

    def test_article_list(self, clean_db):
        """测试文章列表"""
        # 创建几篇文章
        for _ in range(3):
            data = MockData.article()
            requests.post(ARTICLES_API, json=data)

        response = requests.get(ARTICLES_API)

        # 验证
        assert response.status_code == 200
        result = response.json()
        items = result.get("items", []) if isinstance(result, dict) else result
        assert len(items) >= 3

    def test_article_search(self, clean_db):
        """测试文章搜索"""
        # 创建特定文章
        data = MockData.article()
        data["title"] = "特殊搜索词文章"
        requests.post(ARTICLES_API, json=data)

        # 搜索
        response = requests.get(
            ARTICLES_API,
            params={"search": "特殊"}
        )

        # 验证
        assert response.status_code == 200
