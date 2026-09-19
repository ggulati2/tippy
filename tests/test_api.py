import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Use a throwaway database and a known PIN so tests never touch real data.
    monkeypatch.setenv("TIPPY_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PARENT_PIN", "4321")
    from backend.app import create_app
    return TestClient(create_app(), base_url="http://127.0.0.1:8765")


def test_home_page_served(client):
    assert client.get("/").status_code == 200


def test_mascot_line_is_text(client):
    assert client.get("/api/mascot/line?event=success").json()["text"]


def test_foreign_host_is_refused(client):
    assert client.get("/api/settings", headers={"host": "evil.example"}).status_code == 403


def test_parent_endpoints_need_pin(client):
    assert client.post("/api/parent/exit").status_code == 401
    assert client.post("/api/parent/settings", json={"language": "de"}).status_code == 401


def test_pin_flow_and_settings(client):
    assert client.post("/api/parent/verify", json={"pin": "0000"}).status_code == 401
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    resp = client.post("/api/parent/settings", json={"language": "de"}, headers={"X-Parent-Token": token})
    assert resp.json()["language"] == "de"
    assert client.get("/api/settings").json()["language"] == "de"


def test_exit_with_pin_requests_shutdown(client):
    called = []
    client.app.state.request_shutdown = lambda: called.append(True)
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    assert client.post("/api/parent/exit", headers={"X-Parent-Token": token}).json()["ok"]
    import time
    time.sleep(0.8)
    assert called


def test_complete_level_and_read_progress(client):
    resp = client.post("/api/progress/complete", json={"world": "mouse", "level": 1, "stars": 3})
    assert resp.json()["new_stickers"] == ["puppy"]
    state = client.get("/api/progress").json()
    assert state["total_stars"] == 3 and "puppy" in state["stickers"]
    assert any(s["id"] == "puppy" for s in client.get("/api/stickers").json())


def test_complete_level_rejects_nonsense(client):
    assert client.post("/api/progress/complete", json={"world": "mouse", "level": 5, "stars": 3}).status_code == 400
    assert client.post("/api/progress/complete", json={"world": "mouse", "level": 1, "stars": 50}).status_code == 422


def test_unlock_needs_pin(client):
    assert client.post("/api/parent/unlock", json={"world": "all"}).status_code == 401
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    state = client.post("/api/parent/unlock", json={"world": "all"}, headers={"X-Parent-Token": token}).json()
    assert state["worlds"]["free"]["unlocked"]


def test_keystroke_endpoint_validates_and_adapts(client):
    good = {"events": [{"key": "A", "correct": True, "ms": 400}] * 20, "adaptive": True}
    assert client.post("/api/keystrokes", json=good).json()["change"] == "advance"
    assert client.get("/api/letters").json()["letters"] == ["A", "S", "D"]
    bad_key = {"events": [{"key": "<script>", "correct": True, "ms": 1}]}
    assert client.post("/api/keystrokes", json=bad_key).status_code == 422


def test_practice_content_endpoints(client):
    words = client.get("/api/content/words?count=5").json()
    assert len(words["items"]) == 5 and words["source"] in ("cache", "fallback", "mixed")
    assert client.get("/api/content/sentences?count=2").json()["items"]
    assert client.get("/api/content/words?count=999").status_code == 422


def test_llm_status_and_test_button_need_pin(client):
    assert client.get("/api/parent/status").status_code == 401
    assert client.post("/api/parent/llm/test").status_code == 401
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    headers = {"X-Parent-Token": token}
    status = client.get("/api/parent/status", headers=headers).json()
    assert status["mode"] == "mock" and "api_key" not in json.dumps(status).lower()
    assert client.post("/api/parent/llm/test", headers=headers).json()["ok"] is True
