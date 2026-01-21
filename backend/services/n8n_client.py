# -*- coding: utf-8 -*-
"""
n8n Webhook客户端
用这个来和n8n工作流通信，简单高效！
"""

import httpx
from typing import Any, Dict, Optional
from loguru import logger
from backend.config import N8N_WEBHOOK_URL, N8N_TIMEOUT


class N8nClient:
    """
    n8n Webhook客户端

    注意：所有与n8n的通信都通过这个类！
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化n8n客户端

        Args:
            base_url: n8n webhook基础URL，默认从配置读取
        """
        self.base_url = base_url or N8N_WEBHOOK_URL
        self.timeout = N8N_TIMEOUT

    async def call(
        self,
        workflow: str,
        data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        调用n8n工作流

        Args:
            workflow: 工作流名称（如 "distill-keywords"）
            data: 发送给工作流的数据
            timeout: 超时时间（秒），默认使用配置值

        Returns:
            工作流返回的JSON数据
        """
        url = f"{self.base_url}/{workflow}"
        timeout = timeout or self.timeout

        logger.info(f"调用n8n工作流: {workflow}")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                logger.info(f"n8n工作流响应: {workflow} - {result.get('status', 'success')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"n8n工作流超时: {workflow}")
            return {"status": "error", "message": "请求超时"}

        except httpx.HTTPStatusError as e:
            logger.error(f"n8n工作流HTTP错误: {workflow} - {e.response.status_code}")
            return {"status": "error", "message": f"HTTP错误: {e.response.status_code}"}

        except Exception as e:
            logger.error(f"n8n工作流调用失败: {workflow} - {e}")
            return {"status": "error", "message": str(e)}

    async def test_connection(self) -> bool:
        """
        测试与n8n的连接

        Returns:
            是否连接成功
        """
        try:
            result = await self.call("test-connection", {})
            return result.get("status") == "ok"
        except Exception:
            return False


# 全局单例
_n8n_client: Optional[N8nClient] = None


def get_n8n_client() -> N8nClient:
    """
    获取n8n客户端单例

    注意：这是对外暴露的主要接口！
    """
    global _n8n_client
    if _n8n_client is None:
        _n8n_client = N8nClient()
    return _n8n_client
