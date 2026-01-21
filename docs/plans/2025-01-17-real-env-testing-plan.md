# AutoGeo 真实环境自动化测试实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 使用Playwright MCP工具对真实环境的前后端进行自动化测试，收集测试结果并生成反馈报告

**Architecture:** 启动真实前后端服务 → 使用Playwright MCP进行浏览器UI测试 → 收录截图/日志 → 生成HTML反馈报告

**Tech Stack:** Playwright MCP、Python pytest、HTML报告生成

---

## 计划概述

### 测试目标
- 验证前后端服务正常运行
- 验证核心功能UI交互正确
- 验证API接口返回正确
- 收集错误截图和日志
- 生成可视化测试报告

### 测试环境
- **后端**: http://127.0.0.1:8001 (FastAPI)
- **前端**: http://127.0.0.1:5173 (Vue3 + Vite)
- **浏览器**: Chromium (通过Playwright MCP)

### 测试模块
| 模块 | 测试点 | 优先级 |
|------|--------|--------|
| 服务健康检查 | 前后端服务启动 | P0 |
| 账号管理 | 添加/删除/列表账号 | P0 |
| 文章编辑 | 标题/内容输入、保存 | P0 |
| 发布流程 | 单/多平台发布 | P0 |
| 关键词管理 | 项目/关键词CRUD | P1 |
| 收录检测 | AI平台检测 | P1 |

---

## Task 1: 创建测试报告目录结构

**Files:**
- Create: `tests/reports/.gitkeep`
- Create: `tests/reports/screenshots/.gitkeep`
- Create: `tests/reports/logs/.gitkeep`

**Step 1: 创建目录结构**

```bash
# PowerShell命令
mkdir -p tests/reports/screenshots
mkdir -p tests/reports/logs
echo "" > tests/reports/.gitkeep
echo "" > tests/reports/screenshots/.gitkeep
echo "" > tests/reports/logs/.gitkeep
```

**Step 2: 验证目录创建**

Run: `ls tests/reports`
Expected: 显示screenshots和logs子目录

**Step 3: Commit**

```bash
git add tests/reports/
git commit -m "test: 创建测试报告目录结构"
```

---

## Task 2: 创建测试结果收集器

**Files:**
- Create: `tests/helpers/test_reporter.py`

**Step 1: 编写测试报告生成器**

