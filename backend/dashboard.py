"""Numbers for the parent dashboard, the play-time limits, export and reset.

All of this stays on this computer. The child never sees these numbers.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from backend import bank, db, difficulty, progress

MASTERED_MIN_ATTEMPTS = 8       # a letter needs this many tries...
MASTERED_ACCURACY = 0.85        # ...and at least this accuracy to count as "mastered"
WEAK_MIN_ATTEMPTS = 5
MAX_HEARTBEAT_SECONDS = 60      # one report can never add more than this, so a bug cannot fake hours
TREND_DAYS = 14
PLAY_DAYS = 7


# ---------- Play time and limits ----------

def add_play_seconds(db_path: Path, seconds: int, today: date | None = None) -> None:
    seconds = max(0, min(int(seconds), MAX_HEARTBEAT_SECONDS))
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO play_time (day, seconds) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET seconds = seconds + excluded.seconds",
            ((today or date.today()).isoformat(), seconds),
        )


def _int_setting(settings: dict, key: str, default: int) -> int:
    try:
        return int(settings.get(key, default))
    except (TypeError, ValueError):
        return default


def outside_play_window(window: str, hour: int) -> bool:
    """`window` is "" (no window) or "8-18": play is allowed from 8:00 until 18:00."""
    if not window:
        return False
    start, end = (int(part) for part in window.split("-"))
    return not start <= hour < end


def limits_state(db_path: Path, today: date | None = None, hour: int | None = None) -> dict:
    today = today or date.today()
    hour = datetime.now().hour if hour is None else hour
    settings = db.get_settings(db_path)
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT seconds FROM play_time WHERE day = ?", (today.isoformat(),)).fetchone()
    played = row["seconds"] if row else 0
    daily = _int_setting(settings, "daily_limit_minutes", 0)
    return {
        "today_seconds": played,
        "session_minutes": _int_setting(settings, "session_minutes", 10),
        "daily_limit_minutes": daily,
        "daily_reached": daily > 0 and played >= daily * 60,
        # docs/REVAMP_BRIEF.md section 6.4: "allowed time windows". Outside the window Tippy shows the same
        # calm goodnight screen as the daily limit.
        "outside_window": outside_play_window(settings.get("play_window", ""), hour),
    }


# ---------- Keys and trends ----------

def key_report(db_path: Path) -> list[dict]:
    with db.connect(db_path) as conn:
        rows = conn.execute("SELECT key, attempts, correct, avg_ms FROM keystroke_stats ORDER BY key").fetchall()
    return [{"key": r["key"], "attempts": r["attempts"], "correct": r["correct"],
             "accuracy": round(r["correct"] / r["attempts"], 3) if r["attempts"] else None,
             "avg_ms": round(r["avg_ms"])} for r in rows]


def weak_and_strong(keys: list[dict]) -> tuple[list[str], list[str]]:
    """Up to three keys to practise and up to three the child is good at (letters only)."""
    letters = [k for k in keys if len(k["key"]) == 1 and k["attempts"] >= WEAK_MIN_ATTEMPTS]
    weak = [k["key"] for k in sorted(letters, key=lambda k: k["accuracy"]) if k["accuracy"] < 0.8][:3]
    strong = [k["key"] for k in sorted(letters, key=lambda k: -k["accuracy"]) if k["accuracy"] >= 0.9][:3]
    return weak, strong


def dashboard(db_path: Path, today: date | None = None) -> dict:
    today = today or date.today()
    state = progress.get_progress(db_path, today)
    keys = key_report(db_path)
    unlocked = difficulty.get_letters(db_path)["letters"]
    mastered = [k["key"] for k in keys if len(k["key"]) == 1 and k["attempts"] >= MASTERED_MIN_ATTEMPTS
                and k["accuracy"] >= MASTERED_ACCURACY]
    with db.connect(db_path) as conn:
        daily = {r["day"]: r for r in conn.execute("SELECT day, attempts, correct FROM daily_stats")}
        play = {r["day"]: r["seconds"] for r in conn.execute("SELECT day, seconds FROM play_time")}
        profile = conn.execute("SELECT interests, age_band FROM child_profile WHERE id = 1").fetchone()
        interests = profile["interests"]
    trend = []
    for offset in range(TREND_DAYS - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        if day in daily and daily[day]["attempts"]:
            trend.append({"day": day, "attempts": daily[day]["attempts"],
                          "accuracy": round(100 * daily[day]["correct"] / daily[day]["attempts"])})
    minutes = [{"day": (today - timedelta(days=o)).isoformat(),
                "minutes": round(play.get((today - timedelta(days=o)).isoformat(), 0) / 60, 1)}
               for o in range(PLAY_DAYS - 1, -1, -1)]
    total_attempts = sum(k["attempts"] for k in keys)
    total_correct = sum(k["correct"] for k in keys)
    return {
        "streak": state["streak"], "total_stars": state["total_stars"], "sticker_count": len(state["stickers"]),
        "worlds": {w: {"done": len([l for l in info["levels"] if int(l) <= progress.LEVEL_COUNTS.get(w, 0)]), "total": progress.LEVEL_COUNTS.get(w, 0), "unlocked": info["unlocked"]}
                   for w, info in state["worlds"].items()},
        "letters": {"unlocked": unlocked, "mastered": mastered},
        "keys": keys, "trend": trend, "play_minutes": minutes,
        "today_minutes": minutes[-1]["minutes"],
        "keystrokes": total_attempts,
        "overall_accuracy": round(100 * total_correct / total_attempts) if total_attempts else None,
        "interests": [x for x in interests.split(",") if x in bank.THEMES],
        "age_band": profile["age_band"],
    }


def summary_stats(dash: dict) -> dict:
    """The facts the weekly summary is based on. No name, no personal details."""
    weak, strong = weak_and_strong(dash["keys"])
    return {
        "days_played_last_7": sum(1 for d in dash["play_minutes"] if d["minutes"] > 0),
        "minutes_last_7": round(sum(d["minutes"] for d in dash["play_minutes"])),
        "letters_unlocked": len(dash["letters"]["unlocked"]),
        "letters_mastered": len(dash["letters"]["mastered"]),
        "overall_accuracy_percent": dash["overall_accuracy"],
        "keystrokes": dash["keystrokes"],
        "weak_keys": weak, "strong_keys": strong,
        "streak_days": dash["streak"],
        "worlds_completed": [w for w, info in dash["worlds"].items() if info["total"] and info["done"] >= info["total"]],
    }


def local_summary(stats: dict, lang: str = "en") -> dict:
    """A plain summary written from a template, used when the LLM is off or unavailable."""
    weak, strong = ", ".join(stats["weak_keys"]), ", ".join(stats["strong_keys"])
    if lang == "de":
        if not stats["keystrokes"]:
            return {"strengths": "In dieser Woche wurde noch nicht getippt.",
                    "practice": "Noch keine Daten zu einzelnen Tasten.",
                    "tips": "Starte mit dem Buchstabenland. Zehn Minuten am Tag reichen völlig."}
        return {
            "strengths": (f"In den letzten 7 Tagen wurde an {stats['days_played_last_7']} Tagen gespielt, insgesamt etwa "
                          f"{stats['minutes_last_7']} Minuten. Die Trefferquote liegt bei {stats['overall_accuracy_percent']} Prozent, "
                          f"{stats['letters_unlocked']} Buchstaben sind freigeschaltet." + (f" Sicher sitzen: {strong}." if strong else "")),
            "practice": (f"Diese Tasten brauchen noch Übung: {weak}." if weak else "Es gibt noch keine auffälligen Problemtasten."),
            "tips": ("Kurze, tägliche Runden im Buchstabenland helfen am meisten. Lobe die Anstrengung, nicht nur die Treffer."
                     if weak else "Es läuft gut. Als Nächstes passen der Wortwald und der Satzhimmel."),
        }
    if lang == "es":
        if not stats["keystrokes"]:
            return {"strengths": "Todavía no se ha registrado práctica de escritura esta semana.",
                    "practice": "Aún no hay datos sobre teclas concretas.",
                    "tips": "Empieza por la Tierra de Letras. Diez minutos al día bastan."}
        return {
            "strengths": (f"En los últimos 7 días hubo {stats['days_played_last_7']} días de juego y unos "
                          f"{stats['minutes_last_7']} minutos. El porcentaje de aciertos es del {stats['overall_accuracy_percent']} % y hay "
                          f"{stats['letters_unlocked']} letras desbloqueadas." + (f" Teclas seguras: {strong}." if strong else "")),
            "practice": (f"Estas teclas necesitan más práctica: {weak}." if weak else "Todavía no hay teclas problemáticas claras."),
            "tips": ("Las rondas cortas y diarias en la Tierra de Letras ayudan más. Elogia el esfuerzo, no solo los aciertos."
                     if weak else "Todo va bien. El Bosque de Palabras y el Cielo de Frases son buenos siguientes pasos."),
        }
    if not stats["keystrokes"]:
        return {"strengths": "No typing practice has been recorded this week yet.",
                "practice": "There is no data about single keys yet.",
                "tips": "Start with Letter Land. Ten minutes a day is plenty."}
    return {
        "strengths": (f"Over the last 7 days there were {stats['days_played_last_7']} play days and about "
                      f"{stats['minutes_last_7']} minutes of play. Accuracy is {stats['overall_accuracy_percent']}% and "
                      f"{stats['letters_unlocked']} letters are unlocked." + (f" Strong keys: {strong}." if strong else "")),
        "practice": (f"These keys need more practice: {weak}." if weak else "There are no clear problem keys yet."),
        "tips": ("Short daily rounds in Letter Land help most. Praise the effort, not only the hits."
                 if weak else "Things are going well. Word Woods and Sentence Sky are good next steps."),
    }


# ---------- Export and reset ----------

EXPORT_TABLES = ("child_profile", "settings", "progress", "stickers", "keystroke_stats", "daily_stats",
                 "play_time", "play_days", "llm_usage", "sessions", "cards")


def export_data(db_path: Path) -> dict:
    """Everything worth keeping as one JSON-friendly dict (a backup the parent can save)."""
    with db.connect(db_path) as conn:
        data = {t: [dict(r) for r in conn.execute(f"SELECT * FROM {t}")] for t in EXPORT_TABLES}  # nosec B608 - table names come from the fixed EXPORT_TABLES tuple, never from input
    # Not part of the backup: the summary is regenerated on demand, and the PIN hash must not travel
    # in a file that may be emailed around (a 4-digit PIN hash is easy to crack).
    data["settings"] = [s for s in data["settings"] if s["key"] not in ("weekly_summary", "pin_hash")]
    return {"app": "tippy", "format": 2, "exported_at": date.today().isoformat(), "tables": data}


def reset_progress(db_path: Path) -> None:
    """Forget progress, stickers, statistics, play time and saved cards. Settings (name, language...) stay."""
    with db.connect(db_path) as conn:
        for table in ("progress", "stickers", "keystroke_stats", "keystroke_log", "daily_stats", "play_time",
                      "play_days", "sessions", "content_cache", "cards"):
            conn.execute(f"DELETE FROM {table}")  # nosec B608 - table names come from a fixed tuple in this function, never from input
        conn.execute("DELETE FROM settings WHERE key IN ('letters_unlocked', 'letters_changed_at', 'unlocked_worlds', 'weekly_summary')")
