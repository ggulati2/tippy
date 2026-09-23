"""Restoring a backup: round trip, strict validation of untrusted files, safety copy, all-or-nothing."""
import copy
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import dashboard, db, difficulty, progress, restore
from backend.app import create_app
from backend.profiles import AVATARS


def child_with_history(path):
    db.init_db(path, "de")
    db.set_setting(path, "child_name", "Mia")
    db.set_setting(path, "daily_limit_minutes", "45")
    db.set_setting(path, "font_scale", "1.25")
    progress.record_completion(path, "mouse", 1, 3)
    progress.record_completion(path, "mouse", 2, 2)
    progress.record_completion(path, "keyboard", 1, 3)
    difficulty.record_keystrokes(path, [{"key": "A", "correct": True, "ms": 400}] * 25, adaptive=True)   # unlocks a letter
    dashboard.add_play_seconds(path, 60)
    return path


def snapshot(path):
    with db.connect(path) as conn:
        return {t: sorted((tuple(r) for r in conn.execute(f"SELECT * FROM {t}")), key=str) for t in
                ("progress", "stickers", "keystroke_stats", "daily_stats", "play_time", "play_days")}, db.get_settings(path)


# ---------- Round trip ----------

def test_export_then_restore_gives_the_same_child(tmp_path):
    original = child_with_history(tmp_path / "a.db")
    backup = json.loads(json.dumps(dashboard.export_data(original)))       # as a file would carry it
    other = tmp_path / "b.db"
    db.init_db(other, "en")
    progress.record_completion(other, "words", 3, 1)                       # something that must disappear
    result = restore.apply(other, restore.prepare(backup))
    tables_a, settings_a = snapshot(original)
    tables_b, settings_b = snapshot(other)
    assert tables_a == tables_b
    for key in ("child_name", "language", "daily_limit_minutes", "font_scale", "letters_unlocked", "unlocked_worlds"):
        assert settings_a.get(key) == settings_b.get(key), key
    assert result["restored"]["progress"] == 3 and result["skipped"] == 0
    assert difficulty.get_letters(other) == difficulty.get_letters(original)


def test_a_safety_copy_of_the_old_data_is_kept(tmp_path):
    target = child_with_history(tmp_path / "a.db")
    empty = tmp_path / "empty.db"
    db.init_db(empty, "en")
    plan = restore.prepare(dashboard.export_data(empty))                   # an "empty" backup: settings only
    result = restore.apply(target, plan)
    copy_path = tmp_path / result["safety_copy"]
    assert copy_path.exists()
    assert len(progress.get_progress(target)["worlds"]["mouse"]["levels"]) == 0     # replaced
    with sqlite3.connect(copy_path) as old:
        assert old.execute("SELECT COUNT(*) FROM progress").fetchone()[0] == 3        # but nothing lost


def test_age_band_is_restored_and_a_bad_one_is_ignored(tmp_path):
    backup = {"app": "tippy", "exported_at": "2026-09-23", "tables": {
        "settings": [], "progress": [], "sessions": [],
        "child_profile": [{"id": 1, "first_name": "", "interests": "", "age_band": "7"}]}}
    path = tmp_path / "c.db"
    db.init_db(path, "en")
    restore.apply(path, restore.prepare(backup))
    assert db.get_age_band(path) == "7"

    # A bad age_band alongside something else usable: the bad value is dropped, the rest still restores.
    bad = {"app": "tippy", "exported_at": "2026-09-23", "tables": {
        "settings": [{"key": "child_name", "value": "Mia"}], "progress": [], "sessions": [],
        "child_profile": [{"id": 1, "first_name": "", "interests": "", "age_band": "grown-up"}]}}
    restore.apply(path, restore.prepare(bad))
    assert db.get_age_band(path) == "7"      # unchanged: the unrecognised value was never applied
    assert db.get_settings(path)["child_name"] == "Mia"


