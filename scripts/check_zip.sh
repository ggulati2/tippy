#!/bin/bash
# Checks a built Tippy zip: it must contain the app and the double-click starters, and nothing
# private or developer-only. Used by the CI pipeline and by the release pipeline.
#   scripts/check_zip.sh Tippy-0.9.1.zip
zip="${1:-$(ls Tippy-*.zip 2>/dev/null | head -1)}"
[ -f "$zip" ] || { echo "No zip found. Run: python scripts/make_zip.py"; exit 1; }
echo "Checking $zip"
list=$(unzip -Z1 "$zip")
fail=0
for f in Tippy/VERSION Tippy/start.command Tippy/start.bat Tippy/start.sh Tippy/backend/app.py \
         Tippy/frontend/index.html Tippy/.env.example Tippy/requirements.txt Tippy/README.md Tippy/LICENSE Tippy/THIRD-PARTY-NOTICES.md Tippy/frontend/assets/fonts/OFL.txt; do
  echo "$list" | grep -qx "$f" || { echo "  ✗ missing from zip: $f"; fail=1; }
done
private='(^|/)\.env$|\.db|/data/|/logs/|/tests/|\.githooks|check\.sh|check_zip|\.github/'
if echo "$list" | grep -Eq "$private"; then
  echo "  ✗ something private or developer-only is in the zip:"; echo "$list" | grep -E "$private" | sed 's/^/      /'; fail=1
fi
# The version inside the zip must match the file name.
version=$(unzip -p "$zip" Tippy/VERSION | tr -d '[:space:]')
[ "$zip" = "Tippy-$version.zip" ] || [ "$(basename "$zip")" = "Tippy-$version.zip" ] || { echo "  ✗ zip name does not match the VERSION inside ($version)"; fail=1; }
# The starters must stay double-clickable.
for s in Tippy/start.command Tippy/start.sh; do
  unzip -Z "$zip" "$s" | grep -q '^-rwx' || { echo "  ✗ $s lost its execute bit"; fail=1; }
done
[ $fail -eq 0 ] && echo "✓ zip looks right" || exit 1
