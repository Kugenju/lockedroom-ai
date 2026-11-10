"""Tests for the shared FactMatcher (keyword + shingle indexing over arbitrary fact sets)."""

from app.core.infoguard.matcher import FactMatcher
from app.core.scripts.loader import load_script


def _matcher(fact_ids) -> FactMatcher:
    return FactMatcher(load_script("snow-night-villa"), fact_ids)


def test_keyword_hit_returns_match():
    m = _matcher(["t_method"])
    hits = m.match("我好像听见有人说什么胰岛素")
    assert len(hits) == 1
    assert hits[0].fact_id == "t_method"
    assert hits[0].method == "keyword"
    assert hits[0].matched_text == "胰岛素"


def test_shingle_hit_returns_match():
    m = _matcher(["t_method"])
    hits = m.match("老爷死于过量胰岛素注射")
    assert len(hits) == 1
    assert hits[0].method == "shingle"


def test_indexed_facts_outside_set_are_not_matched():
    # t_method not indexed here → its keyword must not hit
    m = _matcher(["t_affair"])
    assert m.match("胰岛素注射") == []


def test_empty_and_clean_text_have_no_hits():
    m = _matcher(["t_method"])
    assert m.match("") == []
    assert m.match("昨晚的雪下得真大。") == []


def test_hits_are_ordered_by_fact_id():
    m = _matcher(["t_method", "t_inheritance"])
    hits = m.match("死于过量胰岛素注射，还有伪造签名的事")
    assert [h.fact_id for h in hits] == ["t_inheritance", "t_method"]
