# Overnight build log — 2026-09-24

This is a running log of the overnight work on `revamp/erster-computer`, following the milestone plan
in `docs/REVAMP_BRIEF.md` §12 and the audit's migration plan in `docs/AUDIT.md` §8. It is updated as each
milestone is finished, so nothing is lost if the run is interrupted partway through. `main` is never
touched by any of this work.

## Milestone 3 — Keyboard layouts

**What was built**

- The three on-screen keyboard shapes (QWERTY, QWERTZ, QWERTY-with-Ñ) moved out of `frontend/js/keyboard.js`
  and into their own data files: `frontend/layouts/qwerty.json`, `qwertz.json`, `qwerty_es.json`. This is
  exactly what brief §4.4 asks for ("store the layout as data... so the on-screen keyboard, finger zones,
  and lessons all read from one source"). Editing a keyboard shape now means editing one of these three
  small JSON files, not hunting through JavaScript.
- Because the frontend has no build step and cannot `fetch()`/`import` a `.json` file as a script, a new
  generator, `scripts/sync_layouts.py`, turns those three files into `frontend/js/layouts-data.js` — the
  same pattern already used for `branding.json` → `frontend/js/config.js` (see `scripts/sync_branding.py`).
  `frontend/js/layouts-data.js` is a generated file (says so in its header) and is loaded by
  `frontend/index.html` just before `keyboard.js`. Run `python scripts/sync_layouts.py` after editing a
  layout file.
- **Layout mismatch detection** (brief §4.4, "detect likely layout mismatches... and gently suggest that
  the parent check the setting"): the German (QWERTZ) and US/UK (QWERTY) keyboards swap the physical Y and
  Z keys. `keyboard.js` now has `trackLayoutMismatch(e)`, called on every real key press during a game. It
  compares `e.code` (the physical key position, which does not change with layout) against `e.key` (the
  character the browser actually produced) for just the Y/Z pair. After five presses in a row that are
  consistent with the *other* keyboard shape, it calls a new endpoint, `POST /api/layout-mismatch`
  (no PIN needed — the child's screen calls it), which sets a `layout_mismatch_flag` setting. The child
  never sees anything about this: no popup, no interruption, no change to the game. The parent sees a
  calm amber note ("Keyboard shape may not match...") at the top of the Settings tab next time they open
  the parent area, with a "Got it" button that clears the flag (`saveSetting({ layout_mismatch_flag: false })`).
- Added the same three text keys (`layoutMismatchTitle/Text/Dismiss`) to all three languages
  (`frontend/js/i18n.js` for English/German, `frontend/js/i18n-es.js` for Spanish), and a small `.notice`
  CSS class (amber, not red — nothing is broken, this is just a heads-up).

**Test coverage added**

- `tests/test_layouts.py`: the generated `layouts-data.js` matches the source `.json` files (fails if
  someone edits the generated file by hand, or edits a layout file and forgets to re-run the generator);
  every keyboard `backend/languages.py` knows about has a layout file; every layout has the keys every
  lesson needs (Shift, Backspace, Space, Enter) with no key repeated; and a specific check that QWERTY and
  QWERTZ really do swap Y and Z in the expected screen positions (top-row / bottom-row), since
  `trackLayoutMismatch` depends on that being true.
- `tests/test_api.py::test_layout_mismatch_flag_set_by_child_cleared_by_parent`: the child-facing endpoint
  sets the flag without a PIN, the flag shows up in `/api/settings`, and only a PIN-holding parent can
  clear it (a request without the parent token is refused with 401, matching every other parent setting).
- Existing suite: `scripts/check.sh` (unit tests + i18n completeness) passes in full (276 tests). The
  browser end-to-end suite (`pytest -m browser`, the existing hand-rolled headless-Chrome harness — kept
  as-is per the user's explicit instruction not to introduce Playwright) was run against this change; see
  the "What to test in the morning" note below for the result, since it runs long.

**What was simplified or deferred, and why**

- The mismatch check only covers the Y/Z swap explicitly named in the brief. It does not attempt to
  detect umlaut-key mismatches (ä/ö/ü/ß on QWERTZ vs. their absence on QWERTY) or the Spanish Ñ, because
  there is no equivalent "this physical position types a different known letter" swap to check against —
  a missing key on the real keyboard just cannot be typed at all, which is a different (and much rarer)
  problem, not a location mismatch. This matches the brief's own example (the Z key) rather than
  overreaching.
- The mismatch flag is deliberately **not** carried through backup export/restore
  (`backend/restore.py`'s `IGNORED_SETTINGS`, alongside things like `weekly_summary` and `pin_hash`) —
  it is a transient "please check something" note, not data worth preserving across a backup, and
  restoring a stale flag onto a different install would be confusing rather than useful.
- No new SQLite column or migration was needed: `layout_mismatch_flag` is a new key in the existing
  generic `settings` table (see `backend/db.py`'s `DEFAULT_SETTINGS`), which already uses
  `INSERT OR IGNORE` for every key, so existing installs pick up the new setting automatically the next
  time they start, at its default value of off. This is simpler than the `ALTER TABLE` pattern and was
  not a judgment call — it is just how the existing generic-settings table already works.

**Decision made on the user's behalf:** none needed for this milestone; §4.4 is prescriptive enough
(QWERTZ default, layouts as data, mismatch detection on Y/Z) that no interpretation was required beyond
picking the five-press threshold, which is a reasonable middle ground between "false positive from one
stray key" and "never fires."

**What to test in the morning (Milestone 3)**

1. Open the app normally; nothing about the child's screens should look or feel different (this milestone
   only reorganised where keyboard *data* lives, plus added a background check).
2. Open the gear icon → parent PIN → **Settings tab**. "Keyboard shape" should still show the three
   choices (QWERTY, QWERTZ, QWERTY Ñ) and switching between them should still redraw the on-screen
   keyboard correctly in Keyboard Kingdom / Letter Land, same as before.
3. To see the new mismatch note: on a real QWERTY (US/UK) keyboard, go into a lesson with the app set to
   German (QWERTZ layout), and press the physical key that is labelled **Y** on your keyboard five times
   while a lesson is running (any lesson that accepts letter keys, e.g. Letter Land). Then open the parent
   area → Settings: you should see an amber box near the top saying "Keyboard shape may not match" with a
   "Got it" button. Click it — the box should disappear and stay gone until it happens again.
4. If your real keyboard already matches the layout you have selected, you should never see this box,
   however much you type — that is the "no false alarms" case and is the more important thing to confirm
   than the alarm itself.

---

## Milestone 4 — Curriculum stages (complete, tagged `revamp-m4`)

Per the audit's own breakdown (`docs/AUDIT.md`, migration-plan table, row 4), milestone 4 has four
distinct pieces: (a) group the 12 existing worlds into the brief's named stages, (b) an audit of
child-facing copy for leftover speed/WPM language, (c) a posture-reminder animation and gradually
shrinking Mouse Meadow targets, (d) the "up to eight family words" pack. This was originally committed
as a partial stop covering only (a) and (b) (see the note at the end of this section); the user then
asked to continue rather than wait, so (c) and (d) were finished and tested afterwards in the same
sitting, and the whole milestone is now tagged.

**A layout bug found by the user, fixed the same night:** the first cut of (a) put every stage on its own
full 4-column grid row. Most stages hold only 1-2 worlds, so short rows left large empty gaps next to
them — reported directly by the person testing it ("too much wastage of space"). Fixed by switching the
map from a fixed-width CSS grid to flex-wrapped rows that size themselves to their own content and
centre on screen, in `frontend/js/app.js` (`mapScreen()`, new `.stage-map`/`.stage-group`/`.stage-row`
markup) and `frontend/css/style.css`. There is a known follow-up: on a wide screen there is still empty
space on both sides of the (now correctly-sized) centred rows, which the user flagged as still not ideal
but asked to defer in favour of finishing the remaining milestones — noted here rather than silently
dropped.

**What was built (a, b)**

- The child's world map (`frontend/js/app.js`, `mapScreen()`) now groups the 12 existing worlds under
  seven stage headings that match brief §5's table exactly: Mouse Meadow, Keyboard Land, My Name, Word
  Woods, Everyday Computer, Safe & Smart, Create Studio — plus an "Extra: logic games" section at the end
  holding just Robot Helper, per the audit's accepted recommendation (it teaches sequencing, not typing,
  so it no longer pretends to be part of the Ten-Finger Path or the main stage sequence).
- No unlocking logic, world code, or level content changed at all — `backend/progress.py`'s
  `WORLD_ORDER`/`UNLOCK_AFTER` chain is untouched. This is a presentation/labelling layer only, which is
  why it was safe to build and verify in one sitting without touching the adaptive-difficulty or
  progress-tracking code the rest of the app depends on.
- Re-checked the whole codebase for WPM/speed language in the child-facing UI
  (`grep -rl "wpm\|WPM\|words per minute\|Wörter pro Minute"` across `frontend/` and `backend/`): there is
  none, and there never was — the audit had already confirmed this was a hard rule that held from the
  original build, so no copy changes were needed for (b).

**A decision made on the user's behalf (recorded per the brief's own §15 instruction to log judgment
calls rather than guess silently):**

- Where an existing world didn't map cleanly to one brief stage, I placed it where the content fits best,
  favouring the audit's own "closest stage" column:
  - **Sentence Sky → Stage 3 "My Name"**, not "between 4 and 7" as the audit phrased it — Sentence Sky
    already contains exactly the name/favourite-word content that stage 3 is about.
  - **Number Land → grouped with Stage 4 "Word Woods"**, since the brief doesn't mention numeracy at all
    (the audit flagged this as an open call) and Word Woods is the nearest existing "short, concrete,
    pre-reading literacy" stage for it to sit beside, consistent with the user's earlier decision to keep
    Number Land in scope rather than cut it.
  - **Computer Cove → grouped with Stage 6 "Safe & Smart"** alongside Internet Island, matching the
    audit's own "closest stage" column, since its safety-related lessons (online safety, "ask a grown-up")
    are its most stage-6-relevant content even though it also teaches general computer literacy.
  These are reversible UI groupings, not data migrations, so they can be freely rearranged later with no
  risk to saved progress.

**Test coverage**

- Added `stage.1`–`stage.7` and `stage.extras` text keys to all three languages (English, German,
  Spanish); `scripts/check_i18n.js` (part of `scripts/check.sh`) confirms all three stay in sync — full
  suite: 276 unit/i18n tests passing.
- No dedicated new unit test was needed for the grouping itself (it's a static data structure consumed by
  existing, already-tested rendering code), but the full **21-test browser suite was re-run end-to-end**
  after this change and passes, including the tests that open every world from the map, play levels, and
  drive the parent area's "unlock a world by hand" list (which also reads from the same world/icon table
  and needed a small matching update in `frontend/js/dashboard.js`).

**What was built (c): posture reminder and shrinking targets**

- A posture/hand reminder now appears once per time the app is opened, right after the child taps Play.
  It is a dismissible pop-up over the map (not a full screen of its own) — `maybeShowPostureReminder()`
  in `frontend/js/app.js` — spoken aloud, with an icon-only cue (🧍 ✋ 👀, no reading required, per the
  brief's non-readers rule) and a "I'm ready!" button. It also closes itself after 4 seconds either way,
  so a child who doesn't or can't tap it is never stuck. It was deliberately built as a pop-up rather
  than a screen: an earlier full-screen version broke several browser tests that assert the screen is
  "map" immediately after tapping Play (`tests/browser/js/who.js` in particular) — a pop-up keeps that
  assertion true while still showing the reminder every time.
- Mouse Meadow's first level (popping balloons) now shrinks the target gradually: five balloons per
  level, sized 150 → 132 → 114 → 96 → 80px (`SIZES` in `frontend/js/mouse.js`'s `levelPop`), matching
  brief §5's "large targets that shrink gradually" while staying well above the 64px minimum touch
  target used everywhere else in the app. The other three Mouse Meadow games (drag-and-drop,
  double-click, scroll) were left as-is: their targets are fixed shapes/counts, not a "click precisely"
  mechanic, so shrinking them isn't what the brief is describing and would have been a bigger,
  less-clearly-scoped change.

**What was built (d): the family-words pack**

- A parent can now enter up to 8 family words (Mama, Papa, Oma, a sibling or pet's name, ...) as one
  comma-separated line in Settings, next to the existing favourite-word field. Stored as a new
  `family_words` setting (same generic settings table as everything else, no schema change), validated
  the same way the favourite word already is (letters only, 15 characters each), capped at 8 words.
- Sentence Sky's fifth round (previously always the single favourite word, typed three times) now draws
  its three items from the favourite word plus the family words, cycling through them if there are fewer
  than three — so a parent who fills in family words sees them show up as real typing practice, exactly
  where the brief says the highest-motivation content should go. If no family words are set, the round
  behaves exactly as before (favourite word, or "fun"/"Spiel"/"juego" if that's empty too), so nothing
  changes for anyone who doesn't use the new field.
- The `family-words` content pack declared in milestone 2 stays a client-side-only, no-files pack exactly
  as documented then — this feature reads the setting directly rather than writing it to disk as pack
  content, since the pack's own manifest already says it's generated in the browser, never sent anywhere.

**Test coverage for (c) and (d)**

- `tests/test_api.py::test_family_words_is_validated_and_saved`: saving, reading back, rejecting more
  than 8 words, rejecting a non-letter word, and clearing the field.
- `tests/test_restore.py::test_family_words_is_restored_and_a_bad_one_is_ignored`: a valid list restores;
  an invalid one (too many words) is skipped while other valid settings in the same backup still apply.
- Full suite re-run after each change: 278 unit/i18n tests and the full 21-test browser suite both pass,
  including after the mouse-target and posture-reminder changes specifically (the posture reminder was
  the one most likely to break existing browser tests, and did on the first attempt — see above).

**What to test in the morning (Milestone 4, now complete)**

1. World map: grey stage headings group the 12 worlds ("1. Mouse Meadow" ... "7. Create Studio", then
   "Extra: logic games" holding just Robot Helper); rows are now centred and sized to their content
   rather than stretched across the screen (the space-wastage fix). There is still some empty margin on
   either side on a wide window — a known, deferred cosmetic point, not a bug.
2. Play Mouse Meadow's first game (popping balloons 🎈): each of the five balloons in a row should be a
   little smaller than the last.
3. Tap Play from the welcome screen: a pop-up with 🧍 ✋ 👀 and a spoken reminder to sit up straight
   should appear over the map, with an "I'm ready!" button; it should also disappear on its own after a
   few seconds if you don't tap anything. It should only appear once per time you open the app, not every
   time you go back to the map.
4. Parent area → Settings → below "Favourite word," a new "Family words" field: type e.g.
   "Mama, Papa, Oma" and save. Then play Sentence Sky's fifth level (💛): the child should be asked to
   type words drawn from that list (and the favourite word), not just the favourite word three times.

## Status and what is next

Milestones 3 and 4 are both complete, tagged (`revamp-m3`, `revamp-m4`), and pushed. `main` is untouched.
The next milestone is **5: everyday-computer simulated-desktop tasks** (brief §6.2) — the audit notes
Desktop Dock already has most of the sandboxed-desktop mechanics built; what's missing is a
picture-password "log in" task and a pop-up-recognition task.
