"""SQLite storage. Uses only Python's built-in sqlite3 module.

All tables are created with "IF NOT EXISTS", so starting the app is always safe
and no separate migration tool is needed. If a table changes later, add a new
column with ALTER TABLE inside init_db().
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from backend import languages

log = logging.getLogger("tippy.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS child_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    first_name TEXT NOT NULL DEFAULT '',
    interests TEXT NOT NULL DEFAULT 'animals,space,dinosaurs,vehicles',
    age_band TEXT NOT NULL DEFAULT ''
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
CREATE TABLE IF NOT EXISTS keystroke_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    correct INTEGER NOT NULL,
    ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS progress (
    world TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'locked',
    stars INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (world, level)
);
CREATE TABLE IF NOT EXISTS play_days (
    day TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS play_time (
    day TEXT PRIMARY KEY,
    seconds INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS daily_stats (
    day TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0
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
    "letter_case": "upper",  # or "lower"
    "child_name": "",       # set by the parent; used only in the browser
    "favorite_word": "",
    "session_minutes": "10",       # Tippy suggests a break after this many minutes (0 = never)
    "daily_limit_minutes": "0",    # 0 = no daily limit
    "font_scale": "1",             # text size: 1, 1.125 or 1.25
    "reduce_motion": "0",          # 1 = no animations
    "has_numpad": "0",             # 1 = this computer has a number pad: Number Land then asks for its keys
    "ask_tippy": "0",              # the picture Q&A is off unless the parent turns it on
    "weekly_summary": "",          # cached weekly summary (JSON), parent area only
}


class _Connection(sqlite3.Connection):
    """A connection that really closes when a `with` block ends.

    Python's own connection only commits at the end of `with`; it stays open until the garbage
    collector notices. On Windows an open database file cannot be renamed or deleted, so we close it.
    """

    def __exit__(self, *error):
        try:
            return super().__exit__(*error)   # commit, or roll back if something went wrong
        finally:
            self.close()


def discard_wal_files(db_path: Path) -> None:
    """Delete the write-ahead files next to a database that was just moved away or replaced, so that a new
    database with the same name never picks up leftovers of the old one."""
    for suffix in ("-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, factory=_Connection)
    conn.row_factory = sqlite3.Row
    # Write-ahead log: readers never wait for a writer and a write does not have to rewrite the whole journal.
    # Measured with scripts/loadtest.py: it removes the long waits when many requests save key presses at once.
    # NORMAL is the recommended setting with WAL. An abrupt power cut can lose the last moments, never corrupt.
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.DatabaseError:
        conn.close()   # a damaged file: Windows cannot move it aside while it is still open
        raise
    return conn


def init_db(db_path: Path, default_language: str = "en") -> None:
    """Create the tables if needed. A damaged database file (for example after a power cut) is moved
    aside, not deleted, and Tippy starts fresh, so the app never gets stuck unable to start."""
    try:
        _init_db(db_path, default_language)
    except sqlite3.DatabaseError:
        aside = db_path.with_name(f"{db_path.name}.damaged-{datetime.now():%Y%m%d-%H%M%S}")
        log.error("Database is damaged. Moving it to %s and starting fresh.", aside)
        db_path.rename(aside)
        discard_wal_files(db_path)
        _init_db(db_path, default_language)


def _init_db(db_path: Path, default_language: str = "en") -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # A child's database made before age_band existed: CREATE TABLE IF NOT EXISTS above leaves an
        # existing table alone, so an older database needs the column added by hand, once.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(child_profile)")}
        if "age_band" not in columns:
            conn.execute("ALTER TABLE child_profile ADD COLUMN age_band TEXT NOT NULL DEFAULT ''")
        conn.execute("INSERT OR IGNORE INTO child_profile (id) VALUES (1)")
        defaults = dict(DEFAULT_SETTINGS, language=default_language)
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        # A German or Spanish UI should start with that language's keyboard shape.
        if languages.default_keyboard(default_language) != "qwerty":
            conn.execute(
                "UPDATE settings SET value = ? WHERE key = 'keyboard_layout' AND NOT EXISTS (SELECT 1 FROM sessions)",
                (languages.default_keyboard(default_language),),
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


# Settings the child's browser may see. Everything else (summary text, model,
# progress counters...) stays on the server and is only shown in the parent area.
CHILD_SETTINGS = ("language", "keyboard_layout", "voice_on", "sound_on", "letter_case", "child_name",
                  "favorite_word", "session_minutes", "daily_limit_minutes", "ask_tippy",
                  "font_scale", "reduce_motion", "has_numpad")

# docs/REVAMP_BRIEF.md section 4.5: how old the child roughly is, nothing more precise than that
# (never a birthdate). Like interests, it lives on child_profile, not in the generic settings table,
# because it belongs to the child, not to a device setting.
AGE_BANDS = ("5", "6", "7", "8+")


def get_age_band(db_path: Path) -> str:
    with connect(db_path) as conn:
        row = conn.execute("SELECT age_band FROM child_profile WHERE id = 1").fetchone()
    return row["age_band"] if row else ""
