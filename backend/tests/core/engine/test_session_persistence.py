"""GameSession → EventStore wiring tests."""

from app.core.engine.events import EventType
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.llm.fake import FakeLLM
from app.core.persistence.event_store import MemoryEventStore
from app.core.scripts.loader import load_script


def test_session_without_store_keeps_in_memory_only():
    session = GameSession("g1", load_script("snow-night-villa"), FakeLLM())
    session.record_message("player", "c", "hi")
    assert len(session.events) == 1


def test_session_appends_events_to_store():
    store = MemoryEventStore()
    session = GameSession("snow-night-villa-g1", load_script("snow-night-villa"), FakeLLM(), event_store=store)
    store.create_game(session.session_id, "snow-night-villa", "intro")

    session.record_message("player", "lin_wanqiu", "在吗？")
    session.advance_phase(Phase.SELF_INTRO)

    stored = store.get_events(session.session_id)
    assert [e.seq for e in stored] == [0, 1]
    assert stored[1].type is EventType.PHASE_CHANGE
    assert store.get_game(session.session_id)["phase"] == "self_intro"
