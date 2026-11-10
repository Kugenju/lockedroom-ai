"""Tests for ContextGuard — InfoGuard Layer 3 input annotation and guarding."""

from app.core.infoguard.context_guard import ContextGuard
from app.core.infoguard.scope import compile_scopes
from app.core.scripts.loader import load_script


def _guard_for(char_id: str) -> ContextGuard:
    script = load_script("snow-night-villa")
    return ContextGuard(script, compile_scopes(script)[char_id])


def test_clean_text_passes_through_unchanged():
    g = _guard_for("lin_wanqiu")
    result = g.guard("你昨晚在哪里？")
    assert result.text == "你昨晚在哪里？"
    assert result.findings == []


def test_text_with_foreign_secret_is_wrapped():
    g = _guard_for("lin_wanqiu")
    result = g.guard("是不是周医生用胰岛素杀了老爷？")
    assert result.findings
    assert {f.fact_id for f in result.findings} == {"t_method"}
    # original content preserved inside the wrapper
    assert "是不是周医生用胰岛素杀了老爷？" in result.text
    # guard note injected
    assert "你不可能知道" in result.text


def test_own_secret_is_not_guarded():
    # t_noise is lin's own fact — mentioning it needs no guard
    g = _guard_for("lin_wanqiu")
    result = g.guard("你听到的争吵声是怎么回事？")
    assert result.findings == []
    assert result.text == "你听到的争吵声是怎么回事？"


def test_killer_only_guarded_against_others_secrets():
    g = _guard_for("zhou_muchen")
    # his own method fact → no guard
    assert g.guard("胰岛素的事与我无关。").findings == []
    # someone else's secret → guarded
    result = g.guard("苏小姐其实是私生女吧？")
    assert {f.fact_id for f in result.findings} == {"t_affair"}


def test_guarded_text_differs_from_original_only_when_needed():
    g = _guard_for("fang_heming")
    clean = g.guard("你怎么看这场雪？")
    dirty = g.guard("那份遗嘱草稿在哪里？")
    assert clean.text == "你怎么看这场雪？"
    assert dirty.text != "那份遗嘱草稿在哪里？"
