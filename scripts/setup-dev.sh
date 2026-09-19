#!/bin/bash
# One-time setup for anyone working on Tippy's code: turns on the shared git hooks.
cd "$(dirname "$0")/.." || exit 1
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/check.sh
echo "✓ Git hooks are on. Every commit is now checked (see CONTRIBUTING.md)."
