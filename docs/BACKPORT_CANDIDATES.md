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