def test_old_0_9_backup_still_restores(tmp_path):
    old_backup = {"app": "tippy", "exported_at": "2026-09-19", "tables": {
        "settings": [{"key": "language", "value": "de"}, {"key": "child_name", "value": "Lea"}, {"key": "openrouter_model", "value": "x"},
                     {"key": "pin_hash", "value": "aa:bb"}],
        "progress": [{"world": "mouse", "level": 1, "status": "done", "stars": 3}],
        "llm_usage": [{"id": 1, "day": "2026-09-19", "model": "m", "prompt_tokens": 1, "completion_tokens": 1, "est_cost_usd": 0.0}],
        "sessions": [], "child_profile": [{"id": 1, "first_name": "", "interests": "space,dinosaurs"}]}}
    path = tmp_path / "c.db"
    db.init_db(path, "en")
    restore.apply(path, restore.prepare(old_backup))
    settings = db.get_settings(path)
    assert settings["child_name"] == "Lea" and settings["language"] == "de"
    assert "pin_hash" not in settings and settings.get("openrouter_model") in (None, "")     # household secrets never come in
    with db.connect(path) as conn:
        assert conn.execute("SELECT interests FROM child_profile").fetchone()[0] == "space,dinosaurs"
        assert conn.execute("SELECT COUNT(*) FROM llm_usage").fetchone()[0] == 0


# ---------- Untrusted input ----------

GOOD = {"app": "tippy", "tables": {"progress": [{"world": "mouse", "level": 1, "status": "done", "stars": 3}]}}


@pytest.mark.parametrize("backup", [None, [], "text", 5, {}, {"app": "other", "tables": {}}, {"app": "tippy"}, {"app": "tippy", "tables": []},
                                    {"app": "tippy", "tables": {"progress": "x"}}, {"app": "tippy", "tables": {"progress": [1, 2]}},
                                    {"app": "tippy", "tables": {"progress": [{"world": "mouse", "level": 1, "status": "done", "stars": 3}] * 20_001}}])
def test_files_that_are_not_backups_are_refused(backup):
    with pytest.raises(restore.RestoreError):
        restore.prepare(backup)


def test_a_backup_with_nothing_usable_is_refused():
    with pytest.raises(restore.RestoreError):
        restore.prepare({"app": "tippy", "tables": {"progress": [{"world": "nope", "level": 1, "status": "done", "stars": 3}]}})


def test_invalid_items_are_skipped_and_counted_not_trusted(tmp_path):
    backup = copy.deepcopy(GOOD)
    t = backup["tables"]
    t["progress"] += [{"world": "mouse", "level": 99, "status": "done", "stars": 3},      # level out of range
                      {"world": "mouse", "level": 2, "status": "done", "stars": 9},       # too many stars
                      {"world": "mouse", "level": 3, "status": "'; DROP TABLE progress;--", "stars": 1},
                      {"world": "../etc", "level": 1, "status": "done", "stars": 1}]
    t["stickers"] = [{"id": "puppy", "earned_at": "2026-09-19"}, {"id": "not-a-sticker", "earned_at": "x"}, {"id": "puppy", "earned_at": 5}]
    t["keystroke_stats"] = [{"key": "A", "attempts": 10, "correct": 8, "avg_ms": 500.0}, {"key": "<script>", "attempts": 1, "correct": 1, "avg_ms": 1},
                            {"key": "B", "attempts": 5, "correct": 6, "avg_ms": 10}, {"key": "C", "attempts": -1, "correct": 0, "avg_ms": 1}]
    t["play_time"] = [{"day": "2026-09-19", "seconds": 600}, {"day": "not a date", "seconds": 5}, {"day": "2026-09-20", "seconds": 10**9}]
    t["daily_stats"] = [{"day": "2026-09-19", "attempts": 3, "correct": 2}, {"day": "2026-09-19", "attempts": 1, "correct": 5}]
    t["settings"] = [{"key": "language", "value": "fr"}, {"key": "child_name", "value": "<b>x</b>"}, {"key": "child_name", "value": "x" * 30},
                     {"key": "session_minutes", "value": 500}, {"key": "unlocked_worlds", "value": "mouse,evil"}, {"key": "anything_else", "value": "1"},
                     {"key": "font_scale", "value": "9"}, {"key": "daily_limit_minutes", "value": 30}]
    plan = restore.prepare(backup)
    assert plan["settings"] == {"daily_limit_minutes": "30"}                                # only the one valid setting
    assert [r for r in plan["rows"]["progress"]] == [("mouse", 1, "done", 3)]
    assert plan["rows"]["stickers"] == [("puppy", "2026-09-19")]
    assert plan["rows"]["keystroke_stats"] == [("A", 10, 8, 500.0)]
    assert plan["rows"]["play_time"] == [("2026-09-19", 600)]
    assert plan["rows"]["daily_stats"] == [("2026-09-19", 3, 2)]
    path = tmp_path / "d.db"
    db.init_db(path, "en")
    result = restore.apply(path, plan)
    assert result["skipped"] > 8
    assert db.get_settings(path)["daily_limit_minutes"] == "30" and db.get_settings(path)["language"] == "en"


