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
