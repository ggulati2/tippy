@echo off
rem Double-click to start Tippy on Windows.
cd /d "%~dp0"
if not exist .venv (
  echo First start: setting things up, this takes about a minute...
  python -m venv .venv || (echo Python 3.11+ is needed. See README.md & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
rem Install only when something is missing, so Tippy also starts without internet after the first run.
python -c "import fastapi, uvicorn, httpx, pydantic" 2>nul || pip install -q -r requirements.txt || (echo Install failed. Are you online? & pause & exit /b 1)
if not exist .env copy .env.example .env >nul
python scripts\launch.py
