# -*- coding: utf-8 -*-
"""
API健康检查测试
我用这个来验证后端API是否正常！
"""

import pytest
import requests


@pytest.mark.asyncio
async def test_backend_health():
    """测试后端健康检查接口"""
    backend_url = "http://127.0.0.1:8001"

    response = requests.get(f"{backend_url}/api/health", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_backend_root():
    """测试后端根接口"""
    backend_url = "http://127.0.0.1:8001"

    response = requests.get(f"{backend_url}/", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_platforms_list():
    """测试平台列表接口"""
    backend_url = "http://127.0.0.1:8001"

    response = requests.get(f"{backend_url}/api/platforms", timeout=5)

    assert response.status_code == 200
    data = response.json()
    assert "platforms" in data
    assert len(data["platforms"]) > 0

    # 验证平台数据结构
    platform = data["platforms"][0]
    assert "id" in platform
    assert "name" in platform
