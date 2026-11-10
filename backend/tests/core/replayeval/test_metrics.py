"""Tests for ReplayEval metrics — pure functions over (script, events)."""

from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.replayeval.metrics import compute_metrics
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")


def ev(seq, event_type, payload):
    return GameEvent(seq, event_type, utc_now_iso(), payload)


def reply(seq, character_id, content):
    return ev(seq, EventType.MESSAGE, {"sender": character_id, "recipient": "player", "content": content})


def player_msg(seq, content):
    return ev(seq, EventType.MESSAGE, {"sender": "player", "recipient": "lin_wanqiu", "content": content})


def test_leak_rate_is_weighted_by_severity():
    events = [
        reply(0, "lin_wanqiu", "a"),
        reply(1, "gu_chengye", "b"),
        reply(2, "su_manqing", "c"),
        reply(3, "fang_heming", "d"),
        ev(4, EventType.LEAK_DETECTED, {"character_id": "lin_wanqiu", "fact_id": "t1", "severity": "hard"}),
        ev(5, EventType.LEAK_DETECTED, {"character_id": "lin_wanqiu", "fact_id": "t2", "severity": "soft"}),
    ]
    m = compute_metrics(SCRIPT, events)
    assert m.leak_rate == 1.3 / 4


def test_zero_replies_means_zero_leak_rate():
    events = [ev(0, EventType.LEAK_DETECTED, {"severity": "hard", "character_id": "c"})]
    m = compute_metrics(SCRIPT, events)
    assert m.leak_rate == 0.0


def test_clue_coverage_counts_required_facts_revealed():
    events = [
        ev(0, EventType.CLUE_UNLOCKED, {"clue_id": "c_report"}),   # → t_method, t_time
        ev(1, EventType.CLUE_UNLOCKED, {"clue_id": "c_insulin"}),  # → t_medicine (not required)
    ]
    m = compute_metrics(SCRIPT, events)
    # required = [t_method, t_time, t_drug, t_window] → 2/4
    assert m.clue_coverage == 0.5


def test_full_clue_coverage():
    events = [
        ev(i, EventType.CLUE_UNLOCKED, {"clue_id": cid})
        for i, cid in enumerate(["c_report", "c_window", "c_ledger"])
    ]
    m = compute_metrics(SCRIPT, events)
    assert m.clue_coverage == 1.0


def test_accusation_outcome_from_accuse_event():
    events = [
        ev(0, EventType.PLAYER_ACTION, {
            "action": "accuse",
            "detail": {"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug",
                       "killer_correct": True, "motive_correct": True},
        })
    ]
    m = compute_metrics(SCRIPT, events)
    assert m.killer_correct is True and m.motive_correct is True


def test_missing_accusation_counts_as_false():
    m = compute_metrics(SCRIPT, [])
    assert m.killer_correct is False and m.motive_correct is False


def test_demo_script_difficulty():
    m = compute_metrics(SCRIPT, [])
    # 4 required × 1.0 + 5 talkable × 0.5 + 10 private facts × 0.2
    assert m.difficulty == 8.5


def test_score_and_grade():
    perfect = [
        *[ev(i, EventType.CLUE_UNLOCKED, {"clue_id": cid})
          for i, cid in enumerate(["c_report", "c_window", "c_ledger"])],
        ev(9, EventType.PLAYER_ACTION, {
            "action": "accuse",
            "detail": {"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug",
                       "killer_correct": True, "motive_correct": True},
        }),
        reply(10, "lin_wanqiu", "clean"),
    ]
    m = compute_metrics(SCRIPT, perfect)
    assert m.score == 100.0
    assert m.grade == "S"

    m_none = compute_metrics(SCRIPT, [])
    assert m_none.score == 0.0
    assert m_none.grade == "C"


def test_leak_penalty_lowers_score():
    events = [
        *[ev(i, EventType.CLUE_UNLOCKED, {"clue_id": cid})
          for i, cid in enumerate(["c_report", "c_window", "c_ledger"])],
        ev(9, EventType.PLAYER_ACTION, {
            "action": "accuse",
            "detail": {"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug",
                       "killer_correct": True, "motive_correct": True},
        }),
        reply(10, "lin_wanqiu", "x"),
        ev(11, EventType.LEAK_DETECTED, {"severity": "hard", "character_id": "lin_wanqiu"}),
        ev(12, EventType.LEAK_DETECTED, {"severity": "hard", "character_id": "lin_wanqiu"}),
    ]
    m = compute_metrics(SCRIPT, events)
    # leak_rate = 2.0 / 1 = 2.0 → 100 - 40 = 60
    assert m.leak_rate == 2.0
    assert m.score == 60.0
    assert m.grade == "B"


def test_metrics_has_summary_counts():
    events = [
        player_msg(0, "在吗"),
        reply(1, "lin_wanqiu", "在"),
        ev(2, EventType.CLUE_UNLOCKED, {"clue_id": "c_report"}),
    ]
    m = compute_metrics(SCRIPT, events)
    assert m.player_questions == 1
    assert m.character_replies == 1
    assert m.clues_unlocked == 1
    assert m.leak_events == 0