def test_restoring_is_all_or_nothing(tmp_path, monkeypatch):
    path = child_with_history(tmp_path / "a.db")
    before = snapshot(path)
    plan = restore.prepare(GOOD)
    plan["rows"]["stickers"] = [("puppy", "2026-09-19"), ("puppy", None)]      # the second row breaks the NOT NULL rule half-way through
    with pytest.raises(sqlite3.IntegrityError):
        restore.apply(path, plan)
    assert snapshot(path) == before                                            # the whole change was rolled back


# ---------- Web API ----------

@pytest.fixture()
def api(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


def test_import_api_needs_the_pin_and_limits_size(api):
    client, parent = api
    body = json.dumps(GOOD)
    assert client.post("/api/parent/import", content=body).status_code == 401
    assert client.post("/api/parent/import", content="not json", headers=parent).status_code == 422
    assert client.post("/api/parent/import", content=json.dumps({"app": "x"}), headers=parent).status_code == 422
    assert client.post("/api/parent/import", content=b"x" * (restore.MAX_BACKUP_BYTES + 1), headers=parent).status_code == 413
    assert client.post("/api/parent/import?target=elsewhere", content=body, headers=parent).status_code == 422


def test_import_replaces_the_shown_child_and_can_add_a_new_child(api):
    client, parent = api
    client.post("/api/progress/complete", json={"world": "keyboard", "level": 1, "stars": 3})      # will be replaced
    backup = {"app": "tippy", "tables": {"settings": [{"key": "child_name", "value": "Lea"}, {"key": "language", "value": "de"}],
                                         "progress": [{"world": "mouse", "level": 1, "status": "done", "stars": 3}]}}
    done = client.post("/api/parent/import", content=json.dumps(backup), headers=parent).json()
    assert done["restored"]["progress"] == 1 and done["target"] == "current" and done["safety_copy"].endswith(".db")
    levels = client.get("/api/progress").json()["worlds"]
    assert levels["mouse"]["levels"] and not levels["keyboard"]["levels"]
    assert client.get("/api/settings").json()["child_name"] == "Lea"
    assert client.get("/api/profiles").json()["profiles"][0]["name"] == "Lea"           # the picker follows the name

    added = client.post("/api/parent/import?target=new", content=json.dumps(backup), headers=parent).json()
    assert added["target"] == "new"
    profiles = client.get("/api/profiles").json()["profiles"]
    assert len(profiles) == 2 and profiles[1]["name"] == "Lea"
    assert client.get("/api/settings").json()["profile_id"] == profiles[0]["id"]          # the parent stays on the same child


def test_a_bad_file_never_creates_a_child(api):
    client, parent = api
    assert client.post("/api/parent/import?target=new", content=json.dumps({"app": "tippy", "tables": {}}), headers=parent).status_code == 422
    assert len(client.get("/api/profiles").json()["profiles"]) == 1


def test_new_child_respects_the_limit_of_six(api):
    client, parent = api
    for i in range(5):
        client.post("/api/parent/profiles", json={"name": "Kid" + "abcde"[i], "avatar": AVATARS[i]}, headers=parent)
    assert client.post("/api/parent/import?target=new", content=json.dumps(GOOD), headers=parent).status_code == 422
    assert len(client.get("/api/profiles").json()["profiles"]) == 6


def test_digit_statistics_and_number_pad_setting_restore(tmp_path):
    backup = {"app": "tippy", "tables": {
        "settings": [{"key": "has_numpad", "value": "1"}, {"key": "has_numpad", "value": "yes"}],
        "keystroke_stats": [{"key": "7", "attempts": 4, "correct": 3, "avg_ms": 600}, {"key": "77", "attempts": 1, "correct": 1, "avg_ms": 1}],
        "progress": [{"world": "numbers", "level": 6, "status": "done", "stars": 3}, {"world": "numbers", "level": 7, "status": "done", "stars": 3}]}}
    plan = restore.prepare(backup)
    assert plan["settings"]["has_numpad"] == "1"
    assert plan["rows"]["keystroke_stats"] == [("7", 4, 3, 600.0)]
    assert plan["rows"]["progress"] == [("numbers", 6, "done", 3)]
