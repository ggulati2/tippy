"""Every supported language must be complete. Adding a language to backend/languages.py makes all of
these tests apply to it, so a half-finished language cannot be merged."""
import json
import unicodedata

import pytest
from fastapi.testclient import TestClient

from backend import bank, dashboard, db, languages, progress, validators
from backend.app import create_app
from backend.content import ContentService
from backend.llm import prompts
from backend.llm.client import LLMClient

CODES = languages.CODES
EXTRA_KEYS = {"qwerty": "", "qwertz": "ÄÖÜ", "qwerty_es": "Ñ"}     # letters with a key of their own on each layout
PUNCTUATION = ".,!?;:\"'-¡¿"


def fold(char: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c))


def typable(text: str, layout: str) -> bool:
    """Can a child type this text on the given keyboard? (Accents without their own key use the plain letter.)"""
    for char in text:
        if char == " " or char in PUNCTUATION:
            continue
        upper = char.upper()
        if upper in EXTRA_KEYS[layout] or fold(upper).isascii() and fold(upper).isalpha():
            continue
        return False
    return True


def test_the_language_list_is_consistent():
    assert "en" in CODES
    for code, info in languages.LANGUAGES.items():
        assert info["keyboard"] in languages.KEYBOARDS and info["voice"].startswith(code) and info["native"] and info["prompt_name"]
    assert set(EXTRA_KEYS) == set(languages.KEYBOARDS)


@pytest.mark.parametrize("code", CODES)
def test_every_bank_has_the_language(code):
    for name, pool in (("WORDS", bank.WORDS), ("SENTENCES", bank.SENTENCES)):
        assert set(pool[code]) == set(pool["en"]), f"{name}[{code}] needs the same themes as English"
        assert all(pool[code][theme] for theme in pool["en"]), f"{name}[{code}] has an empty theme"
    assert bank.PICTURES[code] and bank.FREE_PLAY[code]
    assert set(bank.ASK["answers"][code]) == set(bank.ASK["questions"])
    assert set(bank.MASCOT_LINES[code]) == set(bank.MASCOT_LINES["en"])
    assert all("{child}" in line for line in bank.MASCOT_LINES[code]["welcome"][:2])
    assert bank.ASK_REDIRECT[code]
    assert validators.BLOCKLISTS[code], f"a word blocklist for {code} is required"
    assert prompts.LANGUAGE_NAMES[code]


@pytest.mark.parametrize("code", CODES)
def test_enough_content_for_word_woods_and_sentence_sky(code):
    pictures = bank.PICTURES[code]
    assert len([w for w in pictures if len(w) <= 4]) >= 40, "Word Woods needs 40+ words of up to 4 letters with a picture"
    assert len([w for w in pictures if len(w) <= 3]) >= 10, "the first two Word Woods rounds use words of up to 3 letters"
    sentences = [s for theme in bank.SENTENCES[code].values() for s in theme]
    assert len(sentences) >= 20
    assert len(bank.FREE_PLAY[code]) >= 50


@pytest.mark.parametrize("code", CODES)
def test_everything_is_typable_on_the_default_keyboard(code):
    layout = languages.default_keyboard(code)
    words = [w for theme in bank.WORDS[code].values() for w in theme]
    sentences = [s for theme in bank.SENTENCES[code].values() for s in theme]
    for text in [*words, *sentences, *bank.PICTURES[code], *bank.FREE_PLAY[code]]:
        assert typable(text, layout), f"{code}: cannot be typed on {layout}: {text!r}"
    for sentence in sentences:
        assert 3 <= len(sentence.translate(str.maketrans("", "", PUNCTUATION)).split()) <= 6, sentence


@pytest.mark.parametrize("code", CODES)
def test_the_bank_words_have_pictures_where_word_woods_needs_them(code):
    pictured = [w for theme in bank.WORDS[code].values() for w in theme if w in bank.PICTURES[code]]
    assert len(pictured) >= 40


@pytest.mark.parametrize("code", CODES)
def test_content_service_serves_the_language(tmp_path, code):
    path = tmp_path / "c.db"
    db.init_db(path, code)
    db.set_setting(path, "language", code)
    service = ContentService(path, LLMClient(_settings(tmp_path)), background=False)
    words = service.pictured_words(5, 3)
    assert len(words["items"]) == 5 and all(w in words["pictures"] and len(w) <= 3 for w in words["items"])
    assert len(service.sentences(4)["items"]) == 4
    assert service.mascot_line("welcome") in bank.MASCOT_LINES[code]["welcome"]        # built-in lines are used when the helper is off
    assert service.ask_answer("wifi")["text"] == bank.ASK["answers"][code]["wifi"]
    assert service.ask_answer("nonsense")["text"] == bank.ASK_REDIRECT[code]


