"""Children (profiles): separate storage per child, migration of the old single-child database."""
import json
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend import db, progress
from backend.app import create_app
from backend.config import Settings
from backend.content import ContentService
from backend.llm import mock
from backend.llm.client import LLMClient
from backend.profiles import AVATARS, MAX_PROFILES, Family, ProfileError


def new_family(tmp_path, **kw):
    return Family(tmp_path, "en", **kw)


# ---------- Family basics ----------

def test_fresh_install_has_one_child(tmp_path):
    fam = new_family(tmp_path)
    assert [p["id"] for p in fam.list()] == [1]
    assert fam.active_id == 1 and fam.db_path == tmp_path / "profiles" / "1.db" and fam.db_path.exists()
    assert (tmp_path / "family.db").exists()


def test_children_have_separate_data(tmp_path):
    fam = new_family(tmp_path)
    a = fam.active_id
    progress.record_completion(fam.db_path, "mouse", 1, 3)
    db.set_setting(fam.db_path, "language", "de")
    b = fam.create("Mia", AVATARS[1])["id"]
    fam.select(b)
    assert progress.get_progress(fam.db_path)["stickers"] == []
    assert db.get_settings(fam.db_path)["language"] == "en"
    assert db.get_settings(fam.db_path)["child_name"] == "Mia"
    fam.select(a)
    assert progress.get_progress(fam.db_path)["worlds"]["mouse"]["levels"] == {"1": 3} or progress.get_progress(fam.db_path)["worlds"]["mouse"]["levels"] == {1: 3}
    assert db.get_settings(fam.db_path)["language"] == "de"


def test_new_child_in_german_gets_qwertz(tmp_path):
    fam = new_family(tmp_path)
    child = fam.create("Jürgen", AVATARS[2], language="de")
    assert db.get_settings(fam.path_for(child["id"]))["keyboard_layout"] == "qwertz"


def test_limits_on_number_and_pictures(tmp_path):
    fam = new_family(tmp_path)
    for i in range(MAX_PROFILES - 1):
        fam.create(f"Kid{i}", AVATARS[i % len(AVATARS)])
    with pytest.raises(ProfileError):
        fam.create("Extra", AVATARS[0])
    with pytest.raises(ProfileError):
        new_family(tmp_path / "other").create("X", "not-an-avatar")


def test_rename_keeps_name_in_step_and_select_is_remembered(tmp_path):
    fam = new_family(tmp_path)
    b = fam.create("Mia", AVATARS[1])["id"]
    fam.update(b, name="Mia Rose", avatar=AVATARS[3])
    assert fam.get(b) == {"id": b, "name": "Mia Rose", "avatar": AVATARS[3]}
    assert db.get_settings(fam.path_for(b))["child_name"] == "Mia Rose"
    fam.select(b)
    assert new_family(tmp_path).active_id == b          # a restart remembers who played last


def test_delete_keeps_the_file_aside_and_never_removes_the_last_child(tmp_path):
    fam = new_family(tmp_path)
    a = fam.active_id
    b = fam.create("Mia", AVATARS[1])["id"]
    fam.select(b)
    fam.delete(b)                                         # deleting the active child re-selects another
    assert fam.active_id == a and [p["id"] for p in fam.list()] == [a]
    assert not fam.path_for(b).exists() and list((tmp_path / "profiles").glob(f"removed-{b}-*.db"))
    with pytest.raises(ProfileError):
        fam.delete(a)
    with pytest.raises(ProfileError):
        fam.get(999)


def test_damaged_family_database_is_moved_aside(tmp_path):
    (tmp_path).mkdir(exist_ok=True)
    (tmp_path / "family.db").write_bytes(b"not a database" * 50)
    fam = new_family(tmp_path)
    assert fam.list() and list(tmp_path.glob("family.db.damaged-*"))


# ---------- Migration from the single-child versions (0.9.x) ----------

def make_legacy(path, name="Mia", pin_hash="abcd:1234"):
    db.init_db(path, "de")
    db.set_setting(path, "child_name", name)
    db.set_setting(path, "pin_hash", pin_hash)
    db.set_setting(path, "openrouter_model", "some/model:free")
    db.set_setting(path, "daily_limit_minutes", "45")
    progress.record_completion(path, "mouse", 1, 3)
    progress.record_completion(path, "mouse", 2, 3)
    with db.connect(path) as conn:
        conn.execute("INSERT INTO llm_usage (day, model, prompt_tokens, completion_tokens, est_cost_usd) VALUES (?, 'm', 5, 6, 0.01)",
                     (date.today().isoformat(),))


