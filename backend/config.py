"""Settings loaded from the `.env` file in the project root.

We read `.env` with a tiny parser instead of adding a dependency.
The OpenRouter key is read here, on the backend only. It is never sent to the browser.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from backend import languages, licence

# The packaged app (built with PyInstaller, see packaging/) keeps its code and content inside the app
# bundle, which is read-only and replaced on every update. The family's own files (database, logs,
# the browser window's profile, an optional .env) therefore live in a normal user folder. Running from
# the source folder works as before: everything stays next to the code.
FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent.parent   # code and content


PORTABLE_FOLDER = "tippy-data"


def portable_dir(executable: Path, platform: str) -> Path | None:
    """Portable mode (docs/REVAMP_BRIEF.md section 4.6, for schools and USB sticks): a folder called
    "tippy-data" next to the program makes Tippy keep everything in it instead of the user's folder.
    On a Mac the program is Tippy.app/Contents/MacOS/Tippy, so "next to it" means next to Tippy.app."""
    beside = executable.parents[3] if platform == "darwin" and len(executable.parents) > 3 else executable.parent
    folder = beside / PORTABLE_FOLDER
    return folder if folder.is_dir() else None


def _home_dir() -> Path:
    """Where the family's files live. TIPPY_HOME overrides it (used by the tests)."""
    if os.environ.get("TIPPY_HOME"):
        return Path(os.environ["TIPPY_HOME"])
    if not FROZEN:
        return ROOT
    portable = portable_dir(Path(sys.executable), sys.platform)
    # Portable mode is part of the "school" tier: the licence sits in the stick's own data folder.
    if portable and "portable" in licence.features(portable / "data"):
        return portable
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Tippy"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "Tippy"
    return Path.home() / ".local" / "share" / "tippy"


HOME_DIR = _home_dir()
DATA_DIR = HOME_DIR / "data"
LOG_DIR = HOME_DIR / "logs"
# The two overrides below exist for the automatic browser tests (own port, own copy of the frontend).
FRONTEND_DIR = Path(os.environ.get("TIPPY_FRONTEND_DIR", ROOT / "frontend"))
CONTENT_DIR = ROOT / "content"

HOST = "127.0.0.1"  # Never change this: it keeps the app private to this computer.
PORT = int(os.environ.get("TIPPY_PORT", "8765"))
# Free models (":free") from two providers, compared on Tippy's real tasks with
# scripts/try_models.py (2026-09-19): Nemotron was fastest and best in German; DeepSeek got
# the most English words and sentences through. Google's Gemma free models answered
# HTTP 429 (no capacity) at that time. Results change, so re-run the script now and then.
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_FALLBACK_MODEL = "deepseek/deepseek-v4-flash-0731:free"


def _to_int(text: str, default: int) -> int:
    try:
        return max(0, int(text))
    except ValueError:
        return default


def _read_env_file(path: Path) -> dict:
    """Read KEY=value lines. Ignores blank lines and lines starting with #."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_model: str
    openrouter_fallback_model: str
    app_language: str  # a code from backend/languages.py
    parent_pin: str
    llm_mode: str  # "off" (built-in content only), "mock" (fake LLM, for development) or "live"
    daily_request_cap: int  # most OpenRouter requests per day, so a bug can never run up a bill
    db_path: Path


def load_settings() -> Settings:
    """Environment variables win over the .env file, so tests can override."""
    file_values = _read_env_file(HOME_DIR / ".env")
    # backend/licence.py reads DEV_UNLOCK_ALL from the environment; this lets .env set it too (the environment wins).
    if "DEV_UNLOCK_ALL" in file_values:
        os.environ.setdefault("DEV_UNLOCK_ALL", file_values["DEV_UNLOCK_ALL"])

    def get(key: str, default: str = "") -> str:
        return os.environ.get(key, file_values.get(key, default))

    language = get("APP_LANGUAGE", "en").lower()
    if not languages.is_language(language):
        language = languages.DEFAULT
    mode = get("LLM_MODE", "off").lower()
    if mode == "openrouter":   # the name docs/REVAMP_BRIEF.md section 4.1 uses; "live" (older .env files) means the same
        mode = "live"
    if mode not in ("off", "mock", "live"):
        mode = "off"
    return Settings(
        openrouter_api_key=get("OPENROUTER_API_KEY"),
        openrouter_model=get("OPENROUTER_MODEL") or DEFAULT_MODEL,
        openrouter_fallback_model=get("OPENROUTER_FALLBACK_MODEL") or DEFAULT_FALLBACK_MODEL,
        app_language=language,
        parent_pin=get("PARENT_PIN"),  # empty = the parent chooses one on first start
        llm_mode=mode,
        daily_request_cap=_to_int(get("DAILY_REQUEST_CAP", "45"), 45),
        db_path=Path(get("TIPPY_DB_PATH", str(DATA_DIR / "tippy.db"))),
    )
