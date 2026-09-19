"""Plays the real app in headless Chrome. Slow (a few minutes), so run on demand:

    python -m pytest -m browser -v

The scripts are in tests/browser/js. They found several real bugs (a double-clicked close button,
stale screens after pressing Home, accents in names) that unit tests could not see.
"""
import pytest

from tests.browser.conftest import assert_clean, call, run_script

pytestmark = pytest.mark.browser


@pytest.mark.parametrize("arg", ["en:1", "de:1", "es:1"])
def test_every_level_can_be_played_and_every_screen_fits(server, arg):
    report = run_script(server, "playthrough.js", arg, budget_ms=1_500_000)
    assert_clean(report)


def test_every_level_can_be_played_with_larger_text(server):
    # With the biggest text on a short screen a few screens may scroll, so fit is not enforced here.
    report = run_script(server, "playthrough.js", "en:1.25", budget_ms=1_500_000)
    assert_clean(report, ignore_fit=True)


def test_a_child_cannot_break_it(server):
    assert_clean(run_script(server, "stress.js"))


def test_break_and_daily_limit(server):
    assert_clean(run_script(server, "limits.js", budget_ms=600_000))


def test_parent_area(server):
    assert_clean(run_script(server, "parent.js", budget_ms=600_000))


def test_children_can_be_added_switched_and_have_separate_limits(server):
    assert_clean(run_script(server, "children.js", budget_ms=600_000))


def test_start_with_several_children_asks_who_is_playing(server):
    token = call(server, "/api/parent/verify", {"pin": "2468"})["token"]
    call(server, "/api/parent/settings", {"child_name": "Tom"}, token)
    avatars = call(server, "/api/profiles")["avatars"]
    call(server, "/api/parent/profiles", {"name": "Lea", "avatar": avatars[1], "language": "de"}, token)
    assert_clean(run_script(server, "who.js", budget_ms=300_000))


def test_backup_and_restore_through_the_screens(server):
    assert_clean(run_script(server, "restore.js", budget_ms=600_000))


def test_number_pad_rule(server):
    assert_clean(run_script(server, "numpad.js", budget_ms=300_000))


@pytest.mark.parametrize("lang", ["en", "de", "es"])
def test_first_run_wizard_offers_every_language(fresh_server, lang):
    assert_clean(run_script(fresh_server, "wizard.js", lang, budget_ms=300_000))


def test_spanish_keyboard_accents_and_free_play(server):
    assert_clean(run_script(server, "spanish.js", budget_ms=300_000))


def test_arrow_keys_and_caps_lock_games(server):
    assert_clean(run_script(server, "keygames.js", budget_ms=300_000))


def test_germany_specific_levels_ss_key_and_stickers(server):
    assert_clean(run_script(server, "germany.js", budget_ms=600_000))
