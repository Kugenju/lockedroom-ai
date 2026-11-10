"""Tests for the script (剧本) Pydantic schema and its cross-reference validation."""

import pytest
from app.models.script import Fact, Script, ScriptCharacter, ScriptClue, ScriptEvaluation
from pydantic import ValidationError


def make_fact(fid: str, visibility: str = "private", core: bool = False) -> Fact:
    return Fact(id=fid, visibility=visibility, core=core, content=f"c-{fid}")


def make_script(**overrides) -> Script:
    base = {
        "id": "s1",
        "title": "测试本",
        "brief": "brief",
        "facts": [make_fact("p1", visibility="public"), make_fact("t1")],
        "characters": [
            ScriptCharacter(
                id="c1", name="角色一", role="r", is_killer=True, public_profile="p",
                personality="x", speaking_style="y", known_fact_ids=["t1"],
            )
        ],
        "clues": [
            ScriptClue(
                id="cl1", title="线索", stage=0, location="书房",
                description="d", reveals_fact_ids=["t1"],
            )
        ],
        "evaluation": ScriptEvaluation(
            killer_id="c1", motive_fact_id="t1", required_fact_ids=["t1"]
        ),
    }
    base.update(overrides)
    return Script(**base)


def test_valid_script_constructs():
    script = make_script()
    assert script.id == "s1"
    assert script.get_character("c1").name == "角色一"
    assert script.get_fact("t1").core is False


def test_duplicate_fact_ids_rejected():
    with pytest.raises(ValidationError):
        make_script(facts=[make_fact("t1"), make_fact("t1")])


def test_character_unknown_fact_reference_rejected():
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="c1", name="n", role="r", public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["ghost"],
                )
            ]
        )


def test_private_fact_known_by_nobody_and_no_clue_rejected():
    # t2 is referenced by neither a character nor a clue → the case would be unsolvable
    with pytest.raises(ValidationError):
        make_script(
            facts=[make_fact("p1", visibility="public"), make_fact("t1"), make_fact("t2")],
            characters=[
                ScriptCharacter(
                    id="c1", name="n", role="r", public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["t1"],
                )
            ]
        )


def test_victim_cannot_know_facts_or_be_killer():
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="v1", name="n", role="r", is_victim=True, public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["t1"],
                )
            ]
        )
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="v1", name="n", role="r", is_victim=True, is_killer=True,
                    public_profile="p", personality="x", speaking_style="y",
                )
            ]
        )


def test_killer_must_exist_and_know_core_motive():
    with pytest.raises(ValidationError):
        make_script(evaluation=ScriptEvaluation(killer_id="nobody", motive_fact_id="t1"))
    # killer exists but does not know the motive fact
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="k1", name="n", role="r", is_killer=True, public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=[],
                )
            ],
            evaluation=ScriptEvaluation(killer_id="k1", motive_fact_id="t1"),
        )


def test_killer_must_be_flagged_as_killer():
    # killer_id points at a character that lacks is_killer=True
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="c1", name="n", role="r", public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["t1"],
                )
            ]
        )


def test_clue_revealing_unknown_fact_rejected():
    with pytest.raises(ValidationError):
        make_script(
            clues=[
                ScriptClue(
                    id="cl1", title="t", stage=0, location="l",
                    description="d", reveals_fact_ids=["ghost"],
                )
            ]
        )


def test_exactly_one_victim_and_one_killer_enforced():
    # two killers
    with pytest.raises(ValidationError):
        make_script(
            characters=[
                ScriptCharacter(
                    id="k1", name="n", role="r", is_killer=True, public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["t1"],
                ),
                ScriptCharacter(
                    id="k2", name="n2", role="r", is_killer=True, public_profile="p",
                    personality="x", speaking_style="y", known_fact_ids=["t1"],
                ),
            ],
            evaluation=ScriptEvaluation(killer_id="k1", motive_fact_id="t1"),
        )


def test_demo_script_loads():
    from app.core.scripts.loader import load_script

    script = load_script("snow-night-villa")
    assert script.title == "雪夜·山庄"
    assert sum(c.is_killer for c in script.characters) == 1
    assert sum(c.is_victim for c in script.characters) == 1
    killer = next(c for c in script.characters if c.is_killer)
    assert killer.id == script.evaluation.killer_id
