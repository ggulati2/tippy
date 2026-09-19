"""Compare OpenRouter models on Tippy's real tasks, using YOUR key.

    source .venv/bin/activate
    python scripts/try_models.py                      # tries the built-in shortlist
    python scripts/try_models.py some/model:free ...  # or models you name

For every model it asks for English words, English sentences, English mascot lines
and German words (one request each), then runs the answers through Tippy's own
safety checks. Read the table like this:
  good/asked  how many items passed our checks (higher is better)
  seconds     how long the answer took (lower is better, under 8 is needed)
The best model is the one with mostly "ok" rows and small seconds.
Uses 4 requests per model. Free accounts are limited to 50 requests a day.
"""
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db, difficulty  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.content import ContentService  # noqa: E402
from backend.llm import prompts  # noqa: E402
from backend.llm.client import LLMClient  # noqa: E402

SHORTLIST = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "deepseek/deepseek-v4-flash-0731:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
]

LETTERS = difficulty.letters_for(12)
TASKS = [
    ("words (en)", "words", {"lang": "en", "letters": LETTERS, "themes": ["animals", "space"], "count": 20}),
    ("sentences (en)", "sentences", {"lang": "en", "letters": LETTERS, "themes": ["animals", "vehicles"], "count": 10}),
    ("mascot (en)", "mascot", {"lang": "en", "event": "success", "count": 8}),
    ("words (de)", "words", {"lang": "de", "letters": difficulty.letters_for(20), "themes": ["animals", "dinosaurs"], "count": 20}),
]


def main() -> None:
    settings = load_settings()
    if not settings.openrouter_api_key:
        sys.exit("Put your key in .env first (OPENROUTER_API_KEY=sk-or-...). See README.md.")
    models = sys.argv[1:] or SHORTLIST
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "try.db"
        db.init_db(db_path)
        print(f"{'model':42} {'task':16} {'seconds':>7}  {'good/asked':>10}  result")
        for model in models:
            test_settings = replace(settings, llm_mode="live", openrouter_model=model, db_path=db_path, daily_request_cap=1000)
            client = LLMClient(test_settings)
            service = ContentService(db_path, client, background=False)
            for label, kind, params in TASKS:
                task = {"kind": kind, **params}
                started = time.monotonic()
                text, _fatal = client._try(model, prompts.build_messages(task))
                seconds = time.monotonic() - started
                good = service._validate(kind, text, params) if text else []
                if text is None:
                    result = f"FAILED ({client.last_error})"
                elif not good:
                    result = "rejected by safety checks"
                else:
                    result = "ok" if seconds <= 8 else "ok but slow"
                print(f"{model:42} {label:16} {seconds:7.1f}  {len(good):>4}/{params['count']:<5}  {result}")
                time.sleep(3)  # stay well under 20 requests a minute


if __name__ == "__main__":
    main()