def _settings(tmp_path):
    from backend.config import Settings
    return Settings(openrouter_api_key="", openrouter_model="m", openrouter_fallback_model="f", app_language="en",
                    parent_pin="", llm_mode="off", daily_request_cap=1, db_path=tmp_path / "unused.db")


@pytest.mark.parametrize("code", CODES)
def test_sticker_names_exist_in_every_language(code):
    for sticker in progress.CATALOG:
        assert sticker["name"].get(code), f"sticker {sticker['id']} has no {code} name"


@pytest.mark.parametrize("code", CODES)
def test_the_parent_summary_is_written_in_the_language(code):
    stats = {"days_played_last_7": 3, "minutes_last_7": 40, "letters_unlocked": 8, "letters_mastered": 4, "overall_accuracy_percent": 81,
             "keystrokes": 200, "weak_keys": ["Q"], "strong_keys": ["A"], "streak_days": 3, "worlds_completed": []}
    english = dashboard.local_summary(stats, "en")
    for stats_case in (stats, {**stats, "keystrokes": 0}):
        summary = dashboard.local_summary(stats_case, code)
        assert set(summary) == {"strengths", "practice", "tips"} and all(summary.values())
        if code != "en":
            assert summary != dashboard.local_summary(stats_case, "en"), "summary fell back to English"
    assert "3" in dashboard.local_summary(stats, code)["strengths"] and english


def test_accents_count_as_their_plain_letters():
    assert languages.base_letters("camión") == set("CAMION")
    assert languages.base_letters("Niño ÜBER Straße") == set("NIOUBERSTRA")
    assert bank.letters_outside("león", set("LEON")) == 0 and bank.letters_outside("león", set("LEO")) == 1


def test_llm_output_in_every_language_passes_the_validators():
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert validators.clean_words(["león", "niño", "camión", "gato"], allowed, lang="es", max_len=6) == ["león", "niño", "camión", "gato"]
    assert validators.clean_words(["león", "niño"], allowed, lang="es") == ["león", "niño"]
    assert validators.clean_words(["contraseña", "matar"], allowed, lang="es") == []          # the Spanish blocklist works
    assert validators.clean_sentences(["El perro corre mucho.", "¡Qué bien escribes!"], allowed, lang="es") == ["El perro corre mucho.", "¡Qué bien escribes!"]
    assert validators.clean_line("<b>hola</b>", lang="es") is None


# ---------- The web API knows the languages ----------

@pytest.fixture()
def api(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


def test_languages_endpoint(api):
    client, _ = api
    body = client.get("/api/languages").json()
    assert [l["code"] for l in body["languages"]] == list(CODES) and set(body["keyboards"]) == set(languages.KEYBOARDS)


@pytest.mark.parametrize("code", CODES)
def test_a_child_can_use_each_language(api, code):
    client, parent = api
    assert client.post("/api/parent/settings", json={"language": code, "keyboard_layout": languages.default_keyboard(code)}, headers=parent).json()["language"] == code
    assert len(client.get("/api/content/words?count=5&pictured=true&max_len=3").json()["items"]) == 5
    assert client.get("/api/mascot/line?event=welcome").json()["text"]
    assert client.get("/api/pictures").status_code == 200
    assert client.post("/api/parent/settings", json={"language": "xx"}, headers=parent).status_code == 422
    assert client.post("/api/parent/settings", json={"keyboard_layout": "dvorak"}, headers=parent).status_code == 422


def test_new_children_and_setup_get_the_right_keyboard(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    done = client.post("/api/setup", json={"pin": "2468", "language": "es"}).json()
    assert done["language"] == "es" and done["keyboard_layout"] == "qwerty_es"
    token = client.post("/api/parent/verify", json={"pin": "2468"}).json()["token"]
    headers = {"X-Parent-Token": token}
    listing = client.post("/api/parent/profiles", json={"name": "Lea", "avatar": client.get("/api/profiles").json()["avatars"][1], "language": "de"}, headers=headers).json()
    client.post("/api/profiles/select", json={"id": listing["profiles"][1]["id"]})
    assert client.get("/api/settings").json()["keyboard_layout"] == "qwertz"


def test_restore_accepts_every_language_and_layout(tmp_path):
    from backend import restore
    for code in CODES:
        plan = restore.prepare({"app": "tippy", "tables": {"settings": [{"key": "language", "value": code},
                                                                          {"key": "keyboard_layout", "value": languages.default_keyboard(code)}]}})
        assert plan["settings"]["language"] == code and plan["settings"]["keyboard_layout"] == languages.default_keyboard(code)
    assert restore.prepare({"app": "tippy", "tables": {"settings": [{"key": "language", "value": "es"}, {"key": "language", "value": "fr"}]}})["skipped"] == 1
