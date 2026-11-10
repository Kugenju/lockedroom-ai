"""End-to-end API tests with the FakeLLM — no network, no real model."""

import json

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app(llm=FakeLLM("案发时我在厨房备茶。"))
    return TestClient(app)


def _advance_to_investigation(client, game_id):
    for target in ["self_intro", "evidence", "investigation"]:
        r = client.post(f"/api/games/{game_id}/phase", json={"target": target})
        assert r.status_code == 200, r.text


def test_list_scripts(client):
    r = client.get("/api/scripts")
    assert r.status_code == 200
    assert "snow-night-villa" in r.json()["scripts"]


def test_create_game(client):
    r = client.post("/api/games", json={"script_id": "snow-night-villa"})
    assert r.status_code == 200
    data = r.json()
    assert data["phase"] == "intro"
    # 6 characters minus the victim → 5 talkable
    assert len(data["characters"]) == 5
    assert all(c["id"] != "shen_wanlou" for c in data["characters"])
    # summaries must never contain spoiler material
    assert all("胰岛素" not in json.dumps(c, ensure_ascii=False) for c in data["characters"])


def test_create_game_unknown_script(client):
    r = client.post("/api/games", json={"script_id": "no-such-script"})
    assert r.status_code == 404


def test_talk_and_events_roundtrip(client):
    game_id = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    _advance_to_investigation(client, game_id)

    r = client.post(
        f"/api/games/{game_id}/talk",
        json={"character_id": "lin_wanqiu", "message": "你昨晚在哪？"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "案发时我在厨房备茶。"
    assert data["rewritten"] is False
    assert data["leak_count"] == 0

    r = client.get(f"/api/games/{game_id}/events")
    events = r.json()["events"]
    senders = [e["payload"]["sender"] for e in events if e["type"] == "message"]
    assert senders == ["player", "lin_wanqiu"]


def test_talk_stream_sse(client):
    game_id = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    _advance_to_investigation(client, game_id)

    with client.stream(
        "POST",
        f"/api/games/{game_id}/talk/stream",
        json={"character_id": "lin_wanqiu", "message": "在吗"},
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())

    assert "event: token" in body
    assert "event: done" in body
    done_line = next(
        ln for ln in body.splitlines() if ln.startswith("data:") and "reply" in ln
    )
    payload = json.loads(done_line.removeprefix("data:").strip())
    assert payload["reply"] == "案发时我在厨房备茶。"


def test_talk_to_victim_rejected(client):
    game_id = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    _advance_to_investigation(client, game_id)
    r = client.post(
        f"/api/games/{game_id}/talk",
        json={"character_id": "shen_wanlou", "message": "你怎么死的？"},
    )
    assert r.status_code == 400


def test_illegal_phase_advance_rejected(client):
    game_id = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    r = client.post(f"/api/games/{game_id}/phase", json={"target": "ended"})
    assert r.status_code == 400


def test_leak_events_visible_in_event_log(client):
    app = create_app(llm=FakeLLM(["老爷死于过量胰岛素注射，我看见了。", "我不知道。"]))
    c = TestClient(app)
    game_id = c.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    _advance_to_investigation(c, game_id)

    r = c.post(
        f"/api/games/{game_id}/talk",
        json={"character_id": "lin_wanqiu", "message": "老爷怎么死的？"},
    )
    assert r.json()["rewritten"] is True

    events = c.get(f"/api/games/{game_id}/events").json()["events"]
    leaks = [e for e in events if e["type"] == "leak_detected"]
    assert len(leaks) == 1
    assert leaks[0]["payload"]["fact_id"] == "t_method"
    assert leaks[0]["payload"]["action"] == "rewritten"


def test_unknown_game_returns_404(client):
    assert client.get("/api/games/nope/events").status_code == 404
    r = client.post("/api/games/nope/talk", json={"character_id": "c", "message": "m"})
    assert r.status_code == 404
