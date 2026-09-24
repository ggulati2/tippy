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

---

## Milestone 6 — Safe & Smart (complete, tagged `revamp-m6`)

The two blockers above were resolved directly by the user once they were up: they authorised using their
own OpenAI key (confirmed credit was available) for the voice recordings, and then said to go ahead and
build the milestone. Both are recorded here for the same reason as everything else in this log — so
nothing that happened is silent.

**What was built**

- Three new bonus levels in Computer Cove (`frontend/js/basics.js`), levels 17-19, each a single
  two-choice picture story using the same `chooseSteps` engine every other lesson in this world already
  uses (a wrong tap only wobbles and points at the right answer — nothing here can be "failed"):
  - **17, a stranger asks your name** (🕵️): the safe choice is to tell a grown-up, not answer directly.
  - **18, a pop-up says you've won a prize** (🎉): the safe choice is to tell a grown-up, not tap it.
  - **19, someone asks for your password** (🔑): the safe choice is to keep it secret, not tell them.
- **"When to ask a grown-up," the brief's fourth named topic, was deliberately not built as a fourth new
  level.** Computer Cove's existing level 5 (`lessonAsk`) already teaches exactly that, with three
  scenarios of its own (a prize, a link, a download) — adding a near-duplicate would pad the world without
  teaching anything new. The three new levels reuse "ask/tell a grown-up" as the answer for two of their
  three own scenarios anyway, so the message repeats without a fourth copy of the same lesson.
- A new sticker, "Wise owl" 🦉, awarded on completing the last of the three (level 19), following the same
  pattern as every other world's bonus track.
- `backend/progress.py`'s `BONUS_LEVELS["basics"]` is now 13 (was 10); `frontend/js/rewards.js`'s `BONUS.basics`
  gained the three new icons. None of the three are German-only, so every language sees all three.

**Content note, for the record:** the story prompts are deliberately plain and concrete rather than
dramatic ("Someone you don't know online asks: what is your name? What do you do?"), and every "fact" line
after the correct choice explains *why* in one short, positive sentence, never a warning about what could
go wrong. This follows the brief's own "keep the tone warm, not scary" instruction literally. This is a
judgment call about tone and wording made without a second read from the person who asked for it, since
this was still an unattended step even though the go-ahead was explicit — worth the user actually reading
the six new lines (`ss.stranger`, `ss.prize`, `ss.password` and their `.fact` counterparts, in
`frontend/js/i18n.js` and `frontend/js/i18n-es.js`) before considering this content final, especially the
German and Spanish wording, which (per the audit, still true) has never been checked by a native-speaking
teacher.

**Voice:** all six new lines were recorded in English, German and Spanish with the user's own OpenAI key
(`scripts/make_voice_cloud.py --lang <en|de|es> --voice coral`, same voice and settings as every existing
recording), at a real cost of about $0.01 per language. The same run also caught up the 20 outstanding
clips per language left over from milestones 3-5, so voice coverage is now current everywhere, not just
for this milestone.

**Test coverage**

- `tests/test_progress.py::test_bonus_levels_are_accepted_up_to_the_last_one_and_award_their_stickers`:
  the `basics` entry's "last level" moved from 16 to 19, and a new assertion checks the "owl" sticker is
  awarded at the new last level.
- `tests/browser/js/germany.js`: the hardcoded expected lesson counts moved from 14/16 to 17/19
  (non-German/German), since the three new levels are not German-only and both counts grow by 3.
- `tests/browser/js/playthrough.js` needed **no changes**: it computes each world's expected level count
  from the live `bonusLevels()` function rather than a hardcoded number, so it automatically picked up
  and played all three new levels (with deliberate wrong taps) the moment they existed.
- Full suite: 278 unit/i18n tests, all 9 voice tests, and the full 21-test browser suite pass.

**What to test in the morning (Milestone 6) — please actually read the words, not just click through**

1. Open Computer Cove (🐚), scroll to the bonus levels (past the "✨ Bonus" divider): three new icons
   should appear at the end — 🕵️, 🎉, 🔑 — after the existing weather umbrella ☔.
2. Play through all three. Each is one screen with two big picture choices; picking the safe one (🙋 or
   🤐, always the correct answer) should complete the level, and picking the other should just wobble and
   point at the right one, never end the story badly.
3. Listen to the spoken lines in at least English and German (switch language in parent Settings) and
   judge the tone for yourself — the goal was warm and matter-of-fact, never scary.
4. Completing level 19 should award a new "Wise owl" 🦉 sticker, visible in the sticker album.

