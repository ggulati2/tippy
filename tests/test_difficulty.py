import pytest

from backend import db, difficulty
from backend.difficulty import WINDOW, decide, record_keystrokes


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "d.db"
    db.init_db(path)
    return path


def presses(key, n, correct=True, ms=500):
    return [{"key": key, "correct": correct, "ms": ms}] * n


def test_decide_needs_enough_evidence():
    assert decide([True] * (WINDOW - 1), 2) == "stay"


def test_decide_advance_step_back_stay():
    assert decide([True] * WINDOW, 2) == "advance"
    assert decide([True] * 16 + [False] * 4, 2) == "advance"      # exactly 80%
    assert decide([True] * 15 + [False] * 5, 2) == "stay"         # 75%
    assert decide([False] * WINDOW, 4) == "step_back"


def test_never_below_minimum_or_above_maximum():
    assert decide([False] * WINDOW, difficulty.MIN_UNLOCKED) == "stay"
    assert decide([True] * WINDOW, len(difficulty.LETTER_ORDER)) == "stay"


def test_starts_with_two_home_row_letters(db_path):
    assert difficulty.get_letters(db_path)["letters"] == ["A", "S"]


def test_stats_and_running_average(db_path):
    record_keystrokes(db_path, [{"key": "A", "correct": True, "ms": 1000}, {"key": "A", "correct": False, "ms": 3000}])
    with db.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM keystroke_stats WHERE key = 'A'").fetchone()
    assert (row["attempts"], row["correct"], row["avg_ms"]) == (2, 1, 2000)


def test_long_pauses_are_capped(db_path):
    record_keystrokes(db_path, [{"key": "A", "correct": True, "ms": 500000}])
    with db.connect(db_path) as conn:
        assert conn.execute("SELECT avg_ms FROM keystroke_stats WHERE key = 'A'").fetchone()[0] == difficulty.MAX_MS


def test_advances_after_twenty_good_presses(db_path):
    result = record_keystrokes(db_path, presses("A", WINDOW), adaptive=True)
    assert result["change"] == "advance" and result["letters"] == ["A", "S", "D"]


def test_window_restarts_after_a_change(db_path):
    record_keystrokes(db_path, presses("A", WINDOW), adaptive=True)
    # Ten more good presses are not enough evidence for another change.
    assert record_keystrokes(db_path, presses("A", 10), adaptive=True)["change"] is None


def test_steps_back_when_struggling(db_path):
    record_keystrokes(db_path, presses("A", WINDOW), adaptive=True)   # now 3 letters
    result = record_keystrokes(db_path, presses("D", WINDOW, correct=False), adaptive=True)
    assert result["change"] == "step_back" and result["unlocked"] == 2


def test_non_adaptive_presses_do_not_change_difficulty(db_path):
    result = record_keystrokes(db_path, presses("A", 40), adaptive=False)
    assert result["unlocked"] == 2 and result["change"] is None
