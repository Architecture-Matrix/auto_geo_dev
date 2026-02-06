# -*- coding: utf-8 -*-
"""
n8n 服务封装 - 首席架构师云端对齐版
1. 路径对齐：将 generate_questions 路由重定向至 keyword-distill (解决云端 404)
2. 零依赖：严格从 config 读取配置，适配所有同事环境
3. 指纹加固：维持浏览器 UA 注入，绕过 Cloudflare 503
"""

import httpx
import json
from typing import Any, Literal, Optional, List, Dict
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict

# 🌟 引入全局配置
from backend.config import N8N_WEBHOOK_URL, N8N_TIMEOUT


# ==================== 配置 ====================

class N8nConfig:
    # 动态获取配置，确保本地/云端无缝切换
    WEBHOOK_BASE = N8N_WEBHOOK_URL.rstrip('/')

    # 超时与重试
    TIMEOUT_SHORT = 45.0
    TIMEOUT_LONG = float(N8N_TIMEOUT)
    MAX_RETRIES = 1

    # 🌟 指纹对齐：模拟真实浏览器防止 503
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


# ==================== 请求模型 ====================

class KeywordDistillRequest(BaseModel):
    keywords: Optional[List[str]] = None
    project_id: Optional[int] = None
    core_kw: Optional[str] = None
    target_info: Optional[str] = None
    prefixes: Optional[str] = None
    suffixes: Optional[str] = None
    # 增加类型标记，供 n8n 内部逻辑判断
    task_type: str = "distill"


class GenerateQuestionsRequest(BaseModel):
    question: str
    count: int = 10
    # 🌟 关键：标记为问题生成任务
    task_type: str = "expand_questions"


class GeoArticleRequest(BaseModel):
    keyword: str
    platform: str = "zhihu"
    requirements: str = ""
    word_count: int = 1200


# ==================== 响应模型 ====================

class N8nResponse(BaseModel):
    status: Literal["success", "error", "processing"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== 服务类 ====================

class N8nService:
    def __init__(self, config: Optional[N8nConfig] = None):
        self.config = config or N8nConfig()
        self.log = logger.bind(module="AI中台")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.TIMEOUT_SHORT,
                follow_redirects=True,
                headers=self.config.HEADERS
            )
        return self._client

    async def _call_webhook(self, endpoint: str, payload: Dict[str, Any],
                            timeout: Optional[float] = None) -> N8nResponse:
        """底层调用逻辑"""
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.config.WEBHOOK_BASE}/{clean_endpoint}"
        timeout_val = timeout or self.config.TIMEOUT_SHORT

        self.log.info(f"🛰️ 正在外发云端 AI 请求: {url}")

        for attempt in range(self.config.MAX_RETRIES + 1):
            try:
                response = await self.client.post(url, json=payload, timeout=timeout_val)

                # 诊断 503
                if response.status_code == 503:
                    return N8nResponse(status="error",
                                       error="503 Service Unavailable: 请检查云端工作流是否已点亮 Active")

                # 诊断 404
                if response.status_code == 404:
                    return N8nResponse(status="error",
                                       error=f"404 Not Found: 路径 /{clean_endpoint} 在云端未注册或未激活")

                if response.status_code != 200:
                    return N8nResponse(status="error", error=f"HTTP {response.status_code}: {response.text[:100]}")

                res_data = response.json()
                if isinstance(res_data, list): res_data = res_data[0]

                if isinstance(res_data, dict) and "status" not in res_data:
                    return N8nResponse(status="success", data=res_data)

                return N8nResponse(**res_data)

            except Exception as e:
                if attempt == self.config.MAX_RETRIES:
                    return N8nResponse(status="error", error=str(e))
        return N8nResponse(status="error", error="Unknown Error")

    # ==================== 业务方法 ====================

    async def distill_keywords(self, **kwargs) -> N8nResponse:
        """关键词蒸馏"""
        payload = KeywordDistillRequest(**kwargs).model_dump(exclude_none=True)
        # 路径对齐：使用云端存在的 webhook
        return await self._call_webhook("keyword-distill", payload)

    async def generate_questions(self, question: str, count: int = 10) -> N8nResponse:
        """
        生成问题变体
        🌟 首席架构师修正：由于云端未注册 /generate-questions 路径，
        我们将请求转发至 /keyword-distill 接口，并携带 task_type 参数。
        """
        payload = GenerateQuestionsRequest(question=question, count=count).model_dump()
        return await self._call_webhook("keyword-distill", payload)

    async def generate_geo_article(self, **kwargs) -> N8nResponse:
        """生成 GEO 优化文章"""
        payload = GeoArticleRequest(**kwargs).model_dump()
        return await self._call_webhook("geo-article-generate", payload, timeout=self.config.TIMEOUT_LONG)


# ==================== 单例模式 ====================

_instance: Optional[N8nService] = None


async def get_n8n_service() -> N8nService:
    global _instance
    if _instance is None:
        _instance = N8nService()
    return _instance