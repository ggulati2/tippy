"""Content packs: content/packs/<id>/manifest.json plus the data files it points to.

A pack is the unit Tippy loads vocabulary from. Today there are two: "core-bank" (everything Tippy shipped
with before packs existed, moved here unchanged) and "family-words" (a declaration only: the child's own
name and favourite word, generated at runtime in the browser, never written to disk — see its manifest).
docs/REVAMP_BRIEF.md milestone 7 adds a way for a parent or teacher to add their own pack through the
parent area; it will be validated with the exact same `load_manifest` this module already uses.

Every manifest is checked against content/packs/schema.json (a JSON Schema) at start-up, not only in
tests, so a broken or hand-edited pack fails loudly instead of silently vanishing.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from backend.config import CONTENT_DIR

PACKS_DIR = CONTENT_DIR / "packs"
_SCHEMA = json.loads((PACKS_DIR / "schema.json").read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(_SCHEMA)


class PackError(Exception):
    """A pack's manifest.json, or one of the files it points to, is not usable."""


def load_manifest(pack_dir: Path) -> dict:
    """Read and validate one pack's manifest.json. Raises PackError with a plain-language reason."""
    manifest_path = pack_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise PackError(f"{pack_dir.name}: cannot read manifest.json ({e})") from e
    problems = sorted((err.message for err in _VALIDATOR.iter_errors(manifest)))
    if problems:
        raise PackError(f"{pack_dir.name}: " + "; ".join(problems))
    if manifest["id"] != pack_dir.name:
        raise PackError(f"{pack_dir.name}: manifest id {manifest['id']!r} does not match its folder name")
    for role, filename in manifest["files"].items():
        if not (pack_dir / filename).exists():
            raise PackError(f"{pack_dir.name}: manifest lists {role} = {filename!r}, but that file is missing")
    return manifest


def discover() -> dict[str, dict]:
    """Every pack under content/packs/, keyed by id. Each entry is the manifest plus its folder as "dir"."""
    if not PACKS_DIR.exists():
        return {}
    return {
        (manifest := load_manifest(pack_dir))["id"]: {**manifest, "dir": pack_dir}
        for pack_dir in sorted(p for p in PACKS_DIR.iterdir() if p.is_dir())
    }


def pack_path(pack_id: str, role: str) -> Path:
    """The on-disk path of one of a pack's data files, by its role name (a key in manifest["files"])."""
    packs = discover()
    if pack_id not in packs:
        raise PackError(f"no pack named {pack_id!r}")
    filename = packs[pack_id]["files"].get(role)
    if not filename:
        raise PackError(f"pack {pack_id!r} has no file for {role!r}")
    return packs[pack_id]["dir"] / filename


def pack_file(pack_id: str, role: str) -> dict:
    """Load and parse one of a pack's data files."""
    return json.loads(pack_path(pack_id, role).read_text(encoding="utf-8"))
