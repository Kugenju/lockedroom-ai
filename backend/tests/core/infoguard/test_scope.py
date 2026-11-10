"""Tests for InfoGuard's per-character InformationScope compilation."""

from app.core.infoguard.scope import compile_scopes
from app.core.scripts.loader import load_script


def test_killer_scope_contains_own_facts_excludes_others_secrets():
    script = load_script("snow-night-villa")
    scopes = compile_scopes(script)
    zhou = scopes["zhou_muchen"]

    for fid in ["t_method", "t_time", "t_drug", "t_medicine", "t_window"]:
        assert zhou.may_know(fid), fid
    # other people's secrets must be forbidden to the killer
    for fid in ["t_affair", "t_debt", "t_inheritance", "t_noise", "t_will"]:
        assert not zhou.may_know(fid), fid


def test_public_facts_are_in_every_scope():
    script = load_script("snow-night-villa")
    scopes = compile_scopes(script)
    for scope in scopes.values():
        assert scope.may_know("p_setup")
        assert scope.may_know("p_snow")


def test_innocent_scope_contains_only_own_and_public():
    script = load_script("snow-night-villa")
    scopes = compile_scopes(script)
    lin = scopes["lin_wanqiu"]
    assert lin.may_know("t_noise")
    assert lin.may_know("t_will")
    assert not lin.may_know("t_method")


def test_victim_scope_is_public_only():
    script = load_script("snow-night-villa")
    scopes = compile_scopes(script)
    victim = scopes["shen_wanlou"]
    assert victim.known_fact_ids == {"p_setup", "p_snow"}
    assert victim.forbidden_fact_ids  # everything private is forbidden


def test_forbidden_is_exact_complement_of_known():
    script = load_script("snow-night-villa")
    all_ids = {f.id for f in script.facts}
    for scope in compile_scopes(script).values():
        assert scope.known_fact_ids | scope.forbidden_fact_ids == all_ids
        assert not (scope.known_fact_ids & scope.forbidden_fact_ids)
