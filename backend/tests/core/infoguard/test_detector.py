"""Tests for the rule-based leak detector (InfoGuard Layer 2, first pass)."""

from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.scripts.loader import load_script


def _detector_for(char_id: str) -> LeakDetector:
    script = load_script("snow-night-villa")
    scope = compile_scopes(script)[char_id]
    return LeakDetector(script, scope)


def test_clean_text_has_no_findings():
    d = _detector_for("lin_wanqiu")
    assert d.check("我昨晚一直在厨房准备冬至的汤圆。") == []


def test_keyword_hit_is_soft_leak():
    d = _detector_for("lin_wanqiu")
    findings = d.check("我好像听见周先生提起过什么胰岛素……")
    assert len(findings) == 1
    f = findings[0]
    assert f.fact_id == "t_method"
    assert f.severity == "soft"
    assert f.method == "keyword"


def test_verbatim_content_shingle_is_hard_leak():
    d = _detector_for("lin_wanqiu")
    findings = d.check("老爷其实是死于过量胰岛素注射，我亲眼所见。")
    assert any(f.severity == "hard" and f.fact_id == "t_method" for f in findings)


def test_facts_in_scope_are_not_flagged():
    # zhou knows t_method — mentioning insulin is in-scope for him
    d = _detector_for("zhou_muchen")
    assert d.check("胰岛素过量会导致低血糖昏迷，这是常识。") == []


def test_multiple_distinct_facts_reported_separately():
    d = _detector_for("su_manqing")
    findings = d.check("我听说老爷死于过量胰岛素注射，而且方先生还伪造签名。")
    fact_ids = {f.fact_id for f in findings}
    assert "t_method" in fact_ids
    assert "t_inheritance" in fact_ids
