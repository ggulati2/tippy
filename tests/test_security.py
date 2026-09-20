"""Security regression tests: everything a hostile web page, a curious child or a bad backup file could try.

These run with the normal tests on every change. (The scanners in .github/workflows/security.yml look for known
weaknesses; these tests pin down the behaviour Tippy promises, so it cannot quietly be lost.)
"""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import restore
from backend.app import MAX_REQUEST_BYTES, SECURITY_HEADERS, create_app

ROOT = Path(__file__).resolve().parent.parent
FAKE_KEY = "sk-or-" + "v1-thisisnotarealkeyandmustneverbeshown0123456789"   # joined here so the secret scan does not mistake it for a real key


@pytest.fixture()
def api(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "live", "OPENROUTER_API_KEY": FAKE_KEY}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


# ---------- Only Tippy's own page may talk to Tippy ----------

def test_other_hosts_and_origins_are_refused(api):
    client, _ = api
    assert client.get("/api/settings", headers={"Host": "evil.example"}).status_code == 403                # DNS rebinding
    assert client.get("/api/settings", headers={"Host": "127.0.0.1:8765.evil.example"}).status_code == 403
    assert client.post("/api/visit", headers={"Origin": "https://evil.example"}).status_code == 403          # cross-site request
    assert client.options("/api/settings", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}).status_code == 403


def test_no_cross_origin_sharing_is_ever_enabled(api):
    client, _ = api
    for path in ("/", "/api/settings", "/api/progress", "/js/app.js"):
        response = client.get(path, headers={"Origin": "http://testserver"})
        assert "access-control-allow-origin" not in {k.lower() for k in response.headers}, path


# ---------- Protective headers ----------

@pytest.mark.parametrize("path", ["/", "/api/settings", "/js/app.js", "/css/style.css", "/nothing-here"])
def test_every_response_carries_the_protective_headers(api, path):
    client, _ = api
    response = client.get(path)
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, f"{name} missing on {path}"


def test_the_policy_is_strict():
    policy = SECURITY_HEADERS["Content-Security-Policy"]
    assert "default-src 'self'" in policy and "frame-ancestors 'none'" in policy and "object-src 'none'" in policy
    assert "unsafe-inline" not in policy and "unsafe-eval" not in policy and "*" not in policy


def test_api_answers_are_never_cached(api):
    client, parent = api
    for path in ("/api/settings", "/api/progress", "/api/parent/export"):
        assert client.get(path, headers=parent).headers["cache-control"] == "no-store", path


# ---------- Secrets and private files ----------

def test_the_api_key_never_appears_in_any_answer(api):
    client, parent = api
    urls = ["/api/settings", "/api/languages", "/api/profiles", "/api/progress", "/api/stickers", "/api/letters", "/api/limits",
            "/api/parent/status", "/api/parent/dashboard", "/api/parent/summary", "/api/parent/export", "/api/mascot/line",
            "/api/content/words", "/api/content/sentences", "/api/pictures"]
    for url in urls:
        response = client.get(url, headers=parent)
        assert FAKE_KEY not in response.text and "sk-or-" not in response.text, url
    tested = client.post("/api/parent/llm/test", headers=parent)          # a failing helper test must not leak it either
    assert tested.status_code == 200 and FAKE_KEY not in tested.text


@pytest.mark.parametrize("path", ["/.env", "/../.env", "/%2e%2e/.env", "/data/tippy.db", "/backend/app.py", "/../backend/config.py",
                                  "/tests/test_security.py", "/.git/config", "/js/../../.env", "/logs/tippy.log", "//etc/passwd"])
def test_private_files_are_not_served(api, path):
    client, _ = api
    response = client.get(path)
    assert response.status_code in (404, 403, 400, 307, 308) and FAKE_KEY not in response.text and "OPENROUTER" not in response.text


def test_only_the_frontend_folder_is_public():
    from backend.config import FRONTEND_DIR
    names = {p.name for p in Path(FRONTEND_DIR).iterdir()}
    assert not {name for name in names if name.startswith(".") or name.endswith((".py", ".db", ".env", ".log"))}


# ---------- The parent area ----------

def test_the_parent_area_needs_the_pin_everywhere(api):
    client, _ = api
    parent_paths = [("get", "/api/parent/status"), ("get", "/api/parent/dashboard"), ("get", "/api/parent/summary"), ("get", "/api/parent/export"),
                    ("post", "/api/parent/settings"), ("post", "/api/parent/unlock"), ("post", "/api/parent/reset"), ("post", "/api/parent/exit"),
                    ("post", "/api/parent/import"), ("post", "/api/parent/profiles"), ("post", "/api/parent/pin"), ("post", "/api/parent/llm/test")]
    for method, path in parent_paths:
        for headers in ({}, {"X-Parent-Token": "made-up"}, {"X-Parent-Token": ""}, {"X-Parent-Token": "' OR '1'='1"}):
            response = getattr(client, method)(path, headers=headers, **({"json": {}} if method == "post" else {}))
            assert response.status_code == 401, (method, path, headers)


