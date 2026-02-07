# -*- coding: utf-8 -*-
"""
n8n 服务封装 - 首席架构师加固版
1. 架构对齐：严格同步 backend.config，拒绝硬编码 localhost
2. 指纹对齐：注入真实 User-Agent 绕过 Cloudflare 503 拦截
3. 路径对齐：将 generate_questions 路由重定向至 keyword-distill (解决云端 404)
"""

import httpx
import json
from typing import Any, Literal, Optional, List, Dict
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict

# 🌟 引入全局配置，确保本地/云端无缝切换
from backend.config import N8N_WEBHOOK_URL, N8N_TIMEOUT


# ==================== 配置 ====================

class N8nConfig:
    # 🌟 修复：从全局配置读取并清洗路径
    WEBHOOK_BASE = N8N_WEBHOOK_URL.rstrip('/')

    # 超时配置
    TIMEOUT_SHORT = 45.0
    TIMEOUT_LONG = float(N8N_TIMEOUT)

    # 重试配置
    MAX_RETRIES = 1

    # 🌟 指纹对齐：模拟真实浏览器防止 Cloudflare 拦截
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
    task_type: str = "distill"  # 任务标识


class GenerateQuestionsRequest(BaseModel):
    question: str
    count: int = 10
    task_type: str = "expand_questions"  # 任务标识


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
            # 🌟 注入全局 Headers
            self._client = httpx.AsyncClient(
                timeout=self.config.TIMEOUT_SHORT,
                follow_redirects=True,
                headers=self.config.HEADERS
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_webhook(
            self,
            endpoint: str,
            payload: Dict[str, Any],
            timeout: Optional[float] = None
    ) -> N8nResponse:
        """底层统一调用逻辑"""
        clean_endpoint = endpoint.lstrip('/')
        url = f"{self.config.WEBHOOK_BASE}/{clean_endpoint}"
        timeout_val = timeout or self.config.TIMEOUT_SHORT

        self.log.info(f"🛰️ 正在外发云端 AI 请求: {url}")

        for attempt in range(self.config.MAX_RETRIES + 1):
            try:
                response = await self.client.post(url, json=payload, timeout=timeout_val)
                raw_text = response.text

                # 🌟 503 拦截专项诊断
                if response.status_code == 503:
                    self.log.error("❌ 503 拦截：请确认云端 n8n 工作流右上角是否已点亮 [Active] 按钮！")
                    return N8nResponse(status="error", error="n8n 生产环境未激活 (503)")

                if response.status_code != 200:
                    err_msg = f"HTTP {response.status_code}: {raw_text[:100]}"
                    return N8nResponse(status="error", error=err_msg)

                try:
                    res_data = response.json()
                    if isinstance(res_data, list):
                        res_data = res_data[0] if len(res_data) > 0 else {}

                    if isinstance(res_data, dict) and "status" not in res_data:
                        return N8nResponse(status="success", data=res_data)

                    return N8nResponse(**res_data)

                except json.JSONDecodeError:
                    if "Workflow started" in raw_text:
                        return N8nResponse(status="error", error="工作流缺少 'Respond to Webhook' 节点")
                    return N8nResponse(status="error", error=f"响应解析失败: {raw_text[:50]}")

            except Exception as e:
                if attempt == self.config.MAX_RETRIES:
                    return N8nResponse(status="error", error=f"云端连接异常: {str(e)}")
                continue

        return N8nResponse(status="error", error="未知错误")

    # ==================== 业务方法 ====================

    async def distill_keywords(self, **kwargs) -> N8nResponse:
        """关键词蒸馏"""
        payload = KeywordDistillRequest(**kwargs).model_dump(exclude_none=True)
        return await self._call_webhook("keyword-distill", payload)

    async def generate_questions(self, question: str, count: int = 10) -> N8nResponse:
        """生成问题变体（对齐云端 keyword-distill 入口）"""
        payload = GenerateQuestionsRequest(question=question, count=count).model_dump()
        return await self._call_webhook("keyword-distill", payload)

    async def generate_geo_article(self, **kwargs) -> N8nResponse:
        """生成 GEO 文章 (长任务)"""
        payload = GeoArticleRequest(**kwargs).model_dump()
        return await self._call_webhook("geo-article-generate", payload, timeout=self.config.TIMEOUT_LONG)


# ==================== 单例模式 ====================
_instance: Optional[N8nService] = None


async def get_n8n_service() -> N8nService:
    global _instance
    if _instance is None:
        _instance = N8nService()
    return _instance