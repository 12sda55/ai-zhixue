"""LLM工具 - 统一OpenAI兼容客户端（对照规范 9.1）

支持：
- DeepSeek（OpenAI兼容API）
- 讯飞星火（OpenAI兼容HTTP API）
- 主模型不可用时自动切换备选
- 流式输出 & Function Calling 统一支持
"""

from __future__ import annotations
import logging
from typing import Optional

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Provider → (base_url, api_key) 映射
_PROVIDER_CONFIG = {
    "deepseek": lambda: (
        settings.deepseek_base_url,
        settings.deepseek_api_key,
    ),
    "spark": lambda: (
        "https://spark-api-open.xf-yun.com/v1",
        settings.xunfei_api_password,
    ),
}


class UnifiedLLMClient:
    """统一LLM客户端 - DeepSeek与讯飞星火共用OpenAI兼容接口

    对照规范 9.1：双模型可切换，主模型优先，备选模型降级。
    """

    def __init__(self):
        self._clients: dict[str, OpenAI] = {}
        self._primary = settings.llm_primary
        self._secondary = settings.llm_secondary
        self._fallback_enabled = settings.llm_fallback_enabled

    def _create_client(self, provider: str) -> OpenAI:
        """根据provider创建OpenAI客户端实例

        Args:
            provider: "deepseek" 或 "spark"

        Returns:
            OpenAI 客户端实例
        """
        if provider not in _PROVIDER_CONFIG:
            raise ValueError(f"不支持的provider: {provider}，可选: {list(_PROVIDER_CONFIG.keys())}")

        base_url, api_key = _PROVIDER_CONFIG[provider]()
        if not api_key:
            raise RuntimeError(f"{provider} API密钥未配置")

        return OpenAI(api_key=api_key, base_url=base_url)

    def _get_client(self, provider: str) -> OpenAI:
        """获取（懒加载）指定provider的客户端"""
        if provider not in self._clients:
            self._clients[provider] = self._create_client(provider)
        return self._clients[provider]

    def _get_model_name(self, provider: str) -> str:
        """获取指定provider对应的模型名称"""
        if provider == "spark":
            return settings.xunfei_spark_model
        return settings.deepseek_model

    def _is_available(self, provider: str) -> bool:
        """检查provider是否已配置可用"""
        if provider not in _PROVIDER_CONFIG:
            return False
        _, api_key = _PROVIDER_CONFIG[provider]()
        return bool(api_key)

    # ------------------------------------------------------------------
    #  核心聊天方法
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> str:
        """发送聊天请求（双模型切换）

        优先使用主模型，失败时降级到备选模型。
        如果指定了model参数，直接用DeepSeek（兼容旧行为）。
        """
        if model:
            return self._chat_provider(
                "deepseek", messages, model=model, temperature=temperature,
                max_tokens=max_tokens, response_format=response_format,
            )

        provider = self._primary
        try:
            return self._chat_provider(
                provider, messages, temperature=temperature,
                max_tokens=max_tokens, response_format=response_format,
            )
        except Exception as e:
            if self._fallback_enabled and self._secondary != provider and self._is_available(self._secondary):
                logger.warning(f"{provider}调用失败，降级到{self._secondary}: {e}")
                return self._chat_provider(
                    self._secondary, messages, temperature=temperature,
                    max_tokens=max_tokens, response_format=response_format,
                )
            raise

    def _chat_provider(
        self,
        provider: str,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> str:
        """指定provider的聊天请求"""
        client = self._get_client(provider)
        kwargs = {
            "model": model or self._get_model_name(provider),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # ------------------------------------------------------------------
    #  流式输出
    # ------------------------------------------------------------------

    def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ):
        """流式聊天 - 返回生成器，逐token输出

        DeepSeek与星火均支持OpenAI兼容的stream=True。
        """
        provider = self._primary
        try:
            yield from self._stream_provider(
                provider, messages, model=model,
                temperature=temperature, max_tokens=max_tokens,
            )
        except Exception as e:
            if self._fallback_enabled and self._secondary != provider and self._is_available(self._secondary):
                logger.warning(f"{provider}流式调用失败，降级到{self._secondary}: {e}")
                yield from self._stream_provider(
                    self._secondary, messages, model=model,
                    temperature=temperature, max_tokens=max_tokens,
                )
            else:
                raise

    def _stream_provider(
        self,
        provider: str,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ):
        """指定provider的流式聊天"""
        client = self._get_client(provider)
        response = client.chat.completions.create(
            model=model or self._get_model_name(provider),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # ------------------------------------------------------------------
    #  Function Calling
    # ------------------------------------------------------------------

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> dict:
        """Function Calling聊天请求

        DeepSeek与星火均支持OpenAI兼容的tools参数。
        """
        provider = self._primary
        try:
            return self._chat_with_tools_provider(
                provider, messages, tools, model=model, temperature=temperature,
            )
        except Exception as e:
            if self._fallback_enabled and self._secondary != provider and self._is_available(self._secondary):
                logger.warning(f"{provider} Function Calling失败，降级到{self._secondary}: {e}")
                return self._chat_with_tools_provider(
                    self._secondary, messages, tools, model=model, temperature=temperature,
                )
            raise

    def _chat_with_tools_provider(
        self,
        provider: str,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> dict:
        """指定provider的Function Calling请求"""
        client = self._get_client(provider)
        response = client.chat.completions.create(
            model=model or self._get_model_name(provider),
            messages=messages,
            tools=tools,
            temperature=temperature,
        )
        message = response.choices[0].message
        return {
            "content": message.content or "",
            "tool_calls": message.tool_calls,
        }

    # ------------------------------------------------------------------
    #  chat_completion 别名（向后兼容）
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> str:
        """chat的别名，保持向后兼容"""
        return self.chat(
            messages, model=model, temperature=temperature,
            max_tokens=max_tokens, response_format=response_format,
        )


# 全局单例
llm_client = UnifiedLLMClient()
