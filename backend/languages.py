"""The languages Tippy speaks, in one place.

Adding a language is mostly data: an entry here, a block of screen text in frontend/js/i18n-<code>.js,
the built-in content (words, sentences, pictures... in content/*.json), the mascot lines in
backend/bank.py, a word blocklist in backend/validators.py and a summary template in dashboard.py.
The checks in scripts/check.sh and tests/test_languages.py fail if a language is missing something.
"""
import unicodedata

LANGUAGES = {
    # code: native name, voice for speech synthesis, name used in prompts to the online helper, default keyboard
    "en": {"native": "English", "voice": "en-US", "prompt_name": "English", "keyboard": "qwerty"},
    "de": {"native": "Deutsch", "voice": "de-DE", "prompt_name": "German", "keyboard": "qwertz"},
    "es": {"native": "Español", "voice": "es-ES", "prompt_name": "Spanish (as spoken in Spain)", "keyboard": "qwerty_es"},
}

# On-screen keyboard shapes. The letters are the same except for the extra keys of each language.
KEYBOARDS = ("qwerty", "qwertz", "qwerty_es")

CODES = tuple(LANGUAGES)
DEFAULT = "en"

# Regular expressions for validating request fields.
LANGUAGE_PATTERN = "^(" + "|".join(CODES) + ")$"
KEYBOARD_PATTERN = "^(" + "|".join(KEYBOARDS) + ")$"


def is_language(code) -> bool:
    return code in LANGUAGES


def default_keyboard(code: str) -> str:
    return LANGUAGES.get(code, LANGUAGES[DEFAULT])["keyboard"]


def public_list() -> list[dict]:
    """What the browser needs to build language pickers and choose a voice."""
    return [{"code": code, "native": info["native"], "voice": info["voice"], "keyboard": info["keyboard"]}
            for code, info in LANGUAGES.items()]


def base_letters(text: str) -> set[str]:
    """The plain A-Z letters a text needs, ignoring accents: "camión" needs C, A, M, I, O, N ("ñ" counts as N,
    "ß" as S). The letters unlock in a fixed order, so an accented letter counts as its plain letter."""
    letters = set()
    for char in text:
        if char == "ß":
            letters.add("S")
        elif char.isalpha():
            plain = "".join(c for c in unicodedata.normalize("NFD", char) if not unicodedata.combining(c))
            letters.add(plain.upper())
    return letters


# Every letter any supported language uses (upper and lower case), for validating text and typed words.
LETTERS = "A-Za-zÄÖÜäöüßÑñÁÉÍÓÚáéíóúÜü"