```python
# -*- coding: utf-8 -*-
"""
测试报告生成器
开发者我用这个来收集测试结果并生成HTML报告！
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """单个测试结果"""
    name: str
    status: str  # pass/fail/skip
    duration: float
    error_message: str = ""
    screenshot_path: str = ""
    console_errors: List[str] = field(default_factory=list)
    network_errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class TestSuite:
    """测试套件"""
    name: str
    tests: List[TestResult] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_time: str = ""
    total_duration: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == "fail")

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status == "skip")

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def pass_rate(self) -> str:
        if self.total == 0:
            return "0%"
        return f"{(self.passed / self.total) * 100:.1f}%"


class TestReporter:
    """
    测试报告收集器

    开发者提醒：负责收集所有测试结果并生成HTML报告！
    """

    def __init__(self, report_dir: Path):
        """
        初始化报告收集器

        Args:
            report_dir: 报告输出目录
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.screenshot_dir = self.report_dir / "screenshots"
        self.log_dir = self.report_dir / "logs"

        self.screenshot_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        self.suites: List[TestSuite] = []
        self.current_suite: Optional[TestSuite] = None

    def start_suite(self, name: str):
        """开始一个测试套件"""
        self.current_suite = TestSuite(name=name)
        self.suites.append(self.current_suite)

    def end_suite(self):
        """结束当前测试套件"""
        if self.current_suite:
            self.current_suite.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.current_suite.total_duration = sum(t.duration for t in self.current_suite.tests)

    def add_result(self, test: TestResult):
        """添加测试结果"""
        if self.current_suite:
            self.current_suite.tests.append(test)

    def add_pass(self, name: str, duration: float):
        """添加通过结果"""
        self.add_result(TestResult(name=name, status="pass", duration=duration))

    def add_fail(self, name: str, duration: float, error_message: str,
                 screenshot_path: str = "", console_errors: List[str] = None):
        """添加失败结果"""
        self.add_result(TestResult(
            name=name,
            status="fail",
            duration=duration,
            error_message=error_message,
            screenshot_path=screenshot_path,
            console_errors=console_errors or []
        ))

    def add_skip(self, name: str, duration: float = 0):
        """添加跳过结果"""
        self.add_result(TestResult(name=name, status="skip", duration=duration))

    def save_screenshot(self, name: str, content: bytes) -> str:
        """
        保存截图

        Args:
            name: 截图名称（不含扩展名）
            content: 截图二进制内容

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = self.screenshot_dir / filename

        with open(path, "wb") as f:
            f.write(content)

        return str(path)

    def save_log(self, name: str, content: str) -> str:
        """
        保存日志

        Args:
            name: 日志名称
            content: 日志内容

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.log"
        path = self.log_dir / filename

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(path)

    def save_json(self):
        """保存JSON格式的原始数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"results_{timestamp}.json"

        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suites": [
                {
                    "name": suite.name,
                    "start_time": suite.start_time,
                    "end_time": suite.end_time,
                    "total_duration": suite.total_duration,
                    "total": suite.total,
                    "passed": suite.passed,
                    "failed": suite.failed,
                    "skipped": suite.skipped,
                    "pass_rate": suite.pass_rate,
                    "tests": [
                        {
                            "name": t.name,
                            "status": t.status,
                            "duration": t.duration,
                            "error_message": t.error_message,
                            "screenshot_path": t.screenshot_path,
                            "console_errors": t.console_errors,
                            "timestamp": t.timestamp
                        }
                        for t in suite.tests
                    ]
                }
                for suite in self.suites
            ]
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return json_path

    def generate_html(self) -> str:
        """
        生成HTML报告

        Returns:
            HTML报告文件路径
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 计算总体统计
        total_tests = sum(s.total for s in self.suites)
        total_passed = sum(s.passed for s in self.suites)
        total_failed = sum(s.failed for s in self.suites)
        total_skipped = sum(s.skipped for s in self.suites)
        total_duration = sum(s.total_duration for s in self.suites)
        overall_pass_rate = f"{(total_passed / total_tests * 100):.1f}%" if total_tests > 0 else "0%"

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoGeo 测试报告 - {timestamp}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}

        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}

        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .summary-card .label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}

        .summary-card.total .value {{ color: #667eea; }}
        .summary-card.passed .value {{ color: #28a745; }}
        .summary-card.failed .value {{ color: #dc3545; }}
        .summary-card.rate .value {{ color: #17a2b8; }}

        .suites {{
            padding: 30px;
        }}

        .suite {{
            margin-bottom: 30px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}

        .suite-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }}

        .suite-header:hover {{
            background: #e9ecef;
        }}

        .suite-title {{
            font-weight: 600;
            font-size: 16px;
        }}

        .suite-stats {{
            display: flex;
            gap: 15px;
            font-size: 12px;
        }}

        .suite-stats span {{
            padding: 2px 8px;
            border-radius: 10px;
        }}

        .suite-stats .total {{ background: #e9ecef; }}
        .suite-stats .passed {{ background: #d4edda; color: #155724; }}
        .suite-stats .failed {{ background: #f8d7da; color: #721c24; }}

        .test-list {{
            display: none;
        }}

        .test-list.show {{
            display: block;
        }}

        .test-item {{
            padding: 15px 20px;
            border-top: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .test-item.pass {{
            background: #f8fff9;
        }}

        .test-item.fail {{
            background: #fff8f8;
        }}

        .test-status {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 12px;
        }}

        .test-item.pass .test-status {{
            background: #28a745;
            color: white;
        }}

        .test-item.fail .test-status {{
            background: #dc3545;
            color: white;
        }}

        .test-item.skip .test-status {{
            background: #6c757d;
            color: white;
        }}

        .test-info {{
            flex: 1;
        }}

        .test-name {{
            font-weight: 500;
            margin-bottom: 3px;
        }}

        .test-duration {{
            font-size: 12px;
            color: #999;
        }}

        .test-error {{
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 12px;
            font-family: monospace;
        }}

        .test-screenshot {{
            margin-top: 10px;
        }}

        .test-screenshot img {{
            max-width: 100%;
            max-height: 300px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}

        .console-errors {{
            margin-top: 10px;
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
        }}

        .console-errors h4 {{
            font-size: 12px;
            margin-bottom: 5px;
            color: #856404;
        }}

        .console-errors ul {{
            list-style: none;
            font-size: 11px;
            font-family: monospace;
        }}

        .footer {{
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            color: #666;
            font-size: 12px;
        }}

        .toggle-icon {{
            transition: transform 0.2s;
        }}

        .suite-header.open .toggle-icon {{
            transform: rotate(180deg);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AutoGeo 真实环境测试报告</h1>
            <p>生成时间: {timestamp} | 环境: 真实环境 | 测试框架: Playwright MCP</p>
        </div>

        <div class="summary">
            <div class="summary-card total">
                <div class="value">{total_tests}</div>
                <div class="label">总测试数</div>
            </div>
            <div class="summary-card passed">
                <div class="value">{total_passed}</div>
                <div class="label">通过</div>
            </div>
            <div class="summary-card failed">
                <div class="value">{total_failed}</div>
                <div class="label">失败</div>
            </div>
            <div class="summary-card rate">
                <div class="value">{overall_pass_rate}</div>
                <div class="label">通过率</div>
            </div>
        </div>

        <div class="suites">
"""

        # 生成每个测试套件
        for suite in self.suites:
            html_content += f"""
            <div class="suite">
                <div class="suite-header" onclick="toggleSuite(this)">
                    <div class="suite-title">{suite.name}</div>
                    <div class="suite-stats">
                        <span class="total">总计: {suite.total}</span>
                        <span class="passed">通过: {suite.passed}</span>
                        <span class="failed">失败: {suite.failed}</span>
                        <span class="toggle-icon">▼</span>
                    </div>
                </div>
                <div class="test-list">
"""

            # 生成每个测试
            for test in suite.tests:
                status_class = test.status
                status_icon = "✓" if test.status == "pass" else ("✗" if test.status == "fail" else "-")

                html_content += f"""
                    <div class="test-item {status_class}">
                        <div class="test-status">{status_icon}</div>
                        <div class="test-info">
                            <div class="test-name">{test.name}</div>
                            <div class="test-duration">耗时: {test.duration:.2f}s | {test.timestamp}</div>
"""

                # 添加错误信息
                if test.status == "fail" and test.error_message:
                    html_content += f"""
                            <div class="test-error">{test.error_message}</div>
"""

                # 添加截图
                if test.screenshot_path:
                    # 转换为相对路径
                    rel_path = Path(test.screenshot_path).relative_to(self.report_dir)
                    html_content += f"""
                            <div class="test-screenshot">
                                <img src="{rel_path}" alt="失败截图">
                            </div>
"""

                # 添加控制台错误
                if test.console_errors:
                    html_content += """
                            <div class="console-errors">
                                <h4>控制台错误:</h4>
                                <ul>
"""
                    for error in test.console_errors:
                        html_content += f"                                    <li>{error}</li>\n"
                    html_content += """
                                </ul>
                            </div>
"""

                html_content += """
                        </div>
                    </div>
"""

            html_content += """
                </div>
            </div>
"""

        # 添加JavaScript和结尾
        html_content += f"""
        </div>

        <div class="footer">
            <p>AutoGeo 自动化测试系统 | 总耗时: {total_duration:.2f}s</p>
        </div>
    </div>

    <script>
        function toggleSuite(header) {{
            header.classList.toggle('open');
            const list = header.nextElementSibling;
            list.classList.toggle('show');
        }}

        // 自动展开失败的测试套件
        document.addEventListener('DOMContentLoaded', function() {{
            const suites = document.querySelectorAll('.suite');
            suites.forEach(function(suite) {{
                const failed = suite.querySelector('.test-item.fail');
                if (failed) {{
                    suite.querySelector('.suite-header').click();
                }}
            }});
        }});
    </script>
</body>
</html>
"""

        # 保存HTML报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.report_dir / f"report_{timestamp}.html"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_path)


# 便捷函数
def create_reporter(report_dir: str = None) -> TestReporter:
    """创建测试报告收集器"""
    if report_dir is None:
        report_dir = Path(__file__).parent.parent / "reports"
    return TestReporter(Path(report_dir))
```

