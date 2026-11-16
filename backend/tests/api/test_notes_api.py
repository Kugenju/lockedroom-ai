"""Integration tests: auto-notes from importance scoring + notes API CRUD."""

import pytest
from app.api.app import create_app
from app.core.agents.agent import CharacterAgent
from app.core.agents.memory import AgentMemory
from app.core.engine.session import GameSession
from app.core.engine.state_machine import Phase
from app.core.infoguard.detector import LeakDetector
from app.core.infoguard.scope import compile_scopes
from app.core.llm.fake import FakeLLM
from app.core.scripts.loader import load_script
from fastapi.testclient import TestClient

SCRIPT = load_script("snow-night-villa")


def _agent(session: GameSession, scorer) -> CharacterAgent:
    scope = compile_scopes(SCRIPT)["lin_wanqiu"]
    detector = LeakDetector(SCRIPT, scope)
    memory = AgentMemory(
        scorer_llm=scorer,
        summarizer_llm=FakeLLM("早前对话摘要。"),
        detector=detector,
    )
    return CharacterAgent(
        character=SCRIPT.get_character("lin_wanqiu"),
        script=SCRIPT,
        scope=scope,
        llm=session.llm,
        session=session,
        detector=detector,
        memory=memory,
    )


@pytest.fixture
def session() -> GameSession:
    session = GameSession("s1", SCRIPT, FakeLLM())
    for phase in (Phase.SELF_INTRO, Phase.EVIDENCE, Phase.INVESTIGATION):
        session.advance_phase(phase)
    return session


async def test_high_importance_reply_is_auto_noted(session):
    session.llm = FakeLLM("我昨晚其实看见了遗嘱草稿。")
    agent = _agent(session, scorer=FakeLLM('{"importance": 9}'))
    await agent.respond("你看到了什么？")
    notes = session.notes()
    assert len(notes) == 1
    assert notes[0]["source"] == "auto"
    assert notes[0]["char_id"] == "lin_wanqiu"
    assert notes[0]["importance"] == 9
    assert "遗嘱草稿" in notes[0]["content"]


async def test_low_importance_reply_is_not_noted(session):
    session.llm = FakeLLM("没什么特别的。")
    agent = _agent(session, scorer=FakeLLM('{"importance": 4}'))
    await agent.respond("你昨晚在哪里？")
    assert session.notes() == []


# --- API level (player notes CRUD) ---


@pytest.fixture
def client():
    return TestClient(create_app(llm=FakeLLM()))


@pytest.fixture
def game_id(client):
    return client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]


def test_add_and_list_player_notes(client, game_id):
    r = client.post(f"/api/games/{game_id}/notes", json={"content": "周慕辰的笔有刮痕，可疑"})
    assert r.status_code == 200
    note = r.json()
    assert note["source"] == "player"
    notes = client.get(f"/api/games/{game_id}/notes").json()["notes"]
    assert [n["content"] for n in notes] == ["周慕辰的笔有刮痕，可疑"]


def test_delete_note_folds_from_list(client, game_id):
    note = client.post(f"/api/games/{game_id}/notes", json={"content": "临时笔记"}).json()
    r = client.delete(f"/api/games/{game_id}/notes/{note['note_id']}")
    assert r.status_code == 200
    assert client.get(f"/api/games/{game_id}/notes").json()["notes"] == []


def test_delete_unknown_note_404(client, game_id):
    assert client.delete(f"/api/games/{game_id}/notes/nope").status_code == 404
