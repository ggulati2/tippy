"""docs/REVAMP_BRIEF.md section 4.4: keyboard layouts are stored as data (frontend/layouts/*.json), and
the on-screen keyboard, finger zones and lessons all read from that one source. This checks the source
files are sane and that the generated frontend/js/layouts-data.js (see scripts/sync_layouts.py) is not
stale, the same way tests/test_branding.py checks frontend/js/config.js against branding.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_layouts  # noqa: E402

from backend import languages

REQUIRED_KEYS = {"SHIFT", "BACKSPACE", "SPACE", "ENTER"}


def test_generated_file_matches_the_source_json():
    layouts = sync_layouts.load_layouts()
    expected = sync_layouts.layouts_js(layouts)
    actual = sync_layouts.OUT_FILE.read_text(encoding="utf-8")
    assert actual == expected, "frontend/js/layouts-data.js is out of date: run `python scripts/sync_layouts.py`"


def test_every_keyboard_backend_knows_about_has_a_layout_file():
    # backend/languages.py names the layouts Tippy ships (languages.KEYBOARDS); each must have a source file.
    for layout_id in languages.KEYBOARDS:
        assert (sync_layouts.LAYOUTS_DIR / f"{layout_id}.json").exists(), f"no frontend/layouts/{layout_id}.json for {layout_id}"


def test_every_layout_has_the_keys_every_lesson_relies_on():
    for layout_id, data in sync_layouts.load_layouts().items():
        keys = {key for row in data["rows"] for key in row}
        missing = REQUIRED_KEYS - keys
        assert not missing, f"{layout_id} is missing {missing}"
        # No key should appear twice: renderKeyboard() in keyboard.js keeps one DOM node per key name.
        all_keys = [key for row in data["rows"] for key in row]
        assert len(all_keys) == len(set(all_keys)), f"{layout_id} lists a key twice"
        assert data["name"], f"{layout_id} has no display name"


def test_qwerty_and_qwertz_swap_y_and_z():
    # This is the exact swap docs/REVAMP_BRIEF.md section 4.4 asks Tippy to detect (and keyboard.js's
    # trackLayoutMismatch relies on it): on a German keyboard, the key in the QWERTY "Y position" (top
    # row) types Z, and the key in the QWERTY "Z position" (bottom row) types Y.
    qwerty = json.loads((sync_layouts.LAYOUTS_DIR / "qwerty.json").read_text(encoding="utf-8"))
    qwertz = json.loads((sync_layouts.LAYOUTS_DIR / "qwertz.json").read_text(encoding="utf-8"))
    top_row, bottom_row = 0, 2  # index into "rows": top letter row, and the row with SHIFT
    assert "Y" in qwerty["rows"][top_row] and "Z" in qwertz["rows"][top_row], "Y's position should type Z on QWERTZ"
    assert "Z" in qwerty["rows"][bottom_row] and "Y" in qwertz["rows"][bottom_row], "Z's position should type Y on QWERTZ"
    assert qwerty["rows"][top_row].index("Y") == qwertz["rows"][top_row].index("Z")
    assert qwerty["rows"][bottom_row].index("Z") == qwertz["rows"][bottom_row].index("Y")
