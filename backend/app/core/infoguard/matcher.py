"""Shared fact-matching index: which facts does a piece of text touch?

Used by both directions of InfoGuard:
- output direction (LeakDetector): does a character's reply contain forbidden facts?
- input direction (ContextGuard): does a player message / memory entry contain
  facts the current character cannot know?

Two signals per indexed fact (at most one hit per fact, shingle wins):
- "shingle": a contiguous substring (min 6 chars) of the fact content appears
  verbatim — a strong verbatim-recital signal.
- "keyword": any of the fact's keywords appears — a weak hint.
"""

from dataclasses import dataclass

from app.models.script import Script

MIN_SHINGLE = 6


@dataclass(frozen=True)
class MatchHit:
    fact_id: str
    matched_text: str
    method: str  # "keyword" | "shingle"


class FactMatcher:
    def __init__(self, script: Script, fact_ids):
        self._indexed: list[tuple[str, list[str], set[str]]] = []
        for fid in sorted(fact_ids):
            fact = script.get_fact(fid)
            shingles = (
                {fact.content[i : i + MIN_SHINGLE] for i in range(len(fact.content) - MIN_SHINGLE + 1)}
                if len(fact.content) >= MIN_SHINGLE
                else {fact.content}
            )
            self._indexed.append((fid, fact.keywords, shingles))

    def match(self, text: str) -> list[MatchHit]:
        hits: list[MatchHit] = []
        for fact_id, keywords, shingles in self._indexed:
            shingle_hit = next((s for s in shingles if s in text), None)
            if shingle_hit:
                hits.append(MatchHit(fact_id, shingle_hit, "shingle"))
                continue
            kw_hit = next((k for k in keywords if k and k in text), None)
            if kw_hit:
                hits.append(MatchHit(fact_id, kw_hit, "keyword"))
        return hits
