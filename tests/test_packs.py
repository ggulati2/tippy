"""Content packs (content/packs/): every manifest must validate against the schema, point only at files
that really exist, and the built-in ones must be exactly what backend/bank.py and backend/progress.py expect."""
import pytest

from backend import bank, packs


def test_every_built_in_pack_is_valid():
    found = packs.discover()
    assert set(found) >= {"core-bank", "family-words"}
    for pack_id, manifest in found.items():
        assert manifest["id"] == pack_id
        assert len(manifest["languages"]) >= 1
        assert len(manifest["age_range"]) == 2 and manifest["age_range"][0] <= manifest["age_range"][1]


def test_a_manifest_with_a_missing_file_is_rejected(tmp_path):
    pack_dir = tmp_path / "broken-pack"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        '{"id": "broken-pack", "version": "1.0.0", "languages": ["en"], "age_range": [5, 8], '
        '"licence": "test", "author": "test", "files": {"words": "missing.json"}}',
        encoding="utf-8",
    )
    with pytest.raises(packs.PackError, match="missing"):
        packs.load_manifest(pack_dir)


def test_a_manifest_that_fails_the_schema_is_rejected(tmp_path):
    pack_dir = tmp_path / "bad-schema"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text('{"id": "bad-schema"}', encoding="utf-8")  # missing required fields
    with pytest.raises(packs.PackError):
        packs.load_manifest(pack_dir)


def test_a_manifest_whose_id_does_not_match_its_folder_is_rejected(tmp_path):
    pack_dir = tmp_path / "folder-name"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        '{"id": "different-name", "version": "1.0.0", "languages": ["en"], "age_range": [5, 8], '
        '"licence": "test", "author": "test", "files": {}}',
        encoding="utf-8",
    )
    with pytest.raises(packs.PackError, match="folder"):
        packs.load_manifest(pack_dir)


def test_core_bank_is_what_bank_py_actually_uses():
    """bank.py's WORDS/SENTENCES/etc. must come from the pack, not from a leftover loose copy."""
    assert bank.WORDS == packs.pack_file("core-bank", "words")
    assert bank.SPECIAL == packs.pack_file("core-bank", "special")
    assert bank.PICTURES == packs.pack_file("core-bank", "pictures")


def test_family_words_is_declared_but_generates_nothing_on_disk():
    manifest = packs.discover()["family-words"]
    assert manifest.get("generated") is True
    assert manifest["files"] == {}
