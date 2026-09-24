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

## Milestone 5 — Everyday-computer simulated-desktop tasks (complete, tagged `revamp-m5`)

Per the audit, Desktop Dock already had most of brief §6.2 built (open, sort into folders, rename, trash
and restore, save). The two missing pieces were added as two new levels, 6 and 7, rather than reworking
the existing five.

**What was built**

- **Level 6, picture-password log-in** (`deskLogin` in `frontend/js/desktop.js`): three pictures are shown
  as a hint row, then the child taps the same three pictures, in that order, out of a shuffled six-picture
  grid (the three correct plus three decoys). A wrong tap only wobbles the tile — nothing is lost, no
  penalty — matching every other level's "never punished" rule. This is the brief's "choose three pictures
  in order," which teaches that a password is a secret the child picks, not a lock that can be picked by
  trying every button.
- **Level 7, recognise and close a pop-up** (`deskPopup`): a fake "you've won a prize!" window opens with
  a large, enticing "Claim your prize!" button and a small red close X. Tapping the claim button does
  nothing but wobble (a deliberately undramatic non-reward, not a scary warning — brief §6.3's "keep the
  tone warm, not scary" applies here too even though this is §6.2, not §6.3 proper); the level only
  finishes once the child closes the window with the X.
- `backend/progress.py`'s `LEVEL_COUNTS["desktop"]` is now 7 (was 5); the existing level-2 ("Folder") and
  level-4 ("Save") stickers keep their positions, and the world medal now requires all 7 levels.

**A decision made on the user's behalf:** an early draft of level 7 opened the pop-up after a 900ms delay
with an extra "you are logged in, working on your computer..." framing line, and spoke a distinct warning
line when the child tapped the fake claim button. Both were cut — not for correctness but because they
pushed the running total of not-yet-voice-recorded text in `frontend/voice/es` two clips past the
project's existing 3% test threshold (`tests/test_voice.py`), a threshold that's about not letting real
speech coverage silently rot, not about hitting a number. Cutting the two least-essential lines (a scene-
setting line nobody needs to hear, and a scolding line that the wobble animation already communicates
without words) was the more conservative fix compared to lowering the test's threshold, which would have
weakened that check for everyone, not just this feature. The child does not lose anything: closing the
pop-up window is unaffected, only two spoken lines were removed. Voice recordings for the *new* spoken
lines that remain (the picture-password instruction, the "claim your prize" button, the "close this"
instruction) are not recorded yet in any language — same as milestones 3 and 4's new text — and fall back
to the browser's own synthesised voice until `scripts/make_voice_cloud.py` is next run (that script needs
the owner's own API key and is outside the scope of an unattended session).

**Test coverage**

- `tests/test_progress.py::test_desktop_dock_has_seven_levels_and_stickers` (replaces the old shared
  `[paint, desktop, internet, robot]` parametrised test for desktop specifically, since desktop no longer
  shares the same level count as the other three "everyday" worlds).
- `tests/browser/js/common.js`'s `T.actDesktop` gained a `login:` case that reads the still-needed secret
  sequence directly from `#screen`'s `data-need` attribute (the same "the page tells the test what it
  needs next" pattern every other Desktop Dock level already uses) and a first-wrong-tap check, mirroring
  the drag-and-drop mis-drop check elsewhere in the same file. The pop-up level needed no new test code:
  it reuses the existing `close` need, since closing a fake pop-up window is mechanically identical to
  closing the very first level's file window.
- `tests/browser/js/everyday.js` and `tests/browser/js/playthrough.js` (the two suites that machine-play
  every level of every world) had their hardcoded "5 levels" expectations for desktop updated to 7.
- Full suite: 278 unit/i18n tests and the full 21-test browser suite pass, including both new levels being
  played through automatically by the machine-playthrough tests exactly like a child would (with
  deliberate wrong taps along the way).

**What to test in the morning (Milestone 5)**

1. Open Desktop Dock: it should now show 7 levels instead of 5 (the picker's icon row grew a 🔑 and a 🪧).
2. Level 6 (🔑): three pictures appear at the top as a hint, then a grid of six below. Tap the same three
   pictures shown at the top, in the same order — a wrong tap should just wiggle, not end the level.
3. Level 7 (🪧): a pop-up window appears immediately with a big "Claim your prize!" button. Tapping it
   should do nothing but a little shake — the level only finishes when you close the window with the red X
   in the corner.
4. Both should award their stickers and count toward Desktop Dock's completion medal like any other level.

## Why the night's work stops here, before Milestone 6

Milestones 3, 4 and 5 are complete, tagged (`revamp-m3`, `revamp-m4`, `revamp-m5`), and pushed. `main` is
untouched. Two things came up while starting milestone 6 that are worth explaining rather than working
around silently.

**A stray, unexplained edit to `CLAUDE.md` was found and reverted, uncommitted.** While staging milestone
5's files, `git status` showed `CLAUDE.md` as modified, with four lines of generic-sounding "rules" text
appended to it that nobody in this session's own history wrote deliberately (most likely a stray write
from one of two earlier attempts at continuing this overnight run automatically — see below). It was never
committed or pushed. It has been reverted with `git restore CLAUDE.md`, and the file is back to exactly
its milestone-2 committed text. Flagging this explicitly because a file that states the rules for how this
branch is worked on should never change without it being an obvious, intentional, logged commit — the user
should know this happened even though nothing came of it.

**Milestone 6 (Safe & Smart, brief §6.3) was not started, for two compounding reasons:**

1. Checking the actual voice-recording coverage before writing any new spoken text
   (`tests/test_voice.py::test_nearly_everything_the_app_says_is_recorded`) showed Spanish is now at
   exactly its 3% budget (20 of 697 texts unrecorded) after milestones 3 to 5's new UI text — meaning
   **any further new spoken text, in any language, needs either new voice recordings or the test's
   threshold to move.** The app's own recordings were switched at some point from a free offline voice
   (Piper) to a paid cloud voice (OpenAI TTS, per `scripts/make_voice_cloud.py`) for a nicer, more
   consistent result — recorded in `docs/ADVANCED.md`'s git history, not this session's doing. Since that
   needs the owner's own API key and spends real money per run, generating new recordings is a decision
   for the owner to make, not something to do unattended overnight with an unknown key. (A Piper venv was
   set up and then deliberately not used, once this was discovered, specifically to avoid mixing two
   different-sounding voices into the same app.)
2. Even without that constraint, Safe & Smart's content (a stranger asking a child's name, a prize pop-up,
   someone asking for a password, when to ask a grown-up) is exactly the kind of thing that should not go
   out into even a test build without a human reading the literal words first. The mechanism (a two-choice
   picture story) already exists and works well elsewhere in the app (`chooseSteps` in `frontend/js/basics.js`,
   already covering similar ground in Computer Cove's existing "ask a grown-up" and "keep secrets" lessons);
   writing new instances of it is not the hard part. Writing genuinely good, warm, age-5-to-7-appropriate
   safety copy at the end of a long unattended session, with no way to read it back aloud or show it to a
   child, is a worse use of the remaining time than stopping here cleanly.

**Recommendation for the next session:** decide whether to (a) budget for a small OpenAI TTS voice run
first (the owner's call, since it costs real money and needs their key), (b) accept a temporarily wider
gap between "recorded" and "spoken" text and adjust `tests/test_voice.py`'s 3% threshold deliberately
(also the owner's call, since it's a real quality bar, not a rubber-stamp number), or (c) write milestone
6's story text together in a normal session rather than an unattended overnight one, given its content
sensitivity. Milestone 6 itself (brief §6.3) is otherwise unchanged and ready to pick up: a stranger asks
your name, a pop-up prize, someone asks for a password, when to ask a grown-up — each as a short,
two-choice interactive story, warm rather than scary, per the brief.
