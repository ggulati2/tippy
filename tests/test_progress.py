from datetime import date, timedelta

import pytest

from backend import db, progress

D = date(2026, 1, 10)


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "p.db"
    db.init_db(path)
    return path


def test_streak_counts_consecutive_days():
    days = {D, D - timedelta(days=1), D - timedelta(days=2), D - timedelta(days=5)}
    assert progress.compute_streak(days, D) == 3


def test_streak_survives_until_today_is_played():
    assert progress.compute_streak({D - timedelta(days=1)}, D) == 1


def test_missed_day_restarts_quietly():
    assert progress.compute_streak({D - timedelta(days=3)}, D) == 0


def test_completion_awards_sticker_once(db_path):
    first = progress.record_completion(db_path, "mouse", 1, 3, D)
    assert first["new_stickers"] == ["puppy"]
    again = progress.record_completion(db_path, "mouse", 1, 3, D)
    assert again["new_stickers"] == []


def test_stars_never_go_down(db_path):
    progress.record_completion(db_path, "mouse", 1, 3, D)
    progress.record_completion(db_path, "mouse", 1, 1, D)
    assert progress.get_progress(db_path, D)["worlds"]["mouse"]["levels"]["1"] == 3


def test_finishing_world_unlocks_next_and_awards_medal(db_path):
    assert not progress.get_progress(db_path, D)["worlds"]["keyboard"]["unlocked"]
    for level in range(1, 5):
        result = progress.record_completion(db_path, "mouse", level, 3, D)
    assert "medal" in result["new_stickers"]
    state = progress.get_progress(db_path, D)
    assert state["worlds"]["mouse"]["complete"] and state["worlds"]["keyboard"]["unlocked"]
    assert state["total_stars"] == 12


def test_streak_sticker_after_three_days(db_path):
    for offset in (2, 1):
        progress.record_visit(db_path, D - timedelta(days=offset))
    result = progress.record_completion(db_path, "mouse", 1, 3, D)
    assert "rainbow" in result["new_stickers"]


def test_bad_input_is_rejected(db_path):
    for world, level, stars in [("nope", 1, 3), ("mouse", 9, 3), ("mouse", 1, 9)]:
        with pytest.raises(ValueError):
            progress.record_completion(db_path, world, level, stars, D)


def test_parent_can_unlock_any_world(db_path):
    progress.unlock_world(db_path, "letters")
    assert progress.get_progress(db_path, D)["worlds"]["letters"]["unlocked"]
    progress.unlock_world(db_path, "all")
    assert all(w["unlocked"] for w in progress.get_progress(db_path, D)["worlds"].values())


def test_every_sticker_award_key_is_unique():
    keys = [s["award"] for s in progress.CATALOG]
    assert len(keys) == len(set(keys))


def test_basics_and_free_play_chain(db_path):
    assert not progress.get_progress(db_path, D)["worlds"]["free"]["unlocked"]
    for level in range(1, 7):
        result = progress.record_completion(db_path, "basics", level, 3, D)
    assert "octopus" in result["new_stickers"]
    assert progress.get_progress(db_path, D)["worlds"]["free"]["unlocked"]
    assert "painter" in progress.record_completion(db_path, "free", 1, 3, D)["new_stickers"]


# ---------- Number Land, prerequisites and bonus levels ----------

def finish(path, world, levels=None):
    for level in range(1, (levels or progress.LEVEL_COUNTS[world]) + 1):
        progress.record_completion(path, world, level, 3)


def test_number_land_opens_after_keyboard_kingdom_not_at_the_end(tmp_path):
    path = tmp_path / "p.db"
    db.init_db(path)
    assert not progress.get_progress(path)["worlds"]["numbers"]["unlocked"]
    finish(path, "mouse")
    assert not progress.get_progress(path)["worlds"]["numbers"]["unlocked"]
    finish(path, "keyboard")
    worlds = progress.get_progress(path)["worlds"]
    assert worlds["numbers"]["unlocked"] and worlds["letters"]["unlocked"]


