"""Search (搜证) API tests."""

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(create_app(llm=FakeLLM()))


@pytest.fixture
def game_id(client):
    return client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]


def test_locations_listing(client, game_id):
    r = client.get(f"/api/games/{game_id}/locations")
    assert r.status_code == 200
    locations = r.json()["locations"]
    assert "书房" in locations or any("书房" in loc for loc in locations)
    assert "医疗室" in locations


def test_search_unlocks_clues_by_prefix(client, game_id):
    r = client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    assert r.status_code == 200
    data = r.json()
    unlocked_ids = {c["id"] for c in data["unlocked"]}
    assert unlocked_ids == {"c_report", "c_window", "c_will"}
    # player-facing summaries carry no fact ids (no spoilers)
    assert all("reveals_fact_ids" not in c for c in data["unlocked"])
    assert data["total_unlocked"] == 3


def test_search_is_idempotent(client, game_id):
    client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    r = client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    assert r.json()["unlocked"] == []
    assert r.json()["total_unlocked"] == 3


def test_second_location_accumulates(client, game_id):
    client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    r = client.post(f"/api/games/{game_id}/search", json={"location": "医疗室"})
    assert {c["id"] for c in r.json()["unlocked"]} == {"c_insulin", "c_ledger"}
    assert r.json()["total_unlocked"] == 5


def test_player_clue_list(client, game_id):
    assert client.get(f"/api/games/{game_id}/clues").json()["clues"] == []
    client.post(f"/api/games/{game_id}/search", json={"location": "医疗室"})
    clues = client.get(f"/api/games/{game_id}/clues").json()["clues"]
    assert {c["id"] for c in clues} == {"c_insulin", "c_ledger"}
    assert clues[0]["description"]  # descriptions shown to the player


def test_search_events_in_event_log(client, game_id):
    client.post(f"/api/games/{game_id}/search", json={"location": "书房"})
    events = client.get(f"/api/games/{game_id}/events").json()["events"]
    clue_events = [e for e in events if e["type"] == "clue_unlocked"]
    assert len(clue_events) == 3
    assert clue_events[0]["payload"]["clue_id"].startswith("c_")


def test_search_unknown_location(client, game_id):
    r = client.post(f"/api/games/{game_id}/search", json={"location": "火星"})
    assert r.status_code == 404
