"""L3 integration tests: player messages carrying foreign secrets are guarded before
they reach the model, and the guard note reaches the LLM input."""

import pytest
from app.core.agents.agent import CharacterAgent
from app.core.engine.events import EventType
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.base import ChatMessage
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

QUESTION_WITH_SECRET = "是不是周医生用胰岛素杀了老爷？"


@pytest.fixture
def session() -> GameSession:
    session = GameSession("s1", load_script("snow-night-villa"), FakeLLM())
    for phase in (Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION):
        session.advance_phase(phase)
    return session


def _make_agent(session: GameSession) -> CharacterAgent:
    script = session.script
    scope = compile_scopes(script)["lin_wanqiu"]
    return CharacterAgent(
        character=script.get_character("lin_wanqiu"),
        script=script,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=LeakDetector(script, scope),
    )


async def test_guarded_player_message_reaches_model(session):
    seen: list[list[ChatMessage]] = []

    def spy_factory(replies):
        def factory(messages: list[ChatMessage]) -> str:
            seen.append(messages)
            return replies
        return factory

    session.llm = FakeLLM(spy_factory("我不知道你在说什么。"))
    agent = _make_agent(session)
    await agent.respond(QUESTION_WITH_SECRET)

    last_user_msg = seen[0][-1].content
    assert "你不可能知道" in last_user_msg  # guard note injected
    assert "胰岛素" in last_user_msg  # original question preserved


async def test_clean_player_message_is_not_guarded(session):
    seen: list[list[ChatMessage]] = []
    session.llm = FakeLLM(
        lambda msgs: (seen.append(msgs), "我在厨房。")[1]
    )
    agent = _make_agent(session)
    await agent.respond("你昨晚在哪里？")
    assert "你不可能知道" not in seen[0][-1].content


async def test_memory_messages_are_guarded_on_replay(session):
    seen: list[list[ChatMessage]] = []
    session.llm = FakeLLM(
        lambda msgs: (seen.append([m.content for m in msgs]), "嗯。")[1]
    )
    agent = _make_agent(session)
    await agent.respond(QUESTION_WITH_SECRET)   # turn 1: secret enters memory
    await agent.respond("那你觉得谁最可疑？")     # turn 2: memory replayed

    turn2_input = seen[1]
    # the turn-1 question is present in memory but wrapped in the guard note
    guarded = [m for m in turn2_input if "你不可能知道" in m]
    assert len(guarded) == 1
    assert QUESTION_WITH_SECRET in guarded[0]


async def test_guard_event_recorded(session):
    session.llm = FakeLLM("我不知道你在说什么。")
    agent = _make_agent(session)
    await agent.respond(QUESTION_WITH_SECRET)
    guarded_msgs = [
        e for e in session.events
        if e.type is EventType.MESSAGE and e.payload.get("guarded")
    ]
    assert len(guarded_msgs) == 1
    assert guarded_msgs[0].payload["guarded_fact_ids"] == ["t_method"]
