"""branding.json is the one file to edit (docs/REVAMP_BRIEF.md section 4.7); frontend/js/config.js is
generated from it by scripts/sync_branding.py. This fails if someone edited config.js by hand, or edited
branding.json and forgot to re-run the script."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_branding  # noqa: E402


def test_config_js_matches_branding_json():
    branding = json.loads(sync_branding.BRANDING_FILE.read_text(encoding="utf-8"))
    expected = sync_branding.config_js(branding)
    actual = sync_branding.CONFIG_FILE.read_text(encoding="utf-8")
    assert actual == expected, "frontend/js/config.js is out of date: run `python scripts/sync_branding.py`"


def test_branding_has_the_fields_every_screen_relies_on():
    branding = json.loads(sync_branding.BRANDING_FILE.read_text(encoding="utf-8"))
    assert branding["mascotName"] and branding["mascotColor"] and branding["mascotBellyColor"]
