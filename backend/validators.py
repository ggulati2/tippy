"""Checks for text that came from the LLM before the child may see it.

Rule from the project brief: nothing from the LLM reaches the child unchecked.
If a check fails, the caller silently uses local fallback content instead.
"""
import re

from backend import languages

# Letters (with the accents of the supported languages), digits, spaces and simple punctuation only.
_ALLOWED = re.compile(r"^[" + languages.LETTERS + r"0-9 .,!?¡¿'\-]+$")

# A web address ("www.example.com", "shop.de"): the allowed characters above let one through otherwise. An e-mail
# address is already refused, because "@" is not allowed.
_WEB_ADDRESS = re.compile(r"\.[^\W\d_]")

# Words we never want to show a 6-year-old. Kept short here; extend it freely.
# One list per language, because a harmless word in one language can be a bad
# word in the other (German "die" is just "the"). Without a language we check both.
BLOCKLISTS = {
    "en": {"kill", "dead", "die", "blood", "gun", "knife", "hate", "stupid", "dumb", "sex", "drug", "beer", "wine",
           "god", "war", "password", "address"},
    "de": {"tot", "töten", "blut", "waffe", "messer", "hass", "dumm", "sex", "droge", "bier", "wein", "krieg",
           "passwort", "adresse"},
    "es": {"matar", "muerto", "muerte", "sangre", "arma", "pistola", "cuchillo", "odio", "tonto", "estúpido", "idiota", "sexo",
           "droga", "cerveza", "vino", "guerra", "dios", "contraseña", "dirección", "mierda", "puta", "culo", "joder", "coño"},
}
BLOCKLIST = BLOCKLISTS["en"] | BLOCKLISTS["de"] | BLOCKLISTS["es"]


def _blocked(lang: str | None) -> set[str]:
    return BLOCKLISTS.get(lang, BLOCKLIST)


def clean_line(text, max_words: int = 12, max_chars: int = 80, lang: str | None = None) -> str | None:
    """Return the text if it is safe to show, otherwise None."""
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())  # tidy up spaces and line breaks
    if not text or len(text) > max_chars or len(text.split()) > max_words:
        return None
    if not _ALLOWED.match(text):  # also rejects "<", ">" and emoji, so no HTML can sneak in
        return None
    if _WEB_ADDRESS.search(text):  # "www.example.com": a full stop right before a letter never happens in a child's sentence
        return None
    words = re.findall(r"[a-zäöüßñáéíóú]+", text.lower())
    if any(word in _blocked(lang) for word in words):
        return None
    return text


# ---------- Checks for whole batches from the LLM ----------

_WORD = re.compile(r"^[a-zäöüßñáéíóú]+$")
PLACEHOLDER = "{child}"


def clean_words(items, allowed_letters: set[str], lang: str | None = None, min_len: int = 2, max_len: int = 4) -> list[str]:
    """Keep only words that are lowercase letters, the right length, use only
    the letters the child has unlocked, and are not on the blocklist."""
    good: list[str] = []
    for item in items if isinstance(items, list) else []:
        word = item.strip().lower() if isinstance(item, str) else ""
        if not (_WORD.match(word) and min_len <= len(word) <= max_len):
            continue
        if word in _blocked(lang) or languages.base_letters(word) - allowed_letters:
            continue
        if word not in good:
            good.append(word)
    return good


def clean_sentences(items, allowed_letters: set[str], lang: str | None = None) -> list[str]:
    """Sentences of 3 to 6 simple words, using only allowed letters."""
    good: list[str] = []
    for item in items if isinstance(items, list) else []:
        line = clean_line(item, max_words=6, max_chars=60, lang=lang)
        if not line or len(line.split()) < 3:
            continue
        if languages.base_letters(line) - allowed_letters:
            continue
        if line not in good:
            good.append(line)
    return good


def clean_mascot_lines(items, lang: str | None = None) -> list[str]:
    """Short friendly lines. One "{child}" placeholder is allowed; nothing else
    with curly brackets. The browser fills the placeholder in locally."""
    good: list[str] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, str) or item.count(PLACEHOLDER) > 1:
            continue
        line = clean_line(item.replace(PLACEHOLDER, "Friend"), max_words=12, max_chars=80, lang=lang)
        if line and item.strip() not in good:
            good.append(" ".join(item.split()))
    return good


# ---------- Ask Tippy answers and the parent summary ----------

_PARAGRAPH = re.compile(r"^[" + languages.LETTERS + r"0-9 .,!?¡¿'’\-:;()%/&]+$")


def clean_paragraph(text, max_chars: int = 500) -> str | None:
    """A short paragraph for the parent (never shown to the child)."""
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())
    if not 10 <= len(text) <= max_chars or not _PARAGRAPH.match(text):
        return None
    return text


def clean_answers(items, lang: str | None = None) -> list[str]:
    """Answers for a child: at most 3 short sentences, safe characters, no blocklisted words."""
    good: list[str] = []
    for item in items if isinstance(items, list) else []:
        text = " ".join(item.split()) if isinstance(item, str) else ""
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
        if not text or len(sentences) > 3 or any(len(s.split()) > 14 for s in sentences):
            continue
        if clean_line(text, max_words=42, max_chars=220, lang=lang) and text not in good:
            good.append(text)
    return good
