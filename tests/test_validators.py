from backend.validators import clean_line


def test_accepts_simple_line():
    assert clean_line("Great job, friend!") == "Great job, friend!"


def test_rejects_html_and_emoji():
    assert clean_line("<b>Hi</b>") is None
    assert clean_line("Hi 😀") is None


def test_rejects_too_long():
    assert clean_line("word " * 20) is None
    assert clean_line("a" * 200) is None


def test_rejects_blocklisted_word():
    assert clean_line("Tell me your password") is None


def test_rejects_non_strings_and_empty():
    assert clean_line(None) is None
    assert clean_line(42) is None
    assert clean_line("   ") is None


def test_german_umlauts_ok():
    assert clean_line("Schön gemacht!") == "Schön gemacht!"


# ---------- Batch checks for LLM output ----------
from backend.validators import clean_mascot_lines, clean_sentences, clean_words

ASDF = set("ASDF")


def test_words_only_allowed_letters_and_lengths():
    items = ["sad", "fad", "cat", "a", "saddest", "SAD", "s4d", "add", "<b>", "sad"]
    assert clean_words(items, ASDF) == ["sad", "fad", "add"]  # lowercased, deduped, letters checked


def test_words_reject_blocklist_and_non_lists():
    assert clean_words(["gun", "war"], set("GUNWAR")) == []
    assert clean_words("sad", ASDF) == []
    assert clean_words([1, None, {"a": 1}], ASDF) == []


def test_sentences_word_count_and_letters():
    allowed = set("ATHECS")
    good = clean_sentences(["The cat sat.", "Cat.", "The cat sat on the mat again today.", "The dog ran."], allowed)
    assert good == ["The cat sat."]


def test_mascot_lines_allow_one_child_placeholder_only():
    lines = ["Great job, {child}!", "Hi {child} and {child}!", "Nice {name}!", "<b>Hi</b>", "You did it!"]
    assert clean_mascot_lines(lines) == ["Great job, {child}!", "You did it!"]


def test_blocklist_is_per_language():
    assert clean_line("Die Katze schläft.", lang="de") == "Die Katze schläft."   # German "die" = "the"
    assert clean_line("Die Katze schläft.", lang="en") is None                     # English "die" is blocked
    assert clean_line("Die Katze schläft.") is None                                # unknown language: both lists
    assert clean_line("Wir mögen Krieg.", lang="de") is None


def test_rejects_web_addresses_but_not_normal_sentences():
    for bad in ("Visit www.example.com now.", "Go to shop.de today", "Look at tippy.app"):
        assert clean_line(bad) is None
    for good in ("I like cats. Cats like me.", "Hello, friend!", "It is 3.5 metres long."):
        assert clean_line(good) == good
