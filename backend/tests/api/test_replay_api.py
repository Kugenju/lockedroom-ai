"""Replay / report API tests over a full fake-LLM game."""

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient

CHAIN_JSON = (
    '{"suspect_trajectory": ["周慕辰"], "key_insights": ["胰岛素笔"], '
    '"missed_clues": ["黑账"], "summary": "锁定了医生。"}'
)


@pytest.fixture
def client():
    # FakeLLM replies: first call(s) = dialogue, later call = reveal, then chain
    return TestClient(create_app(llm=FakeLLM(["我在厨房。", "真相揭晓……", CHAIN_JSON])))


@pytest.fixture
def finished_game(client):
    gid = client.post("/api/games", json={"script_id": "snow-night-villa"}).json()["game_id"]
    for p in ["self_intro", "evidence", "investigation"]:
        client.post(f"/api/games/{gid}/phase", json={"target": p})
    client.post(f"/api/games/{gid}/search", json={"location": "医疗室"})
    client.post(f"/api/games/{gid}/talk", json={"character_id": "lin_wanqiu", "message": "你昨晚在哪？"})
    client.post(
        f"/api/games/{gid}/accuse",
        json={"suspect_id": "zhou_muchen", "motive_fact_id": "t_drug"},
    )
    return gid


def test_replay_assembles_timeline_and_metrics(client, finished_game):
    r = client.get(f"/api/games/{finished_game}/replay")
    assert r.status_code == 200
    data = r.json()
    assert data["phase"] == "ended"
    assert data["metrics"]["killer_correct"] is True
    assert data["metrics"]["clues_unlocked"] == 2
    assert data["metrics"]["character_replies"] >= 1
    assert len(data["events"]) > 5
    assert {c["id"] for c in data["clues"]} == {"c_insulin", "c_ledger"}


def test_report_endpoint_returns_markdown(client, finished_game):
    r = client.get(f"/api/games/{finished_game}/report")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text.startswith("# 复盘报告")
    assert "锁定了医生" in r.text  # chain content embedded


def test_chain_endpoint_returns_structured_json(client, finished_game):
    r = client.get(f"/api/games/{finished_game}/chain")
    assert r.status_code == 200
    data = r.json()
    assert data["suspect_trajectory"] == ["周慕辰"]
    assert data["summary"] == "锁定了医生。"


def test_replay_unknown_game_404(client):
    assert client.get("/api/games/nope/replay").status_code == 404
    assert client.get("/api/games/nope/report").status_code == 404
