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
