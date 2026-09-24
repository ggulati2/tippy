"""The offline licence file (docs/REVAMP_BRIEF.md section 8). Each test signs with a throwaway key of its own and
points the app at it, so the owner's real signing key is never needed (or touched) by the tests."""
import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from backend import licence


@pytest.fixture()
def key(monkeypatch):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(licence, "PUBLIC_KEY", base64.b64encode(public).decode())
    monkeypatch.delenv("DEV_UNLOCK_ALL", raising=False)
    return private


def signed(private, tiers, **extra):
    payload = {"tiers": tiers, "issued_to": "Grundschule am See", "issued": "2026-09-24", **extra}
    return {"licence": payload, "signature": base64.b64encode(private.sign(licence.canonical(payload))).decode()}


def test_no_licence_means_the_free_core_tier(key, tmp_path):
    assert licence.features(tmp_path) == set()


def test_a_signed_licence_unlocks_its_tiers_only(key, tmp_path):
    (tmp_path / "licence.json").write_text(json.dumps(signed(key, ["school"])))
    assert licence.features(tmp_path) == {"classroom", "portable"}
    (tmp_path / "licence.json").write_text(json.dumps(signed(key, ["plus", "school"])))
    assert licence.features(tmp_path) == licence.ALL_FEATURES


def test_a_changed_or_foreign_licence_is_refused(key, tmp_path):
    good = signed(key, ["plus"])
    changed = {**good, "licence": {**good["licence"], "tiers": ["plus", "school"]}}         # someone added a tier by hand
    foreign = signed(Ed25519PrivateKey.generate(), ["plus", "school"])                     # signed with another key
    for bad in (changed, foreign, {"licence": good["licence"]}, {"signature": "x"}, [], "licence"):
        with pytest.raises(licence.LicenceError):
            licence.verify(bad)
        (tmp_path / "licence.json").write_text(json.dumps(bad))
        assert licence.features(tmp_path) == set()


def test_unknown_tiers_are_ignored(key, tmp_path):
    (tmp_path / "licence.json").write_text(json.dumps(signed(key, ["gold", "plus"])))
    assert licence.features(tmp_path) == {"ai_extras", "printables"}


def test_dev_unlock_all_switches_everything_on(key, tmp_path, monkeypatch):
    monkeypatch.setenv("DEV_UNLOCK_ALL", "true")
    assert licence.features(tmp_path) == licence.ALL_FEATURES


@pytest.fixture()
def app(key, tmp_path, monkeypatch):
    for name, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "live", "OPENROUTER_API_KEY": "x"}.items():
        monkeypatch.setenv(name, value)
    from backend.app import create_app
    client = TestClient(create_app(), base_url="http://127.0.0.1:8765")
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


def test_without_a_licence_classroom_mode_cannot_be_switched_on_and_the_helper_stays_off(app):
    client, parent = app
    settings = client.get("/api/settings").json()
    assert settings["features"] == [] and settings["online_helper"] is False       # LLM_MODE=live, but not licensed
    assert client.post("/api/parent/class", json={"classroom": True}, headers=parent).status_code == 403


def test_installing_a_licence_in_the_parent_area(app, key):
    client, parent = app
    good = json.dumps(signed(key, ["school"]))
    assert client.post("/api/parent/licence", content=good).status_code == 401                              # PIN needed
    assert client.post("/api/parent/licence", content="not json", headers=parent).status_code == 422
    assert client.post("/api/parent/licence", content=json.dumps(signed(Ed25519PrivateKey.generate(), ["school"])),
                       headers=parent).json()["detail"] == "bad-signature"
    installed = client.post("/api/parent/licence", content=good, headers=parent).json()
    assert installed["features"] == ["classroom", "portable"] and installed["issued_to"] == "Grundschule am See"
    assert client.get("/api/settings").json()["features"] == ["classroom", "portable"]
    assert client.post("/api/parent/class", json={"classroom": True}, headers=parent).status_code == 200
    assert client.get("/api/parent/licence", headers=parent).json()["tiers"] == ["school"]


def test_portable_mode_needs_the_school_tier(key, tmp_path, monkeypatch):
    from backend import config
    exe = tmp_path / "Tippy.exe"
    (tmp_path / "tippy-data" / "data").mkdir(parents=True)
    monkeypatch.setattr(config, "FROZEN", True)
    monkeypatch.setattr(config.sys, "executable", str(exe))
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.delenv("TIPPY_HOME", raising=False)
    assert config._home_dir() != tmp_path / "tippy-data"                                  # no licence: the user folder
    (tmp_path / "tippy-data" / "data" / "licence.json").write_text(json.dumps(signed(key, ["school"])))
    assert config._home_dir() == tmp_path / "tippy-data"


def test_the_online_helper_needs_the_parents_yes_even_when_licensed(key, tmp_path, monkeypatch):
    monkeypatch.setenv("DEV_UNLOCK_ALL", "1")
    for name, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "openrouter", "OPENROUTER_API_KEY": "x"}.items():
        monkeypatch.setenv(name, value)
    from backend.app import create_app
    client = TestClient(create_app(), base_url="http://127.0.0.1:8765")
    parent = {"X-Parent-Token": client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]}
    status = client.get("/api/parent/status", headers=parent).json()
    assert status["mode"] == "live" and status["consent"] is False
    assert client.post("/api/parent/ai-consent", json={"on": True}).status_code == 401
    assert client.post("/api/parent/ai-consent", json={"on": True}, headers=parent).json()["consent"] is True
    assert client.post("/api/parent/ai-consent", json={"on": False}, headers=parent).json()["consent"] is False
