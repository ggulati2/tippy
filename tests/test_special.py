"""Language-specific sets (Germany-specific words and sentences): valid, typable, and only for their language."""
import pytest
from fastapi.testclient import TestClient

from backend import bank, db, languages
from backend.app import create_app
from backend.content import ContentService
from backend.llm.client import LLMClient
from tests.test_languages import _settings, typable

SETS = [(code, name, spec) for code, sets in bank.SPECIAL.items() for name, spec in sets.items()]


def test_special_sets_belong_to_known_languages():
    assert set(bank.SPECIAL) <= set(languages.CODES) and SETS


@pytest.mark.parametrize("code,name,spec", SETS, ids=[f"{c}-{n}" for c, n, _ in SETS])
def test_every_special_set_is_valid_and_typable(code, name, spec):
    layout = languages.default_keyboard(code)
    if spec["type"] == "words":
        assert len(spec["items"]) >= 12, "a level draws 5 words per round; keep a good supply"
        for word, emoji in spec["items"].items():
            assert word == word.lower() and word.isalpha() and 2 <= len(word) <= 11 and emoji, word
            assert typable(word, layout), f"{word!r} cannot be typed on {layout}"
    else:
        assert len(spec["items"]) >= 8
        for sentence in spec["items"]:
            assert typable(sentence, layout) and 3 <= bank.word_count(sentence) <= 6, sentence
            assert sentence[0].isupper() and sentence.rstrip()[-1] in ".!?"


def test_the_umlaut_set_really_needs_the_extra_keys():
    words = bank.SPECIAL["de"]["umlaut_words"]["items"]
    assert all(any(c in "äöüß" for c in w) for w in words)
    assert {"ä", "ö", "ü", "ß"} <= {c for w in words for c in w}, "the level should practise every extra key"


def test_content_service_serves_special_sets_only_for_their_language(tmp_path):
    path = tmp_path / "c.db"
    db.init_db(path, "de")
    service = ContentService(path, LLMClient(_settings(tmp_path)), background=False)
    words = service.special("culture_words", 5)
    assert len(words["items"]) == 5 and all(w in words["pictures"] for w in words["items"])
    assert len(service.special("festival_sentences", 3)["items"]) == 3
    assert service.special("no_such_set", 3) is None
    db.set_setting(path, "language", "es")
    assert service.special("culture_words", 5) is None            # Spanish has no Germany-specific sets


@pytest.fixture()
def api(tmp_path, monkeypatch):
    for key, value in {"TIPPY_DB_PATH": str(tmp_path / "tippy.db"), "PARENT_PIN": "4321", "LLM_MODE": "off", "OPENROUTER_API_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    client = TestClient(create_app())
    token = client.post("/api/parent/verify", json={"pin": "4321"}).json()["token"]
    return client, {"X-Parent-Token": token}


def test_special_content_endpoint(api):
    client, parent = api
    assert client.get("/api/content/special?set=culture_words").status_code == 404          # English has none
    client.post("/api/parent/settings", json={"language": "de", "keyboard_layout": "qwertz"}, headers=parent)
    found = client.get("/api/content/special?set=umlaut_words&count=4").json()
    assert len(found["items"]) == 4 and set(found["pictures"]) == set(found["items"])
    assert client.get("/api/content/special?set=culture_sentences").json()["items"]
    assert client.get("/api/content/special?set=nope").status_code == 404
    for bad in ("/api/content/special?set=../x", "/api/content/special?set=ab", "/api/content/special?set=culture_words&count=99", "/api/content/special"):
        assert client.get(bad).status_code == 422, bad
