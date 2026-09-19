"""Settings loaded from the `.env` file in the project root.

We read `.env` with a tiny parser instead of adding a dependency.
The OpenRouter key is read here, on the backend only. It is never sent to the browser.
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
FRONTEND_DIR = ROOT / "frontend"
CONTENT_DIR = ROOT / "content"

HOST = "127.0.0.1"  # Never change this: it keeps the app private to this computer.
PORT = 8765


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
    app_language: str  # "en" or "de"
    parent_pin: str
    llm_mode: str  # "mock" (no network, no cost) or "live"
    db_path: Path


def load_settings() -> Settings:
    """Environment variables win over the .env file, so tests can override."""
    file_values = _read_env_file(ROOT / ".env")

    def get(key: str, default: str = "") -> str:
        return os.environ.get(key, file_values.get(key, default))

    language = get("APP_LANGUAGE", "en").lower()
    if language not in ("en", "de"):
        language = "en"
    mode = get("LLM_MODE", "mock").lower()
    if mode not in ("mock", "live"):
        mode = "mock"
    return Settings(
        openrouter_api_key=get("OPENROUTER_API_KEY"),
        openrouter_model=get("OPENROUTER_MODEL"),
        openrouter_fallback_model=get("OPENROUTER_FALLBACK_MODEL"),
        app_language=language,
        parent_pin=get("PARENT_PIN", "1234"),
        llm_mode=mode,
        db_path=Path(get("TIPPY_DB_PATH", str(DATA_DIR / "tippy.db"))),
    )
