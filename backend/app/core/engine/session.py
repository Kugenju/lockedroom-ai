"""A single game session: script + LLM + phase machine + append-only event log.

When an event_store is attached, every mutation is written through — the
in-memory log and the database stay identical, and ReplayEval can rebuild
finished games from the store.
"""

from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.engine.state_machine import GameStateMachine, Phase
from app.core.llm.base import BaseChatModel
from app.core.persistence.event_store import EventStore
from app.models.script import Script


class GameSession:
    def __init__(
        self,
        session_id: str,
        script: Script,
        llm: BaseChatModel,
        event_store: EventStore | None = None,
    ):
        self.session_id = session_id
        self.script = script
        self.llm = llm
        self.event_store = event_store
        self._sm = GameStateMachine()
        self._events: list[GameEvent] = []
        self._unlocked_clues: set[str] = set()

    @property
    def phase(self) -> Phase:
        return self._sm.phase

    @property
    def events(self) -> list[GameEvent]:
        return list(self._events)

    def _emit(self, event_type: EventType, payload: dict) -> GameEvent:
        event = GameEvent(seq=len(self._events), type=event_type, ts=utc_now_iso(), payload=payload)
        self._events.append(event)
        if self.event_store is not None:
            self.event_store.append_event(self.session_id, event)
        return event

    # --- engine operations, each appends events ---

    def advance_phase(self, target: Phase) -> GameEvent:
        previous = self._sm.phase
        self._sm.advance(target)  # raises IllegalPhaseTransition; no event on rejection
        if self.event_store is not None:
            self.event_store.update_phase(self.session_id, target.value)
        return self._emit(
            EventType.PHASE_CHANGE, {"from": previous.value, "to": target.value}
        )

    def record_message(
        self, sender: str, recipient: str, content: str, **meta
    ) -> GameEvent:
        return self._emit(
            EventType.MESSAGE,
            {"sender": sender, "recipient": recipient, "content": content, **meta},
        )

    def record_player_action(self, action: str, detail: dict) -> GameEvent:
        return self._emit(EventType.PLAYER_ACTION, {"action": action, "detail": detail})

    def record_clue_unlocked(self, clue_id: str, title: str) -> GameEvent:
        return self._emit(
            EventType.CLUE_UNLOCKED, {"clue_id": clue_id, "title": title}
        )

    def unlock_clue(self, clue_id: str, title: str) -> GameEvent | None:
        """Unlock a clue unless already unlocked; returns the event or None."""
        if clue_id in self._unlocked_clues:
            return None
        self._unlocked_clues.add(clue_id)
        return self.record_clue_unlocked(clue_id, title)

    @property
    def unlocked_clue_ids(self) -> frozenset[str]:
        return frozenset(self._unlocked_clues)

    def record_system(self, kind: str, content: str) -> GameEvent:
        return self._emit(EventType.SYSTEM, {"kind": kind, "content": content})

    def record_leak(
        self,
        character_id: str,
        fact_id: str,
        severity: str,  # "soft" | "hard"
        action: str,  # e.g. "passed" | "rewritten" | "fallback"
        detail: str = "",
    ) -> GameEvent:
        return self._emit(
            EventType.LEAK_DETECTED,
            {
                "character_id": character_id,
                "fact_id": fact_id,
                "severity": severity,
                "action": action,
                "detail": detail,
            },
        )

    # --- queries ---

    def events_since(self, seq: int) -> list[GameEvent]:
        """Events with seq >= the given sequence (inclusive tail for SSE resume)."""
        return [e for e in self._events if e.seq >= seq]
