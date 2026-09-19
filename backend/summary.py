"""The weekly progress summary for the parent: written by the LLM when it is available,
otherwise from a template. Built only from anonymous statistics (see dashboard.summary_stats)."""
import json
import logging
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from backend import dashboard, db, validators
from backend.llm.client import LLMClient
from backend.llm.schemas import SummaryReply

log = logging.getLogger("tippy.summary")
FIELDS = ("strengths", "practice", "tips")


def week_key(today: date) -> str:
    year, week, _ = today.isocalendar()
    return f"{year}-W{week:02d}"


def _from_llm(llm: LLMClient, stats: dict, lang: str) -> dict | None:
    text = llm.generate({"kind": "summary", "lang": lang, "stats": stats})
    if not text:
        return None
    try:
        reply = SummaryReply.model_validate_json(text.strip().removeprefix("```json").removesuffix("```").strip())
    except ValidationError:
        log.warning("Summary reply rejected: not the expected JSON")
        return None
    cleaned = {f: validators.clean_paragraph(getattr(reply, f)) for f in FIELDS}
    if not all(cleaned.values()):
        log.warning("Summary reply rejected: failed the text checks")
        return None
    return cleaned


def get_summary(db_path: Path, llm: LLMClient, today: date | None = None, refresh: bool = False) -> dict:
    """Returns {"week", "lang", "source", "strengths", "practice", "tips"}. Cached per week and language."""
    today = today or date.today()
    settings = db.get_settings(db_path)
    lang = settings.get("language", "en")
    if not refresh and settings.get("weekly_summary"):
        cached = json.loads(settings["weekly_summary"])
        if cached.get("week") == week_key(today) and cached.get("lang") == lang:
            return cached
    stats = dashboard.summary_stats(dashboard.dashboard(db_path, today))
    result, source = None, "builtin"
    if llm.mode == "live" and llm.enabled:
        result = _from_llm(llm, stats, lang)
        source = "llm"
    if result is None:
        result, source = dashboard.local_summary(stats, lang), "builtin"
    summary = {"week": week_key(today), "lang": lang, "source": source, **result}
    db.set_setting(db_path, "weekly_summary", json.dumps(summary))
    return summary
