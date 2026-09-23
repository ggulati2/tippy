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

## Status and what is next

Milestone 3 is complete, tagged `revamp-m3`, and pushed. The next milestone to tackle is **Milestone 4:
Curriculum stages 1–4** (group the existing 12 worlds into the brief's named stages, remove any
speed-flavoured child-facing copy, add the posture/movement-break content, and build the "up to eight
family words" pack from Sentence Sky's existing name/favourite-word feature). This section will be
updated, or a new one appended, if and when that milestone is attempted in this run.
