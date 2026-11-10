"""EventStore: append-only persistence for games and their event streams.

MemoryEventStore — tests and injected-llm dev apps.
SqlAlchemyEventStore — production (SQLite/PostgreSQL via SM_DATABASE_URL).
ReplayEval (W3) reads from this layer to rebuild finished games.
"""

import json
import threading
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.persistence.db import make_engine
from app.core.persistence.models import EventRow, GameRow


class EventStore(Protocol):
    def create_game(self, game_id: str, script_id: str, phase: str) -> None: ...
    def update_phase(self, game_id: str, phase: str) -> None: ...
    def append_event(self, game_id: str, event: GameEvent) -> None: ...
    def get_events(self, game_id: str) -> list[GameEvent]: ...
    def get_game(self, game_id: str) -> dict | None: ...


class MemoryEventStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._games: dict[str, dict] = {}
        self._events: dict[str, list[GameEvent]] = {}

    def create_game(self, game_id: str, script_id: str, phase: str) -> None:
        with self._lock:
            self._games[game_id] = {
                "game_id": game_id,
                "script_id": script_id,
                "phase": phase,
                "created_at": utc_now_iso(),
                "ended_at": None,
            }
            self._events.setdefault(game_id, [])

    def update_phase(self, game_id: str, phase: str) -> None:
        with self._lock:
            self._games[game_id]["phase"] = phase
            if phase == "ended":
                self._games[game_id]["ended_at"] = utc_now_iso()

    def append_event(self, game_id: str, event: GameEvent) -> None:
        with self._lock:
            self._events[game_id].append(event)

    def get_events(self, game_id: str) -> list[GameEvent]:
        with self._lock:
            return list(self._events.get(game_id, []))

    def get_game(self, game_id: str) -> dict | None:
        with self._lock:
            return self._games.get(game_id)


class SqlAlchemyEventStore:
    def __init__(self, engine=None):
        self._engine = engine or make_engine()
        self._lock = threading.Lock()

    def _with_session(self, fn):
        with self._lock, Session(self._engine) as session:
            result = fn(session)
            session.commit()
            return result

    def create_game(self, game_id: str, script_id: str, phase: str) -> None:
        def op(session: Session) -> None:
            session.add(GameRow(
                id=game_id, script_id=script_id, phase=phase, created_at=utc_now_iso()
            ))
        self._with_session(op)

    def update_phase(self, game_id: str, phase: str) -> None:
        def op(session: Session) -> None:
            row = session.get(GameRow, game_id)
            if row is None:
                return
            row.phase = phase
            if phase == "ended":
                row.ended_at = utc_now_iso()
        self._with_session(op)

    def append_event(self, game_id: str, event: GameEvent) -> None:
        def op(session: Session) -> None:
            session.add(EventRow(
                game_id=game_id,
                seq=event.seq,
                type=event.type.value,
                ts=event.ts,
                payload=json.dumps(event.payload, ensure_ascii=False),
            ))
        self._with_session(op)

    def get_events(self, game_id: str) -> list[GameEvent]:
        def op(session: Session) -> list[GameEvent]:
            rows = session.query(EventRow).filter_by(game_id=game_id).order_by(EventRow.seq)
            return [
                GameEvent(
                    seq=r.seq,
                    type=EventType(r.type),
                    ts=r.ts,
                    payload=json.loads(r.payload),
                )
                for r in rows
            ]
        return self._with_session(op)

    def get_game(self, game_id: str) -> dict | None:
        def op(session: Session) -> dict | None:
            row = session.get(GameRow, game_id)
            if row is None:
                return None
            return {
                "game_id": row.id,
                "script_id": row.script_id,
                "phase": row.phase,
                "created_at": row.created_at,
                "ended_at": row.ended_at,
            }
        return self._with_session(op)
