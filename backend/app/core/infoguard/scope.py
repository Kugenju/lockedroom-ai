"""InfoGuard Layer 1 — static information scoping.

At script-compile time, every character gets an :class:`InformationScope`:
the exact set of facts its prompt and context may contain. Everything else is
forbidden and feeds the Layer-2 leak detector.

Scope semantics:
- ``known_fact_ids``  = public facts ∪ facts the character privately knows.
  These may appear in the character's prompt and (for secrets) in its replies.
- ``forbidden_fact_ids`` = the exact complement. The prompt builder must never
  inject these; the leak detector watches generated speech against them.

Note: the killer *knows* the murder facts (they committed the act), so those
facts are in-scope for the killer — keeping them hidden is the prompt's job
(persona + concealment instruction), not InfoGuard's. InfoGuard guards facts a
character cannot plausibly know; self-incrimination by the killer is a
gameplay-quality issue tracked separately in evaluation.
"""

from dataclasses import dataclass

from app.models.script import Script


@dataclass(frozen=True)
class InformationScope:
    character_id: str
    known_fact_ids: frozenset[str]
    forbidden_fact_ids: frozenset[str]

    def may_know(self, fact_id: str) -> bool:
        return fact_id in self.known_fact_ids


def compile_scopes(script: Script) -> dict[str, InformationScope]:
    """Build the information scope for every character of a validated script."""
    all_ids = frozenset(f.id for f in script.facts)
    public_ids = frozenset(f.id for f in script.facts if f.visibility == "public")

    scopes: dict[str, InformationScope] = {}
    for c in script.characters:
        known = public_ids | frozenset(c.known_fact_ids)
        scopes[c.id] = InformationScope(
            character_id=c.id,
            known_fact_ids=known,
            forbidden_fact_ids=all_ids - known,
        )
    return scopes