def test_adding_a_world_never_relocks_a_child_who_was_further_on(tmp_path):
    """A child who finished mouse to sentences before Number Land existed keeps everything open."""
    path = tmp_path / "p.db"
    db.init_db(path)
    for world in ("mouse", "keyboard", "letters", "words", "sentences"):
        finish(path, world)
    worlds = progress.get_progress(path)["worlds"]
    assert [w for w in progress.WORLD_ORDER if worlds[w]["unlocked"] and w != "numbers"] == ["mouse", "keyboard", "letters", "words", "sentences", "basics"]
    assert worlds["numbers"]["unlocked"] and not worlds["numbers"]["complete"]


def test_number_land_has_six_levels_and_its_own_stickers(tmp_path):
    path = tmp_path / "p.db"
    db.init_db(path)
    got = []
    for level in range(1, 7):
        got += progress.record_completion(path, "numbers", level, 3)["new_stickers"]
    assert got == ["bee", "giraffe", "trophy"]
    assert progress.get_progress(path)["worlds"]["numbers"]["complete"]
    with pytest.raises(ValueError):
        progress.record_completion(path, "numbers", 7, 3)


def test_bonus_levels_give_rewards_but_never_change_completion(tmp_path, monkeypatch):
    monkeypatch.setitem(progress.BONUS_LEVELS, "letters", 2)
    path = tmp_path / "p.db"
    db.init_db(path)
    progress.record_completion(path, "letters", 6, 3)                       # a bonus level, nothing else done
    progress.record_completion(path, "letters", 7, 3)
    state = progress.get_progress(path)["worlds"]["letters"]
    assert not state["complete"] and set(state["levels"]) == {"6", "7"}
    with pytest.raises(ValueError):
        progress.record_completion(path, "letters", 8, 3)                  # beyond the last bonus level
    finish(path, "letters")                                                # now the five core levels
    after = progress.get_progress(path)
    assert after["worlds"]["letters"]["complete"] and after["worlds"]["words"]["unlocked"]


def test_bonus_levels_do_not_award_the_world_done_sticker_early(tmp_path, monkeypatch):
    monkeypatch.setitem(progress.BONUS_LEVELS, "letters", 3)
    path = tmp_path / "p.db"
    db.init_db(path)
    got = []
    for level in (4, 5, 6, 7, 8):                                           # 2 core + 3 bonus levels = 5 rows, but only 2 core
        got += progress.record_completion(path, "letters", level, 3)["new_stickers"]
    assert "lion" not in got
    for level in (1, 2, 3):
        got += progress.record_completion(path, "letters", level, 3)["new_stickers"]
    assert "lion" in got


def test_bonus_levels_are_accepted_up_to_the_last_one_and_award_their_stickers(tmp_path):
    path = tmp_path / "p.db"
    db.init_db(path)
    # (world, last level, a bonus level with a sticker, that sticker). Some of the numbers in between are German-only.
    for world, last, level, sticker in (("letters", 9, 8, "fish"), ("words", 15, 10, "flamingo"), ("sentences", 13, 8, "peacock"),
                                        ("keyboard", 7, 7, "crocodile"), ("basics", 16, 10, "sloth")):
        assert progress.max_level(world) == last
        assert sticker in progress.record_completion(path, world, level, 3)["new_stickers"]
        progress.record_completion(path, world, last, 3)
        with pytest.raises(ValueError):
            progress.record_completion(path, world, last + 1, 3)
    state = progress.get_progress(path)["worlds"]
    assert not state["letters"]["complete"] and not state["words"]["complete"]        # bonus levels alone never complete a world


def test_german_only_stickers_are_marked_and_awarded_like_any_other(tmp_path):
    path = tmp_path / "p.db"
    db.init_db(path)
    german = {s["id"] for s in progress.public_catalog() if s["langs"] == ["de"]}
    assert german == {"pretzel", "xmastree", "castle", "pumpkin", "bear", "firetruck", "trafficlight"}
    assert progress.record_completion(path, "words", 11, 3)["new_stickers"] == ["pretzel"]
    assert all(s["langs"] is None for s in progress.public_catalog() if s["id"] not in german)
