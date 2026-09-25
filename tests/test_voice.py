"""Tippy's recorded voice (frontend/voice): the recordings match what the app looks for, and nothing is left over."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_voice  # noqa: E402  (a developer tool; Piper itself is only imported when recording)

VOICE_DIR = ROOT / "frontend" / "voice"
LANGUAGES = sorted(p.name for p in VOICE_DIR.iterdir() if (p / "index.json").exists()) if VOICE_DIR.exists() else []

SAMPLES = ["Play", "Press the glowing key!", "  Hello   World ", "Ärger über Öl", "¡Hola! ¿Qué tal?", "Tippy 🐱", "ß", "0", "A",
           "Computer\u00adbucht"]


def test_python_and_javascript_make_the_same_file_names():
    """If these two ever differ, the browser looks for files that do not exist and the voice silently stops."""
    script = ("global.window={};global.settings={};global.screenSerial=0;" + (ROOT / "frontend/js/voice.js").read_text(encoding="utf-8")
              + ";console.log(JSON.stringify(%s.map(voiceKey)))" % json.dumps(SAMPLES))
    from_js = json.loads(subprocess.run(["node", "-e", script], capture_output=True, encoding="utf-8", check=True).stdout)
    assert from_js == [make_voice.clip_name(text) for text in SAMPLES]


def test_text_is_tidied_before_hashing():
    assert make_voice.clip_name("  The   Cat ") == make_voice.clip_name("the cat")
    assert make_voice.clip_name("Computer\u00adbucht") == make_voice.clip_name("Computerbucht")   # a soft hyphen is not spoken
    assert make_voice.clip_name("cat") != make_voice.clip_name("cat.")          # punctuation matters: it is part of the sentence


@pytest.mark.skipif(not LANGUAGES, reason="no recordings yet")
@pytest.mark.parametrize("lang", LANGUAGES)
def test_the_index_and_the_files_agree(lang):
    folder = VOICE_DIR / lang
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    listed, present = set(index["clips"]), {p.stem for p in folder.glob("*.ogg")}
    assert listed == present, f"index and files differ: missing {sorted(listed - present)[:3]}, extra {sorted(present - listed)[:3]}"
    for before, after in index["templates"]:
        for piece in (before, after):
            assert not piece or make_voice.clip_name(piece) in listed, f"missing recording for {piece!r}"
    assert all(p.stat().st_size > 200 for p in folder.glob("*.ogg")), "an empty recording"


@pytest.mark.skipif(not LANGUAGES, reason="no recordings yet")
@pytest.mark.parametrize("lang", LANGUAGES)
def test_nearly_everything_the_app_says_is_recorded(lang):
    """Not everything needs a recording (the computer's voice is the fallback), but new content should be recorded:
    run scripts/make_voice.py again when this fails."""
    index = set(json.loads((VOICE_DIR / lang / "index.json").read_text(encoding="utf-8"))["clips"])
    texts = make_voice.load_strings(lang)["texts"]
    missing = [t for t in texts if make_voice.clip_name(t) not in index]
    assert len(missing) <= len(texts) * 0.03, f"{len(missing)} of {len(texts)} texts have no recording, for example {missing[:5]}"


def test_the_recordings_are_small_enough_to_ship():
    total = sum(p.stat().st_size for p in VOICE_DIR.rglob("*") if p.is_file()) if VOICE_DIR.exists() else 0
    assert total < 40 * 1024 * 1024, f"{total // 1024 // 1024} MB of recordings"
