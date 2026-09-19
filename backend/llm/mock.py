"""The fake LLM (LLM_MODE=mock): answers instantly from the built-in bank.

It returns JSON text in exactly the shape the real LLM should, so the same
validation and caching code runs in mock mode. No network, no cost.
"""
import json

from backend import bank


def mock_generate(task: dict) -> str:
    kind = task["kind"]
    if kind == "ping":
        return json.dumps({"ok": True})
    lang = task.get("lang", "en")
    if kind == "words":
        return json.dumps({"words": bank.pick(bank.WORDS, lang, set(task["letters"]), task["themes"], task["count"])})
    if kind == "sentences":
        return json.dumps({"sentences": bank.pick(bank.SENTENCES, lang, set(task["letters"]), task["themes"], task["count"])})
    if kind == "mascot":
        lines = bank.MASCOT_LINES.get(lang, bank.MASCOT_LINES["en"]).get(task["event"], [])
        return json.dumps({"lines": lines})
    raise ValueError(f"unknown task kind: {kind}")
