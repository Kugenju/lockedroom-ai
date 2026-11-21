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
        self._script = script
        self._scope = scope
        self._exempted: set[str] = set()
        self._rebuild()

    def _rebuild(self) -> None:
        fact_ids = set(self._scope.forbidden_fact_ids) - self._exempted
        self._matcher = FactMatcher(self._script, fact_ids)

    def exempt_fact(self, fact_id: str) -> None:
        """A fact became public knowledge (e.g. its clue was unlocked): stop
        treating mentions of it as leaks for this agent."""
        self._exempted.add(fact_id)
        self._rebuild()

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
