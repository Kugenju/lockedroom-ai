"""Integration tests: agent + judge wiring — only judge-confirmed hard leaks trigger rewrite."""

import json

import pytest
from app.core.agents.agent import CharacterAgent
from app.core.engine.events import EventType
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.judge import LeakJudge
from app.core.infoguard.scope import compile_scopes
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

HARD_LEAK_TEXT = "老爷死于过量胰岛素注射，我看见了。"


def _judge_reply(verdict: str) -> str:
    return json.dumps(
        {"rulings": [{"fact_id": "t_method", "verdict": verdict, "reason": "test"}]},
        ensure_ascii=False,
    )


@pytest.fixture
def session() -> GameSession:
    session = GameSession("s1", load_script("snow-night-villa"), FakeLLM())
    for phase in (Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION):
        session.advance_phase(phase)
    return session


def _make_agent(session: GameSession, judge: LeakJudge | None) -> CharacterAgent:
    script = session.script
    scope = compile_scopes(script)["lin_wanqiu"]
    return CharacterAgent(
        character=script.get_character("lin_wanqiu"),
        script=script,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=LeakDetector(script, scope),
        judge=judge,
    )


async def test_confirmed_hard_leak_triggers_rewrite(session):
    session.llm = FakeLLM([HARD_LEAK_TEXT, "我什么都不知道。"])
    judge = LeakJudge(FakeLLM(_judge_reply("confirmed")), session.script)
    agent = _make_agent(session, judge)

    reply = await agent.respond("老爷怎么死的？")
    assert reply.text == "我什么都不知道。"
    assert reply.rewritten is True

    leaks = [e for e in session.events if e.type is EventType.LEAK_DETECTED]
    assert leaks[0].payload["action"] == "rewritten"
    assert "confirmed" in leaks[0].payload["detail"]


async def test_dismissed_hard_leak_passes_without_rewrite(session):
    session.llm = FakeLLM(HARD_LEAK_TEXT)  # single reply: rewrite would need a 2nd
    judge = LeakJudge(FakeLLM(_judge_reply("dismissed")), session.script)
    agent = _make_agent(session, judge)

    reply = await agent.respond("老爷怎么死的？")
    assert reply.text == HARD_LEAK_TEXT
    assert reply.rewritten is False
    assert all(e.type is not EventType.LEAK_DETECTED for e in session.events)


async def test_downgraded_hard_leak_passes_as_soft(session):
    session.llm = FakeLLM(HARD_LEAK_TEXT)
    judge = LeakJudge(FakeLLM(_judge_reply("downgraded")), session.script)
    agent = _make_agent(session, judge)

    reply = await agent.respond("老爷怎么死的？")
    assert reply.rewritten is False
    leaks = [e for e in session.events if e.type is EventType.LEAK_DETECTED]
    assert len(leaks) == 1
    assert leaks[0].payload["severity"] == "soft"
    assert leaks[0].payload["action"] == "passed"


async def test_no_judge_keeps_rule_only_behavior(session):
    session.llm = FakeLLM([HARD_LEAK_TEXT, "我不知道。"])
    agent = _make_agent(session, judge=None)
    reply = await agent.respond("老爷怎么死的？")
    assert reply.rewritten is True  # hard rule hit rewrites directly
