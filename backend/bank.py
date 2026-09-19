"""The built-in content bank: safe words, sentences and mascot lines.

This is what the child gets when the internet or the LLM is unavailable, or
when the LLM's answer fails our checks. The app is fully usable with only this.
"""
import json
import random

from backend.config import CONTENT_DIR

THEMES = ("animals", "space", "dinosaurs", "vehicles")  # the only interests the parent can pick


def _load(name: str) -> dict:
    return json.loads((CONTENT_DIR / name).read_text(encoding="utf-8"))


WORDS = _load("fallback_words.json")          # {"en": {"animals": [...], ...}, "de": {...}}
SENTENCES = _load("fallback_sentences.json")

# Short warm lines per moment. "{child}" is replaced by the browser with the
# child's name, so the name never leaves this computer.
MASCOT_LINES = {
    "en": {
        "welcome": ["Hi {child}! Let's play!", "Hello {child}! I missed you!", "Yay, you are here!"],
        "success": ["Great job, {child}!", "You did it!", "Wow, super typing!"],
        "oops": ["Oops! Try this one.", "Almost! Look at the glowing key."],
        "streak": ["You came back again! Hooray!", "Another happy day!"],
    },
    "de": {
        "welcome": ["Hallo {child}! Los geht's!", "Hallo {child}! Schön, dass du da bist!", "Juhu, du bist da!"],
        "success": ["Toll gemacht, {child}!", "Du hast es geschafft!", "Wow, super getippt!"],
        "oops": ["Huch! Probier diese Taste.", "Fast! Schau auf die leuchtende Taste."],
        "streak": ["Du bist wieder da! Hurra!", "Wieder ein schöner Tag!"],
    },
}


def letters_outside(text: str, allowed: set[str]) -> int:
    """How many different letters of `text` are not in the allowed set."""
    return len({c.upper() for c in text if c.isalpha()} - allowed)


def pick(pool: dict, lang: str, allowed: set[str], interests: list[str], count: int, exclude=()) -> list[str]:
    """Choose `count` items from a bank, using only the allowed letters where possible.

    Items that fit the letters come first, favouring the child's interests.
    If there are not enough (very early levels), we take the items that need
    the fewest extra letters, so the caller always gets something.
    """
    themes = pool.get(lang) or pool["en"]
    liked = [t for t in interests if t in THEMES]
    items = [(text, theme) for theme, texts in themes.items() for text in texts if text not in set(exclude)]
    fitting = [(text, theme) for text, theme in items if letters_outside(text, allowed) == 0]
    random.shuffle(fitting)
    fitting.sort(key=lambda x: x[1] not in liked and x[1] != "general")  # liked themes first (stable sort)
    chosen = [text for text, _ in fitting[:count]]
    if len(chosen) < count:
        rest = [x for x in items if x[0] not in chosen and letters_outside(x[0], allowed) > 0]
        random.shuffle(rest)
        rest.sort(key=lambda x: letters_outside(x[0], allowed))
        chosen += [text for text, _ in rest[: count - len(chosen)]]
    return chosen


def local_mascot_line(lang: str, event: str) -> str:
    lines = MASCOT_LINES.get(lang, MASCOT_LINES["en"])
    return random.choice(lines.get(event, lines["welcome"]))
