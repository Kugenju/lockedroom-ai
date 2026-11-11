"""Game API routes: scripts, session lifecycle, dialogue (JSON + SSE), event log."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    AccusationOutcome,
    AccuseRequest,
    AccuseResponse,
    ChainResponse,
    CharacterSummary,
    ClueListResponse,
    ClueSummary,
    CreateGameRequest,
    EventLogResponse,
    GameInfo,
    MotiveOption,
    MotiveOptionsResponse,
    PhaseRequest,
    PhaseResponse,
    ReplayResponse,
    SearchRequest,
    SearchResponse,
    TalkRequest,
    TalkResponse,
)
from app.api.store import GameRecord, GameStore, UnknownGameError
from app.core.engine.state_machine import IllegalPhaseTransition, Phase
from app.core.replayeval.chain import extract_chain
from app.core.replayeval.metrics import compute_metrics
from app.core.replayeval.report import render_report
from app.core.scripts.loader import list_scripts

router = APIRouter(prefix="/api", tags=["game"])


def get_store(request: Request) -> GameStore:
    return request.app.state.store


def _get_record(store: GameStore, game_id: str) -> GameRecord:
    try:
        return store.get(game_id)
    except UnknownGameError:
        raise HTTPException(status_code=404, detail=f"game {game_id} not found") from None


def _get_agent(record: GameRecord, character_id: str):
    agent = record.agents.get(character_id)
    if agent is None:
        raise HTTPException(status_code=400, detail=f"character {character_id} is not talkable")
    return agent


@router.get("/scripts")
def list_available_scripts() -> dict:
    return {"scripts": list_scripts()}


@router.post("/games", status_code=200)
def create_game(req: CreateGameRequest, store: GameStore = Depends(get_store)) -> GameInfo:
    try:
        record = store.create(req.script_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    session = record.session
    return GameInfo(
        game_id=session.session_id,
        script_id=session.script.id,
        title=session.script.title,
        mode=session.script.mode,
        phase=session.phase.value,
        brief=session.script.brief,
        characters=[
            CharacterSummary(id=c.id, name=c.name, role=c.role, personality=c.personality)
            for c in session.script.talkable_characters
        ],
    )


@router.get("/games/{game_id}")
def get_game(game_id: str, store: GameStore = Depends(get_store)) -> GameInfo:
    record = _get_record(store, game_id)
    session = record.session
    return GameInfo(
        game_id=session.session_id,
        script_id=session.script.id,
        title=session.script.title,
        mode=session.script.mode,
        phase=session.phase.value,
        brief=session.script.brief,
        characters=[
            CharacterSummary(id=c.id, name=c.name, role=c.role, personality=c.personality)
            for c in session.script.talkable_characters
        ],
    )


@router.post("/games/{game_id}/phase")
def advance_phase(
    game_id: str, req: PhaseRequest, store: GameStore = Depends(get_store)
) -> PhaseResponse:
    record = _get_record(store, game_id)
    try:
        target = Phase(req.target)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown phase {req.target!r}") from None
    try:
        record.session.advance_phase(target)
    except IllegalPhaseTransition as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return PhaseResponse(phase=record.session.phase.value)


@router.post("/games/{game_id}/talk")
async def talk(game_id: str, req: TalkRequest, store: GameStore = Depends(get_store)) -> TalkResponse:
    record = _get_record(store, game_id)
    agent = _get_agent(record, req.character_id)
    reply = await agent.respond(req.message)
    return TalkResponse(
        character_id=agent.character.id,
        reply=reply.text,
        rewritten=reply.rewritten,
        fell_back=reply.fell_back,
        leak_count=len(reply.leaks),
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/games/{game_id}/talk/stream")
async def talk_stream(
    game_id: str, req: TalkRequest, store: GameStore = Depends(get_store)
) -> StreamingResponse:
    record = _get_record(store, game_id)
    agent = _get_agent(record, req.character_id)

    async def gen() -> AsyncIterator[str]:
        # The reply is fully screened by InfoGuard before any token is emitted:
        # unapproved text never reaches the wire.
        reply = await agent.respond(req.message)
        for i in range(0, len(reply.text), 3):
            yield _sse("token", {"chunk": reply.text[i : i + 3]})
        yield _sse(
            "done",
            {
                "character_id": agent.character.id,
                "reply": reply.text,
                "rewritten": reply.rewritten,
                "fell_back": reply.fell_back,
                "leak_count": len(reply.leaks),
            },
        )

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/games/{game_id}/events")
def get_events(game_id: str, store: GameStore = Depends(get_store)) -> EventLogResponse:
    record = _get_record(store, game_id)
    return EventLogResponse(
        game_id=game_id,
        phase=record.session.phase.value,
        events=[e.to_dict() for e in record.session.events],
    )


def _clue_summary(clue) -> ClueSummary:
    return ClueSummary(id=clue.id, title=clue.title, location=clue.location, description=clue.description)


@router.get("/games/{game_id}/locations")
def list_locations(game_id: str, store: GameStore = Depends(get_store)) -> dict:
    """Searchable locations with per-location clue counts (counts only, no spoilers)."""
    record = _get_record(store, game_id)
    session = record.session
    unlocked = session.unlocked_clue_ids
    by_loc: dict[str, dict] = {}
    for clue in session.script.clues:
        entry = by_loc.setdefault(
            clue.location, {"location": clue.location, "total": 0, "unlocked": 0}
        )
        entry["total"] += 1
        if clue.id in unlocked:
            entry["unlocked"] += 1
    return {"locations": sorted(by_loc.values(), key=lambda x: x["location"])}


@router.post("/games/{game_id}/search")
def search_clues(
    game_id: str, req: SearchRequest, store: GameStore = Depends(get_store)
) -> SearchResponse:
    record = _get_record(store, game_id)
    session = record.session
    matches = [c for c in session.script.clues if c.location.startswith(req.location)]
    if not matches:
        raise HTTPException(status_code=404, detail=f"no searchable location matches {req.location!r}")
    unlocked = []
    for clue in matches:
        if session.unlock_clue(clue.id, clue.title) is not None:
            unlocked.append(_clue_summary(clue))
    return SearchResponse(
        location=req.location,
        unlocked=unlocked,
        total_unlocked=len(session.unlocked_clue_ids),
    )


@router.get("/games/{game_id}/clues")
def get_player_clues(game_id: str, store: GameStore = Depends(get_store)) -> ClueListResponse:
    record = _get_record(store, game_id)
    session = record.session
    by_id = {c.id: c for c in session.script.clues}
    clues = [_clue_summary(by_id[cid]) for cid in sorted(session.unlocked_clue_ids) if cid in by_id]
    return ClueListResponse(clues=clues)


@router.get("/games/{game_id}/motive-options")
def get_motive_options(
    game_id: str, store: GameStore = Depends(get_store)
) -> MotiveOptionsResponse:
    """Spoiler-free motive candidates: only facts the player has already revealed via clues."""
    record = _get_record(store, game_id)
    session = record.session
    script = session.script
    revealed = {
        fid
        for clue in script.clues
        if clue.id in session.unlocked_clue_ids
        for fid in clue.reveals_fact_ids
    }
    options = [MotiveOption(fact_id=None, statement="我不确定动机")]
    options += [
        MotiveOption(fact_id=fid, statement=script.get_fact(fid).content)
        for fid in sorted(revealed)
    ]
    return MotiveOptionsResponse(options=options)


@router.post("/games/{game_id}/accuse")
async def accuse(
    game_id: str, req: AccuseRequest, store: GameStore = Depends(get_store)
) -> AccuseResponse:
    record = _get_record(store, game_id)
    session = record.session
    script = session.script
    if session.phase is not Phase.INVESTIGATION:
        raise HTTPException(status_code=400, detail="accusation is only allowed during investigation")
    try:
        suspect = script.get_character(req.suspect_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"unknown suspect {req.suspect_id!r}") from None
    if suspect.is_victim:
        raise HTTPException(status_code=400, detail="the victim cannot be the killer")
    if req.motive_fact_id is not None:
        try:
            script.get_fact(req.motive_fact_id)
        except KeyError:
            raise HTTPException(
                status_code=400, detail=f"unknown motive fact {req.motive_fact_id!r}"
            ) from None

    session.advance_phase(Phase.ACCUSATION)
    outcome = AccusationOutcome(
        killer_correct=req.suspect_id == script.evaluation.killer_id,
        motive_correct=req.motive_fact_id is not None
        and req.motive_fact_id == script.evaluation.motive_fact_id,
    )
    session.record_player_action(
        "accuse",
        {
            "suspect_id": req.suspect_id,
            "motive_fact_id": req.motive_fact_id,
            "killer_correct": outcome.killer_correct,
            "motive_correct": outcome.motive_correct,
        },
    )

    from app.core.engine.reveal import generate_reveal

    reveal = await generate_reveal(script, req.suspect_id, req.motive_fact_id, session.llm)
    session.advance_phase(Phase.REVEAL)
    session.record_system("reveal", reveal)
    session.advance_phase(Phase.ENDED)
    return AccuseResponse(outcome=outcome, reveal=reveal)


@router.get("/games/{game_id}/replay")
def get_replay(game_id: str, store: GameStore = Depends(get_store)) -> ReplayResponse:
    record = _get_record(store, game_id)
    session = record.session
    metrics = compute_metrics(session.script, session.events)
    by_id = {c.id: c for c in session.script.clues}
    clues = [_clue_summary(by_id[cid]) for cid in sorted(session.unlocked_clue_ids) if cid in by_id]
    return ReplayResponse(
        game_id=game_id,
        script_id=session.script.id,
        title=session.script.title,
        phase=session.phase.value,
        metrics=metrics.to_dict(),
        clues=clues,
        events=[e.to_dict() for e in session.events],
    )


@router.get("/games/{game_id}/chain")
async def get_chain(game_id: str, store: GameStore = Depends(get_store)) -> ChainResponse:
    record = _get_record(store, game_id)
    session = record.session
    chain = await extract_chain(session.script, session.events, session.llm)
    return ChainResponse(
        suspect_trajectory=chain.suspect_trajectory,
        key_insights=chain.key_insights,
        missed_clues=chain.missed_clues,
        summary=chain.summary,
    )


@router.get("/games/{game_id}/report")
async def get_report(game_id: str, store: GameStore = Depends(get_store)) -> Response:
    record = _get_record(store, game_id)
    session = record.session
    metrics = compute_metrics(session.script, session.events)
    chain = await extract_chain(session.script, session.events, session.llm)
    md = render_report(session.script, session.events, metrics, chain)
    return Response(content=md, media_type="text/markdown; charset=utf-8")