def test_old_single_child_database_becomes_the_first_child(tmp_path):
    legacy = tmp_path / "tippy.db"
    make_legacy(legacy)
    fam = Family(tmp_path, "en", legacy_db=legacy)
    assert not legacy.exists()                                            # moved, not copied
    assert list(tmp_path.glob("tippy.db.before-profiles-*"))              # safety copy kept
    (only,) = fam.list()
    assert only["name"] == "Mia"
    child = db.get_settings(fam.db_path)
    assert child["language"] == "de" and child["daily_limit_minutes"] == "45" and child["child_name"] == "Mia"
    assert "pin_hash" not in child and "openrouter_model" not in child    # household settings left the child file
    household = db.get_settings(tmp_path / "family.db")
    assert household["pin_hash"] == "abcd:1234" and household["openrouter_model"] == "some/model:free"
    assert len(progress.get_progress(fam.db_path)["stickers"]) >= 0 and len(progress.get_progress(fam.db_path)["worlds"]["mouse"]["levels"]) == 2
    with db.connect(tmp_path / "family.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM llm_usage").fetchone()[0] == 1   # the daily request count carries over


def test_migration_happens_once(tmp_path):
    legacy = tmp_path / "tippy.db"
    make_legacy(legacy)
    Family(tmp_path, "en", legacy_db=legacy)
    again = Family(tmp_path, "en", legacy_db=legacy)                      # second start: nothing to migrate
    assert len(again.list()) == 1 and len(list(tmp_path.glob("tippy.db.before-profiles-*"))) == 1


def test_damaged_old_database_is_set_aside_and_tippy_starts(tmp_path):
    legacy = tmp_path / "tippy.db"
    legacy.write_bytes(b"garbage" * 100)
    fam = Family(tmp_path, "en", legacy_db=legacy)
    assert len(fam.list()) == 1 and list(tmp_path.glob("tippy.db.damaged-*"))


