"""Discussion channel API: transcript, player say, AI speak (SSE), propagation."""

import json

import pytest
from app.api.app import create_app
from app.core.llm.fake import FakeLLM
from fastapi.testclient import TestClient

SEAT = "lin_wanqiu"


@pytest.fixture
def client():
    return TestClient(create_app(llm=FakeLLM()))


@pytest.fixture
def game_id(client):
    gid = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()["game_id"]
    for p in ["self_intro", "evidence", "investigation"]:
        client.post(f"/api/games/{gid}/phase", json={"target": p})
    return gid


def test_say_and_transcript(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/discussion/say", json={"message": "大家说说昨晚的行踪。"}
    )
    assert r.status_code == 200
    messages = r.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["sender"] == "player"
    assert messages[0]["sender_name"] == "玩家"
    r = client.get(f"/api/games/{game_id}/discussion")
    assert len(r.json()["messages"]) == 1


def test_ai_speak_streams_and_broadcasts(client, game_id):
    client.post(f"/api/games/{game_id}/discussion/say", json={"message": "谁最后见到老爷？"})
    with client.stream(
        "POST",
        f"/api/games/{game_id}/discussion/speak",
        json={"character_id": "zhou_muchen"},
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "event: token" in body and "event: done" in body
    done_line = next(ln for ln in body.splitlines() if ln.startswith("data:") and "reply" in ln)
    payload = json.loads(done_line.removeprefix("data:").strip())
    assert payload["character_id"] == "zhou_muchen"
    # speech landed in the public thread with the speaker's name
    thread = client.get(f"/api/games/{game_id}/discussion").json()["messages"]
    assert len(thread) == 2
    assert thread[1]["sender"] == "zhou_muchen"
    assert thread[1]["sender_name"] == "周慕辰"


def test_player_seat_cannot_speak_as_ai(client, game_id):
    r = client.post(
        f"/api/games/{game_id}/discussion/speak", json={"character_id": SEAT}
    )
    assert r.status_code == 400


def test_discussion_blocked_outside_investigation(client):
    gid = client.post(
        "/api/games", json={"script_id": "snow-night-villa", "player_seat": SEAT}
    ).json()["game_id"]
    r = client.post(f"/api/games/{gid}/discussion/say", json={"message": "hi"})
    assert r.status_code == 400
