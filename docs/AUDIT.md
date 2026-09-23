# Audit of Tippy v1, before the "Mein erster Computer" revamp

This covers everything on `main` at the tag `tippy-v1-baseline` (the commit this branch, `revamp/erster-computer`, started from). It answers the questions in §3 of `docs/REVAMP_BRIEF.md` and ends with a migration plan. **Nothing has been changed yet** — this is the audit the brief asks me to stop on for approval before any revamp work begins.

The short version: Tippy v1 is further along than the brief assumes. It already has 12 working worlds (not seven), three languages including German with a real QWERTZ layout and umlaut/ß lessons, a licence-free-friendly LLM-optional architecture, child profiles, and an offline-first design with a real automated test suite (288 tests). The revamp's real work is less "build the foundations" and more "re-point the curriculum at ages 5–7, add the missing safety/classroom/monetisation pieces, and repackage." See §6 for exactly what that means for the milestone order.

## 1. Architecture today

```
Browser (Chrome/Edge, kiosk window)
   |  fetch() / JSON, no build step
   v
FastAPI app (127.0.0.1 only)  --  backend/app.py
   |                 |                    |
   v                 v                    v
SQLite            content bank         LLM client (optional)
(per-child db,    (content/*.json,     backend/llm/client.py
 family.db)        backend/bank.py)    -> OpenRouter, or mock.py
```

