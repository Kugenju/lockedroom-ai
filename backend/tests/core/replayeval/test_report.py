"""Tests for the markdown replay report renderer."""

from app.core.engine.events import EventType, GameEvent, utc_now_iso
from app.core.replayeval.chain import ReasoningChain
from app.core.replayeval.metrics import compute_metrics
from app.core.replayeval.report import render_report
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")


def _full_game_events():
    return [
        GameEvent(0, EventType.PHASE_CHANGE, utc_now_iso(), {"from": "intro", "to": "self_intro"}),
        GameEvent(1, EventType.CLUE_UNLOCKED, utc_now_iso(), {"clue_id": "c_report", "title": "初步检验结果"}),
        GameEvent(2, EventType.CLUE_UNLOCKED, utc_now_iso(), {"clue_id": "c_window", "title": "窗台的融雪水渍"}),
        GameEvent(3, EventType.CLUE_UNLOCKED, utc_now_iso(), {"clue_id": "c_ledger", "title": "异常的采购单"}),
        GameEvent(4, EventType.MESSAGE, utc_now_iso(), {"sender": "player", "recipient": "zhou_muchen", "content": "你的药箱里少了什么？"}),
        GameEvent(5, EventType.MESSAGE, utc_now_iso(), {"sender": "zhou_muchen", "recipient": "player", "content": "没有少任何东西。"}),
        GameEvent(6, EventType.LEAK_DETECTED, utc_now_iso(), {"character_id": "zhou_muchen", "fact_id": "t_affair", "severity": "soft", "action": "passed", "detail": "keyword hit: 私生女 | judge confirmed: 测试"}),
        GameEvent(7, EventType.PLAYER_ACTION, utc_now_iso(), {"action": "accuse", "detail": {"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug", "killer_correct": True, "motive_correct": True}}),
        GameEvent(8, EventType.SYSTEM, utc_now_iso(), {"kind": "reveal", "content": "真相是……"}),
        GameEvent(9, EventType.PHASE_CHANGE, utc_now_iso(), {"from": "reveal", "to": "ended"}),
    ]


def test_report_structure():
    events = _full_game_events()
    metrics = compute_metrics(SCRIPT, events)
    chain = ReasoningChain(
        suspect_trajectory=["周慕辰（药箱线索）"],
        key_insights=["胰岛素笔少了一支"],
        missed_clues=["采购单黑账"],
        summary="玩家直接锁定了医生。",
    )
    md = render_report(SCRIPT, events, metrics, chain)

    assert md.startswith("# 复盘报告")
    assert "雪夜·山庄" in md
    # 结论 section shows accusation vs truth
    assert "周慕辰" in md and "正确" in md
    # metrics table
    assert "| 指标 |" in md
    assert "泄露率" in md and "线索覆盖率" in md
    assert "S" in md  # perfect play grade
    # leak section lists the event
    assert "泄露事件" in md
    assert "私生女" in md
    # chain section
    assert "推理链" in md
    assert "玩家直接锁定了医生" in md
    assert "采购单黑账" in md
    # timeline section includes key beats
    assert "时间线" in md
    assert "搜获线索：初步检验结果" in md
    assert "真相揭晓" in md


def test_report_handles_failed_chain():
    events = _full_game_events()
    metrics = compute_metrics(SCRIPT, events)
    md = render_report(SCRIPT, events, metrics, ReasoningChain(summary="（推理链提取失败，可查看原始事件流了解对局过程。）"))
    assert "推理链" in md  # section still renders
    assert "提取失败" in md
