"""Builds a zip you can give to other families:  python scripts/make_zip.py

It packs only the files that git tracks. Your .env (with your OpenRouter key), the data/
folder (your child's progress), logs and the .venv are never tracked, so they can never end up
in the zip. Commit your changes first: uncommitted edits are not included.
"""
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEFT_OUT = ("tests/", "scripts/try_models.py", "scripts/make_zip.py", "scripts/check.sh", "scripts/check_i18n.js",
            "scripts/setup-dev.sh", "scripts/check_zip.sh", "scripts/release_notes.sh", ".githooks/", ".github/", ".gitignore", ".gitattributes", ".editorconfig", "CLAUDE.md",
            "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md", "pytest.ini")
SECRET = re.compile(rb"sk-or-[A-Za-z0-9_-]{20,}")


def main() -> None:
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    files = [f for f in files if f and not f.startswith(LEFT_OUT)]  # startswith also matches whole folders and exact names
    version = (ROOT / "VERSION").read_text().strip()
    out = ROOT / f"Tippy-{version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            data = (ROOT / name).read_bytes()
            if SECRET.search(data):  # last safety net: never ship something that looks like a key
                sys.exit(f"Stopped: {name} contains something that looks like an API key.")
            info = zipfile.ZipInfo(f"Tippy/{name}", date_time=(2026, 1, 1, 0, 0, 0))
            executable = name.endswith((".command", ".sh"))
            info.external_attr = (0o100000 | (0o755 if executable else 0o644)) << 16  # regular file + permissions  # keep double-click scripts runnable
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    print(f"Created {out.name} with {len(files)} files ({out.stat().st_size // 1024} KB).")


if __name__ == "__main__":
    main()