## A note on milestone numbers (tags vs. the brief)

The brief's §12 bundles "Everyday Computer **and** Safe & Smart" into one milestone (its number 5). They were
built and tagged separately here (`revamp-m5` desktop tasks, `revamp-m6` Safe & Smart), so from this point the
tag numbers run one ahead of the brief's. Pushed tags are not renamed; this is the mapping:

| Tag | Brief §12 milestone |
|---|---|
| `revamp-m1` ... `revamp-m4` | 1 ... 4 |
| `revamp-m5` + `revamp-m6` | 5. Everyday Computer and Safe & Smart |
| `revamp-m7` | 6. Create Studio and optional Ten-Finger Path |
| `revamp-m8` onwards | 7 onwards (always the brief's number + 1) |

## Brief milestone 6 — Create Studio and optional Ten-Finger Path (tagged `revamp-m7`)

**Create Studio: save a scene as a card and open it again.** Free Play gained two buttons: 💾 saves the scene
on the canvas as a "card", 🖼️ opens a list of saved cards, and tapping one draws that scene again. Only the typed
words are stored (a new `cards` table in the child's own database, newest 12 kept; a new card makes room rather
than being refused). Cards are part of the parent's backup (export), a restore brings them back (checked like
every other restored row: letters and spaces only, at most 14 characters), and "reset progress" clears them.
Nothing about a card ever leaves the computer.

*Decision made on the user's behalf:* the brief's stage 7 says "draw, type a caption, make a card, save and
reopen it." Drawing already exists in Paint Place and typing-into-a-scene in Free Play; the two were **not**
merged into one combined draw-plus-caption editor. Saving and reopening was the part genuinely missing, and it
now exists; merging two working worlds would have been a much larger, riskier change for the same goal.

**Ten-Finger Path** (`frontend/js/tenfinger.js`, world id `tenfinger`): five short levels using the existing
typing engine and the on-screen keyboard's finger colours — the two keys with a bump (F, J), left hand (A S D F),
right hand (J K L), both hands plus the reach to G and H, then real words made only of home-row letters
(English "dad, sad, all, fall, glad"; German "das, als, Glas, Hals, Saal"; Spanish "sala, hada, falda, salsa,
gala"). It is **locked by default and never opens by playing**: `PARENT_ONLY` in `backend/progress.py` means
only a parent opening it (by hand in Settings, or with "unlock all") makes it available, exactly as the brief
asks. It sits on the map under a new "Optional: for age 7 and up" heading, and finishing it earns a 🎹 sticker.

**Tests:** new unit tests for cards (save, list, 12-card cap, validation, export, reset), for restoring cards
(a bad one is skipped), and for the Ten-Finger Path (stays locked after finishing every other world; opens by
parent; opens with "unlock all"; awards its sticker). The browser playthrough now plays all five Ten-Finger
levels in English, German and Spanish, and saves a card, opens the list, and reopens it. One bug was in the
test itself (a reused variable name) and was fixed before anything was committed. 282 unit/i18n tests, 9 voice
tests, and 21 browser tests pass; the 13 new spoken lines were recorded in all three languages.

**What to test:** in Free Play, make a scene, tap 💾, then 🖼️ and tap the saved card. In the parent area's
Settings, open the Ten-Finger Path (🖐️) by hand and play a level; before that, it should show as locked on the map.

## A privacy bug found on the way (also on `main`)

While writing the privacy page, checking what the computer's own voice does showed that it could be an
**online** voice: `pickVoice()` only slightly preferred voices built into the computer, so a Chrome online voice
named "Natural" could win, and with no match the browser's default voice (possibly online) was used. The
system voice is what says the child's name, so the name could reach a speech server. Fixed in its own commit
(`fix: never use an online voice for the computer's own speech`): only built-in voices are used, and with none
for the language Tippy stays silent for that sentence (the recordings still play). Listed in
`docs/BACKPORT_CANDIDATES.md`; `main` is untouched, per brief §1.5.

## Brief milestone 7 — Parent area upgrades (tagged `revamp-m8`)

Already there before this milestone: template weekly report, session length and daily limit, backup (export),
reset, removing a child. Added:

- **Allowed play hours** (Settings → "Play only between": off, 7–19, 8–18, 9–17, 14–19). Outside them Tippy shows
  the same calm goodnight screen as the daily limit. *Decision:* a few fixed windows rather than free
  from/until pickers, to keep the Settings tab as simple as the other rows; easy to add more.
- **Own word list** (Settings → "Own word list", up to 20 words, letters only, like any word in a pack). Once set,
  Word Woods shows an extra 📝 level with those words. *Decision:* kept in the child's settings (so it is in
  backups and per child) rather than as a separate pack folder on disk; it is validated with the same rules.
