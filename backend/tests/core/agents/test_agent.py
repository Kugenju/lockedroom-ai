"""Tests for the CharacterAgent dialogue pipeline with leak interception."""

import pytest
from app.core.agents.agent import CharacterAgent
from app.core.engine.events import EventType
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script


def _make_agent(char_id: str, session: GameSession) -> CharacterAgent:
    script = session.script
    scope = compile_scopes(script)[char_id]
    return CharacterAgent(
        character=script.get_character(char_id),
        script=script,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=LeakDetector(script, scope),
    )


@pytest.fixture
def session() -> GameSession:
    session = GameSession("s1", load_script("snow-night-villa"), FakeLLM())
    for phase in (Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION):
        session.advance_phase(phase)
    return session


async def test_normal_reply_is_recorded_and_kept_in_memory(session):
    session.llm = FakeLLM("我一直在厨房备茶。")
    agent = _make_agent("lin_wanqiu", session)
    reply = await agent.respond("你昨晚在哪？")
    assert reply.text == "我一直在厨房备茶。"
    assert reply.leaks == []

    msgs = [e for e in session.events if e.type is EventType.MESSAGE]
    assert msgs[0].payload == {
        "sender": "player", "recipient": "lin_wanqiu", "content": "你昨晚在哪？", "phase": "investigation"
    }
    assert msgs[1].payload["content"] == "我一直在厨房备茶。"

    # follow-up sees the dialogue history
    await agent.respond("有人能证明吗？")
    assert len(agent.memory) >= 4


async def test_hard_leak_triggers_single_rewrite(session):
    session.llm = FakeLLM([
        "老爷死于过量胰岛素注射，我都看见了。",  # hard leak
        "案发时我在整理药材，别问我这些。",      # clean rewrite
    ])
    agent = _make_agent("lin_wanqiu", session)
    reply = await agent.respond("老爷是怎么死的？")
    assert reply.text == "案发时我在整理药材，别问我这些。"
    assert reply.rewritten is True

    leaks = [e for e in session.events if e.type is EventType.LEAK_DETECTED]
    assert len(leaks) == 1
    assert leaks[0].payload["fact_id"] == "t_method"
    assert leaks[0].payload["action"] == "rewritten"


async def test_persistent_leaker_falls_back_to_safe_line(session):
    session.llm = FakeLLM("老爷死于过量胰岛素注射，千真万确。")
    agent = _make_agent("lin_wanqiu", session)
    reply = await agent.respond("老爷是怎么死的？")
    assert "不太清楚" in reply.text or "沉默" in reply.text

    leaks = [e for e in session.events if e.type is EventType.LEAK_DETECTED]
    assert len(leaks) == 2  # original attempt + failed rewrite
    assert leaks[1].payload["action"] == "fallback"


async def test_no_memory_mutation_when_reply_is_rewritten(session):
    session.llm = FakeLLM(["老爷死于过量胰岛素注射。", "我不知道。"])
    agent = _make_agent("lin_wanqiu", session)
    await agent.respond("怎么死的？")
    # the leaked draft must never enter the visible dialogue memory
    remembered = "\n".join(m.content for m in agent.memory)
    assert "死于过量胰岛素注射" not in remembered