**Step 2: 验证文件创建**

Run: `ls tests/helpers/test_reporter.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add tests/helpers/test_reporter.py
git commit -m "test: 添加测试报告收集器"
```

---

## Task 3: 创建真实环境测试主程序

**Files:**
- Create: `tests/run_real_env_tests.py`

**Step 1: 编写真实环境测试主程序**

```python
# -*- coding: utf-8 -*-
"""
真实环境自动化测试主程序
开发者我用Playwright MCP来自动测试真实环境！
"""

import sys
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.helpers.test_reporter import TestReporter


class RealEnvTester:
    """
    真实环境测试器

    开发者提醒：这个类负责启动环境、执行测试、生成报告！
    """

    def __init__(self):
        self.project_root = project_root
        self.backend_url = "http://127.0.0.1:8001"
        self.frontend_url = "http://127.0.0.1:5173"
        self.backend_proc = None
        self.frontend_proc = None
        self.reporter = TestReporter(self.project_root / "tests" / "reports")
        self.mcp_browser = None  # Playwright MCP工具实例

    def check_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result != 0  # 端口未被占用

    def start_backend(self) -> bool:
        """启动后端服务"""
        print("\n[INFO] 正在启动后端服务...")

        # 检查后端是否已运行
        try:
            import requests
            resp = requests.get(f"{self.backend_url}/api/health", timeout=2)
            if resp.status_code == 200:
                print(f"[OK] 后端服务已运行: {self.backend_url}")
                return True
        except:
            pass

        # 启动后端
        cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host=127.0.0.1",
            "--port=8001",
            "--log-level=warning"
        ]

        self.backend_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.project_root)
        )

        # 等待服务启动
        for i in range(30):
            try:
                import requests
                resp = requests.get(f"{self.backend_url}/api/health", timeout=2)
                if resp.status_code == 200:
                    print(f"[OK] 后端服务启动成功: {self.backend_url}")
                    return True
            except:
                time.sleep(1)
                print(f"    等待后端启动... ({i+1}/30)")

        print("[FAIL] 后端服务启动超时！")
        return False

    def start_frontend(self) -> bool:
        """启动前端服务"""
        print("\n[INFO] 正在启动前端服务...")

        # 检查前端是否已运行
        try:
            import requests
            resp = requests.get(self.frontend_url, timeout=2)
            if resp.status_code == 200:
                print(f"[OK] 前端服务已运行: {self.frontend_url}")
                return True
        except:
            pass

        # 启动前端
        cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]

        self.frontend_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.project_root / "fronted"),
            shell=True
        )

        # Vite启动较慢
        for i in range(60):
            try:
                import requests
                resp = requests.get(self.frontend_url, timeout=2)
                if resp.status_code == 200:
                    print(f"[OK] 前端服务启动成功: {self.frontend_url}")
                    return True
            except:
                time.sleep(1)
                if i % 10 == 0:
                    print(f"    等待前端启动... ({i+1}/60)")

        print("[FAIL] 前端服务启动超时！")
        return False

    def stop_services(self):
        """停止所有服务"""
        print("\n[STOP] 正在停止服务...")

        if self.backend_proc:
            self.backend_proc.terminate()
            try:
                self.backend_proc.wait(timeout=5)
            except:
                self.backend_proc.kill()

        if self.frontend_proc:
            self.frontend_proc.terminate()
            try:
                self.frontend_proc.wait(timeout=5)
            except:
                self.frontend_proc.kill()

        print("[OK] 所有服务已停止")

    async def run_test_suite(self, suite_name: str, tests: list) -> bool:
        """
        运行测试套件

        Args:
            suite_name: 套件名称
            tests: 测试函数列表

        Returns:
            是否全部通过
        """
        print(f"\n{'='*50}")
        print(f"[SUITE] {suite_name}")
        print(f"{'='*50}")

        self.reporter.start_suite(suite_name)
        all_passed = True

        for test_func in tests:
            test_name = test_func.__name__
            print(f"\n[TEST] {test_name}...", end=" ")

            start_time = time.time()

            try:
                result = await test_func(self)
                duration = time.time() - start_time

                if result.get("success"):
                    print(f"✓ PASS ({duration:.2f}s)")
                    self.reporter.add_pass(test_name, duration)
                else:
                    print(f"✗ FAIL ({duration:.2f}s)")
                    all_passed = False
                    self.reporter.add_fail(
                        test_name,
                        duration,
                        result.get("error", "未知错误"),
                        result.get("screenshot", ""),
                        result.get("console_errors", [])
                    )

            except Exception as e:
                duration = time.time() - start_time
                print(f"✗ ERROR ({duration:.2f}s): {e}")
                all_passed = False
                self.reporter.add_fail(
                    test_name,
                    duration,
                    str(e)
                )

        self.reporter.end_suite()
        return all_passed

    async def test_backend_health(self) -> dict:
        """测试后端健康检查"""
        import requests

        try:
            resp = requests.get(f"{self.backend_url}/api/health", timeout=5)
            if resp.status_code == 200:
                return {"success": True}
            else:
                return {"success": False, "error": f"状态码: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_frontend_load(self) -> dict:
        """测试前端加载"""
        import requests

        try:
            resp = requests.get(self.frontend_url, timeout=10)
            if resp.status_code == 200:
                # 检查是否包含Vue应用标识
                if "auto-geo" in resp.text.lower() or "vue" in resp.text.lower():
                    return {"success": True}
                else:
                    return {"success": False, "error": "页面内容异常"}
            else:
                return {"success": False, "error": f"状态码: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_api_platforms(self) -> dict:
        """测试平台列表API"""
        import requests

        try:
            resp = requests.get(f"{self.backend_url}/api/platforms", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "platforms" in data and len(data["platforms"]) > 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": "平台列表为空"}
            else:
                return {"success": False, "error": f"状态码: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_browser_navigate_frontend(self) -> dict:
        """测试浏览器导航到前端"""
        if not self.mcp_browser:
            return {"success": False, "error": "Playwright MCP未初始化"}

        try:
            # 导航到前端
            await self.mcp_browser.browser_navigate(url=self.frontend_url)
            await asyncio.sleep(2)

            # 获取快照
            snapshot = await self.mcp_browser.browser_snapshot()

            if snapshot:
                # 检查控制台错误
                console_errors = await self.mcp_browser.browser_console_messages(level="error")

                return {
                    "success": True,
                    "console_errors": console_errors if isinstance(console_errors, list) else []
                }
            else:
                return {"success": False, "error": "无法获取页面快照"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_browser_screenshot(self) -> dict:
        """测试浏览器截图"""
        if not self.mcp_browser:
            return {"success": False, "error": "Playwright MCP未初始化"}

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tests/reports/screenshots/home_{timestamp}.png"

            await self.mcp_browser.browser_take_screenshot(filename=filename)

            # 验证文件存在
            if Path(filename).exists():
                return {"success": True, "screenshot": filename}
            else:
                return {"success": False, "error": "截图文件未生成"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_report(self) -> str:
        """生成测试报告"""
        print("\n[REPORT] 正在生成测试报告...")

        # 保存JSON
        json_path = self.reporter.save_json()
        print(f"[JSON] {json_path}")

        # 生成HTML
        html_path = self.reporter.generate_html()
        print(f"[HTML] {html_path}")

        return html_path

    async def run_all_tests(self, use_browser: bool = True) -> bool:
        """
        运行所有测试

        Args:
            use_browser: 是否使用浏览器测试

        Returns:
            是否全部通过
        """
        print("\n" + "="*50)
        print("[AutoGeo] 真实环境自动化测试开始")
        print("="*50)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"后端: {self.backend_url}")
        print(f"前端: {self.frontend_url}")
        print(f"浏览器测试: {'启用' if use_browser else '禁用'}")
        print("="*50)

        all_passed = True

        # 套件1: 服务健康检查
        all_passed &= await self.run_test_suite(
            "服务健康检查",
            [
                self.test_backend_health,
                self.test_frontend_load,
                self.test_api_platforms,
            ]
        )

        # 套件2: 浏览器测试（如果启用）
        if use_browser and self.mcp_browser:
            all_passed &= await self.run_test_suite(
                "浏览器UI测试",
                [
                    self.test_browser_navigate_frontend,
                    self.test_browser_screenshot,
                ]
            )

        # 生成报告
        report_path = self.generate_report()

        # 输出总结
        print("\n" + "="*50)
        print("[SUMMARY] 测试总结")
        print("="*50)

        for suite in self.reporter.suites:
            print(f"\n{suite.name}:")
            print(f"  通过: {suite.passed}/{suite.total}")
            print(f"  失败: {suite.failed}/{suite.total}")
            print(f"  通过率: {suite.pass_rate}")

        print("\n" + "="*50)
        if all_passed:
            print("[OK] 所有测试通过！")
        else:
            print("[FAIL] 存在测试失败，请查看报告！")
        print("="*50)

        return all_passed


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="AutoGeo 真实环境自动化测试")
    parser.add_argument("--no-browser", action="store_true", help="禁用浏览器测试")
    parser.add_argument("--skip-start", action="store_true", help="跳过服务启动")
    args = parser.parse_args()

    tester = RealEnvTester()

    try:
        # 启动服务（如果需要）
        if not args.skip_start:
            if not tester.start_backend():
                print("\n[ERROR] 后端启动失败，退出测试！")
                return 1

            if not tester.start_frontend():
                print("\n[ERROR] 前端启动失败，退出测试！")
                return 1

        # 初始化Playwright MCP（如果需要浏览器测试）
        if not args.no_browser:
            print("\n[INFO] 初始化Playwright MCP...")
            # 这里需要实际的MCP浏览器工具
            # tester.mcp_browser = <mcp_browser_tool>
            print("[WARN] Playwright MCP需要手动初始化")

        # 运行测试
        all_passed = await tester.run_all_tests(use_browser=not args.no_browser)

        # 返回退出码
        return 0 if all_passed else 1

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] 测试被用户中断")
        return 130
    finally:
        # 停止服务
        if not args.skip_start:
            tester.stop_services()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

**Step 2: 验证文件创建**

Run: `ls tests/run_real_env_tests.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add tests/run_real_env_tests.py
git commit -m "test: 添加真实环境测试主程序"
```

---

## Task 4: 创建API测试模块

**Files:**
- Create: `tests/test_api/test_health.py`

**Step 1: 编写API健康检查测试**

```python
# -*- coding: utf-8 -*-
"""
API健康检查测试
开发者我用这个来验证后端API是否正常！
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
```

**Step 2: 验证文件创建**

Run: `ls tests/test_api/test_health.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add tests/test_api/
git commit -m "test: 添加API健康检查测试"
```

---

## Task 5: 创建浏览器测试用例

**Files:**
- Create: `tests/test_browser/test_navigation.py`

**Step 1: 编写浏览器导航测试**

```python
# -*- coding: utf-8 -*-
"""
浏览器导航测试
开发者我用Playwright MCP来测试前端页面！
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
```

**Step 2: 验证文件创建**

Run: `ls tests/test_browser/test_navigation.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add tests/test_browser/
git commit -m "test: 添加浏览器导航测试"
```

---

## Task 6: 创建测试执行脚本

**Files:**
- Create: `tests/exec_real_test.py`

**Step 1: 编写一键执行脚本**

```python
# -*- coding: utf-8 -*-
"""
一键执行真实环境测试
开发者我用这个来快速启动测试！
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.run_real_env_tests import RealEnvTester


async def main():
    """主函数"""
    print("="*50)
    print("[AutoGeo] 一键执行真实环境测试")
    print("="*50)

    # 创建测试器
    tester = RealEnvTester()

    try:
        # 启动服务
        print("\n[STEP 1/3] 启动服务...")
        backend_ok = tester.start_backend()
        frontend_ok = tester.start_frontend()

        if not (backend_ok and frontend_ok):
            print("\n[ERROR] 服务启动失败！")
            print("提示: 可以先手动启动服务，然后运行 --skip-start")
            return 1

        # 运行测试（不使用浏览器MCP，先测试API）
        print("\n[STEP 2/3] 运行API测试...")
        all_passed = await tester.run_all_tests(use_browser=False)

        # 生成报告
        print("\n[STEP 3/3] 生成报告...")
        report_path = tester.generate_report()
        print(f"\n[REPORT] 测试报告已生成:")
        print(f"   file:///{report_path.replace(chr(92), '/')}")

        return 0 if all_passed else 1

    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] 测试被中断")
        return 130
    finally:
        tester.stop_services()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    input("\n按回车键退出...")
    sys.exit(exit_code)
```

**Step 2: 验证文件创建**

Run: `ls tests/exec_real_test.py`
Expected: 文件存在

**Step 3: Commit**

```bash
git add tests/exec_real_test.py
git commit -m "test: 添加一键执行测试脚本"
```

---

## 执行流程

### 手动执行步骤

**1. 启动后端服务**
```bash
cd E:/CodingPlace/AI/auto_geo
python backend/main.py
```

**2. 启动前端服务（新终端）**
```bash
cd E:/CodingPlace/AI/auto_geo/fronted
npm run dev
```

**3. 运行测试（第三个终端）**
```bash
cd E:/CodingPlace/AI/auto_geo
python tests/exec_real_test.py
```

### 使用Playwright MCP执行UI测试

**Step 1: 导航到前端**
```
browser_navigate: url="http://127.0.0.1:5173"
```

**Step 2: 获取页面快照**
```
browser_snapshot
```

**Step 3: 检查控制台错误**
```
browser_console_messages: level="error"
```

**Step 4: 截图保存**
```
browser_take_screenshot: filename="tests/reports/screenshots/test_001.png"
```

**Step 5: 测试交互（如果有账号）**
```
# 点击账号菜单
browser_click: element="账号菜单", ref="<从snapshot获取的ref>"

# 等待页面加载
browser_wait_for: time=2

# 再次截图
browser_take_screenshot: filename="tests/reports/screenshots/test_002.png"
```

---

## 反馈报告格式

测试完成后，将生成以下报告：

### HTML报告
- 位置: `tests/reports/report_<timestamp>.html`
- 内容:
  - 总体统计（通过/失败/通过率）
  - 每个测试套件的详细结果
  - 失败测试的错误信息和截图
  - 控制台错误列表

### JSON报告
- 位置: `tests/reports/results_<timestamp>.json`
- 内容: 原始测试数据，可用于后续分析

### 截图
- 位置: `tests/reports/screenshots/`
- 格式: `<test_name>_<timestamp>.png`

---

## 附录: 测试检查清单

### 环境检查
- [ ] Python 3.10+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] 后端依赖已安装 (`pip install -r backend/requirements.txt`)
- [ ] 前端依赖已安装 (`cd fronted && npm install`)
- [ ] 端口8001未被占用
- [ ] 端口5173未被占用

### 服务检查
- [ ] 后端健康检查接口返回200
- [ ] 前端首页加载成功
- [ ] 平台列表接口返回数据

### 功能检查
- [ ] 账号列表可以加载
- [ ] 可以添加新账号
- [ ] 文章编辑器可以打开
- [ ] 可以输入标题和内容
- [ ] 发布按钮可用

### 测试报告检查
- [ ] HTML报告生成
- [ ] JSON报告生成
- [ ] 截图保存成功
- [ ] 失败测试有详细错误信息

---

**计划完成**

下一步：选择执行方式
1. 在当前会话逐个任务执行（使用superpowers:subagent-driven-development）
2. 开启新会话批量执行（使用superpowers:executing-plans）
