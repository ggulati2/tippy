"""Progress, stars, stickers and the daily streak.

The rules live here (not in the browser) so they are easy to test and the
browser cannot cheat by accident. Nothing here ever punishes the child:
stars and stickers only go up, and a missed day just means the streak starts over quietly.
"""
import json
from datetime import date, timedelta
from pathlib import Path

from backend import db, packs

# Worlds in the order they unlock. A world unlocks when the one before it is complete.
WORLD_ORDER = ["mouse", "keyboard", "letters", "words", "sentences", "basics", "free", "numbers", "paint", "desktop", "internet", "robot"]

# How many levels each *built* world has. Add a world here when it is built.
LEVEL_COUNTS = {"mouse": 4, "keyboard": 5, "letters": 5, "words": 5, "sentences": 5, "basics": 6, "free": 1, "numbers": 6,
                "paint": 5, "desktop": 7, "internet": 5, "robot": 5}

# Bonus levels come after the core levels of a world. They give stars and stickers, but they never
# change whether the world counts as complete, so adding them cannot re-lock anything for a child
# who has already played. Some bonus levels only appear for one language (decided in the browser).
# Some numbers are only shown for German (see BONUS in frontend/js/rewards.js): letters 9 (umlauts), words 11 and 12,
# sentences 9 and 10, basics 11 and 12. Levels added later for every language (words 13 to 15, sentences 11 to 13,
# basics 13 to 16) simply carry on the numbering, so nothing a child already earned changes.
BONUS_LEVELS: dict[str, int] = {"keyboard": 2, "letters": 4, "words": 10, "sentences": 8, "basics": 13}

# By default a world opens when the one before it in WORLD_ORDER is complete. A world listed here
# opens after the named world instead. Number Land (added later) opens after Keyboard Kingdom; putting it
# in the middle of the chain would have re-locked worlds for children who were already further on.
UNLOCK_AFTER = {"numbers": "keyboard",
                # The four "everyday computer" worlds open when the skill they need has been learned:
                # painting needs the mouse, the robot needs the arrow keys (Keyboard Kingdom), the pretend desktop needs
                # the Computer Cove lessons (windows, folders) and the pretend internet needs typing sentences.
                "paint": "mouse", "robot": "keyboard", "desktop": "basics", "internet": "sentences"}


def max_level(world: str) -> int:
    """The highest level number a world has (core levels plus bonus levels)."""
    return LEVEL_COUNTS.get(world, 0) + BONUS_LEVELS.get(world, 0)

MAX_STARS_PER_LEVEL = 3


def load_catalog(path: Path = packs.pack_path("core-bank", "stickers")) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


CATALOG = load_catalog()


def public_catalog() -> list[dict]:
    """What the browser needs to draw the album (no internal award keys)."""
    return [{"id": s["id"], "emoji": s["emoji"], "name": s["name"], "langs": s.get("langs")} for s in CATALOG]


# ---------- Play days and streak ----------

def record_visit(db_path: Path, today: date) -> None:
    with db.connect(db_path) as conn:
        conn.execute("INSERT OR IGNORE INTO play_days (day) VALUES (?)", (today.isoformat(),))


def compute_streak(days: set[date], today: date) -> int:
    """Days in a row. If today is not played yet, yesterday still counts,
    so the child is never shown a zero first thing in the morning."""
    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def _streak(conn, today: date) -> int:
    rows = conn.execute("SELECT day FROM play_days").fetchall()
    return compute_streak({date.fromisoformat(r["day"]) for r in rows}, today)


# ---------- Stickers ----------

def _award(conn, key: str, now: str) -> str | None:
    """Give the sticker tied to `key` if it exists and is not owned yet."""
    for sticker in CATALOG:
        if sticker["award"] == key:
            cur = conn.execute("INSERT OR IGNORE INTO stickers (id, earned_at) VALUES (?, ?)", (sticker["id"], now))
            return sticker["id"] if cur.rowcount else None
    return None


# ---------- Worlds ----------

def _manual_unlocks(conn) -> set[str]:
    row = conn.execute("SELECT value FROM settings WHERE key = 'unlocked_worlds'").fetchone()
    value = row["value"] if row else ""
    return set(WORLD_ORDER) if value == "all" else {w for w in value.split(",") if w}


def unlock_world(db_path: Path, world: str) -> None:
    """Parent action: open one world (or "all") without finishing the earlier ones."""
    if world != "all" and world not in WORLD_ORDER:
        raise ValueError("unknown world")
    with db.connect(db_path) as conn:
        current = _manual_unlocks(conn)
        value = "all" if world == "all" else ",".join(sorted(current | {world}))
    db.set_setting(db_path, "unlocked_worlds", value)


def record_completion(db_path: Path, world: str, level: int, stars: int, today: date | None = None) -> dict:
    """Save a finished level. Returns the ids of any newly earned stickers."""
    today = today or date.today()
    if world not in LEVEL_COUNTS or not 1 <= level <= max_level(world):
        raise ValueError("unknown level")
    if not 0 <= stars <= MAX_STARS_PER_LEVEL:
        raise ValueError("bad star count")
    now = today.isoformat()
    new_stickers: list[str] = []
    with db.connect(db_path) as conn:
        conn.execute("INSERT OR IGNORE INTO play_days (day) VALUES (?)", (now,))
        # Stars only ever go up, so replaying can never lose anything.
        conn.execute(
            "INSERT INTO progress (world, level, status, stars) VALUES (?, ?, 'done', ?) "
            "ON CONFLICT(world, level) DO UPDATE SET status = 'done', stars = MAX(stars, excluded.stars)",
            (world, level, stars),
        )
        done = conn.execute("SELECT COUNT(*) FROM progress WHERE world = ? AND status = 'done' AND level <= ?",
                            (world, LEVEL_COUNTS[world])).fetchone()[0]     # only core levels count towards "world done"
        keys = [f"{world}:{level}"]
        if done >= LEVEL_COUNTS[world]:
            keys.append(f"{world}:done")
        streak = _streak(conn, today)
        keys += [f"streak:{n}" for n in (3, 7) if streak >= n]
        for key in keys:
            sticker_id = _award(conn, key, now)
            if sticker_id:
                new_stickers.append(sticker_id)
    return {"new_stickers": new_stickers}


def get_progress(db_path: Path, today: date | None = None) -> dict:
    today = today or date.today()
    with db.connect(db_path) as conn:
        rows = conn.execute("SELECT world, level, stars FROM progress WHERE status = 'done'").fetchall()
        manual = _manual_unlocks(conn)
        streak = _streak(conn, today)
        stickers = [r["id"] for r in conn.execute("SELECT id FROM stickers ORDER BY earned_at, rowid")]
    levels: dict[str, dict[str, int]] = {w: {} for w in WORLD_ORDER}
    for row in rows:
        levels[row["world"]][str(row["level"])] = row["stars"]

    def complete(world: str) -> bool:
        core = [level for level in levels[world] if int(level) <= LEVEL_COUNTS.get(world, 0)]
        return world in LEVEL_COUNTS and len(core) >= LEVEL_COUNTS[world]

    worlds = {}
    for i, world in enumerate(WORLD_ORDER):
        before = UNLOCK_AFTER.get(world) or (WORLD_ORDER[i - 1] if i else None)
        unlocked = before is None or world in manual or complete(before)
        worlds[world] = {"unlocked": unlocked, "complete": complete(world), "built": world in LEVEL_COUNTS,
                         "levels": levels[world]}
    return {
        "worlds": worlds,
        "total_stars": sum(r["stars"] for r in rows),
        "streak": streak,
        "stickers": stickers,
    }
