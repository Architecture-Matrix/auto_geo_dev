# -*- coding: utf-8 -*-
"""
浏览器导航测试
我用Playwright MCP来测试前端页面！
"""

import pytest
import asyncio


@pytest.mark.browser
@pytest.mark.asyncio
async def test_frontend_home_load(browser_helper):
    """测试前端首页加载"""
    frontend_url = "http://127.0.0.1:5173"

    # 导航到首页
    success = await browser_helper.navigate(frontend_url)
    assert success, "导航到首页失败"

    # 获取页面快照
    snapshot = await browser_helper.get_snapshot()
    assert snapshot is not None, "无法获取页面快照"

    # 检查控制台错误
    console_errors = await browser_helper.get_console_errors()
    assert len(console_errors) == 0, f"存在控制台错误: {console_errors}"


@pytest.mark.browser
@pytest.mark.asyncio
async def test_frontend_page_title(browser_helper):
    """测试页面标题"""
    frontend_url = "http://127.0.0.1:5173"

    await browser_helper.navigate(frontend_url)
    await asyncio.sleep(1)

    # 获取页面标题（通过快照）
    snapshot = await browser_helper.get_snapshot()
    content = str(snapshot)

    # 检查是否包含预期内容
    assert "auto" in content.lower() or "geo" in content.lower(), "页面内容异常"


@pytest.mark.browser
@pytest.mark.asyncio
async def test_account_page_navigation(browser_helper):
    """测试账号页面导航"""
    frontend_url = "http://127.0.0.1:5173"

    # 导航到首页
    await browser_helper.navigate(frontend_url)
    await asyncio.sleep(1)

    # 获取快照，查找账号相关元素
    snapshot = await browser_helper.get_snapshot()
    assert snapshot is not None

    # 这里可以添加具体的页面导航测试
    # 例如点击账号菜单、查看账号列表等
