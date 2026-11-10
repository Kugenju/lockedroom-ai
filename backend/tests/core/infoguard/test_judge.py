"""Tests for LeakJudge — LLM adjudication over rule-based findings."""

import json

from app.core.infoguard.detector import LeakFinding
from app.core.infoguard.judge import LeakJudge
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script

FINDING_HARD = LeakFinding(fact_id="t_method", severity="hard", matched_text="过量胰岛素注射", method="shingle")
FINDING_SOFT = LeakFinding(fact_id="t_debt", severity="soft", matched_text="公款", method="keyword")


def _judge(reply: str) -> LeakJudge:
    return LeakJudge(llm=FakeLLM(reply), script=load_script("snow-night-villa"))


def _rulings(*items) -> str:
    return json.dumps({"rulings": list(items)}, ensure_ascii=False)


async def test_confirmed_verdict_keeps_finding():
    judge = _judge(_rulings({"fact_id": "t_method", "verdict": "confirmed", "reason": "直接复述了手法"}))
    out = await judge.adjudicate("lin_wanqiu", "老爷死于过量胰岛素注射", [FINDING_HARD])
    assert len(out) == 1
    assert out[0].verdict == "confirmed"
    assert out[0].effective_severity == "hard"
    assert "直接复述" in out[0].reason


async def test_downgrade_maps_hard_to_soft():
    judge = _judge(_rulings({"fact_id": "t_method", "verdict": "downgraded", "reason": "医学常识范畴"}))
    out = await judge.adjudicate("lin_wanqiu", "胰岛素过量会致命", [FINDING_HARD])
    assert out[0].effective_severity == "soft"


async def test_dismissal_drops_finding():
    judge = _judge(_rulings({"fact_id": "t_method", "verdict": "dismissed", "reason": "只是提到药名"}))
    out = await judge.adjudicate("lin_wanqiu", "我不懂什么胰岛素", [FINDING_HARD])
    assert out == []


async def test_partial_rulings_fail_safe_to_confirmed():
    judge = _judge(_rulings({"fact_id": "t_method", "verdict": "dismissed", "reason": "ok"}))
    out = await judge.adjudicate("lin_wanqiu", "text", [FINDING_HARD, FINDING_SOFT])
    by_fact = {a.finding.fact_id: a for a in out}
    assert "t_method" not in by_fact  # dismissed → dropped
    # t_debt missing from rulings → fail-safe confirmed
    assert by_fact["t_debt"].verdict == "confirmed"


async def test_malformed_json_fails_safe_to_confirmed():
    judge = _judge("我不是JSON")
    out = await judge.adjudicate("lin_wanqiu", "text", [FINDING_HARD])
    assert len(out) == 1
    assert out[0].verdict == "confirmed"
    assert "parse" in out[0].reason


async def test_json_wrapped_in_prose_is_extracted():
    body = _rulings({"fact_id": "t_method", "verdict": "downgraded", "reason": "r"})
    judge = _judge(f"好的，裁决如下：{body}\n以上。")
    out = await judge.adjudicate("lin_wanqiu", "text", [FINDING_HARD])
    assert out[0].verdict == "downgraded"