- **Deletions ask for the PIN again:** reset progress, remove a child, and a new **Delete everything** (Data tab).
  A wrong PIN changes nothing. "Delete everything" erases every child, every kept-aside copy and the PIN, and Tippy
  starts again with the first-run setup.
  *Tradeoff to know about:* removing a single child still keeps that child's file aside (renamed), as it did before,
  in case it was a mistake. The privacy page says so, and "Delete everything" removes those files too.
- **Printables** (Progress tab → 🖨️ Print): a certificate for every finished stage (child's name, stage, date,
  mascot) and a keyboard to colour in, drawn for the child's own keyboard shape. Both use the browser's print
  dialog, which can also save a PDF. Checked visually (German certificate and QWERTZ sheet).
- **`docs/PRIVACY.md`** (German and English, plain language: what is stored, where, what leaves the computer, how to
  delete) and a **Datenschutz** tab showing the same text, generated by `scripts/sync_privacy.py` and kept in step by
  `tests/test_privacy.py` (same pattern as `branding.json`).

**Tests:** unit tests for the PIN re-entry (reset, remove child, delete everything, wrong PIN), delete everything
starting fresh, play window and word list validation, the play-window hours, and the privacy text. Browser tests
now type the PIN when resetting or removing a child, check a wrong PIN deletes nothing (the parent test first
earns a sticker, so "reset clears stickers" is no longer true by default), open the Datenschutz tab, print the
keyboard sheet, show the goodnight screen outside the play hours, and play the new own-word-list level in three
languages. 287 unit/i18n tests, 9 voice tests and 21 browser tests pass; new lines recorded in all languages.

**What to test:** Settings → set a play window that excludes now, go back to the child's screen (goodnight);
Settings → own word list "Haus, Baum" → Word Woods shows 📝; Data → reset with a wrong PIN, then the right one;
Progress → print a certificate; the Datenschutz tab.

## Brief milestone 8 — Classroom mode and portable mode (tagged `revamp-m9`)

- **Teacher setup:** the first-run wizard now asks "At home / In a classroom" after the language. A classroom gets a
  *teacher* PIN, a class size (10–30) and an optional "start fresh every day", and opens on "who is playing?".
- **Anonymous by default:** children in a class have only a picture (30 different animal pictures now, the first 12
  unchanged so saved children keep theirs); a nickname is optional. The picker drops the "Player" label for them and
  switches to a compact 6-column grid for big classes (checked visually with 30).
- **Up to 30 children** in classroom mode (6 at home); "Add 5 children" in the Children tab; switching back to home
  mode is refused while there are more than 6 children.
- **Daily reset:** the first start (or first child picked) of a new day resets every child's progress.
- **Class overview** in the Children tab: every child against the 7 stages (✓ when a stage is done) plus stars, and a
  CSV download. The CSV quotes every cell and neutralises a leading `= + - @` so no cell can run as a spreadsheet formula.
- **Portable mode:** a folder called `tippy-data` next to the program (next to `Tippy.app` on a Mac) makes Tippy keep
  everything there, for USB sticks. Documented in `docs/ADVANCED.md`.
- In classroom mode the parent area is titled "Teacher area" / "Lehrerbereich".

**A regression of my own, fixed:** `scripts/fetch_emoji.py` still scanned `content/*.json`, but milestone 2 moved those
files into `content/packs/`. Running it would have found none of the content emoji and deleted their pictures. It now
scans recursively; rerunning it added 7 new pictures and removed none. Branch-only (not on `main`).

**Tests:** unit tests for classroom setup (25 anonymous children, distinct pictures, the cap of 30, refusing home mode
with too many), home setup, the class overview (needs the PIN, per-child counts), daily reset (off by default, once a
day), and portable-folder detection (Windows, Mac, a file of that name). A new browser test runs the whole classroom
setup in German on a fresh install, checks the 25-card picker fits the screen, the overview table, the CSV contents,
and filling the class to 30. The wizard test now picks "At home". 294 unit/i18n tests and 22 browser tests pass.

**What to test:** a fresh install (or "delete everything") → choose "In der Klasse" → 20 children → the picture
picker; teacher area → Kinder → class overview and CSV.

## Brief milestone 9 — Feature flags and offline licence file (tagged `revamp-m10`)

