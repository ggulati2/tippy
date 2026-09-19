"""SQLite storage. Uses only Python's built-in sqlite3 module.

All tables are created with "IF NOT EXISTS", so starting the app is always safe
and no separate migration tool is needed. If a table changes later, add a new
column with ALTER TABLE inside init_db().
"""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS child_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    first_name TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT 'animals,space,dinosaurs,vehicles'
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    seconds_played INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS keystroke_stats (
    key TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    avg_ms REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS progress (
    world TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'locked',
    stars INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (world, level)
);
CREATE TABLE IF NOT EXISTS stickers (
    id TEXT PRIMARY KEY,
    earned_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS content_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    level INTEGER NOT NULL,
    json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    est_cost_usd REAL NOT NULL DEFAULT 0
);
"""

# Values the parent can change. Used when nothing has been saved yet.
DEFAULT_SETTINGS = {
    "language": "en",
    "keyboard_layout": "qwerty",  # or "qwertz"
    "voice_on": "1",
    "sound_on": "1",
}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path, default_language: str = "en") -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO child_profile (id) VALUES (1)")
        defaults = dict(DEFAULT_SETTINGS, language=default_language)
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        # A German UI should start with the German keyboard shape.
        if default_language == "de":
            conn.execute(
                "UPDATE settings SET value = 'qwertz' WHERE key = 'keyboard_layout' "
                "AND NOT EXISTS (SELECT 1 FROM sessions)"
            )


def get_settings(db_path: Path) -> dict:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_setting(db_path: Path, key: str, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
