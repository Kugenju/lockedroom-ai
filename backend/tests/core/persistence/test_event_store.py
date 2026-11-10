"""Roundtrip tests for the persistence layer (memory + in-memory SQLite)."""

import pytest
from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.persistence.db import make_engine
from app.core.persistence.event_store import MemoryEventStore, SqlAlchemyEventStore


@pytest.fixture(params=["memory", "sqlite"])
def store(request):
    if request.param == "memory":
        return MemoryEventStore()
    return SqlAlchemyEventStore(make_engine("sqlite:///:memory:"))


def _sample_events() -> list[GameEvent]:
    return [
        GameEvent(0, EventType.PHASE_CHANGE, utc_now_iso(), {"from": "intro", "to": "self_intro"}),
        GameEvent(1, EventType.MESSAGE, utc_now_iso(), {"sender": "player", "recipient": "c1", "content": "hi"}),
        GameEvent(2, EventType.LEAK_DETECTED, utc_now_iso(), {"fact_id": "t1", "severity": "hard"}),
    ]


def test_create_and_get_game(store):
    store.create_game("g1", "snow-night-villa", "intro")
    game = store.get_game("g1")
    assert game is not None
    assert game["script_id"] == "snow-night-villa"
    assert game["phase"] == "intro"
    assert game["ended_at"] is None


def test_get_unknown_game_returns_none(store):
    assert store.get_game("nope") is None


def test_events_roundtrip(store):
    store.create_game("g1", "s", "intro")
    samples = _sample_events()
    for e in samples:
        store.append_event("g1", e)
    loaded = store.get_events("g1")
    assert loaded == samples


def test_phase_update(store):
    store.create_game("g1", "s", "intro")
    store.update_phase("g1", "investigation")
    assert store.get_game("g1")["phase"] == "investigation"


def test_events_are_scoped_per_game(store):
    store.create_game("g1", "s", "intro")
    store.create_game("g2", "s", "intro")
    store.append_event("g1", _sample_events()[0])
    store.append_event("g2", _sample_events()[1])
    assert [e.seq for e in store.get_events("g1")] == [0]
    assert [e.seq for e in store.get_events("g2")] == [1]
