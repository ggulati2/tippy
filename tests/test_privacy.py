"""docs/PRIVACY.md is the one text to edit; frontend/js/privacy-text.js (the parent area's Datenschutz tab) is
generated from it by scripts/sync_privacy.py. This fails if the two are out of step."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_privacy  # noqa: E402


def test_privacy_text_js_matches_privacy_md():
    expected = sync_privacy.privacy_js(sync_privacy.PRIVACY_FILE.read_text(encoding="utf-8"))
    actual = sync_privacy.OUTPUT_FILE.read_text(encoding="utf-8")
    assert actual == expected, "frontend/js/privacy-text.js is out of date: run `python scripts/sync_privacy.py`"


def test_privacy_page_has_german_and_english_with_the_required_topics():
    text = sync_privacy.sections(sync_privacy.PRIVACY_FILE.read_text(encoding="utf-8"))
    assert set(text) == {"de", "en"}
    for heading in ("### What is stored", "### Where it is stored", "### What leaves this computer", "### Deleting"):
        assert heading in text["en"]
    for heading in ("### Was gespeichert wird", "### Wo es gespeichert wird", "### Was den Computer verlässt", "### Löschen"):
        assert heading in text["de"]
