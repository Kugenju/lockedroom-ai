"""OpenAI-compatible chat backend.

Works with any endpoint speaking the OpenAI chat-completions protocol:
DeepSeek, OpenAI, Groq, OpenRouter, vLLM, and Ollama (via its /v1 compat layer).
"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.llm.base import BaseChatModel, ChatMessage, LLMResponse


class OpenAICompatChat(BaseChatModel):
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        client: Any | None = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 2048,
        extra_body: dict | None = None,
    ):
        self.model = model
        self.base_url = base_url
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._extra_body = extra_body
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _payload(self, messages: list[ChatMessage], temperature: float | None,
                 max_tokens: int | None) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
        }
        if self._extra_body is not None:
            payload["extra_body"] = self._extra_body
        return payload

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            **self._payload(messages, temperature, max_tokens)
        )
        usage = resp.usage
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=getattr(resp, "model", None) or self.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            raw=resp,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature, max_tokens)
        payload["stream"] = True
        resp = await self._client.chat.completions.create(**payload)
        async for chunk in resp:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
