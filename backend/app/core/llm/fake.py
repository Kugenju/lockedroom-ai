"""Scripted LLM for tests and offline development.

Replies may be:
- a single string (always returned),
- a list of strings (returned in order; the last one repeats on exhaustion),
- a callable taking the message history and returning a string.
Every call is recorded in ``calls`` for assertions.
"""

from collections.abc import AsyncIterator, Callable

from app.core.llm.base import BaseChatModel, ChatMessage, LLMResponse

Reply = str | list[str] | Callable[[list[ChatMessage]], str]


class FakeLLM(BaseChatModel):
    def __init__(self, replies: Reply = "……", model: str = "fake"):
        self._replies = replies
        self._model = model
        self.calls: list[list[ChatMessage]] = []

    def _resolve(self, messages: list[ChatMessage]) -> str:
        r = self._replies
        if callable(r):
            return r(messages)
        if isinstance(r, str):
            return r
        if not r:
            return "……"
        call_index = len(self.calls) - 1  # the current call was already recorded
        return r[min(call_index, len(r) - 1)]

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        msgs = list(messages)
        self.calls.append(msgs)
        return LLMResponse(content=self._resolve(msgs), model=self._model)

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        resp = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        for i in range(0, len(resp.content), 3):
            yield resp.content[i : i + 3]
