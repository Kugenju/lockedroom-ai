"""Accusation (指认) + reveal (真相揭晓) API tests."""

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient

REVEAL_TEXT = "各位，真相是：周慕辰医生利用胰岛素……"


@pytest.fixture
def client():
    return TestClient(create_app(llm=FakeLLM(REVEAL_TEXT)))


@pytest.fixture
def game_id(client):
    gid = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    for p in ["self_intro", "evidence", "investigation"]:
        client.post(f"/api/games/{gid}/phase", json={"target": p})
    return gid


def test_correct_accusation_walks_to_ended(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["outcome"] == {"killer_correct": True, "motive_correct": True}
    assert data["reveal"] == REVEAL_TEXT

    game = client.get(f"/api/games/{game_id}").json()
    assert game["phase"] == "ended"


def test_wrong_accusation_records_outcome(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "fang_heming", "motive_fact_id": "t_inheritance"},
    )
    assert r.json()["outcome"] == {"killer_correct": False, "motive_correct": False}
    assert client.get(f"/api/games/{game_id}").json()["phase"] == "ended"


def test_half_correct_accusation(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_window"},
    )
    assert r.json()["outcome"] == {"killer_correct": True, "motive_correct": False}


def test_accuse_only_from_investigation(client):
    gid = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    r = client.post(
        f"/api/games/{gid}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug"},
    )
    assert r.status_code == 400


def test_accuse_unknown_suspect_or_motive(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "batman", "motive_fact_id": "t_drug"},
    )
    assert r.status_code == 400
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_nope"},
    )
    assert r.status_code == 400


def test_accusation_cannot_target_victim(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "shen_wanlou", "motive_fact_id": "t_drug"},
    )
    assert r.status_code == 400


def test_event_log_contains_accusation_and_reveal(client, game_id):
    client.post(
        f"/api/games/{game_id}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug"},
    )
    events = client.get(f"/api/games/{game_id}/events").json()["events"]
    phases = [e["payload"]["to"] for e in events if e["type"] == "phase_change"]
    assert phases == ["self_intro", "evidence", "investigation", "accusation", "reveal", "ended"]

    accuse = next(e for e in events if e["type"] == "player_action" and e["payload"]["action"] == "accuse")
    assert accuse["payload"]["detail"]["killer_correct"] is True

    reveal = next(e for e in events if e["type"] == "system")
    assert reveal["payload"]["kind"] == "reveal"
    assert REVEAL_TEXT in reveal["payload"]["content"]


def test_motive_options_spoiler_free(client, game_id):
    r = client.get(f"/api/games/{game_id}/motive-options")
    assert r.status_code == 200
    options = r.json()["options"]
    # before searching, only the "unsure" fallback is offered — no spoilers
    assert len(options) == 1
    assert options[0]["fact_id"] is None

    client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    r = client.get(f"/api/games/{game_id}/motive-options")
    fact_ids = {o["fact_id"] for o in r.json()["options"]}
    # study drawer reveals t_will + t_inheritance
    assert {"t_will", "t_inheritance"} <= fact_ids
    assert "t_drug" not in fact_ids  # the true motive stays hidden


def test_motive_option_statements_readable(client, game_id):
    client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    options = client.get(f"/api/games/{game_id}/motive-options").json()["options"]
    statements = [o["statement"] for o in options]
    assert any("遗嘱" in s for s in statements)
