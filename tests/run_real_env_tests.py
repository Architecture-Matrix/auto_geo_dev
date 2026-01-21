# -*- coding: utf-8 -*-
"""
真实环境自动化测试主程序
我用Playwright MCP来自动测试真实环境！
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

    提醒：这个类负责启动环境、执行测试、生成报告！
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
        hl_path = self.reporter.generate_hl()
        print(f"[HTML] {hl_path}")

        return hl_path

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