def test_app_start_migrates_and_keeps_the_old_pin(tmp_path, monkeypatch):
    from backend.security import hash_pin
    legacy = tmp_path / "tippy.db"
    make_legacy(legacy, pin_hash=hash_pin("2468"))
    for key, value in {"TIPPY_DB_PATH": str(legacy), "PARENT_PIN": "", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    assert client.get("/api/settings").json()["setup_needed"] is False    # no new setup for an existing family
    assert client.post("/api/parent/verify", json={"pin": "2468"}).status_code == 200
    assert client.get("/api/settings").json()["child_name"] == "Mia"


# ---------- Services follow the active child ----------

def test_usage_counter_and_model_belong_to_the_household(tmp_path):
    fam = new_family(tmp_path)
    settings = Settings(openrouter_api_key="k", openrouter_model="m", openrouter_fallback_model="f", app_language="en",
                        parent_pin="", llm_mode="live", daily_request_cap=50, db_path=tmp_path / "unused.db")
    client = LLMClient(settings, state_db=fam.family_db)
    client._record("m", 1, 2, 0.5)
    b = fam.create("Mia", AVATARS[1])["id"]
    fam.select(b)
    assert client.usage_today()["requests"] == 1 and client.usage_today()["cost_usd"] == 0.5   # same count for every child


def test_background_refill_lands_in_the_right_childs_cache(tmp_path):
    fam = new_family(tmp_path)
    a = fam.active_id
    b = fam.create("Mia", AVATARS[1])["id"]

    class SwitchingLLM:
        enabled = True
        mode = "mock"

        def generate(self, task):
            fam.select(b)                       # another child starts playing while the answer is on its way
            return mock.mock_generate(task)

    service = ContentService(fam, SwitchingLLM(), background=False)
    service.mascot_line("welcome")
    assert fam.active_id == b

    def cached(profile):
        with db.connect(fam.path_for(profile)) as conn:
            return conn.execute("SELECT COUNT(*) FROM content_cache").fetchone()[0]

    assert cached(a) > 0 and cached(b) == 0


# ---------- The web API ----------

@pytest.fixture()
def api(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


def test_profiles_api_flow(api):
    client, parent = api
    assert client.get("/api/settings").json()["profile_count"] == 1
    assert client.post("/api/parent/profiles", json={"name": "Mia", "avatar": AVATARS[1]}).status_code == 401
    listing = client.post("/api/parent/profiles", json={"name": "Mia", "avatar": AVATARS[1]}, headers=parent).json()
    assert [p["name"] for p in listing["profiles"]] == ["", "Mia"] and listing["avatars"] == AVATARS
    mia = listing["profiles"][1]["id"]
    # a child taps their picture: no PIN
    chosen = client.post("/api/profiles/select", json={"id": mia}).json()
    assert chosen["profile_id"] == mia and chosen["child_name"] == "Mia" and chosen["profile_count"] == 2
    # progress is separate
    client.post("/api/progress/complete", json={"world": "mouse", "level": 1, "stars": 3})
    assert client.get("/api/progress").json()["worlds"]["mouse"]["levels"]
    client.post("/api/profiles/select", json={"id": 1})
    assert not client.get("/api/progress").json()["worlds"]["mouse"]["levels"]
    # rename through Settings updates the picture list
    client.post("/api/parent/settings", json={"child_name": "Ann"}, headers=parent)
    assert client.get("/api/profiles").json()["profiles"][0]["name"] == "Ann"
    # edit, validate, delete
    assert client.post(f"/api/parent/profiles/{mia}", json={"name": "Mia Rose"}, headers=parent).status_code == 200
    assert client.post(f"/api/parent/profiles/{mia}", json={"avatar": "x"}, headers=parent).status_code == 422
    assert client.post("/api/parent/profiles", json={"name": "<b>", "avatar": AVATARS[0]}, headers=parent).status_code == 422
    assert client.post("/api/parent/profiles", json={"name": "", "avatar": AVATARS[0]}, headers=parent).status_code == 422
    assert client.post(f"/api/parent/profiles/{mia}/delete", json={"confirm": "no"}, headers=parent).status_code == 422
    assert client.post(f"/api/parent/profiles/{mia}/delete", json={"confirm": "DELETE"}, headers=parent).status_code == 403   # PIN again
    assert client.post(f"/api/parent/profiles/{mia}/delete", json={"confirm": "DELETE", "pin": "4321"}, headers=parent).status_code == 200
    assert client.post("/api/profiles/select", json={"id": mia}).status_code == 422
    assert client.post("/api/parent/profiles/1/delete", json={"confirm": "DELETE", "pin": "4321"}, headers=parent).status_code == 422   # the last child


def test_helper_model_is_household_wide(api):
    client, parent = api
    client.post("/api/parent/settings", json={"openrouter_model": "x/y:free"}, headers=parent)
    mia = client.post("/api/parent/profiles", json={"name": "Mia", "avatar": AVATARS[1]}, headers=parent).json()["profiles"][1]["id"]
    client.post("/api/profiles/select", json={"id": mia})
    assert client.get("/api/parent/status", headers=parent).json()["model"] == "x/y:free"


# ---------- Classroom mode (docs/REVAMP_BRIEF.md section 6.5) ----------

@pytest.fixture()
def fresh(tmp_path, monkeypatch):
    """A brand-new install: no PIN yet, so the first-run setup is allowed."""
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    return TestClient(create_app())


def test_classroom_setup_makes_an_anonymous_class(fresh):
    settings = fresh.post("/api/setup", json={"pin": "9876", "language": "de", "classroom": True, "class_size": 25}).json()
    assert settings["classroom"] is True and settings["profile_count"] == 25
    listing = fresh.get("/api/profiles").json()
    assert listing["max"] == 30 and all(p["name"] == "" for p in listing["profiles"])
    assert len({p["avatar"] for p in listing["profiles"]}) == 25                 # every child has their own picture
    teacher = {"X-Parent-Token": fresh.post("/api/parent/verify", json={"pin": "9876"}).json()["token"]}
    assert len(fresh.post("/api/parent/class", json={"add": 10}, headers=teacher).json()["profiles"]) == 30   # never more than 30
    assert fresh.post("/api/parent/profiles", json={"name": "Extra", "avatar": AVATARS[0]}, headers=teacher).status_code == 422
    assert fresh.post("/api/parent/class", json={"classroom": False}, headers=teacher).status_code == 422   # 30 > home maximum


def test_home_setup_stays_a_family(fresh):
    settings = fresh.post("/api/setup", json={"pin": "9876", "child_name": "Mia"}).json()
    assert settings["classroom"] is False and settings["profile_count"] == 1
    assert fresh.get("/api/profiles").json()["max"] == 6


def test_class_overview_needs_the_pin_and_shows_each_child(api):
    client, parent = api
    assert client.get("/api/parent/class/overview").status_code == 401
    client.post("/api/parent/class", json={"classroom": True, "add": 2}, headers=parent)
    client.post("/api/progress/complete", json={"world": "mouse", "level": 1, "stars": 3})
    children = client.get("/api/parent/class/overview", headers=parent).json()["children"]
    assert len(children) == 3
    assert children[0]["worlds"]["mouse"] == {"done": 1, "total": 4} and children[1]["worlds"]["mouse"]["done"] == 0


def test_daily_reset_clears_every_child_once_a_day(tmp_path):
    from backend import dashboard, progress
    family = Family(tmp_path)
    family.set_classroom(True)
    family.add_anonymous(1)
    for profile in family.list():
        progress.record_completion(family.path_for(profile["id"]), "mouse", 1, 3)
    assert not family.reset_all_if_new_day("2026-09-24", dashboard.reset_progress)   # off by default
    db.set_setting(family.family_db, "daily_reset", "1")
    assert family.reset_all_if_new_day("2026-09-24", dashboard.reset_progress)
    assert all(not progress.get_progress(family.path_for(p["id"]))["worlds"]["mouse"]["levels"] for p in family.list())
    progress.record_completion(family.db_path, "mouse", 1, 3)
    assert not family.reset_all_if_new_day("2026-09-24", dashboard.reset_progress)   # the same day: kept
    assert family.reset_all_if_new_day("2026-09-25", dashboard.reset_progress)       # the next day: reset again
