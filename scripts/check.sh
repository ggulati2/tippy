#!/bin/bash
# The one place that says "is this change good enough to commit / merge?".
#   scripts/check.sh fast   quick checks (secrets, syntax, texts). Used by the pre-commit hook.
#   scripts/check.sh        everything, including the automatic tests. Used before pushing and,
#                           later, by the CI pipeline. CI should run exactly this script.
cd "$(dirname "$0")/.." || exit 1
MODE="${1:-full}"
fail=0
step() { echo "• $1"; }
bad()  { echo "  ✗ $1"; fail=1; }

step "no secrets or private files in git"
# Files that must never be committed.
staged=$(git diff --cached --name-only 2>/dev/null; git ls-files)
if echo "$staged" | grep -Eq '(^|/)\.env$|\.db$|\.db-|^data/|^logs/|\.zip$'; then
  bad "a private file is tracked or staged (.env, database, data/, logs/ or a zip):"
  echo "$staged" | grep -E '(^|/)\.env$|\.db$|\.db-|^data/|^logs/|\.zip$' | sort -u | sed 's/^/      /'
fi
# Anything that looks like an OpenRouter key or a private key, in tracked files or in what is staged.
if { git grep -nEI 'sk-or-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----' -- . ':!scripts/check.sh' ':!scripts/make_zip.py'; \
     git diff --cached -U0 2>/dev/null | grep -E '^\+.*(sk-or-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'; } | grep -q .; then
  bad "something that looks like an API key or private key was found"
fi

step "Python files compile"
python3 -m compileall -q backend scripts tests >/dev/null 2>&1 || python -m compileall -q backend scripts tests || bad "a Python file has a syntax error"

if command -v node >/dev/null 2>&1; then
  step "JavaScript files have valid syntax"
  for f in frontend/js/*.js; do node --check "$f" 2>&1 | head -3 | grep -q . && { bad "syntax error in $f"; node --check "$f"; }; done
  step "English and German texts match"
  node scripts/check_i18n.js || bad "text keys differ between languages"
else
  echo "• (Node.js not installed: skipping JavaScript and text checks)"
fi

if [ "$MODE" != "fast" ]; then
  step "automatic tests"
  PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
  $PY -m pytest -q || bad "tests failed"
fi

if [ $fail -ne 0 ]; then echo; echo "✗ Checks failed."; exit 1; fi
echo "✓ All checks passed."
