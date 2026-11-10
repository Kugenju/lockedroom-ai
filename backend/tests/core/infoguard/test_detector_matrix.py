"""Adversarial matrix: every talkable character × every private fact of the demo script.

Four corpus categories per cell:
- own-secret mention   → must NOT be flagged (fact is in scope)
- foreign keyword      → must be flagged soft
- foreign shingle      → must be flagged hard
- innocent chatter     → zero false positives

The matrix is generated from the script itself, so any future script change or
detector regression shows up as a named matrix cell failure.
"""

import pytest
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.scripts.loader import load_script

SCRIPT = load_script("snow-night-villa")
SCOPES = compile_scopes(SCRIPT)
TALKABLE = [c for c in SCRIPT.talkable_characters]

INNOCENT_LINES = [
    "昨晚的雪下得好大，你吃过晚饭了吗？",
    "案发时你在哪里？",
    "你觉得这场雪什么时候停？",
]


def _keyword_of(fact) -> str:
    return min(fact.keywords, key=len)  # shortest keyword = most conservative probe


def _shingle_of(fact) -> str:
    return fact.content[:10]


def _cases():
    for char in TALKABLE:
        scope = SCOPES[char.id]
        for fact in SCRIPT.facts:
            if fact.visibility != "private":
                continue
            if fact.id in scope.known_fact_ids:
                yield ("own", char, fact)
            else:
                yield ("keyword", char, fact)
                yield ("shingle", char, fact)


CASES = list(_cases())


@pytest.mark.parametrize("kind,char,fact", CASES, ids=[
    f"{kind}:{char.id}:{fact.id}" for kind, char, fact in CASES
])
def test_matrix_cell(kind, char, fact):
    detector = LeakDetector(SCRIPT, SCOPES[char.id])
    if kind == "own":
        findings = detector.check(f"确实，{fact.content[:12]}……是我亲历的。")
        assert findings == [], f"{char.id} recalling own fact {fact.id} must not be flagged"
    elif kind == "keyword":
        findings = detector.check(f"我听人说，事情好像和{_keyword_of(fact)}有关？")
        hit = next((f for f in findings if f.fact_id == fact.id), None)
        assert hit is not None, f"{char.id} must flag foreign keyword of {fact.id}"
        assert hit.severity == "soft"
    else:  # shingle
        findings = detector.check(f"其实我早就知道，{_shingle_of(fact)}……")
        hit = next((f for f in findings if f.fact_id == fact.id), None)
        assert hit is not None, f"{char.id} must flag foreign shingle of {fact.id}"
        assert hit.severity == "hard"


@pytest.mark.parametrize("char", TALKABLE, ids=[c.id for c in TALKABLE])
def test_innocent_lines_zero_false_positives(char):
    detector = LeakDetector(SCRIPT, SCOPES[char.id])
    for line in INNOCENT_LINES:
        assert detector.check(line) == [], f"{char.id} false positive on: {line}"
