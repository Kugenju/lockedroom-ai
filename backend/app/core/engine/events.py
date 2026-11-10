"""Event-sourced game log — the backbone of ReplayEval.

Every notable happening in a session is appended as an immutable GameEvent.
The full log replays the game; ReplayEval (W3) derives metrics and reports from it.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class EventType(str, Enum):
    PHASE_CHANGE = "phase_change"
    MESSAGE = "message"  # dialogue between player and characters
    PLAYER_ACTION = "player_action"  # clue search, accusation, note, ...
    CLUE_UNLOCKED = "clue_unlocked"
    LEAK_DETECTED = "leak_detected"  # InfoGuard Layer-2 output
    SYSTEM = "system"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class GameEvent:
    seq: int  # position in the session log
    type: EventType
    ts: str  # ISO-8601 UTC
    payload: dict

    def to_dict(self) -> dict:
        return {"seq": self.seq, "type": self.type.value, "ts": self.ts, "payload": self.payload}

    @classmethod
    def from_dict(cls, data: dict) -> "GameEvent":
        return cls(
            seq=data["seq"],
            type=EventType(data["type"]),
            ts=data["ts"],
            payload=data["payload"],
        )
