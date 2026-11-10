"""Tests for the OpenAI-compatible chat backend and the provider factory.

The AsyncOpenAI client is replaced by a stub so no network happens here.
"""

from app.core.config import Settings
from app.core.llm.base import ChatMessage
from app.core.llm.factory import create_chat_model
from app.core.llm.openai_compat import OpenAICompatChat

from .stubs import StubClient


async def test_chat_maps_messages_and_usage():
    stub = StubClient()
    llm = OpenAICompatChat(
        model="m1", api_key="k", base_url="https://example.test", client=stub
    )
    resp = await llm.chat(
        [ChatMessage(role="system", content="s"), ChatMessage(role="user", content="u")],
        temperature=0.3,
        max_tokens=64,
    )
    assert resp.content == "你好，玩家"
    assert resp.prompt_tokens == 10
    assert resp.completion_tokens == 5

    sent = stub.chat.completions.init_args()
    assert sent["model"] == "m1"
    assert sent["messages"] == [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    assert sent["temperature"] == 0.3
    assert sent["max_tokens"] == 64


async def test_stream_aggregates_delta_content_in_order():
    stub = StubClient()
    llm = OpenAICompatChat(model="m1", api_key="k", base_url=None, client=stub)
    chunks = [c async for c in llm.stream([ChatMessage(role="user", content="u")])]
    assert "".join(chunks) == "你好，玩家"

    sent = stub.chat.completions.init_args()
    assert sent["stream"] is True


def test_factory_builds_deepseek_with_custom_base(monkeypatch):
    monkeypatch.setenv("SM_INFERENCE_SERVICE", "deepseek")
    monkeypatch.setenv("SM_MODEL", "deepseek-chat")
    monkeypatch.setenv("SM_API_KEY", "sk-test")
    monkeypatch.setenv("SM_OPENAI_API_BASE", "https://api.deepseek.com")
    llm = create_chat_model(Settings())
    assert isinstance(llm, OpenAICompatChat)
    assert llm.model == "deepseek-chat"
    assert str(llm.base_url) == "https://api.deepseek.com"


def test_factory_builds_ollama_with_v1_suffix(monkeypatch):
    monkeypatch.setenv("SM_INFERENCE_SERVICE", "ollama")
    monkeypatch.setenv("SM_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("SM_OLLAMA_URL", "http://localhost:11434")
    llm = create_chat_model(Settings())
    assert isinstance(llm, OpenAICompatChat)
    assert str(llm.base_url) == "http://localhost:11434/v1"
