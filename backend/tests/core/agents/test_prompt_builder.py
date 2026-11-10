"""Tests for the per-character system prompt assembly (InfoGuard Layer 1 enforcement point)."""

from app.core.agents.prompt_builder import build_system_prompt
from app.core.infoguard.scope import compile_scopes
from app.core.scripts.loader import load_script


def _prompt_for(char_id: str) -> str:
    script = load_script("snow-night-villa")
    scope = compile_scopes(script)[char_id]
    return build_system_prompt(script, script.get_character(char_id), scope)


def test_prompt_contains_persona_and_public_facts():
    prompt = _prompt_for("lin_wanqiu")
    assert "林晚秋" in prompt
    assert "谨慎克制" in prompt
    assert "暴风雪" in prompt  # public fact content


def test_prompt_injects_only_own_private_facts():
    prompt = _prompt_for("lin_wanqiu")
    assert "争吵" in prompt  # t_noise — lin's own fact
    assert "遗嘱" in prompt  # t_will — lin's own fact
    # forbidden facts must not appear anywhere in the prompt
    assert "胰岛素" not in prompt
    assert "私生女" not in prompt
    assert "胰岛素笔" not in prompt
    assert "采购" not in prompt


def test_killer_prompt_carries_concealment_instruction():
    prompt = _prompt_for("zhou_muchen")
    assert "真凶" in prompt
    assert "不能承认" in prompt


def test_innocent_prompt_has_no_killer_instruction():
    prompt = _prompt_for("su_manqing")
    assert "真凶" not in prompt


def test_prompt_forbids_out_of_scope_knowledge():
    prompt = _prompt_for("gu_chengye")
    assert "不知道" in prompt  # instructed to plead ignorance
    assert "绝不要" in prompt or "不得" in prompt
