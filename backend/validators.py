"""Checks for text that came from the LLM before the child may see it.

Rule from the project brief: nothing from the LLM reaches the child unchecked.
If a check fails, the caller silently uses local fallback content instead.
"""
import re

# Letters (including German umlauts), digits, spaces and simple punctuation only.
_ALLOWED = re.compile(r"^[A-Za-zÄÖÜäöüß0-9 .,!?'\-]+$")

# Words we never want to show a 6-year-old. Kept short here; extend it freely.
BLOCKLIST = {
    "kill", "dead", "die", "blood", "gun", "knife", "hate", "stupid", "dumb",
    "sex", "drug", "beer", "wine", "god", "war", "password", "address",
    "tot", "töten", "blut", "waffe", "messer", "hass", "dumm",
}


def clean_line(text, max_words: int = 12, max_chars: int = 80) -> str | None:
    """Return the text if it is safe to show, otherwise None."""
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())  # tidy up spaces and line breaks
    if not text or len(text) > max_chars or len(text.split()) > max_words:
        return None
    if not _ALLOWED.match(text):  # also rejects "<", ">" and emoji, so no HTML can sneak in
        return None
    words = re.findall(r"[a-zäöüß]+", text.lower())
    if any(word in BLOCKLIST for word in words):
        return None
    return text