def test_no_parent_endpoint_can_be_added_without_the_pin_check(api):
    """Looks at the real route table: every /api/parent/ route (except signing in) must depend on the PIN check."""
    client, _ = api
    routes = [route for route in client.app.routes if getattr(route, "path", "").startswith("/api/parent/")]
    assert len(routes) >= 15, "the route table looks wrong"
    unprotected = [route.path for route in routes if route.path != "/api/parent/verify"
                   and "parent_only" not in [dep.call.__name__ for dep in route.dependant.dependencies]]
    assert not unprotected, f"these parent endpoints do not ask for the PIN: {unprotected}"


def test_guessing_the_pin_locks_out_and_hides_the_hash(api):
    client, _ = api
    codes = [client.post("/api/parent/verify", json={"pin": f"000{n}"}).status_code for n in range(7)]
    assert 429 in codes, "guessing must be slowed down"
    assert client.post("/api/parent/verify", json={"pin": "4321"}).status_code == 429          # even the right PIN waits during the lockout
    assert "pin_hash" not in json.dumps(client.get("/api/settings").json())


def test_every_sign_in_gets_a_different_long_random_token(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    tokens = {client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"] for _ in range(4)}
    assert len(tokens) == 4 and all(len(t) >= 24 for t in tokens)


# ---------- Hostile input ----------

def test_oversized_requests_are_refused(api):
    client, parent = api
    assert client.post("/api/keystrokes", content=b"x" * (MAX_REQUEST_BYTES + 1), headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/api/parent/import", content=b"x" * (restore.MAX_BACKUP_BYTES + 100), headers=parent).status_code == 413
    assert client.post("/api/keystrokes", headers={"Content-Length": "not a number"}).status_code in (400, 413, 422)


INJECTIONS = ["'; DROP TABLE progress;--", "\" OR 1=1 --", "<script>alert(1)</script>", "../../etc/passwd", "%00", "{{7*7}}",
              "${jndi:ldap://x}", "a" * 5000, chr(0x202E) + chr(0)]


def test_hostile_text_never_breaks_or_leaks_anything(api):
    client, parent = api
    for text in INJECTIONS:
        for response in (client.get("/api/content/words", params={"theme": text, "max_len": text, "count": text}),
                         client.get("/api/content/sentences", params={"kind": text}),
                         client.get("/api/ask", params={"topic": text}),
                         client.get("/api/mascot/line", params={"event": text}),
                         client.post("/api/keystrokes", json={"events": [{"key": text, "correct": True, "ms": 1}]}),
                         client.post("/api/progress/complete", json={"world": text, "level": 1, "stars": 3}),
                         client.post("/api/parent/settings", json={"child_name": text, "favorite_word": text, "openrouter_model": text}, headers=parent),
                         client.post("/api/parent/profiles", json={"name": text, "avatar": text}, headers=parent),
                         client.post("/api/profiles/select", json={"id": text}),
                         client.post("/api/parent/unlock", json={"world": text}, headers=parent)):
            assert response.status_code < 500, (text[:20], response.request.url, response.status_code)
    # the database still works and nothing was dropped
    assert client.get("/api/progress").status_code == 200 and client.get("/api/parent/export", headers=parent).status_code == 200


def test_a_backup_file_cannot_smuggle_in_secrets_or_code(api):
    client, parent = api
    hostile = {"app": "tippy", "tables": {"settings": [{"key": "pin_hash", "value": "aa:bb"}, {"key": "openrouter_model", "value": "evil/x"},
                                                       {"key": "child_name", "value": "<img src=x onerror=alert(1)>"},
                                                       {"key": "'; DROP TABLE settings;--", "value": "x"}],
                                          "progress": [{"world": "'; DROP TABLE progress;--", "level": 1, "status": "done", "stars": 1}]}}
    assert client.post("/api/parent/import", content=json.dumps(hostile), headers=parent).status_code == 422       # nothing usable in it
    assert client.get("/api/parent/status", headers=parent).json()["model"] != "evil/x"
    assert client.post("/api/parent/verify", json={"pin": "4321"}).status_code in (200, 429)


# ---------- The frontend never renders foreign text as HTML ----------

def test_the_frontend_has_no_dangerous_code_patterns():
    dangerous = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function\(|javascript:|setAttribute\(\s*[\"']on")
    found = []
    for path in sorted((ROOT / "frontend").rglob("*.js")) + [ROOT / "frontend" / "index.html"]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if dangerous.search(line):
                found.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    # The one allowed use: the mascot's own fixed SVG markup (never text from anywhere else).
    assert len(found) == 1 and "wrapper.innerHTML = svg" in found[0], "new dangerous code found:\n" + "\n".join(found)


def test_the_page_loads_nothing_from_other_sites():
    external = re.compile(r"(?:src|href)\s*=\s*[\"']?(?:https?:)?//|url\(\s*[\"']?https?:|@import\s+[\"']?https?:|fetch\(\s*[\"']https?:")
    for path in sorted((ROOT / "frontend").rglob("*")):
        if path.suffix in (".js", ".css", ".html"):
            assert not external.search(path.read_text(encoding="utf-8")), f"{path.relative_to(ROOT)} loads something from another site"
