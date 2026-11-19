"""Roleplay mode: player seat selection, role card privacy, agent exclusion."""

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient

SEAT = "zhou_muchen"  # the killer seat in snow-night-villa


@pytest.fixture
def client():
    return TestClient(create_app(llm=FakeLLM()))


def test_create_with_player_seat(client):
    game = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()
    assert game["player_seat"] == SEAT
    # seat holder is excluded from talkable agents but still listed in the cast
    assert any(c["id"] == SEAT for c in game["characters"])
    assert len(game["characters"]) == 5


def test_create_without_seat_defaults_none(client):
    game = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()
    assert game["player_seat"] is None


def test_create_with_bad_seat_rejected(client):
    r = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": "shen_wanlou"}
    )
    assert r.status_code == 400
    # victim seat is not selectable
    r = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": "shen_wanlou".replace("shen_wanlou", "shen_wanlou")}
    )
    assert r.status_code == 400


def test_player_seat_agent_not_talkable(client):
    game = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()
    gid = game["game_id"]
    for p in ["self_intro", "evidence", "investigation"]:
        client.post(f"/api/games/{gid}/phase", json={"target": p})
    r = client.post(
        f"/api/games/{gid}/talk", json={"character_id": SEAT, "message": "hi"}
    )
    assert r.status_code == 400


def test_role_card_reveals_own_secrets_only(client):
    game = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()
    gid = game["game_id"]
    r = client.get(f"/api/games/{gid}/role-card")
    assert r.status_code == 200
    card = r.json()
    assert card["character"]["id"] == SEAT
    joined = "\n".join(card["secrets"])
    # killer knows the method fact; he must NOT see other people's secrets
    assert "胰岛素" in joined
    assert "私生女" not in joined
    assert "遗嘱" not in joined


def test_role_card_absent_without_seat(client):
    game = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()
    assert client.get(f"/api/games/{game['game_id']}/role-card").status_code == 400


def test_secrets_never_leak_via_gameinfo_or_replay(client):
    game = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()
    gid = game["game_id"]
    info = client.get(f"/api/games/{gid}").json()
    assert "胰岛素" not in str(info)
    replay = client.get(f"/api/games/{gid}/replay").json()
    assert "胰岛素" not in str(replay)
