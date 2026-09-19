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
