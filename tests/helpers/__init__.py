# -*- coding: utf-8 -*-
"""
测试辅助工具模块
写的测试辅助工具，好使！
"""

from .app_launcher import AppLauncher
from .browser_helper import BrowserHelper
from .mock_data import MockData
from .error_collector import ErrorCollector

__all__ = ["AppLauncher", "BrowserHelper", "MockData", "ErrorCollector"]
