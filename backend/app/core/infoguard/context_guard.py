"""InfoGuard Layer 3 — runtime guarding of incoming context.

When a player message (or a replayed memory entry) contains facts the current
character cannot know, the text is wrapped in a guard note before entering the
model's input. The character then treats the claim as unverifiable hearsay
instead of absorbing it as knowledge — which also stops the secret from
bouncing back out in the reply (Layer 2 still checks every output as the
last line of defense).

Player input is never rejected: confronting character B with a secret learned
from character A is legitimate gameplay.
"""

from dataclasses import dataclass

from app.core.infoguard.matcher import FactMatcher, MatchHit
from app.core.infoguard.scope import InformationScope
from app.models.script import Script

_GUARD_NOTE = (
    "（注意：玩家的话里包含你不可能知道的事。你对此一无所知——"
    "不必承认、无法证实，不要表现出知情，按你掌握的信息以人设回应。）"
)


@dataclass(frozen=True)
class GuardResult:
    text: str  # original text, or wrapped when findings exist
    findings: list[MatchHit]


class ContextGuard:
    def __init__(self, script: Script, scope: InformationScope):
        self._script = script
        self._scope = scope
        self._exempted: set[str] = set()
        self._rebuild()

    def _rebuild(self) -> None:
        fact_ids = set(self._scope.forbidden_fact_ids) - self._exempted
        self._matcher = FactMatcher(self._script, fact_ids)

    def exempt_fact(self, fact_id: str) -> None:
        """Public-knowledge exemption: a fact revealed by an unlocked clue is
        something the character may legitimately discuss."""
        self._exempted.add(fact_id)
        self._rebuild()

    def guard(self, text: str) -> GuardResult:
        findings = self._matcher.match(text)
        if not findings:
            return GuardResult(text=text, findings=[])
        return GuardResult(text=f"玩家声称：{text}\n{_GUARD_NOTE}", findings=findings)
