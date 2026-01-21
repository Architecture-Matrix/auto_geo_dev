# -*- coding: utf-8 -*-
"""
应用启动器
自动启动前后端服务
"""

import time
import subprocess
import sys
from pathlib import Path
import requests


class AppLauncher:
    """应用启动器 - 写的一键启动工具"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_process = None
        self.frontend_process = None
        self.backend_url = "http://127.0.0.1:8001"
        self.frontend_url = "http://127.0.0.1:5173"

    def start_backend(self) -> bool:
        """启动后端服务"""
        print("[INFO] 启动后端服务...")

        cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host=127.0.0.1",
            "--port=8001",
            "--log-level=warning"
        ]

        self.backend_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.project_root)
        )

        # 等待服务就绪
        for i in range(30):
            try:
                resp = requests.get(f"{self.backend_url}/api/health", timeout=2)
                if resp.status_code == 200:
                    print(f"[OK] 后端启动成功: {self.backend_url}")
                    return True
            except:
                time.sleep(1)

        print("[FAIL] 后端启动超时！")
        return False

    def start_frontend(self) -> bool:
        """启动前端服务"""
        print("[INFO] 启动前端服务...")

        cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]

        self.frontend_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.project_root / "fronted"),
            shell=True
        )

        # Vite启动比较慢，多等一会
        for i in range(60):
            try:
                resp = requests.get(self.frontend_url, timeout=2)
                if resp.status_code == 200:
                    print(f"[OK] 前端启动成功: {self.frontend_url}")
                    return True
            except:
                time.sleep(1)

        print("[FAIL] 前端启动超时！")
        return False

    def start_all(self) -> bool:
        """启动所有服务"""
        backend_ok = self.start_backend()
        frontend_ok = self.start_frontend()
        return backend_ok and frontend_ok

    def stop_all(self):
        """停止所有服务"""
        print("[STOP] 停止所有服务...")

        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait(timeout=5)

        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process.wait(timeout=5)

        print("[OK] 所有服务已停止")

    def health_check(self) -> dict:
        """健康检查"""
        result = {
            "backend": False,
            "frontend": False
        }

        try:
            resp = requests.get(f"{self.backend_url}/api/health", timeout=2)
            result["backend"] = resp.status_code == 200
        except:
            pass

        try:
            resp = requests.get(self.frontend_url, timeout=2)
            result["frontend"] = resp.status_code == 200
        except:
            pass

        return result
