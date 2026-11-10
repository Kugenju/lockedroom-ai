"""InfoGuard Layer 2 — leak detection on generated speech.

Thin policy layer over :class:`FactMatcher`: for a character's *output*, a
shingle hit is a hard leak (verbatim recital of unknowable content) and a
keyword hit is a soft leak (suspicious mention). An LLM judge adjudicates the
hits (confirm/downgrade/dismiss) in a later pipeline stage.
"""

from dataclasses import dataclass

from app.core.infoguard.matcher import FactMatcher
from app.core.infoguard.scope import InformationScope
from app.models.script import Script


@dataclass(frozen=True)
class LeakFinding:
    fact_id: str
    severity: str  # "soft" | "hard"
    matched_text: str
    method: str  # "keyword" | "shingle"


class LeakDetector:
    def __init__(self, script: Script, scope: InformationScope):
        self._matcher = FactMatcher(script, scope.forbidden_fact_ids)

    def check(self, text: str) -> list[LeakFinding]:
        return [
            LeakFinding(
                fact_id=h.fact_id,
                severity="hard" if h.method == "shingle" else "soft",
                matched_text=h.matched_text,
                method=h.method,
            )
            for h in self._matcher.match(text)
        ]
