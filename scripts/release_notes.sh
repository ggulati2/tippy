#!/bin/bash
# Prints the CHANGELOG.md section of one version (used as the text of a GitHub release).
#   scripts/release_notes.sh 0.9.1
v="$1"
notes=$(awk -v v="$v" '$0 ~ "^## \\[" v "\\]" {f=1; next} /^## \[/ {f=0} f' "$(dirname "$0")/../CHANGELOG.md")
if [ -z "$(echo "$notes" | tr -d '[:space:]')" ]; then
  echo "Tippy $v"; echo; echo "See CHANGELOG.md for details."
else
  echo "$notes"
fi
