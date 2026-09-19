#!/bin/bash
# Start Tippy on Linux: ./start.sh
cd "$(dirname "$0")" || exit 1
[ -d ".venv" ] || python3 -m venv .venv || { echo "Python 3.11+ is needed. See README.md"; exit 1; }
source .venv/bin/activate
pip install -q -r requirements.txt || { echo "Install failed. Are you online?"; exit 1; }
[ -f ".env" ] || cp .env.example .env
python scripts/launch.py
