import json
from datetime import date, timedelta

import pytest

from backend import dashboard, db, difficulty, progress, summary
from backend.config import Settings
from backend.llm.client import LLMClient

D = date(2026, 3, 11)


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "d.db"
    db.init_db(path)
    return path


def presses(key, right, wrong):
    return [{"key": key, "correct": True, "ms": 400}] * right + [{"key": key, "correct": False, "ms": 900}] * wrong


# ---------- keys and letters ----------

def test_key_report_and_weak_strong_keys(db_path):
    difficulty.record_keystrokes(db_path, presses("A", 10, 0) + presses("Q", 3, 7) + presses("P", 2, 1))
    keys = {k["key"]: k for k in dashboard.key_report(db_path)}
    assert keys["Q"]["accuracy"] == 0.3 and keys["A"]["accuracy"] == 1.0
    weak, strong = dashboard.weak_and_strong(list(keys.values()))
    assert weak == ["Q"] and strong == ["A"]        # P has too few tries to judge


def test_mastered_letters_need_enough_tries(db_path):
    difficulty.record_keystrokes(db_path, presses("A", 8, 0) + presses("S", 7, 0) + presses("D", 6, 4))
    assert dashboard.dashboard(db_path, D)["letters"]["mastered"] == ["A"]


def test_daily_accuracy_trend_only_lists_days_with_data(db_path):
    difficulty.record_keystrokes(db_path, presses("A", 3, 1))   # recorded for today's real date
    trend = dashboard.dashboard(db_path, date.today())["trend"]
    assert trend == [{"day": date.today().isoformat(), "attempts": 4, "accuracy": 75}]
    assert dashboard.dashboard(db_path, date.today() - timedelta(days=30))["trend"] == []


# ---------- play time and limits ----------

def test_play_minutes_fill_missing_days_with_zero(db_path):
    dashboard.add_play_seconds(db_path, 60, D)
    dashboard.add_play_seconds(db_path, 30, D)
    minutes = dashboard.dashboard(db_path, D)["play_minutes"]
    assert len(minutes) == 7 and minutes[-1] == {"day": D.isoformat(), "minutes": 1.5}
    assert all(m["minutes"] == 0 for m in minutes[:-1])


def test_one_heartbeat_cannot_add_more_than_a_minute(db_path):
    dashboard.add_play_seconds(db_path, 100000, D)
    assert dashboard.limits_state(db_path, D)["today_seconds"] == dashboard.MAX_HEARTBEAT_SECONDS


def test_daily_limit(db_path):
    assert dashboard.limits_state(db_path, D)["daily_reached"] is False       # off by default
    db.set_setting(db_path, "daily_limit_minutes", "1")
    dashboard.add_play_seconds(db_path, 59, D)
    assert dashboard.limits_state(db_path, D)["daily_reached"] is False
    dashboard.add_play_seconds(db_path, 1, D)
    state = dashboard.limits_state(db_path, D)
    assert state["daily_reached"] is True and state["session_minutes"] == 10


# ---------- summary ----------

def make_llm(tmp_path, mode="mock", reply=None):
    settings = Settings("k" if mode == "live" else "", "m", "b", "en", "1234", mode, 50, tmp_path / "d.db")
    db.init_db(settings.db_path)
    db.set_setting(settings.db_path, "ai_consent", "1")   # a parent has switched the online helper on

    class Fake(LLMClient):
        calls = 0

        def generate(self, task):
            Fake.calls += 1
            return reply

    return Fake(settings)


def test_local_summary_has_no_names_and_both_languages(db_path):
    difficulty.record_keystrokes(db_path, presses("A", 10, 0) + presses("Q", 3, 7))
    stats = dashboard.summary_stats(dashboard.dashboard(db_path, date.today()))
    assert stats["weak_keys"] == ["Q"] and "name" not in json.dumps(stats).lower()
    en, de = dashboard.local_summary(stats, "en"), dashboard.local_summary(stats, "de")
    assert "Q" in en["practice"] and "Q" in de["practice"] and en != de
    assert dashboard.local_summary({**stats, "keystrokes": 0}, "en")["practice"].startswith("There is no data")


def test_summary_uses_llm_when_valid_and_caches_per_week(db_path, tmp_path):
    good = json.dumps({"strengths": "Good week with steady practice.", "practice": "Practice the Q key a little.", "tips": "Keep sessions short and happy."})
    llm = make_llm(tmp_path, "live", good)
    first = summary.get_summary(db_path, llm, D)
    assert first["source"] == "llm" and first["strengths"].startswith("Good week")
    summary.get_summary(db_path, llm, D)
    assert llm.calls == 1                                            # second call came from the cache
    summary.get_summary(db_path, llm, D + timedelta(days=7))         # a new week asks again
    assert llm.calls == 2
    summary.get_summary(db_path, llm, D + timedelta(days=7), refresh=True)
    assert llm.calls == 3


@pytest.mark.parametrize("bad", [None, "nonsense", json.dumps({"strengths": "<b>x</b> hello there", "practice": "ok fine then", "tips": "ok fine then"}),
                                 json.dumps({"strengths": "fine text here", "practice": "", "tips": "fine text here"})])
def test_bad_llm_summary_falls_back_to_template(db_path, tmp_path, bad):
    result = summary.get_summary(db_path, make_llm(tmp_path, "live", bad), D)
    assert result["source"] == "builtin" and result["tips"]


def test_mock_mode_never_asks_llm_for_summary(db_path, tmp_path):
    llm = make_llm(tmp_path, "mock", "unused")
    assert summary.get_summary(db_path, llm, D)["source"] == "builtin" and llm.calls == 0


# ---------- export and reset ----------

def test_export_contains_progress_but_not_the_cached_summary(db_path):
    progress.record_completion(db_path, "mouse", 1, 3, D)
    db.set_setting(db_path, "weekly_summary", "{}")
    tables = dashboard.export_data(db_path)["tables"]
    assert tables["progress"][0]["world"] == "mouse" and tables["stickers"][0]["id"] == "puppy"
    assert "weekly_summary" not in {s["key"] for s in tables["settings"]}


def test_reset_clears_progress_but_keeps_settings(db_path):
    progress.record_completion(db_path, "mouse", 1, 3, D)
    difficulty.record_keystrokes(db_path, presses("A", 20, 0), adaptive=True)
    db.set_setting(db_path, "child_name", "Kim")
    dashboard.reset_progress(db_path)
    assert progress.get_progress(db_path, D)["total_stars"] == 0
    assert difficulty.get_letters(db_path)["unlocked"] == 2 and dashboard.key_report(db_path) == []
    assert db.get_settings(db_path)["child_name"] == "Kim"


def test_play_window_shows_the_goodnight_screen_outside_it(db_path):
    assert dashboard.limits_state(db_path, D, hour=21)["outside_window"] is False    # no window by default
    db.set_setting(db_path, "play_window", "8-18")
    assert dashboard.limits_state(db_path, D, hour=7)["outside_window"] is True
    assert dashboard.limits_state(db_path, D, hour=8)["outside_window"] is False
    assert dashboard.limits_state(db_path, D, hour=17)["outside_window"] is False
    assert dashboard.limits_state(db_path, D, hour=18)["outside_window"] is True
