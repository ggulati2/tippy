"""The single doorway to the LLM.

Milestone 1 only has the mock: it needs no internet and costs nothing.
Milestone 4 adds the real OpenRouter call behind the same function, with the
mock lines as the fallback. The rest of the app never needs to know which is used.

Privacy: only structured stats (event name, accuracy, streak) are ever passed
in here. Never pass the child's name or any personal detail.
"""
import random

from backend.validators import clean_line

# Short warm lines per event. The "{child}" placeholder is filled in by the
# browser, locally, so the name never travels anywhere.
_MOCK_LINES = {
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


def get_mascot_line(event: str, language: str = "en") -> str:
    """Return one short, safe line for the mascot to say."""
    lines = _MOCK_LINES.get(language, _MOCK_LINES["en"])
    candidates = lines.get(event, lines["welcome"])
    # Even our own lines pass through the validator: same rule for all text.
    safe = [line for line in candidates if clean_line(line.replace("{child}", "friend"))]
    return random.choice(safe or candidates)
