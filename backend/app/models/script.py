"""Structured murder-mystery script (剧本) schema.

A script is the single source of truth for a case:
- ``facts``: atomic pieces of information, each with a stable id. ``public`` facts are
  common knowledge; ``private`` facts are secrets that only specific characters know
  (or that only clues can reveal).
- ``characters``: the cast. Each character privately knows the facts listed in
  ``known_fact_ids`` — this is the foundation of InfoGuard's information isolation.
- ``clues``: physical evidence unlocked during the investigation; each reveals facts.
- ``evaluation``: the ground truth used by ReplayEval (killer, motive, required facts).
"""

from pydantic import BaseModel, Field, model_validator


class Fact(BaseModel):
    id: str
    visibility: str = "private"  # "public" | "private"
    core: bool = False  # core facts are required for a correct solution (eval metric)
    content: str
    keywords: list[str] = Field(default_factory=list)  # seeds for the leak detector


class ScriptCharacter(BaseModel):
    id: str
    name: str
    role: str
    is_victim: bool = False
    is_killer: bool = False
    public_profile: str = ""
    personality: str = ""
    speaking_style: str = ""
    known_fact_ids: list[str] = Field(default_factory=list)

    @property
    def talkable(self) -> bool:
        return not self.is_victim


class ScriptClue(BaseModel):
    id: str
    title: str
    stage: int = 0  # unlock batch during the evidence phase
    location: str = ""
    description: str = ""
    reveals_fact_ids: list[str] = Field(default_factory=list)


class ScriptEvaluation(BaseModel):
    killer_id: str
    motive_fact_id: str
    required_fact_ids: list[str] = Field(default_factory=list)


class Script(BaseModel):
    id: str
    title: str
    brief: str = ""
    facts: list[Fact]
    characters: list[ScriptCharacter]
    clues: list[ScriptClue]
    evaluation: ScriptEvaluation

    def get_fact(self, fact_id: str) -> Fact:
        for f in self.facts:
            if f.id == fact_id:
                return f
        raise KeyError(fact_id)

    def get_character(self, char_id: str) -> ScriptCharacter:
        for c in self.characters:
            if c.id == char_id:
                return c
        raise KeyError(char_id)

    @property
    def talkable_characters(self) -> list[ScriptCharacter]:
        return [c for c in self.characters if c.talkable]

    @property
    def killer(self) -> ScriptCharacter:
        return self.get_character(self.evaluation.killer_id)

    @model_validator(mode="after")
    def validate_references(self) -> "Script":
        fact_ids = [f.id for f in self.facts]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("duplicate fact ids")
        for f in self.facts:
            if f.visibility not in ("public", "private"):
                raise ValueError(f"fact {f.id}: unknown visibility {f.visibility!r}")

        char_ids = [c.id for c in self.characters]
        if len(set(char_ids)) != len(char_ids):
            raise ValueError("duplicate character ids")

        for c in self.characters:
            if c.is_victim and c.is_killer:
                raise ValueError(f"character {c.id}: cannot be both victim and killer")
            if c.is_victim and c.known_fact_ids:
                raise ValueError(f"victim {c.id} cannot know facts")
            for fid in c.known_fact_ids:
                if fid not in fact_ids:
                    raise ValueError(f"character {c.id}: unknown fact {fid}")

        killers = [c for c in self.characters if c.is_killer]
        if len(killers) != 1:
            raise ValueError(f"exactly one killer required, found {len(killers)}")
        victims = [c for c in self.characters if c.is_victim]
        if len(victims) > 1:
            raise ValueError(f"at most one victim allowed, found {len(victims)}")

        for clue in self.clues:
            for fid in clue.reveals_fact_ids:
                if fid not in fact_ids:
                    raise ValueError(f"clue {clue.id}: unknown fact {fid}")

        ev = self.evaluation
        if ev.killer_id not in char_ids:
            raise ValueError(f"evaluation.killer_id {ev.killer_id} is not a character")
        if not self.get_character(ev.killer_id).is_killer:
            raise ValueError("evaluation.killer_id must mark the character with is_killer")
        for fid in [ev.motive_fact_id, *ev.required_fact_ids]:
            if fid not in fact_ids:
                raise ValueError(f"evaluation: unknown fact {fid}")
        if ev.motive_fact_id not in self.get_character(ev.killer_id).known_fact_ids:
            raise ValueError("the killer must know the motive fact")

        # Solvability: every private fact must be reachable — either some character
        # knows it (player can extract it via dialogue) or some clue reveals it.
        known = {fid for c in self.characters for fid in c.known_fact_ids}
        revealed = {fid for clue in self.clues for fid in clue.reveals_fact_ids}
        for f in self.facts:
            if f.visibility == "private" and f.id not in known and f.id not in revealed:
                raise ValueError(
                    f"private fact {f.id} is known by nobody and revealed by no clue"
                )
        return self
