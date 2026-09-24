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
    if kind == "story":   # two built-in sentences per "story": enough to run the whole pipeline without a network
        lines = bank.pick(bank.SENTENCES, lang, set(task["letters"]), task["themes"], task["count"] * 2)
        return json.dumps({"stories": [lines[i:i + 2] for i in range(0, len(lines) - 1, 2)]})
    if kind == "mascot":
        lines = bank.MASCOT_LINES.get(lang, bank.MASCOT_LINES["en"]).get(task["event"], [])
        return json.dumps({"lines": lines})
    if kind == "ask":
        answers = bank.ASK["answers"].get(lang, bank.ASK["answers"]["en"])
        return json.dumps({"answers": [answers[task["topic"]]]})
    if kind == "summary":
        from backend import dashboard
        return json.dumps(dashboard.local_summary(task["stats"], lang))
    raise ValueError(f"unknown task kind: {kind}")
