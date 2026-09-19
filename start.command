#!/bin/bash
# Double-click to start Tippy on macOS.
cd "$(dirname "$0")" || exit 1

# First run: create the private Python environment and install what Tippy needs.
if [ ! -d ".venv" ]; then
  echo "First start: setting things up (this takes about a minute)..."
  python3 -m venv .venv || { echo "Python 3.11+ is needed. See README.md"; read -r -p "Press Enter to close"; exit 1; }
fi
source .venv/bin/activate
pip install -q -r requirements.txt || { echo "Install failed. Are you online?"; read -r -p "Press Enter to close"; exit 1; }

[ -f ".env" ] || cp .env.example .env   # first run: create settings file with defaults
python scripts/launch.py
