"""API request/response schemas.

Note: responses never carry secret material — character summaries are persona-only,
and talk responses expose leak *counts*, not leak details (those live in the
developer-facing event log, which ReplayEval consumes).
"""

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    script_id: str


class CharacterSummary(BaseModel):
    id: str
    name: str
    role: str
    personality: str


class GameInfo(BaseModel):
    game_id: str
    script_id: str
    title: str
    mode: str = "investigation"
    phase: str
    brief: str
    characters: list[CharacterSummary]


class PhaseRequest(BaseModel):
    target: str


class PhaseResponse(BaseModel):
    phase: str


class TalkRequest(BaseModel):
    character_id: str
    message: str = Field(min_length=1)


class TalkResponse(BaseModel):
    character_id: str
    reply: str
    rewritten: bool = False
    fell_back: bool = False
    leak_count: int = 0


class EventLogResponse(BaseModel):
    game_id: str
    phase: str
    events: list[dict]


class ClueSummary(BaseModel):
    id: str
    title: str
    location: str
    description: str


class SearchRequest(BaseModel):
    location: str = Field(min_length=1)


class SearchResponse(BaseModel):
    location: str
    unlocked: list[ClueSummary]
    total_unlocked: int


class ClueListResponse(BaseModel):
    clues: list[ClueSummary]


class AccuseRequest(BaseModel):
    suspect_id: str
    motive_fact_id: str | None = None  # None = "我不确定动机"


class AccusationOutcome(BaseModel):
    killer_correct: bool
    motive_correct: bool


class AccuseResponse(BaseModel):
    outcome: AccusationOutcome
    reveal: str


class ReplayResponse(BaseModel):
    game_id: str
    script_id: str
    title: str
    phase: str
    metrics: dict
    clues: list[ClueSummary]
    events: list[dict]


class ChainResponse(BaseModel):
    suspect_trajectory: list[str]
    key_insights: list[str]
    missed_clues: list[str]
    summary: str


class MotiveOption(BaseModel):
    fact_id: str | None  # None = "我不确定动机"
    statement: str


class MotiveOptionsResponse(BaseModel):
    options: list[MotiveOption]
