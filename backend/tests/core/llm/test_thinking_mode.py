"""Tests for the DeepSeek thinking-mode switch."""

from app.core.config import Settings
from app.core.llm.base import ChatMessage
from app.core.llm.factory import create_chat_model
from app.core.llm.openai_compat import OpenAICompatChat

from .stubs import StubClient


async def test_extra_body_forwarded_in_chat():
    client = StubClient()
    llm = OpenAICompatChat(
        model="m", api_key="k", client=client, extra_body={"thinking": {"type": "disabled"}}
    )
    await llm.chat([ChatMessage(role="user", content="u")])
    payload = client.chat.completions.init_args()
    assert payload["extra_body"] == {"thinking": {"type": "disabled"}}


async def test_extra_body_forwarded_in_stream():
    client = StubClient()
    llm = OpenAICompatChat(
        model="m", api_key="k", client=client, extra_body={"thinking": {"type": "enabled"}}
    )
    _ = [c async for c in llm.stream([ChatMessage(role="user", content="u")])]
    payload = client.chat.completions.init_args()
    assert payload["extra_body"] == {"thinking": {"type": "enabled"}}


def test_factory_deepseek_thinking_disabled_by_default(monkeypatch):
    monkeypatch.setenv("SM_INFERENCE_SERVICE", "deepseek")
    monkeypatch.setenv("SM_API_KEY", "k")
    llm = create_chat_model(Settings())
    assert llm._extra_body == {"thinking": {"type": "disabled"}}


def test_factory_deepseek_thinking_enabled_via_env(monkeypatch):
    monkeypatch.setenv("SM_INFERENCE_SERVICE", "deepseek")
    monkeypatch.setenv("SM_API_KEY", "k")
    monkeypatch.setenv("SM_THINKING_ENABLED", "true")
    llm = create_chat_model(Settings())
    assert llm._extra_body == {"thinking": {"type": "enabled"}}


def test_factory_non_deepseek_has_no_thinking_param(monkeypatch):
    monkeypatch.setenv("SM_INFERENCE_SERVICE", "openai")
    monkeypatch.setenv("SM_API_KEY", "k")
    llm = create_chat_model(Settings())
    assert llm._extra_body is None
