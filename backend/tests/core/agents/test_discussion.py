"""Public discussion channel: agent.discuss() scoping, leak screening, propagation."""

import pytest
from app.core.agents.agent import CharacterAgent
from app.core.agents.memory import AgentMemory
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.base import ChatMessage
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")
SCOPES = compile_scopes(SCRIPT)


def _agent(session: GameSession, char_id: str, replies) -> CharacterAgent:
    scope = SCOPES[char_id]
    detector = LeakDetector(SCRIPT, scope)
    return CharacterAgent(
        character=SCRIPT.get_character(char_id),
        script=SCRIPT,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=detector,
        memory=AgentMemory(
            scorer_llm=FakeLLM('{"importance": 4}'),
            summarizer_llm=FakeLLM("早前对话摘要。"),
            detector=detector,
        ),
    )


@pytest.fixture
def session() -> GameSession:
    session = GameSession("s1", SCRIPT, FakeLLM())
    for p in (Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION):
        session.advance_phase(p)
    return session


async def test_discuss_records_public_message(session):
    session.llm = FakeLLM("我觉得方先生昨晚的行踪值得再问。")
    agent = _agent(session, "lin_wanqiu", None)
    reply = await agent.discuss([])
    assert reply.rewritten is False
    thread = session.discussion()
    assert len(thread) == 1
    assert thread[0]["sender"] == "lin_wanqiu"
    assert "方先生" in thread[0]["content"]


async def test_discuss_guards_foreign_facts_per_listener(session):
    # player publicly blurts a secret; a listener who cannot know it gets the guard note
    seen: list[list[ChatMessage]] = []
    session.llm = FakeLLM(
        lambda msgs: (seen.append(msgs), "我不知道什么胰岛素。")[1]
    )
    session.record_message("player", "all", "明明就是胰岛素注射！", phase="investigation")
    agent = _agent(session, "lin_wanqiu", None)
    await agent.discuss([("player", "明明就是胰岛素注射！")])
    transcript_lines = [m.content for m in seen[0] if "胰岛素" in m.content]
    assert len(transcript_lines) == 1
    assert "你不可能知道" in transcript_lines[0]


async def test_discuss_leak_is_screened(session):
    session.llm = FakeLLM([
        "老爷死于过量胰岛素注射，我亲眼所见。",
        "我对方先生的赌债更感兴趣。",
    ])
    agent = _agent(session, "lin_wanqiu", None)
    reply = await agent.discuss([])
    assert reply.rewritten is True
    rewritten = [
        e for e in session.events
        if e.type.name == "LEAK_DETECTED" and e.payload["action"] == "rewritten"
    ]
    assert len(rewritten) == 1
    assert "胰岛素" not in session.discussion()[0]["content"]


async def test_public_speech_enters_other_agents_memory_as_observation(session):
    speaker = _agent(session, "lin_wanqiu", None)
    listener = _agent(session, "gu_chengye", None)
    session.llm = FakeLLM("我听见书房昨晚有争吵声。")
    reply = await speaker.discuss([])
    listener.memory.add_turn(
        "user", f"[公共讨论] 林晚秋：{reply.text}", importance=5
    )
    remembered = "\n".join(m.content for m in listener.memory.build_context())
    assert "[公共讨论] 林晚秋" in remembered


def test_discussion_thread_fold(session):
    session.record_message("player", "all", "大家说说昨晚在哪。", phase="investigation")
    session.record_message("lin_wanqiu", "all", "我在厨房。", phase="investigation")
    thread = session.discussion()
    assert [t["sender"] for t in thread] == ["player", "lin_wanqiu"]
    # private messages never enter the public thread
    session.record_message("player", "lin_wanqiu", "悄悄话", phase="investigation")
    assert len(session.discussion()) == 2
