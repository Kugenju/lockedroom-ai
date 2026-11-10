"""Tests for the event-sourced game session."""

import pytest
from app.core.engine.events import EventType, GameEvent
from app.core.engine.session import GameSession
from app.core.engine.state_machine import IllegalPhaseTransition, Phase
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script


@pytest.fixture
def session() -> GameSession:
    script = load_script("snow-night-villa")
    return GameSession(session_id="sess-1", script=script, llm=FakeLLM())


def test_events_are_sequenced_and_ordered(session):
    e1 = session.record_message("player", "lin_wanqiu", "你昨晚在哪？")
    e2 = session.record_message("lin_wanqiu", "player", "我在厨房备茶。")
    assert e1.seq == 0 and e2.seq == 1
    assert e1.ts <= e2.ts
    assert [e.type for e in session.events] == [EventType.MESSAGE, EventType.MESSAGE]


def test_phase_transition_emits_event(session):
    session.advance_phase(Phase.SELF_INTRO)
    changes = [e for e in session.events if e.type is EventType.PHASE_CHANGE]
    assert len(changes) == 1
    assert changes[0].payload == {"from": "intro", "to": "self_intro"}


def test_illegal_phase_change_is_rejected_without_event(session):
    with pytest.raises(IllegalPhaseTransition):
        session.advance_phase(Phase.ENDED)
    assert all(e.type is not EventType.PHASE_CHANGE for e in session.events)


def test_events_since_filters_by_sequence(session):
    session.record_message("player", "lin_wanqiu", "a")
    session.record_message("lin_wanqiu", "player", "b")
    tail = session.events_since(1)
    assert len(tail) == 1 and tail[0].payload["content"] == "b"


def test_event_roundtrip_through_dict(session):
    e = session.record_player_action("accuse", {"suspect": "zhou_muchen"})
    restored = GameEvent.from_dict(e.to_dict())
    assert restored == e
    assert restored.type is EventType.PLAYER_ACTION


def test_leak_event_is_recorded(session):
    e = session.record_leak(
        character_id="zhou_muchen", fact_id="t_method",
        severity="hard", action="rewritten", detail="n-gram hit: 胰岛素",
    )
    assert e.type is EventType.LEAK_DETECTED
    assert e.payload["severity"] == "hard"
