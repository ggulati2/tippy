import json

import httpx
import pytest

from backend import db
from backend.config import Settings
from backend.llm import prompts
from backend.llm.client import LLMClient


def make_settings(tmp_path, **changes):
    values = dict(openrouter_api_key="sk-test", openrouter_model="main/model", openrouter_fallback_model="backup/model",
                  app_language="en", parent_pin="1234", llm_mode="live", daily_request_cap=50, db_path=tmp_path / "t.db")
    values.update(changes)
    settings = Settings(**values)
    db.init_db(settings.db_path)
    return settings


def reply(text='{"ok": true}', cost=0.0001):
    return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 20, "completion_tokens": 5, "cost": cost}}


def client_with(settings, handler):
    return LLMClient(settings, transport=httpx.MockTransport(handler))


def test_successful_call_is_logged_with_cost(tmp_path):
    settings = make_settings(tmp_path)
    client = client_with(settings, lambda request: httpx.Response(200, json=reply()))
    assert json.loads(client.generate({"kind": "ping"})) == {"ok": True}
    usage = client.usage_today()
    assert usage["requests"] == 1 and usage["cost_usd"] == pytest.approx(0.0001)
    assert client.online is True


def test_request_carries_key_and_no_personal_data(tmp_path):
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=reply())

    client_with(make_settings(tmp_path), handler).generate({"kind": "mascot", "lang": "en", "event": "welcome", "count": 5})
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    text = json.dumps(seen["body"])
    assert "{child}" in text                       # the placeholder is sent, never a real name
    assert set(seen["body"]) == {"model", "messages", "response_format", "reasoning", "temperature", "max_tokens"}
    assert seen["body"]["reasoning"] == {"effort": "none"}


def test_falls_back_to_second_model_after_server_error(tmp_path):
    models = []

    def handler(request):
        models.append(json.loads(request.content)["model"])
        return httpx.Response(500) if len(models) == 1 else httpx.Response(200, json=reply())

    client = client_with(make_settings(tmp_path), handler)
    assert client.generate({"kind": "ping"}) is not None
    assert models == ["main/model", "backup/model"]
    assert client.usage_today()["requests"] == 2      # the failed try counts toward the cap


def test_timeout_then_fallback(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json=reply())

    assert client_with(make_settings(tmp_path), handler).generate({"kind": "ping"}) is not None


def test_bad_key_stops_without_second_try(tmp_path):
    calls = []
    client = client_with(make_settings(tmp_path), lambda r: (calls.append(1), httpx.Response(401))[1])
    assert client.generate({"kind": "ping"}) is None
    assert len(calls) == 1 and client.last_error == "HTTP 401"


def test_garbage_reply_returns_none(tmp_path):
    client = client_with(make_settings(tmp_path), lambda r: httpx.Response(200, json={"nope": 1}))
    assert client.generate({"kind": "ping"}) is None


def test_daily_cap_blocks_requests(tmp_path):
    settings = make_settings(tmp_path, daily_request_cap=2)
    calls = []
    client = client_with(settings, lambda r: (calls.append(1), httpx.Response(200, json=reply()))[1])
    assert client.generate({"kind": "ping"}) and client.generate({"kind": "ping"})
    assert client.generate({"kind": "ping"}) is None
    assert len(calls) == 2 and client.last_error == "daily request cap reached"


def test_no_key_means_no_network(tmp_path):
    client = client_with(make_settings(tmp_path, openrouter_api_key=""), lambda r: pytest.fail("network used"))
    assert client.generate({"kind": "ping"}) is None and not client.enabled


def test_mock_mode_never_uses_network(tmp_path):
    client = client_with(make_settings(tmp_path, llm_mode="mock", openrouter_api_key=""), lambda r: pytest.fail("network used"))
    assert json.loads(client.generate({"kind": "mascot", "lang": "en", "event": "success", "count": 3}))["lines"]
    assert client.test_connection()["ok"] is True


def test_connection_test_reports_failure(tmp_path):
    result = client_with(make_settings(tmp_path), lambda r: httpx.Response(402)).test_connection()
    assert result["ok"] is False and result["error"] == "HTTP 402"


def test_prompt_builder_has_no_place_for_a_name():
    for task in ({"kind": "words", "lang": "de", "letters": list("ASDF"), "themes": ["animals"], "count": 5},
                 {"kind": "sentences", "lang": "en", "letters": list("ASDF"), "themes": ["space"], "count": 5},
                 {"kind": "mascot", "lang": "en", "event": "oops", "count": 5}):
        text = " ".join(m["content"] for m in prompts.build_messages(task))
        assert "6-year-old" in text and "Never ask for or mention names" in text
