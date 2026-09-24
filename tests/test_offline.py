"""docs/REVAMP_BRIEF.md sections 10 and 13: with the online helper off, Tippy makes zero outbound network calls.

The whole core flow runs here with every outgoing connection blocked and recorded: first-run setup, every kind of
practice content, finishing levels, stickers, the parent area (dashboard, weekly report, backup), children,
cards and the privacy text. The test client talks to the app in-process, so any socket opened is an outbound call.
"""
import socket

import pytest
from fastapi.testclient import TestClient


LOOPBACK = {"127.0.0.1", "localhost", "::1"}


@pytest.fixture()
def blocked(monkeypatch):
    """Connections to this computer itself stay allowed (on Windows, Python's event loop connects a socket to
    127.0.0.1 when it starts); every connection to anywhere else is refused and recorded."""
    attempts = []
    real = {"connect": socket.socket.connect, "connect_ex": socket.socket.connect_ex, "create": socket.create_connection}

    def outbound(address) -> bool:
        return isinstance(address, tuple) and address[0] not in LOOPBACK

    def guard(name):
        def call(self, address, *args, **kwargs):
            if outbound(address):
                attempts.append(address)
                raise OSError("network blocked by the offline test")
            return real[name](self, address, *args, **kwargs)
        return call

    def create_connection(address, *args, **kwargs):
        if outbound(address):
            attempts.append(address)
            raise OSError("network blocked by the offline test")
        return real["create"](address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard("connect"))
    monkeypatch.setattr(socket.socket, "connect_ex", guard("connect_ex"))
    monkeypatch.setattr(socket, "create_connection", create_connection)
    return attempts


def test_the_blocker_catches_a_real_outbound_request(blocked):
    import httpx
    with pytest.raises(httpx.ConnectError):
        httpx.get("https://openrouter.ai", timeout=3)
    assert blocked and blocked[0][0] == "openrouter.ai"


def test_the_core_flow_makes_no_network_calls(blocked, tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "", "LLM_MODE": "off",
                       "OPENROUTER_API_KEY": "sk-not-used"}.items():
        monkeypatch.setenv(key, value)
    from backend.app import create_app
    client = TestClient(create_app(), base_url="http://127.0.0.1:8765")

    assert client.post("/api/setup", json={"pin": "2468", "language": "de", "child_name": "Mia"}).status_code == 200
    assert client.post("/api/visit").status_code == 200
    for path in ("/api/settings", "/api/languages", "/api/mascot/line?event=success", "/api/content/words?count=5",
                 "/api/content/words?count=5&pictured=true", "/api/content/sentences?count=3",
                 "/api/content/sentences?count=3&kind=themed", "/api/pictures", "/api/progress", "/api/stickers", "/api/limits"):
        assert client.get(path).status_code == 200, path
    for level in range(1, 5):
        assert client.post("/api/progress/complete", json={"world": "mouse", "level": level, "stars": 3}).status_code == 200
    assert client.post("/api/keystrokes", json={"events": [{"key": "A", "correct": True, "ms": 400}] * 5, "adaptive": True}).status_code == 200
    assert client.post("/api/cards", json={"words": "roter hund"}).status_code == 200
    assert client.post("/api/session/heartbeat", json={"seconds": 15}).status_code == 200

    parent = {"X-Parent-Token": client.post("/api/parent/verify", json={"pin": "2468"}).json()["token"]}
    for path in ("/api/parent/dashboard", "/api/parent/summary", "/api/parent/export", "/api/parent/status", "/api/parent/licence"):
        assert client.get(path, headers=parent).status_code == 200, path
    assert client.post("/api/parent/llm/test", headers=parent).json()["ok"] is False      # off: it does not even try

    assert blocked == [], f"outbound network calls were attempted: {blocked}"
