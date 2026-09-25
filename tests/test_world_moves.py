"""Moving a child's progress to the regrouped worlds (backend/world_moves.py): nothing earned is lost, nothing that
was open is locked, and it happens exactly once."""
from backend import db, progress, restore, world_moves
from backend.world_moves import _OLD_CORE

# The old layout's bonus levels (backend/progress.py before the move).
OLD_MAX = {**_OLD_CORE, "keyboard": 7, "letters": 9, "words": 16, "sentences": 13, "basics": 19}


def old_database(path, rows, unlocked=""):
    """A database as the old Tippy left it: no layout mark, progress in the old worlds."""
    db.init_db(path)
    with db.connect(path) as conn:
        conn.execute("DELETE FROM settings WHERE key = 'world_layout'")
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('unlocked_worlds', ?)", (unlocked,))
        conn.executemany("INSERT INTO progress (world, level, status, stars) VALUES (?, ?, 'done', ?)", rows)


def test_every_old_level_has_a_valid_new_place_and_none_collide():
    places = []
    for world, last in OLD_MAX.items():
        for level in range(1, last + 1):
            for new_world, new_level in world_moves.move_level(world, level):
                assert new_world in progress.LEVEL_COUNTS and 1 <= new_level <= progress.max_level(new_world), (world, level)
                places.append((new_world, new_level))
    assert len(places) == len(set(places))


def test_levels_stars_and_open_worlds_move_along(tmp_path):
    path = tmp_path / "child.db"
    # Finished the old Sentence Sky and the six old Computer Cove core lessons (not the internet or saving ones):
    # the old rules opened Free Play and the pretend desktop.
    rows = [(w, lv, 3) for w in ("mouse", "keyboard", "letters", "words") for lv in range(1, _OLD_CORE[w] + 1)]
    rows += [("sentences", lv, 2) for lv in range(1, 6)] + [("basics", lv, 3) for lv in range(1, 7)] + [("basics", 17, 1)]
    old_database(path, rows)
    db.init_db(path)                                                       # opening it runs the move
    state = progress.get_progress(path)
    worlds = state["worlds"]
    assert worlds["name"]["levels"] == {"1": 2, "2": 2, "3": 2} and worlds["name"]["complete"]
    assert worlds["sentences"]["levels"] == {"1": 2, "2": 2, "3": 2}
    assert worlds["safety"]["levels"] == {"1": 3, "2": 3, "4": 1}          # ask, secrets, the stranger story
    assert worlds["basics"]["levels"] == {"1": 3, "2": 3, "3": 3, "6": 3}  # parts, window, folders, breaks
    assert state["total_stars"] == sum(stars for *_, stars in rows) + 2    # the old level 5 is now two levels
    assert all(worlds[w]["unlocked"] for w in ("free", "desktop", "internet", "safety", "quiz", "name"))
    assert (tmp_path / "child.db.before-world-layout-2").exists()          # the way back to an older Tippy


def test_the_move_happens_once(tmp_path):
    path = tmp_path / "child.db"
    old_database(path, [("sentences", 4, 3)])
    db.init_db(path)
    db.init_db(path)                                   # sentences 4 is now a bonus level: it must not move again
    assert progress.get_progress(path)["worlds"]["name"]["levels"] == {"1": 3}
    progress.record_completion(path, "sentences", 4, 2)
    db.init_db(path)
    assert progress.get_progress(path)["worlds"]["sentences"]["levels"] == {"4": 2}


def test_a_new_child_needs_no_move_and_no_copy(tmp_path):
    db.init_db(tmp_path / "new.db")
    assert db.get_settings(tmp_path / "new.db")["world_layout"] == world_moves.LAYOUT
    assert not list(tmp_path.glob("*.before-world-layout-2"))


def test_unlock_all_stays_all(tmp_path):
    path = tmp_path / "child.db"
    old_database(path, [("mouse", 1, 3)], unlocked="all")
    db.init_db(path)
    assert db.get_settings(path)["unlocked_worlds"] == "all"


def test_an_old_backup_is_moved_on_restore():
    backup = {"app": "tippy", "format": 2, "tables": {
        "settings": [{"key": "unlocked_worlds", "value": "robot"}],
        "progress": [{"world": "basics", "level": 13, "status": "done", "stars": 3},
                     {"world": "sentences", "level": 4, "status": "done", "stars": 2}]}}
    plan = restore.prepare(backup)
    assert sorted(plan["rows"]["progress"]) == [("name", 1, "done", 2), ("quiz", 1, "done", 3)]
    assert plan["settings"]["unlocked_worlds"] == "robot"
    backup["format"] = 3                                                      # a new backup is taken as it is:
    plan = restore.prepare(backup)                                            # basics 13 does not exist any more
    assert plan["rows"]["progress"] == [("sentences", 4, "done", 2)] and plan["skipped"] == 1