- **Three tiers** (`backend/licence.py`): *core* (free: every stage, every language, the own word list),
  *plus* (online helper, printables), *school* (classroom mode, portable mode). "Unlimited custom lists" is part of
  *plus* in the brief, but Tippy only has one own word list, so there is nothing to lock there yet.
- **Offline licence file:** signed JSON (Ed25519), checked on the computer against a public key built into the app.
  No payments, no accounts, no online check. A parent adds it in Data → "Add a licence"; it is kept in Tippy's data
  folder ("delete everything" leaves it). For portable mode it goes in `tippy-data/data/licence.json` on the stick.
- **Owner's signing tool:** `scripts/make_licence.py --tiers plus,school --to "Name"`. The key pair was made once
  with `--init`: **the private key is in `~/.config/tippy/licence-signing-key` on this Mac, outside the project and
  never committed.** Losing it means making a new pair and new licences; anyone who has it can make licences.
- **`DEV_UNLOCK_ALL=true`** (environment or `.env`) switches everything on. The browser test servers use it.
- **Where it is enforced (a decision):** only where something is switched on: choosing classroom mode (setup or the
  Children tab), the print card, the online helper (with LLM_MODE=live but no *plus*, Tippy uses built-in content)
  and portable mode (without *school* the `tippy-data` folder is ignored). A class that already exists keeps working;
  nothing a child is using gets locked mid-way.
- **New dependency:** `cryptography==50.0.1` (the standard Python library cannot check this kind of signature;
  writing signature checking by hand would be home-made cryptography).

**Heads-up for the owner:** your own Tippy with `LLM_MODE=live` in `.env` now needs either a *plus* licence
(make one for yourself) or `DEV_UNLOCK_ALL=true`, or the online helper stays off.

**Tests:** `tests/test_licence.py` signs with a throwaway key per test (the real key is never used by tests): no
licence = core; a licence unlocks only its tiers; a hand-edited or foreign-signed file is refused; unknown tiers
ignored; dev unlock; without a licence classroom cannot be switched on and the helper stays off; installing a licence
through the parent area (PIN needed, bad files refused); portable mode needs *school*. The real key pair was checked
once end to end (a licence made with the owner's key verifies with the app's built-in key). 302 unit/i18n tests pass.

## Another bug found on the way (also on `main`)

Testing tiny stories showed the filter for text from the online helper accepted "Visit www.example.com now." — web
addresses are made only of allowed characters. Fixed in its own commit (`fix: refuse web addresses in text from the
online helper`): a full stop directly followed by a letter is refused. Listed in `docs/BACKPORT_CANDIDATES.md`.

## Brief milestone 10 — Optional AI extras (tagged `revamp-m11`)

- **Provider modes** as the brief names them: `LLM_MODE=off` (default), `mock`, `openrouter` (`live`, the older name,
  still works so existing `.env` files keep working).
- **Consent screen:** the online helper now stays off until a parent opens "Extra: online helper" and says yes after
  reading, in plain language, what is sent (a theme, the language, known letters; numbers only for the weekly report),
  what is never sent, where it goes (OpenRouter) and what it can cost (free models by default, at most N requests a
  day). Until then nothing goes out, not even the "Test connection" ping. A button switches it off again. The tab is
  labelled "Extra" in all three languages. (It still also needs the *plus* tier from milestone 9 and a key in `.env`.)
- **Tiny stories** (brief §6.6): 2–3 sentence stories about Tippy and the child's interest, used by Sentence Sky's
  "things I like" level when the helper is on. Every sentence of a story must pass the same checks as any sentence, or
  the whole story is dropped; stories are typed whole and in order. Without the helper (or before a story is ready)
  the level uses built-in sentences, as before.
- Personalised practice words by interest and "Ask Tippy" already existed and keep their filters.

**Heads-up for the owner:** your own Tippy with the online helper now needs you to press "Yes" once on that screen.

**Tests:** nothing is sent before consent (not even the test ping), consent needs the PIN and toggles both ways,
`openrouter` equals `live`, a story is served whole and in order, a story with one bad sentence is dropped whole,
and without the helper the level uses built-in sentences. The consent screen was checked visually in German; the
throwaway server made no request to OpenRouter. 309 unit/i18n tests pass. The privacy page was updated to match.

## Status and what is next

Brief milestones 1–10 are complete (tags `revamp-m1` to `revamp-m11`); `main` untouched. Next is the brief's
**milestone 11: packaging** (tag `revamp-m12`).
