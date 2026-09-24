"""Children (profiles) and the family-level storage.

Every child has their own database file (data/profiles/<id>.db) with their own progress, stickers,
statistics, play time and settings, so one child's backup, reset or delete never touches another
child. A small family database (data/family.db) holds what belongs to the whole household: the
parent PIN, the online-helper model, the list of children (name and picture for the "who is
playing?" screen) and the online-helper usage counter (so the daily request cap is shared).

The rest of the app asks `family.db_path` for "the database of whoever is playing right now".
"""
import logging
import shutil
import sqlite3
import threading
from contextlib import closing
from datetime import datetime
from pathlib import Path

from backend import db, languages

log = logging.getLogger("tippy.profiles")

MAX_PROFILES = 6
AVATARS = ["🦊", "🐼", "🦁", "🐯", "🐸", "🐙", "🦄", "🐧", "🦖", "🚀", "🐝", "🦋"]

FAMILY_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    avatar TEXT NOT NULL DEFAULT '🦊',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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


class ProfileError(ValueError):
    """A request the parent can fix (too many children, unknown child...). The message is safe to show."""


class Family:
    def __init__(self, data_dir: Path, default_language: str = "en", legacy_db: Path | None = None):
        self.data_dir = data_dir
        self.family_db = data_dir / "family.db"
        self.profiles_dir = data_dir / "profiles"
        self.default_language = default_language
        self._lock = threading.Lock()
        self._active = 0
        self._open(legacy_db)

    # ---------- Start-up and migration ----------

    def _open(self, legacy_db: Path | None) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        fresh_family = not self.family_db.exists()
        self._init_family_db()
        if fresh_family and legacy_db is not None and legacy_db.exists():
            self._migrate_single_child(legacy_db)
        if not self.list():
            self._create(name="", avatar=AVATARS[0])            # there is always at least one child
        remembered = int(db.get_settings(self.family_db).get("active_profile") or 0)
        ids = [p["id"] for p in self.list()]
        self._active = remembered if remembered in ids else ids[0]
        db.init_db(self.path_for(self._active), self.default_language)

    def _init_family_db(self) -> None:
        try:
            with closing(db.connect(self.family_db)) as conn, conn:
                conn.executescript(FAMILY_SCHEMA)
        except sqlite3.DatabaseError:
            aside = self.family_db.with_name(f"family.db.damaged-{datetime.now():%Y%m%d-%H%M%S}")
            log.error("Family database is damaged. Moving it to %s and starting fresh.", aside)
            self.family_db.rename(aside)
            db.discard_wal_files(self.family_db)
            with closing(db.connect(self.family_db)) as conn, conn:
                conn.executescript(FAMILY_SCHEMA)

    def _migrate_single_child(self, legacy: Path) -> None:
        """Versions up to 0.9.x kept one child in data/tippy.db. That file becomes the first child."""
        try:
            old = db.get_settings(legacy)
            with db.connect(legacy) as conn:
                usage = [tuple(r) for r in conn.execute(
                    "SELECT day, model, prompt_tokens, completion_tokens, est_cost_usd FROM llm_usage")]
        except sqlite3.DatabaseError:
            aside = legacy.with_name(f"{legacy.name}.damaged-{datetime.now():%Y%m%d-%H%M%S}")
            log.error("The old database is damaged. Moving it to %s and starting fresh.", aside)
            legacy.rename(aside)
            db.discard_wal_files(legacy)
            return
        backup = legacy.with_name(f"{legacy.name}.before-profiles-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(legacy, backup)                                # safety copy: nothing is ever lost
        log.info("Moving the single-child database into profiles (safety copy: %s)", backup)
        profile_id = self._create(name=old.get("child_name", ""), avatar=AVATARS[0])
        shutil.move(str(legacy), str(self.path_for(profile_id)))
        db.init_db(self.path_for(profile_id), self.default_language)
        for key in ("pin_hash", "openrouter_model"):                  # household settings move to the family file
            if old.get(key):
                db.set_setting(self.family_db, key, old[key])
        with closing(db.connect(self.path_for(profile_id))) as conn, conn:
            conn.execute("DELETE FROM settings WHERE key IN ('pin_hash', 'openrouter_model')")
        with db.connect(self.family_db) as conn:
            conn.executemany("INSERT INTO llm_usage (day, model, prompt_tokens, completion_tokens, est_cost_usd) VALUES (?, ?, ?, ?, ?)", usage)

    # ---------- Reading ----------

    def path_for(self, profile_id: int) -> Path:
        return self.profiles_dir / f"{int(profile_id)}.db"

    @property
    def db_path(self) -> Path:
        """The database of the child who is playing right now."""
        return self.path_for(self._active)

    @property
    def active_id(self) -> int:
        return self._active

    def list(self) -> list[dict]:
        with db.connect(self.family_db) as conn:
            return [dict(r) for r in conn.execute("SELECT id, name, avatar FROM profiles ORDER BY id")]

    def get(self, profile_id: int) -> dict:
        for profile in self.list():
            if profile["id"] == profile_id:
                return profile
        raise ProfileError("That child does not exist.")

    # ---------- Changing ----------

    def _create(self, name: str, avatar: str) -> int:
        with db.connect(self.family_db) as conn:
            profile_id = conn.execute("INSERT INTO profiles (name, avatar) VALUES (?, ?)", (name, avatar)).lastrowid
        return profile_id

    def create(self, name: str, avatar: str, language: str | None = None) -> dict:
        if len(self.list()) >= MAX_PROFILES:
            raise ProfileError(f"Tippy supports up to {MAX_PROFILES} children.")
        if avatar not in AVATARS:
            raise ProfileError("Please pick one of the pictures.")
        profile_id = self._create(name, avatar)
        path = self.path_for(profile_id)
        db.init_db(path, language or self.default_language)
        db.set_setting(path, "child_name", name)
        db.set_setting(path, "keyboard_layout", languages.default_keyboard(language or self.default_language))
        return self.get(profile_id)

    def update(self, profile_id: int, name: str | None = None, avatar: str | None = None) -> dict:
        self.get(profile_id)
        if avatar is not None and avatar not in AVATARS:
            raise ProfileError("Please pick one of the pictures.")
        with db.connect(self.family_db) as conn:
            if name is not None:
                conn.execute("UPDATE profiles SET name = ? WHERE id = ?", (name, profile_id))
            if avatar is not None:
                conn.execute("UPDATE profiles SET avatar = ? WHERE id = ?", (avatar, profile_id))
        if name is not None:
            db.set_setting(self.path_for(profile_id), "child_name", name)   # one name, kept in step
        return self.get(profile_id)

    def rename_active(self, name: str) -> None:
        """The parent typed a new name in Settings: keep the picture list in step."""
        with db.connect(self.family_db) as conn:
            conn.execute("UPDATE profiles SET name = ? WHERE id = ?", (name, self._active))

    def select(self, profile_id: int) -> dict:
        profile = self.get(profile_id)
        with self._lock:
            self._active = profile_id
        db.init_db(self.path_for(profile_id), self.default_language)
        db.set_setting(self.family_db, "active_profile", str(profile_id))
        return profile

    def erase_everything(self) -> None:
        """Delete every child, every kept-aside copy and the family file (PIN included), then start again with
        one blank child, as on a brand-new install. Nothing is kept: this is the "delete everything" button."""
        with self._lock:
            shutil.rmtree(self.profiles_dir, ignore_errors=True)
            for path in self.data_dir.iterdir():
                if path.is_file() and path.name.startswith(("family.db", "tippy.db")):
                    path.unlink()
            self._open(None)

    def delete(self, profile_id: int) -> None:
        """Remove a child. The database file is kept aside (renamed), not erased, in case it was a mistake."""
        self.get(profile_id)
        remaining = [p["id"] for p in self.list() if p["id"] != profile_id]
        if not remaining:
            raise ProfileError("The last child cannot be removed.")
        if profile_id == self._active:
            self.select(remaining[0])
        with db.connect(self.family_db) as conn:
            conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        path = self.path_for(profile_id)
        if path.exists():
            aside = self.profiles_dir / f"removed-{profile_id}-{datetime.now():%Y%m%d-%H%M%S}.db"
            path.rename(aside)
            db.discard_wal_files(path)
