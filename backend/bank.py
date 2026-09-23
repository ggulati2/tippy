"""The built-in content bank: safe words, sentences and mascot lines.

This is what the child gets when the internet or the LLM is unavailable, or
when the LLM's answer fails our checks. The app is fully usable with only this.
"""
import random
import re

from backend import languages, packs

THEMES = ("animals", "space", "dinosaurs", "vehicles")  # the only interests the parent can pick

# All of this used to be loose files under content/; it is now the "core-bank" content pack
# (content/packs/core-bank/, see backend/packs.py). The wording has not changed.
WORDS = packs.pack_file("core-bank", "words")          # {"en": {"animals": [...], ...}, "de": {...}}
SENTENCES = packs.pack_file("core-bank", "sentences")
FREE_PLAY = packs.pack_file("core-bank", "free_play")  # more word pictures, only for the Free Play Studio
ASK = packs.pack_file("core-bank", "ask")              # topics, questions, built-in answers for "Ask Tippy"
SPECIAL = packs.pack_file("core-bank", "special")      # {"de": {"culture_words": {"type": "words", "items": {...}}, ...}}: sets for one language only
PICTURES = packs.pack_file("core-bank", "pictures")    # {"en": {"cat": "🐱", ...}, "de": {...}} for Word Woods

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
    "es": {
        "welcome": ["¡Hola {child}! ¡A jugar!", "¡Hola {child}! ¡Te echaba de menos!", "¡Qué bien, ya estás aquí!"],
        "success": ["¡Muy bien, {child}!", "¡Lo conseguiste!", "¡Guau, qué bien escribes!"],
        "oops": ["¡Ups! Prueba con esta.", "¡Casi! Mira la tecla que brilla."],
        "streak": ["¡Has vuelto! ¡Hurra!", "¡Otro día feliz!"],
    },
}


ASK_REDIRECT = {"en": "That is a great question for a grown-up!", "de": "Das ist eine tolle Frage für einen Erwachsenen!",
                "es": "¡Esa es una gran pregunta para un adulto!"}


def letters_outside(text: str, allowed: set[str]) -> int:
    """How many different letters of `text` are not in the allowed set."""
    return len(languages.base_letters(text) - allowed)


QUESTIONS = "questions"   # question sentences: only used when a level asks for them


def word_count(text: str) -> int:
    return len(re.sub(r"[.,!?¡¿]", "", text).split())


def pick(pool: dict, lang: str, allowed: set[str], interests: list[str], count: int, exclude=(), only=None,
         themes=None, min_words: int = 0) -> list[str]:
    """Choose `count` items from a bank, using only the allowed letters where possible.

    `only` limits the choice to a given set (Word Woods uses it to get words that have a picture).
    `themes` limits it to those themes (a themed level); without it the "questions" theme is left out.
    `min_words` keeps only sentences with at least that many words (the longer-sentences level).
    Items that fit the letters come first, favouring the child's interests.
    If there are not enough (very early levels), we take the items that need
    the fewest extra letters, so the caller always gets something.
    """
    pool_themes = pool.get(lang) or pool["en"]
    liked = [t for t in interests if t in THEMES]
    wanted = set(themes) if themes else None
    items = [(text, theme) for theme, texts in pool_themes.items()
             if (theme in wanted if wanted else theme != QUESTIONS)
             for text in texts
             if text not in set(exclude) and (only is None or text in only) and word_count(text) >= min_words]
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
