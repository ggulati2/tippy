# Backport candidates

Genuine bugs found on this branch that also exist on `main`, each isolated in its own commit here so the owner can cherry-pick it into the original later. Nothing here is applied to `main` directly (see `docs/REVAMP_BRIEF.md` §1).

## The computer's own voice could be an online voice, and it says the child's name
- Commit: `4584cf8` on `revamp/erster-computer`
- Also present on `main` at: `tippy-v1-baseline`
- What goes wrong and how to see it: `pickVoice()` in `frontend/js/app.js` only preferred built-in voices
  (+2) and slightly disliked "Google" ones (-1), so an online voice named "Natural" or "Premium" (+8) could
  win, and with no match the browser's default voice (possibly online) was used. The child's name is always
  spoken by this system voice, never by a recording, so in Chrome with an online voice the name went to a
  speech server. Seen by listing `speechSynthesis.getVoices()` in Chrome: several have `localService: false`.
- Suggested fix (one line): keep only `v.localService` voices in `pickVoice()` and stay silent when none is found.

Format for each entry:

## <short title>
- Commit: `<hash>` on `revamp/erster-computer`
- Also present on `main` at: `tippy-v1-baseline` (or a later commit, if found after this tag)
- What goes wrong and how to see it:
- Suggested fix (one line):

## Text from the online helper could contain a web address
- Commit: `e08c986` on `revamp/erster-computer`
- Also present on `main` at: `tippy-v1-baseline`
- What goes wrong and how to see it: `clean_line()` in `backend/validators.py` allows letters, digits, spaces and
  simple punctuation, so `clean_line("Visit www.example.com now.")` returned the text unchanged. With the online helper
  on, an answer containing a web address could become typing material or an "Ask Tippy" answer. Links are never
  clickable (text is only ever added with textContent), but the brief rules out external links for children entirely.
- Suggested fix (one line): refuse text where a full stop is directly followed by a letter (regex `\.[^\W\d_]`).


## After an update the browser could keep showing the old screens
- Commit: `3123ae9` on `revamp/erster-computer`
- Also present on `main` at: `tippy-v1-baseline` (seen in the v0.14.0 release)
- What goes wrong and how to see it: app files (`/`, `js/*.js`, `css/*.css`) were sent without a
  `Cache-Control` header, so Chrome guessed how long its saved copy stays good and reused it without asking. Every
  Tippy version shares one browser profile (`~/Library/Caches/Tippy/…` on a Mac), so after running a newer build,
  opening the genuine 0.14.0 app still showed the newer screens until that cache was deleted by hand.
- Suggested fix (one line): in `protective_headers` in `backend/app.py`, send `Cache-Control: no-cache` for every path outside `/api/`.

## A typed sentence was cut off before it had been read aloud
- Commit: `ae11aaf` on `revamp/erster-computer`
- Also present on `main` at: `tippy-v1-baseline`
- What goes wrong and how to see it: after the last letter, `typingRound()` in `frontend/js/typing.js` starts reading
  the word or sentence aloud and moves to the next one after a fixed 1.8 s. A longer sentence in Sentence Street
  takes longer than that to say, so the next round (or the end of the level) cut it off. Seen by the owner.
- Suggested fix (one line): give `speak()` an `onEnd` callback and move on only after both it and the 1.8 s have passed (with a 20 s safety limit).
