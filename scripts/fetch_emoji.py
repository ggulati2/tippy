"""Bundles Twemoji pictures for every emoji Tippy actually uses, instead of relying on the operating system's
own emoji font. Native emoji look different (and are sometimes missing, for example no flags on Windows) on
every computer; Twemoji is one open, colourful, consistent picture set that looks the same everywhere.

This is a DEVELOPER tool. It is not needed to run Tippy; only its output (frontend/assets/twemoji/ and
frontend/js/emoji-map.js) is part of the app, and both are committed to the repository.

One-time setup (downloads the Twemoji source once, about 6 MB; needs the `regex` package for correct emoji
grouping, which the standard library cannot do):
    pip install regex

Run it again whenever a new emoji is used anywhere in the code or in content/*.json:
    python scripts/fetch_emoji.py

It downloads the Twemoji SVGs from GitHub (https://github.com/jdecked/twemoji, MIT code / CC-BY 4.0 graphics,
see THIRD-PARTY-NOTICES.md), scans the app for every emoji it can find, copies only the pictures actually used
into frontend/assets/twemoji/, and writes the lookup table frontend/js/emoji-map.js. Emoji with no matching
picture are simply left as plain text by the browser (frontend/js/emoji.js), so nothing ever breaks if one
is missing.
"""
import glob
import io
import json
import sys
import tarfile
import httpx
from pathlib import Path

import regex  # pip install regex: the standard `re` module cannot group "🇯🇵" or "👍🏽" into one character

ROOT = Path(__file__).resolve().parent.parent
TWEMOJI_TAG = "v17.0.3"
TWEMOJI_URL = f"https://github.com/jdecked/twemoji/archive/refs/tags/{TWEMOJI_TAG}.tar.gz"
OUT_DIR = ROOT / "frontend" / "assets" / "twemoji"
MAP_FILE = ROOT / "frontend" / "js" / "emoji-map.js"

# Unicode blocks that hold emoji and emoji-like symbols. Broad on purpose: a false positive (matching a
# character that turns out not to be an emoji, for example a curly quote) is harmless, because the lookup
# below simply finds no picture for it and the fetch script skips it.
EMOJI_BLOCKS = [(0x2190, 0x21FF), (0x2300, 0x23FF), (0x25A0, 0x27BF), (0x2B00, 0x2BFF), (0x1F000, 0x1FFFF)]


def is_emoji_grapheme(cluster: str) -> bool:
    return any(any(lo <= ord(ch) <= hi for lo, hi in EMOJI_BLOCKS) for ch in cluster)


def find_emoji(text: str) -> set[str]:
    """Every emoji "letter" in this text (grapheme clusters, so "🇯🇵" and "👍🏽" count as one each, not two)."""
    return {cluster for cluster in regex.findall(r"\X", text) if is_emoji_grapheme(cluster)}


def collect_used_emoji() -> set[str]:
    found: set[str] = set()
    for path in glob.glob("frontend/js/*.js") + glob.glob("frontend/*.html"):
        if "emoji-map.js" in path:               # this script's own output: skip so removed emoji drop out
            continue
        found |= find_emoji(Path(path).read_text(encoding="utf-8"))

    def walk(node):
        if isinstance(node, str):
            found.update(find_emoji(node))
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(key)
                walk(value)

    for path in glob.glob("content/*.json"):
        walk(json.loads(Path(path).read_text(encoding="utf-8")))
    return found


def twemoji_filename(emoji: str) -> str:
    """Twemoji's own file-naming rule: lower-case hex code points joined by "-", with the invisible
    "please show this as a picture" mark (U+FE0F) left out, except where that mark is the only thing that
    makes two different emoji use different code points (a small enough list that trying both ways first,
    and falling back to nothing found, is simpler and just as reliable)."""
    codepoints = [ord(ch) for ch in emoji]
    plain = "-".join(f"{cp:x}" for cp in codepoints)
    without_vs16 = "-".join(f"{cp:x}" for cp in codepoints if cp != 0xFE0F)
    return plain, without_vs16


def main() -> None:
    print("Downloading the Twemoji picture set (one-time, about 6 MB)...")
    response = httpx.get(TWEMOJI_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    archive = tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz")
    prefix = f"twemoji-{TWEMOJI_TAG.lstrip('v')}/assets/svg/"
    svgs = {name.removeprefix(prefix): archive.extractfile(name).read()
            for name in archive.getnames() if name.startswith(prefix) and name.endswith(".svg")}
    print(f"{len(svgs)} pictures available.")

    used = collect_used_emoji()
    print(f"{len(used)} different emoji found in the app.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keep = {p.name for p in OUT_DIR.glob("*.svg")}
    table: dict[str, str] = {}
    missing: list[str] = []
    for emoji in sorted(used):
        for candidate in twemoji_filename(emoji):
            filename = f"{candidate}.svg"
            if filename in svgs:
                (OUT_DIR / filename).write_bytes(svgs[filename])
                table[emoji] = filename
                keep.discard(filename)
                break
        else:
            missing.append(emoji)

    for stale in keep:                            # a picture that is no longer used by anything: remove it
        (OUT_DIR / stale).unlink()

    MAP_FILE.write_text(
        "// Generated by scripts/fetch_emoji.py: do not edit by hand.\n"
        "// Maps each emoji the app uses to its Twemoji picture in frontend/assets/twemoji. Used by emoji.js.\n"
        "window.EMOJI_MAP = " + json.dumps(table, ensure_ascii=False, sort_keys=True) + ";\n",
        encoding="utf-8",
    )
    total = sum(p.stat().st_size for p in OUT_DIR.glob("*.svg"))
    print(f"Saved {len(table)} pictures ({total // 1024} KB) to {OUT_DIR}.")
    if missing:
        print(f"No Twemoji picture found for {len(missing)} of them (they will show as plain text): {missing[:10]}")


if __name__ == "__main__":
    main()