- **Backend**: Python 3.11+, FastAPI, plain `sqlite3` (no ORM). One process, no background workers except a thread that refills the LLM content cache. Served only on `127.0.0.1`.
- **Frontend**: no framework, no build step. Plain HTML + vanilla JS files loaded as `<script>` tags in a fixed order from `frontend/index.html`; one shared `el()` helper builds every element with `textContent` only (never `innerHTML`, with one documented exception for the mascot's own fixed SVG). A `MutationObserver`-based helper (`emoji.js`) swaps emoji characters for bundled Twemoji pictures after the fact, everywhere, without the game code needing to know about it.
- **Storage**: `data/family.db` (PIN hash, model choice, the list of child profiles) plus one `data/profiles/<id>.db` per child (progress, keystroke stats, settings, cached LLM content). A single legacy `tippy.db` migrates automatically the first time a new build sees it.
- **Distribution**: a source zip (any OS, Python + a start script), a standalone Windows installer and a standalone Mac app (both built by PyInstaller; Windows and Apple-silicon Mac are built in CI, Intel Mac is built by hand since the only Mac available is Intel). The window itself is a real installed browser (Chrome/Edge) launched in kiosk mode by `scripts/launch.py`, not an embedded webview.
- **CI**: GitHub Actions runs unit tests, a headless-Chrome end-to-end suite, CodeQL, a security scan (pip-audit, bandit, OWASP ZAP baseline), and a performance/load test, on every pull request. `main` is branch-protected (PR required, required checks, linear history).

## 2. What each of the twelve worlds actually implements

The brief's "seven worlds" is the *original* plan. Five more were added since: Number Land, and four "everyday computer" worlds (Paint Place, Desktop Dock, Internet Island, Robot Helper) that already cover a good chunk of §6.2 and part of §5's "Everyday Computer" stage.

| World | Brief's closest stage | What it does today | Completeness |
|---|---|---|---|
| Mouse Meadow | 1. Mauswiese | Click, drag into baskets, double-click, scroll; targets do **not** currently shrink over time | Solid |
| Keyboard Kingdom | 2. Tastaturland | Find the glowing key; mini-games for Space/Enter/Backspace/Shift; bonus levels for arrow keys and Caps Lock | Solid |
| Letter Land | 2. Tastaturland | Type single letters, finger-zone colours, adaptive difficulty (starts at A/S, adds a letter at ~80% accuracy over the last 20 keys, drops one below 50%); bonus levels for top/bottom row, case, and (German only) umlauts on the real ß key | Solid, and the adaptive-difficulty engine (`backend/difficulty.py`) is exactly the kind of per-key adaptation §5 asks to keep |
| Number Land | — (not in the brief) | Find/count/order/add/type digits, an on-screen number pad or the digit row | Solid; the brief doesn't mention numbers — worth a decision on whether it's in scope |
| Word Woods | 4. Wörterwald | Type 2–4 letter words with a picture; bonus levels for longer words and themes (animals, space, dinosaurs, vehicles, and for German only: country/food/wild-animal sets, culture and festival words) | Solid |
| Sentence Sky | — (between 4 and 7) | Type short sentences, then the child's own name and a "favourite word" (set once by the parent) | Solid; this is most of §6.1's "name mode", just not the "up to eight family words" version |
| Computer Cove | 6. Sicher im Netz (partly) + general computer literacy | 16 short picture-and-choice lessons: screen/mouse/keyboard, windows, folders, breaks, "ask a grown-up", online safety (never share your name/address), touchpad, flags, animal homes, food, weather, and (German only) emergency numbers and traffic lights | Solid on general literacy; the *safety* content is a handful of one-shot picture choices, not the two-choice interactive stories §6.3 asks for |
| Free Play Studio | 7. Malen & Schreiben (typing half) | Type any word, see a sticker scene; nothing typed here is ever sent anywhere | Solid for typing; there is no drawing and no save/reopen |
| Paint Place | 5. Computer-Alltag (mouse half) | Mouse painting: colours, brush size, stamps, Undo | New this year; a real head start on "draw something" |
| Desktop Dock | 5. Computer-Alltag (desktop half) | A **sandboxed pretend desktop already exists**: double-click to open, drag files into folders, name a file by typing, trash bin and restore, a save dialog that asks "do you want to save?" | This is most of §6.2 already built — it needs a picture-password "log in" task and a pop-up-recognition task added, not a rebuild |
| Internet Island | 6. Sicher im Netz (partly) | A **pretend, fully offline browser**: click links, Back, search by typing, three picture-choice questions about pop-ups/downloads/strangers, keep a favourite page | The pop-up/stranger content is exactly the shape §6.3 wants, just as one-shot choices rather than a short story; a good base to extend |
| Robot Helper | Ten-Finger Path (loosely) | Arrow-card "programs" that move a robot to a battery; not touch typing at all | Not what the brief's optional track means — a decision is needed on whether to keep it as-is (it teaches sequencing, not typing) |

Every world: no WPM or timers shown to the child anywhere (this was already a hard rule in the original brief and it held). Difficulty never auto-advances past what §5 calls a "stage" in the brief's sense, though today there is no stage grouping — worlds unlock each other one at a time in a fixed chain (`UNLOCK_AFTER`/`WORLD_ORDER` in `backend/progress.py`), which is a smaller idea than the brief's "child picks their next adventure from unlocked options" but the unlocking data model can grow into that without a rewrite.

## 3. Where content comes from

- **Local bank (works with zero network)**: `content/*.json` — `fallback_words.json`, `fallback_sentences.json`, `word_pictures.json`, `free_play.json`, `stickers.json`, `ask_tippy.json`, `special.json` (language-specific sets, e.g. German culture/festival/umlaut words). All hand-written by the assistant during earlier sessions, validated by `tests/test_languages.py` and `tests/test_special.py` (typable on the target keyboard, length limits, minimum counts per theme). **These are already a "content pack" in everything but name and folder structure** — §4.2's `manifest.json`/`content/packs/<id>/` layout is a reorganisation and a licence/version field, not new content logic.
- **Optional LLM (OpenRouter)**: `backend/llm/client.py` behind `LLM_MODE` (`off` default for a shared build, `mock` for tests, `live` for a developer's own key). Generates fresh themed words/sentences and short encouragement lines; output goes through Pydantic schemas then `validators.py` (allowed characters, length, per-language blocklist) before the child ever sees it; anything that fails is silently dropped in favour of the local bank. This already **is** the "provider interface with three modes" the brief asks for in §4.1 — it needs a shared abstraction if more providers are ever added, but the mode switch and graceful degradation already exist and are tested (`tests/test_llm_client.py`, mocked transport, never a real network call in CI).
- **"Ask Tippy"**: picture-only topics (`content/ask_tippy.json`), off by default, LLM answers filtered the same way; a fixed topic list, no open text box — already matches §6.6's constraints.
- **Nothing is hard-coded English-only**: every screen string lives in `frontend/js/i18n.js` (English + German) and `frontend/js/i18n-es.js` (Spanish), and `scripts/check_i18n.js` fails the build if a key is missing in any language or referenced but undefined — this is §4.3's i18n test, already written, just for three languages instead of two.

## 4. Test coverage

- **288 automatic tests total.** 261 run on every commit (`python -m pytest`): PIN checks, difficulty adaptation, keystroke scoring, LLM validation/fallback, i18n completeness (via the Node script, not pytest, but wired into the same `scripts/check.sh`), profile storage, backup/restore, security regression tests (headers, PIN-on-every-parent-route, hostile input, no `innerHTML`), and voice-recording integrity.
- **27 browser tests** (marker `browser`, run in CI only, not on every local commit): a headless-Chrome harness (`tests/browser/`, custom, not Playwright) that plays every level of every world in three languages with deliberate mistakes, stresses the app (key-mashing, Home-button spam, shortcut keys), and drives the whole parent area (settings, backup/restore, children, limits). This is the brief's §10 "child completes one lesson in each stage" and "parent changes settings and exports data" already, just under a hand-rolled harness instead of Playwright.
- **No dedicated "offline with networking disabled" test** exists yet, though `LLM_MODE=off` is what every shared build ships with and is covered incidentally. §13's "zero outbound network calls, verified by test" is a real gap to close.
- **Performance and security**: a load test (20 simulated children, a simulated year of data, memory growth) and a security scan (pip-audit, bandit, OWASP ZAP baseline) both run in CI already, advisory (not blocking merges) at the moment.

## 5. Known bugs and technical debt

- The Spanish and German written content (words, sentences, safety text) was written by the assistant and has **not been reviewed by a native speaker**. For a German-market product this matters more than it did as a bonus language and should move up the priority list.
- Mac packaging is ad-hoc signed only (no paid Apple Developer ID), so first launch needs a manual "Open Anyway"; same idea applies to an eventual Windows code-signing certificate. Not a blocker for testing, but worth deciding on before a real classroom rollout.
- The window is a real external browser in kiosk mode, not an embedded webview — simpler and it's what let this ship without extra native dependencies, but it means "one click, no browser chrome ever visible" depends on the family having Chrome or Edge installed (the app falls back to the default browser, non-fullscreen, if neither is found). §4.6 asks for `pywebview`; that's a real architecture change, not a tweak.
- No feature-flag or licensing system exists at all (§8) — entirely new.
- No classroom mode (§6.5) — entirely new; the closest existing thing is the 6-profile family picker, which is a good visual/data starting point but not built for 30 anonymous profiles or CSV export.
- No printable certificates/colouring sheets (§6.4) — entirely new.
- Mouse Meadow's targets are a fixed size; the brief wants them to shrink gradually — small, contained change.
- There is no "posture and hand reminder" animation, and no movement-break stretch animation (there is already a break *prompt* after the session length, just no stretch content) — content addition, not architecture.

## 6. Keep, refactor, replace — mapped to the brief

**Keep as-is (already matches the brief's intent):**
- FastAPI + SQLite + no-build-step frontend (§ intro).
- `LLM_MODE` off/mock/live and the validate-then-fall-back-silently pattern (§4.1, §6.6).
- The i18n-completeness test pattern (§4.3) — just needs the same treatment kept as languages are added/removed.
- QWERTZ-as-German-default and umlaut/ß handling already exist and are tested (§4.4) — this is not new work, it is already done.
- Child profiles with a picture picker, first-name-only, fixed interest list, max count (§4.5) — needs raising the cap for classroom mode, not rebuilding.
- Branding in one file (`frontend/js/config.js`) (§4.7) — rename/relocate to `branding.json` if you want the exact filename the brief names; the pattern already exists.
- The adaptive per-key difficulty engine (§5's "difficulty adapts per key").
- Desktop Dock and Internet Island's sandboxed-simulation approach (§6.2) — extend, don't replace.
- The security posture: 127.0.0.1-only, no telemetry, no ads, no accounts, PIN-gated parent area, validated LLM output, name never sent to the LLM (§7) — already the whole design, not a retrofit.

**Refactor:**
- `content/*.json` → `content/packs/<id>/manifest.json` + data files, with a JSON Schema and a pack validator test (§4.2). The content itself mostly carries over; this is a reshuffle plus a manifest.
- World unlocking (`UNLOCK_AFTER`, `WORLD_ORDER`) → a "stage" grouping the child can choose within, per §5's "never auto-advances, child picks their next adventure."
- Computer Cove's and Internet Island's one-shot safety questions → the two-choice interactive stories §6.3 describes. The picture-choice engine (`chooseSteps` in `basics.js`) is close; it needs branching, not a rewrite.
- Sentence Sky's single "favourite word" → the "up to eight family words" pack (§6.1); the underlying idea (a setting that becomes typing content, never sent to the LLM) is identical.

**Replace / build new:**
- Kiosk browser window → `pywebview` embedded window, if you want to keep §4.6 as written (this is the single biggest architecture change in the whole brief; see the open question in §7 below).
- Feature flags + offline licence file (§8).
- Classroom mode (§6.5).
- Printable certificates/colouring sheets (§6.4).
- `docs/PRIVACY.md` and a "Datenschutz" screen (§7) — the practice is already privacy-respecting; the *document* explaining it to a parent or teacher does not exist yet.
- The mismatch-detection idea in §4.4 (physical key doesn't match the selected layout) — nothing like it exists today.

## 7. Open questions (§15 of the brief), with a recommendation on each

1. **Which worlds are finished enough to migrate, which to rebuild?** All twelve are finished enough to migrate as-is into the new stage structure (see the completeness column in §2) — none needs a rewrite. The real decision is scope: do Number Land and Robot Helper stay in the ages-5–7 product, get moved to an "extra" bucket, or get dropped for this positioning? My recommendation: keep Number Land (numeracy fits the age band fine), and re-badge Robot Helper as a clearly optional "logic games" extra rather than the Ten-Finger Path (it isn't a typing track at all, and pretending otherwise would be confusing) — but this is your product call, not mine.
2. **Ship the Ten-Finger Path in the first release, or later?** Nothing resembling home-row touch typing exists today (Letter Land teaches finger *zones*, i.e. which general area, not full touch-typing form). Recommend: build it later (milestone 6, as the brief already schedules it), and locked-by-default from day one either way, since the brief itself says 7-year-old spelling ability is the usual readiness bar.
3. **Parent-survey results reordering milestones 5–10:** the plan below is written so milestones 5 onward are independent of each other (Everyday Computer/Safe & Smart, Create Studio, Parent upgrades, Classroom, Feature flags, AI extras) — reordering them once survey results arrive should not require re-planning, just re-sequencing.

One more decision I'd like from you before milestone 2, not in the brief's own list: **keep the existing hand-rolled headless-Chrome test harness, or adopt Playwright** for the new end-to-end tests the brief asks for in §10? Playwright is proven to work in this environment (used it this session for visual checks) and is a more standard/maintainable choice for a growing test suite; the existing harness works today and all 27 current browser tests would need porting either way if you switch. I lean Playwright given the brief explicitly names it, but it's a real one-time cost.

## 8. Migration plan mapped to the brief's milestones (§12)

| Milestone | Mostly new work, or extending what exists? |
|---|---|
| 1. Branch and audit | **Done** — this document, the branch, and the `tippy-v1-baseline` tag. |
| 2. Foundations (packs, i18n, branding, `LLM_MODE=off` default, profiles) | Mostly **extending**: reshape `content/*.json` into packs with manifests + a schema validator; i18n is already complete for en/de, just needs the pack-driven word lists wired in; `LLM_MODE=off` is already the shared-build default — only the *first-run wizard's* default needs checking; profiles need a raised cap and an age-band field. |
| 3. Keyboard layouts | Mostly **done**; the remaining new piece is layout-mismatch detection and confirming the on-screen keyboard/finger-zone data is cleanly separated as its own data file rather than embedded in `keyboard.js`. |
| 4. Curriculum stages 1–4 | **Extending**: group the existing worlds into named stages, remove any remaining speed-flavoured language from the UI copy (an audit of `i18n.js`/`i18n-de.json` strings, not a code change), add the posture reminder and gradually-shrinking mouse targets, and build the "up to eight family words" pack from Sentence Sky's existing name/favourite-word idea. |
| 5. Everyday Computer + Safe & Smart | **Extending** Desktop Dock and Internet Island (new tasks: picture-password login, pop-up recognition) and turning the existing one-shot safety questions into branching two-choice stories. |
| 6. Create Studio + Ten-Finger Path | Create Studio **extends** Free Play (add drawing + save/reopen, reusing Desktop Dock's save-dialog pattern); Ten-Finger Path is **new**. |
| 7. Parent area upgrades | Time controls and data export/delete **already exist**; template weekly reports **exist** (the LLM only rephrases them, matching §6.4 exactly) and just need re-tuning for the new stage language; custom word lists, printables, and `PRIVACY.md`/Datenschutz screen are **new**. |
| 8. Classroom mode | **New**, though the profile picker and per-child data isolation it needs already exist as a pattern to copy. |
| 9. Feature flags + licensing | **New.** |
| 10. Optional AI extras | Mostly **already built** (personalised words, tiny stories, Ask Tippy, server-side validation, caching) — this milestone is really "add the consent screen and confirm the tier gating from milestone 9 applies here," not building the AI features themselves. |
| 11. Packaging | Windows and Mac builds **already exist** and run in CI; the new work is entirely the `pywebview` embedded-window decision from §6 above, and portable-mode (USB stick, data next to the executable) which the current `TIPPY_HOME` override makes straightforward. |
| 12. Polish and review | As planned. |

**I am stopping here, as the brief's §3 instructs, to wait for your approval of this audit and plan before starting milestone 2.** In particular I'd like your call on the two open items in §7 (worlds scope, and the Playwright-vs-existing-harness question) before writing any new code.
