"""ReplayEval metrics — quantitative evaluation of a finished (or running) game.

All metrics derive from the event log, the single source of truth:

- leak_rate        = Σ leak weights (hard=1.0, soft=0.3) / character replies
- clue_coverage    = |required facts revealed by unlocked clues| / |required facts|
- killer/motive    = from the accuse player_action event (False when absent)
- score            = 100 × (0.45×coverage + 0.35×killer + 0.20×motive) − 20×leak_rate
- grade            = S ≥ 90, A ≥ 75, B ≥ 60, else C
- difficulty       = min(10, required×1.0 + talkable×0.5 + private_facts×0.2)
"""

from dataclasses import asdict, dataclass

from app.core.engine.events import EventType, GameEvent
from app.models.script import Script

WEIGHT_HARD = 1.0
WEIGHT_SOFT = 0.3


@dataclass
class Metrics:
    leak_rate: float = 0.0
    clue_coverage: float = 0.0
    killer_correct: bool = False
    motive_correct: bool = False
    score: float = 0.0
    grade: str = "C"
    difficulty: float = 0.0
    # summary counts
    player_questions: int = 0
    character_replies: int = 0
    clues_unlocked: int = 0
    leak_events: int = 0
    hard_leaks: int = 0
    soft_leaks: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _grade(score: float) -> str:
    if score >= 90:
        return "S"
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    return "C"


def compute_metrics(script: Script, events: list[GameEvent]) -> Metrics:
    m = Metrics()

    m.player_questions = sum(
        1 for e in events
        if e.type is EventType.MESSAGE and e.payload.get("sender") == "player"
    )
    m.character_replies = sum(
        1 for e in events
        if e.type is EventType.MESSAGE
        and e.payload.get("recipient") == "player"
        and e.payload.get("sender") not in (None, "player", "narrator")
    )
    leak_events = [e for e in events if e.type is EventType.LEAK_DETECTED]
    m.leak_events = len(leak_events)
    m.hard_leaks = sum(1 for e in leak_events if e.payload.get("severity") == "hard")
    m.soft_leaks = m.leak_events - m.hard_leaks
    if m.character_replies > 0:
        weight = m.hard_leaks * WEIGHT_HARD + m.soft_leaks * WEIGHT_SOFT
        m.leak_rate = round(weight / m.character_replies, 4)

    unlocked = {e.payload.get("clue_id") for e in events if e.type is EventType.CLUE_UNLOCKED}
    m.clues_unlocked = len(unlocked)
    revealed_facts = {
        fid
        for clue in script.clues
        if clue.id in unlocked
        for fid in clue.reveals_fact_ids
    }
    required = set(script.evaluation.required_fact_ids)
    if required:
        m.clue_coverage = round(len(revealed_facts & required) / len(required), 4)

    for e in events:
        if e.type is EventType.PLAYER_ACTION and e.payload.get("action") == "accuse":
            detail = e.payload.get("detail", {})
            m.killer_correct = bool(detail.get("killer_correct"))
            m.motive_correct = bool(detail.get("motive_correct"))
            break

    m.difficulty = round(
        min(
            10.0,
            len(script.evaluation.required_fact_ids) * 1.0
            + len(script.talkable_characters) * 0.5
            + sum(1 for f in script.facts if f.visibility == "private") * 0.2,
        ),
        1,
    )

    m.score = round(
        max(
            0.0,
            100.0 * (0.45 * m.clue_coverage + 0.35 * float(m.killer_correct)
                     + 0.20 * float(m.motive_correct))
            - 20.0 * m.leak_rate,
        ),
        1,
    )
    m.grade = _grade(m.score)
    return m
