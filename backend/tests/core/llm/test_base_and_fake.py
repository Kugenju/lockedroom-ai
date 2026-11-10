"""Tests for the LLM abstraction base and the scripted FakeLLM."""

from app.core.llm.base import ChatMessage, LLMResponse
from app.core.llm.fake import FakeLLM


async def test_fake_returns_scripted_reply():
    llm = FakeLLM("你好，我是林管家。")
    resp = await llm.chat([ChatMessage(role="user", content="你是谁？")])
    assert isinstance(resp, LLMResponse)
    assert resp.content == "你好，我是林管家。"
    assert resp.model == "fake"


async def test_fake_pops_replies_in_order_and_repeats_last():
    llm = FakeLLM(["第一句", "第二句"])
    r1 = await llm.chat([ChatMessage(role="user", content="a")])
    r2 = await llm.chat([ChatMessage(role="user", content="b")])
    r3 = await llm.chat([ChatMessage(role="user", content="c")])
    assert r1.content == "第一句"
    assert r2.content == "第二句"
    assert r3.content == "第二句"  # exhaustion repeats the last scripted reply


async def test_fake_accepts_reply_factory_callable():
    def reply_factory(messages: list[ChatMessage]) -> str:
        return f"echo:{messages[-1].content}"

    llm = FakeLLM(reply_factory)
    resp = await llm.chat([ChatMessage(role="user", content="xyz")])
    assert resp.content == "echo:xyz"


async def test_fake_stream_yields_full_text_across_chunks():
    llm = FakeLLM("abcdef")
    chunks = [c async for c in llm.stream([ChatMessage(role="user", content="hi")])]
    assert "".join(chunks) == "abcdef"
    assert len(chunks) > 1


async def test_fake_records_call_history():
    llm = FakeLLM()
    await llm.chat([ChatMessage(role="user", content="x")])
    await llm.chat([ChatMessage(role="system", content="s"), ChatMessage(role="user", content="y")])
    assert len(llm.calls) == 2
    assert llm.calls[0][0].content == "x"
    assert len(llm.calls[1]) == 2
