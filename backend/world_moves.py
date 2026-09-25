"""Moving a child's progress to the 2026 world layout, once.

The worlds were regrouped so that every stage has one clear skill (docs/OVERNIGHT_BUILD_LOG.md, "World layout 2"):
- Sentence Sky lost its name and family-word levels to a new world, Name Nest ("name").
- Computer Cove kept the computer lessons; the safety lessons went to Safety Harbour ("safety") and the
  general-knowledge quizzes (flags, animal homes, food, weather) to Quiz Corner ("quiz").

A child's finished levels, stars and stickers move with the lessons, and no world a child could open before is
locked afterwards. This module has no other Tippy imports, so db.py can run it when a database is opened.
"""
import sqlite3
from pathlib import Path

LAYOUT = "2"

# Old (world, level) -> new places. Levels not listed stay where they are.
_MOVES: dict[tuple[str, int], list[tuple[str, int]]] = {
    ("sentences", 4): [("name", 1)],                     # the child's own name
    ("sentences", 5): [("name", 2), ("name", 3)],        # favourite word and family words, now two levels
    **{("sentences", old): [("sentences", old - 2)] for old in range(6, 14)},   # bonus levels close the gap
    ("basics", 4): [("basics", 6)],                      # take a break
    ("basics", 5): [("safety", 1)],                      # ask a grown-up
    ("basics", 6): [("safety", 2)],                      # some things stay secret
    ("basics", 7): [("basics", 4)],                      # what the internet is
    ("basics", 8): [("basics", 5)],                      # saving
    ("basics", 9): [("safety", 3)],                      # be kind
    ("basics", 10): [("basics", 7)],                     # the touchpad
    ("basics", 11): [("safety", 7)],                     # 112 (German only)
    ("basics", 12): [("safety", 8)],                     # traffic (German only)
    ("basics", 13): [("quiz", 1)],                       # flags
    ("basics", 14): [("quiz", 2)],                       # animal homes
    ("basics", 15): [("quiz", 3)],                       # food
    ("basics", 16): [("quiz", 4)],                       # weather
    ("basics", 17): [("safety", 4)],                     # a stranger asks your name
    ("basics", 18): [("safety", 5)],                     # "you won a prize" pop-up
    ("basics", 19): [("safety", 6)],                     # someone asks for your password
}

# An old world a child could open -> the new worlds its lessons are in now.
_OPENS = {"sentences": ["sentences", "name"], "basics": ["basics", "safety", "quiz"]}

# The unlock rules before the move (backend/progress.py at that time), kept to work out what was open.
_OLD_ORDER = ["mouse", "keyboard", "letters", "words", "sentences", "basics", "free", "numbers", "paint", "desktop",
              "internet", "robot", "tenfinger"]
_OLD_CORE = {"mouse": 4, "keyboard": 5, "letters": 5, "words": 5, "sentences": 5, "basics": 6, "free": 1, "numbers": 6,
             "paint": 5, "desktop": 7, "internet": 5, "robot": 5, "tenfinger": 5}
_OLD_AFTER = {"numbers": "keyboard", "paint": "mouse", "robot": "keyboard", "desktop": "basics", "internet": "sentences"}


def move_level(world: str, level: int) -> list[tuple[str, int]]:
    return _MOVES.get((world, level), [(world, level)])


def move_rows(rows: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """(world, level, stars) rows in the old layout -> the same rows in the new one (best stars kept)."""
    best: dict[tuple[str, int], int] = {}
    for world, level, stars in rows:
        for place in move_level(world, level):
            best[place] = max(stars, best.get(place, 0))
    return [(world, level, stars) for (world, level), stars in best.items()]


def opened_worlds(rows: list[tuple[str, int, int]], manual: str) -> list[str]:
    """The worlds (new names) a child had opened in the old layout by playing or from the parent, from old rows and
    the old unlock setting. The first world, open for everyone, is left out."""
    if manual == "all":
        return []                                        # "all" still means all
    done = {w: {lv for (x, lv, _) in rows if x == w and lv <= _OLD_CORE.get(w, 0)} for w in _OLD_ORDER}
    complete = {w: len(done[w]) >= _OLD_CORE[w] for w in _OLD_ORDER}
    parent = {w for w in manual.split(",") if w}
    opened = []
    for i, world in enumerate(_OLD_ORDER):
        before = _OLD_AFTER.get(world) or (_OLD_ORDER[i - 1] if i else None)
        if world in parent or (world != "tenfinger" and before is not None and complete[before]):
            opened += _OPENS.get(world, [world])
    return opened


def upgrade(conn: sqlite3.Connection, db_path: Path) -> None:
    """Moves an old database to the new layout, once. A copy of the old file is kept next to it first, so the
    family can go back to an older Tippy (which does not know the new worlds) by putting that copy back."""
    if conn.execute("SELECT 1 FROM settings WHERE key = 'world_layout'").fetchone():
        return
    rows = [(r[0], r[1], r[2]) for r in conn.execute("SELECT world, level, stars FROM progress WHERE status = 'done'")]
    if rows:
        conn.commit()
        with sqlite3.connect(db_path.with_name(db_path.name + ".before-world-layout-2")) as copy:
            conn.backup(copy)
        row = conn.execute("SELECT value FROM settings WHERE key = 'unlocked_worlds'").fetchone()
        manual = row[0] if row else ""
        opened = opened_worlds(rows, manual)
        if opened:
            keep = [w for w in manual.split(",") if w] + opened
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('unlocked_worlds', ?)",
                         (",".join(sorted(set(keep))),))
        conn.execute("DELETE FROM progress")
        conn.executemany("INSERT INTO progress (world, level, status, stars) VALUES (?, ?, 'done', ?)", move_rows(rows))
    conn.execute("INSERT INTO settings (key, value) VALUES ('world_layout', ?)", (LAYOUT,))
