"""Checks for text that came from the LLM before the child may see it.

Rule from the project brief: nothing from the LLM reaches the child unchecked.
If a check fails, the caller silently uses local fallback content instead.
"""
import re

# Letters (including German umlauts), digits, spaces and simple punctuation only.
_ALLOWED = re.compile(r"^[A-Za-zÄÖÜäöüß0-9 .,!?'\-]+$")

# Words we never want to show a 6-year-old. Kept short here; extend it freely.
# One list per language, because a harmless word in one language can be a bad
# word in the other (German "die" is just "the"). Without a language we check both.
BLOCKLISTS = {
    "en": {"kill", "dead", "die", "blood", "gun", "knife", "hate", "stupid", "dumb", "sex", "drug", "beer", "wine",
           "god", "war", "password", "address"},
    "de": {"tot", "töten", "blut", "waffe", "messer", "hass", "dumm", "sex", "droge", "bier", "wein", "krieg",
           "passwort", "adresse"},
}
BLOCKLIST = BLOCKLISTS["en"] | BLOCKLISTS["de"]


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
    words = re.findall(r"[a-zäöüß]+", text.lower())
    if any(word in _blocked(lang) for word in words):
        return None
    return text


# ---------- Checks for whole batches from the LLM ----------

_WORD = re.compile(r"^[a-z]+$")
PLACEHOLDER = "{child}"


def clean_words(items, allowed_letters: set[str], lang: str | None = None, min_len: int = 2, max_len: int = 4) -> list[str]:
    """Keep only words that are lowercase letters, the right length, use only
    the letters the child has unlocked, and are not on the blocklist."""
    good: list[str] = []
    for item in items if isinstance(items, list) else []:
        word = item.strip().lower() if isinstance(item, str) else ""
        if not (_WORD.match(word) and min_len <= len(word) <= max_len):
            continue
        if word in _blocked(lang) or {c.upper() for c in word} - allowed_letters:
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
        if {c.upper() for c in line if c.isalpha()} - allowed_letters:
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
