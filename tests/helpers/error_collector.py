# -*- coding: utf-8 -*-
"""
错误收集器
收集测试失败时的各种信息
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict


class ErrorCollector:
    """
    错误收集器
    我写的工具能帮你快速定位问题
    """

    def __init__(self, report_dir: Path = None):
        """
        初始化
        :param report_dir: 报告目录，默认为tests/reports
        """
        if report_dir is None:
            report_dir = Path(__file__).parent.parent / "reports"

        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # 创建时间戳子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.report_dir / timestamp
        self.session_dir.mkdir(exist_ok=True)

    def get_session_dir(self) -> Path:
        """获取当前会话目录"""
        return self.session_dir

    async def save_failure(self, test_name: str, browser_helper=None, error: Exception = None):
        """
        保存测试失败信息
        :param test_name: 测试名称
        :param browser_helper: 浏览器辅助工具实例
        :param error: 错误对象
        """
        test_dir = self.session_dir / test_name.replace("/", "_").replace("\\", "_")
        test_dir.mkdir(exist_ok=True)

        # 1. 截图
        if browser_helper:
            await self._save_screenshot(test_dir, test_name, browser_helper)
            await self._save_page_source(test_dir, test_name, browser_helper)
            await self._save_console_logs(test_dir, test_name, browser_helper)

        # 2. 保存错误信息
        if error:
            self._save_error_summary(test_dir, test_name, error)

        print(f"[CAMERA] 错误信息已保存到: {test_dir}")

    async def _save_screenshot(self, test_dir: Path, test_name: str, browser_helper):
        """保存截图"""
        try:
            screenshot_path = test_dir / "screenshot.png"
            await browser_helper.take_screenshot(str(screenshot_path))
        except Exception as e:
            print(f"[WARN] 截图保存失败: {e}")

    async def _save_page_source(self, test_dir: Path, test_name: str, browser_helper):
        """保存页面快照"""
        try:
            snapshot = await browser_helper.get_snapshot()
            if snapshot:
                source_path = test_dir / "page_snapshot.txt"
                with open(source_path, "w", encoding="utf-8") as f:
                    if isinstance(snapshot, dict):
                        f.write(json.dumps(snapshot, ensure_ascii=False, indent=2))
                    else:
                        f.write(str(snapshot))
        except Exception as e:
            print(f"[WARN] 页面快照保存失败: {e}")

    async def _save_console_logs(self, test_dir: Path, test_name: str, browser_helper):
        """保存控制台日志"""
        try:
            console_errors = await browser_helper.get_console_errors()
            if console_errors:
                log_path = test_dir / "console_errors.log"
                with open(log_path, "w", encoding="utf-8") as f:
                    for error in console_errors:
                        f.write(f"{error}\n")
        except Exception as e:
            print(f"[WARN] 控制台日志保存失败: {e}")

    def _save_error_summary(self, test_dir: Path, test_name: str, error: Exception):
        """保存错误摘要"""
        summary_path = test_dir / "error_summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"测试名称: {test_name}\n")
            f.write(f"失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"错误类型: {type(error).__name__}\n")
            f.write(f"错误信息: {str(error)}\n")
            f.write("="*50 + "\n")
            if hasattr(error, "__traceback__"):
                import traceback
                f.write("\n堆栈信息:\n")
                traceback.print_exception(type(error), error, error.__traceback__, file=f)

    def save_json(self, name: str, data: Any):
        """保存JSON数据"""
        json_path = self.session_dir / f"{name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return json_path

    def save_text(self, name: str, content: str):
        """保存文本内容"""
        text_path = self.session_dir / f"{name}.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(content)
        return text_path

    def list_failures(self) -> list:
        """列出所有失败的测试目录"""
        failures = []
        for item in self.session_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                failures.append(item)
        return failures
