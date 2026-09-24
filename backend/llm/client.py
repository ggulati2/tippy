"""The single doorway to the LLM (OpenRouter, or the fake one in mock mode).

Everything that talks to the internet is in this file. Rules:
- Only prompts built by prompts.py go out: no names or personal details.
- Short timeout, at most two tries (main model, then the fallback model).
- Every try is written to the llm_usage table, and a daily cap stops runaway use.
- On any problem we return None and the caller quietly uses the built-in bank.
"""
import json
import logging
import time
from pathlib import Path
from datetime import date

import httpx

from backend import db
from backend.config import Settings
from backend.llm import mock, prompts

log = logging.getLogger("tippy.llm")

API_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 8.0
FATAL_STATUS = {401, 402, 403}  # wrong key or no credit: retrying another model will not help


class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None, state_db: Path | None = None):
        self.settings = settings
        # Usage counter and the parent's model choice belong to the household, not to one child.
        self._state_db = state_db or settings.db_path
        self._transport = transport  # tests pass a fake network here
        self.online: bool | None = None  # None = not tried yet
        self.last_error = ""

    # ---------- What is available ----------

    @property
    def mode(self) -> str:
        return self.settings.llm_mode

    @property
    def consented(self) -> bool:
        """A parent switched the online helper on after reading what it sends and costs (docs/REVAMP_BRIEF.md 4.1).
        Until then nothing at all goes out, not even the "Test connection" ping."""
        return db.get_settings(self._state_db).get("ai_consent") == "1"

    @property
    def enabled(self) -> bool:
        """True if generate() can produce anything (mock always; live needs a key and the parent's yes)."""
        return self.mode == "mock" or (self.mode == "live" and bool(self.settings.openrouter_api_key) and self.consented)

    @property
    def model(self) -> str:
        """The main model: the parent's choice in the parent area, otherwise the one from .env."""
        return db.get_settings(self._state_db).get("openrouter_model") or self.settings.openrouter_model

    # ---------- Usage and cost ----------

    def usage_today(self) -> dict:
        with db.connect(self._state_db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(est_cost_usd), 0) AS cost FROM llm_usage WHERE day = ?",
                (date.today().isoformat(),),
            ).fetchone()
        return {"requests": row["n"], "cost_usd": round(row["cost"], 6), "cap": self.settings.daily_request_cap}

    def _record(self, model: str, prompt_tokens: int = 0, completion_tokens: int = 0, cost: float = 0.0) -> None:
        with db.connect(self._state_db) as conn:
            conn.execute(
                "INSERT INTO llm_usage (day, model, prompt_tokens, completion_tokens, est_cost_usd) VALUES (?, ?, ?, ?, ?)",
                (date.today().isoformat(), model, prompt_tokens, completion_tokens, cost),
            )

    # ---------- Asking ----------

    def generate(self, task: dict) -> str | None:
        """Return the model's JSON text for a task, or None if anything goes wrong."""
        if self.mode == "off":
            return None
        if self.mode == "mock":
            self.online = None
            return mock.mock_generate(task)
        if not self.settings.openrouter_api_key:
            self.last_error = "no API key"
            return None
        if not self.consented:
            self.last_error = "not switched on in the parent area"
            return None

        messages = prompts.build_messages(task)
        models = [self.model, self.settings.openrouter_fallback_model]
        for model in models:
            if self.usage_today()["requests"] >= self.settings.daily_request_cap:
                self.last_error = "daily request cap reached"
                log.warning("LLM daily request cap reached (%s)", self.settings.daily_request_cap)
                return None
            text, fatal = self._try(model, messages)
            if text is not None:
                return text
            if fatal:
                break
        return None

    def _try(self, model: str, messages: list[dict]) -> tuple[str | None, bool]:
        """One request. Returns (text, fatal). Never raises."""
        body = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            # Some models "think" first, and that thinking would eat the whole token
            # budget and leave an empty answer. We only need short, direct output.
            "reasoning": {"effort": "none"},
            "temperature": 0.8,
            "max_tokens": 700,
        }
        headers = {"Authorization": f"Bearer {self.settings.openrouter_api_key}"}
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS, transport=self._transport) as http:
                response = http.post(API_URL, json=body, headers=headers)
        except httpx.HTTPError as error:
            return self._fail(model, type(error).__name__), False
        if response.status_code != 200:
            # We log only the status code, never the response body or the key.
            return self._fail(model, f"HTTP {response.status_code}"), response.status_code in FATAL_STATUS
        try:
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
        except (ValueError, KeyError, IndexError, TypeError):
            return self._fail(model, "unreadable reply"), False
        if not isinstance(text, str):
            return self._fail(model, "unreadable reply"), False
        self._record(model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), float(usage.get("cost") or 0))
        self.online, self.last_error = True, ""
        return text, False

    def _fail(self, model: str, reason: str) -> None:
        log.warning("LLM request to %s failed: %s", model, reason)
        self._record(model)  # failed tries still count toward the daily cap
        self.online, self.last_error = False, reason

    # ---------- Parent area ----------

    def test_connection(self) -> dict:
        """A tiny real request, for the parent's "Test connection" button."""
        started = time.monotonic()
        if self.mode == "mock":
            return {"ok": True, "mode": "mock", "model": "mock", "latency_ms": 0, "error": ""}
        text = self.generate({"kind": "ping"})
        ok = False
        if text is not None:
            try:
                ok = json.loads(text).get("ok") is True
            except (ValueError, AttributeError):
                ok = False
        return {
            "ok": ok, "mode": "live", "model": self.model,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": "" if ok else (self.last_error or "unexpected answer"),
        }

    def status(self) -> dict:
        return {
            "mode": self.mode, "key_set": bool(self.settings.openrouter_api_key), "consent": self.consented,
            "model": self.model, "fallback_model": self.settings.openrouter_fallback_model,
            "online": self.online, "last_error": self.last_error, **self.usage_today(),
        }
