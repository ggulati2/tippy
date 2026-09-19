"""The words we send to the LLM.

Privacy rule: prompts are built only from coarse, non-personal facts (which
letters are unlocked, a theme like "animals", the language, a moment such as
"finished a game"). They never contain the child's name, age or anything about
the family. Where a name would be nice, the LLM is told to write "{child}" and
the browser fills that in locally.
"""

SYSTEM_PROMPT = (
    "You are Tippy, a kind, playful helper for a 6-year-old learning to use a computer. "
    "Use only very simple words and very short sentences. Be positive and patient; never criticise. "
    "Only talk about learning to type, using the computer, and gentle fun topics "
    "(animals, colours, space, dinosaurs, vehicles). "
    "Never ask for or mention names, addresses, schools, photos, passwords or any personal information. "
    "Never discuss violence, scary things, romance, medicine, politics, religion, "
    "or anything unsuitable for young children. "
    "When asked for JSON, return only valid JSON matching the requested schema, with no extra text."
)

LANGUAGE_NAMES = {"en": "English", "de": "German"}

MOMENTS = {
    "welcome": "the child just opened the app to play",
    "success": "the child just finished a game",
    "oops": "the child pressed a wrong key and needs a gentle, cheerful hint",
    "streak": "the child came back to play again",
}


def user_prompt(task: dict) -> str:
    kind = task["kind"]
    if kind == "ping":
        return 'Reply with exactly this JSON: {"ok": true}'
    language = LANGUAGE_NAMES.get(task.get("lang"), "English")
    if kind == "words":
        return (
            f"Give {task['count']} different simple {language} words for a child to type. "
            f"Each word has 2 to 4 letters and uses ONLY these letters: {' '.join(task['letters'])}. "
            f"Themes: {', '.join(task['themes'])}. Lowercase letters only, no spaces. "
            'Return JSON like {"words": ["cat", "sun"]}.'
        )
    if kind == "sentences":
        return (
            f"Give {task['count']} different very short {language} sentences of 3 to 6 words for a child to type. "
            f"Use ONLY these letters (ignoring spaces): {' '.join(task['letters'])}. "
            f"Themes: {', '.join(task['themes'])}. Simple words, one full stop or nothing at the end. "
            'Return JSON like {"sentences": ["The sun is hot."]}.'
        )
    if kind == "mascot":
        return (
            f"Give {task['count']} different warm encouragement lines in {language}, each at most 8 words, "
            f"for this moment: {MOMENTS.get(task['event'], MOMENTS['welcome'])}. "
            'You may use the placeholder {child} once for the child\'s first name; never invent a name. '
            'Return JSON like {"lines": ["Great job, {child}!"]}.'
        )
    raise ValueError(f"unknown task kind: {kind}")


def build_messages(task: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(task)}]
