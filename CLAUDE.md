# Project Brief: "Tippy" — a local computer & typing learning app for a 6-year-old

## 1. Your role and the goal

You are a senior full-stack engineer and child-friendly UX designer. Build a **local, graphical, intuitive desktop-style application** that teaches a **6-year-old child** his first computer skills: using the mouse, discovering the keyboard, and typing letters, words and short sentences. The app uses **OpenRouter** with an LLM to generate fresh, personalised, age-appropriate practice content and friendly feedback, while staying fully usable (with a built-in content bank) when the internet or the LLM is unavailable.

"Working title" is *Tippy* (a friendly mascot). The name and mascot must be easy to change in one config file.

## 2. Who the users are

- **Child (primary user):** age 6. Can recognise letters, reads slowly, cannot be expected to read long instructions. Short attention span (5 to 15 minute sessions). Gets frustrated by failure, loves stickers, animals, sounds and animation.
- **Parent (developer/owner):** an AWS cloud architect with **limited software development experience**. He will run and lightly maintain this. So: keep the code simple, well commented, with minimal dependencies, and explain things in plain language.

## 3. How you must work with me

1. **Before writing code**, ask me at most 5 short clarifying questions (operating system, Python version installed, whether a microphone/speaker is available, the child's interests, English or German UI). If I don't answer, choose sensible defaults and state them.
2. Then produce a **short plan** (architecture, folder structure, milestones) and wait for my "go".
3. Build **milestone by milestone** (Section 12). After each milestone: make sure it runs, tell me exactly how to start it and what I should see, and commit to git with a clear message.
4. Prefer simple, readable code over clever code. No unnecessary frameworks. No over-engineering.
5. Whenever I must do something manually (install Python, create an OpenRouter key, etc.), give me numbered, copy-paste-ready steps.
6. Write a `README.md` (setup, run, configure, troubleshoot) and keep a `CLAUDE.md` in the repo root with project conventions so future sessions stay consistent.

## 4. Tech stack and architecture (recommended; justify any deviation)

- **Backend:** Python 3.11+, **FastAPI** running on `127.0.0.1` only (never exposed to the network). SQLite (via the standard `sqlite3` module) for progress and cached content.
- **Frontend:** plain **HTML + CSS + vanilla JavaScript** (no build step), served by the backend and opened automatically in a **fullscreen/kiosk-style browser window** on launch. Use CSS animations, inline SVG and emoji/simple illustrations; keep all assets local (no CDN dependencies) so it works offline.
- **Speech:** use the browser's built-in Web Speech API (`speechSynthesis`) for reading instructions and words aloud. Make voice on/off and language configurable. No microphone/speech recognition in v1.
- **Sound:** small local sound effects (key press, success, sticker earned). Generate simple sounds with the Web Audio API if no audio files are available. Provide a mute toggle.
- **One-click launch:** provide `start.bat` (Windows), `start.command` (macOS) and `start.sh` (Linux) that create/activate a virtual environment, install requirements on first run, start the server and open the app. Detect the OS and tell me which one applies to me.
- **Config:** `.env` file (never committed) with `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL`, `APP_LANGUAGE` (en/de), `PARENT_PIN`. Provide `.env.example`.
- **The API key must live only on the backend.** The frontend never sees it.

## 5. Learning design (the curriculum)

Design short, game-like activities grouped into "worlds". Each world unlocks after the previous is reasonably complete, but the parent can unlock any world manually.

1. **Mouse Meadow:** move, click big targets, drag-and-drop shapes into baskets, double-click, and scroll. (Goal: comfortable mouse/trackpad control.)
2. **Keyboard Kingdom (discovery):** an on-screen keyboard that highlights a key; the child finds and presses it. Introduce Space, Enter, Backspace and Shift with mini-games ("Press Space to make the rocket jump!").
3. **Letter Land:** type single letters (start with the home row A S D F J K L, then expand). Show a large letter, highlight the matching key on the on-screen keyboard, and colour-code finger zones to build correct finger habits gently.
4. **Word Woods:** type 2 to 4 letter words with a picture (cat, sun, dog). Read the word aloud on request and after success.
5. **Sentence Sky:** type short sentences (3 to 6 words), then type his own name and a favourite word.
6. **Computer Basics Cove:** tiny interactive lessons with icons and narration: what are the screen, mouse, keyboard, windows, and files; how to open and close a window; why we take screen breaks; and simple safety rules (ask a grown-up before clicking unknown things, never share your name or address online).
7. **Free Play Studio:** a big, safe typing canvas where the child types a word and Tippy turns it into a fun animation or sticker scene.

Pedagogy rules:
- **Errors are never punished.** A wrong key gets a soft "oops, try this one" with the correct key pulsing. No red screens, no buzzers, no lives, no timers or speed pressure in the early worlds.
- Adapt difficulty automatically from recent accuracy (e.g., introduce new letters only after ~80% accuracy over the last 20 keystrokes; step back if he struggles).
- Sessions default to about 10 minutes, then Tippy suggests a break. The parent can change this.
- Reward effort, not just correctness: stars, stickers and a growing sticker album; a friendly "daily streak" with no guilt if a day is missed.
- Show uppercase letters first, with a toggle to lowercase later. Support both regular and "keyboard-shaped" layouts for German (QWERTZ) and English (QWERTY); detect or let the parent choose.

## 6. UX and visual design requirements

- **Pre-reader friendly:** every instruction is (a) icon/animation driven and (b) read aloud. Text is short, large and secondary.
- Large click/touch targets (minimum ~64 px), high contrast, rounded shapes, bright but not overstimulating colours, a friendly rounded font (bundle it locally), generous spacing. No tiny UI.
- One clear task per screen. A persistent "Home" button and a big "Play" button. No hidden menus, no dense settings in the child's view.
- **Prevent accidental exits:** capture the keyboard while playing (block Alt+F4/F5/Ctrl+W as far as the browser allows, and ignore stray shortcuts inside the game). Exiting the app requires the parent PIN.
- Smooth, responsive feel: key feedback under 50 ms; animations at 60 fps on an ordinary laptop.
- Accessibility: adjustable font size, mute and reduced-motion options, works with mouse or trackpad.

## 7. LLM integration via OpenRouter

**Use OpenRouter's OpenAI-compatible endpoint** (`https://openrouter.ai/api/v1/chat/completions`) via the `openai` Python SDK with a custom `base_url`, or `httpx`. Check the current OpenRouter docs and the live model list (`https://openrouter.ai/api/v1/models`) before choosing default model IDs; do not rely on memory for model names. Pick a **cheap, fast, instruction-following model** as default and a second one as automatic fallback, both configurable via `.env`. Add sensible timeouts (about 8 s), limited retries, and clear logging of failures.

**LLM features (all optional-online; the app must fully work without them):**

1. **Practice content generator:** generates word lists, tiny sentences and mini-stories restricted to the letters the child has already unlocked, themed on his interests (parent-configurable, e.g., animals, space, dinosaurs). Request **strict JSON output** and validate it with Pydantic.
2. **Mascot feedback:** short, warm, varied encouragement lines (max ~12 words) generated from **structured stats** (accuracy, streak, new letter learned), never from raw personal data.
3. **"Ask Tippy" (parent-toggle, default OFF):** a tightly scoped Q&A where the child can ask simple questions about computers ("What is the internet?"). Answers must be 1 to 3 very short sentences at a 6-year-old reading level. Off-topic or unsafe questions get a gentle redirect ("That's a great question for a grown-up!").
4. **Parent progress summary:** a plain-language weekly summary of strengths, weak keys and suggestions, shown only in the parent area.

**Reliability and cost design:**
- **Prefetch and cache:** generate content in batches in the background and store it in SQLite, so the child never waits on the network. Reuse cached items when offline or when the API errors.
- **Local fallback content bank** (a few hundred safe words and sentences per level, stored in JSON) used whenever the LLM is unavailable or output fails validation.
- Show a small, non-alarming indicator for online/offline status in the parent area only, not in the child's view.
- Log token usage and estimated cost; add a configurable daily request cap.

**Draft in-app system prompt for the LLM (refine it, keep it short and strict):**

> You are Tippy, a kind, playful helper for a 6-year-old learning to use a computer. Use only very simple words and very short sentences. Be positive and patient; never criticise. Only talk about learning to type, using the computer, and gentle fun topics (animals, colours, space). Never ask for or mention names, addresses, schools, photos, passwords or any personal information. Never discuss violence, scary things, romance, medicine, politics, religion, or anything unsuitable for young children. If asked about something else, say it is a good question for a grown-up and suggest a typing game. When asked for JSON, return only valid JSON matching the requested schema, with no extra text.

## 8. Child safety and privacy (non-negotiable)

- **The child's real name, age, location and any identifying information are never sent to OpenRouter.** Use a placeholder (e.g., `{child}`) in prompts and substitute it locally.
- **Validate every LLM output on the server** before it reaches the child: allowed characters only, length limits, a blocklist/allowlist check, and a JSON schema check. If it fails, silently use fallback content. Never render raw LLM output as HTML (escape it).
- The child never gets an open text chat with the LLM. "Ask Tippy" is scoped, short, filtered, and off by default.
- No analytics, no tracking, no ads, no external links, no in-app browser, no network access other than to OpenRouter from the backend.
- Bind the server to `127.0.0.1` only. Store the API key only in `.env`; make sure `.gitignore` excludes `.env` and the database.
- All progress data stays **local** on this machine.

## 9. Parent area (PIN-protected)

Accessible from a small, unobtrusive icon that requires the PIN. Include:
- Progress dashboard: letters mastered, accuracy trend, time played, per-key accuracy heat map on a keyboard, streak, and the weekly LLM summary.
- Settings: child's first name (stored locally only), interests, UI/voice language, keyboard layout, session length, daily play limit, sound and voice toggles, "Ask Tippy" toggle, unlock worlds manually, and reset progress.
- LLM settings: test-connection button, choose model, show the current online/offline status and estimated cost.
- Exit application.

## 10. Data model (keep it simple)

SQLite tables (suggested): `child_profile`, `sessions`, `keystroke_stats` (per key: attempts, correct, avg time), `progress` (world/level status), `stickers`, `content_cache` (type, level, JSON, created_at, used), `llm_usage`. Provide a tiny migration or "create if not exists" approach and a backup/export-to-JSON button in the parent area.

## 11. Project structure and quality

- Suggested layout: `backend/` (FastAPI app, services, LLM client, validators, DB), `frontend/` (HTML, CSS, JS, assets), `content/` (fallback JSON), `tests/`, `scripts/`, `README.md`, `CLAUDE.md`, `.env.example`, `requirements.txt`.
- Write **unit tests** for: LLM output validation and fallback logic, difficulty adaptation, keystroke scoring, and PIN checks. Include a "fake LLM" mode (`LLM_MODE=mock`) so the app can be developed and tested without spending API credits.
- Add a lightweight structured logger and friendly error handling: the child should never see a stack trace or technical message; show a smiling "Let's try another game!" screen and log details for the parent.
- Comment the code for a non-expert: explain why, not only what.

## 12. Milestones (stop after each and let me test)

1. **Skeleton:** project structure, git, one-click launch, fullscreen welcome screen with mascot, parent PIN, and exit. Mock LLM mode wired up.
2. **Mouse Meadow** plus the reward/sticker system and persistent progress.
3. **Keyboard Kingdom and Letter Land** with the on-screen keyboard, finger-zone colours, adaptive difficulty and soft error handling.
4. **OpenRouter integration:** content generator, JSON validation, caching, fallback bank and mascot feedback. Test-connection button in the parent area.
5. **Word Woods and Sentence Sky**, voice narration and sound effects.
6. **Computer Basics Cove** and Free Play Studio.
7. **Parent dashboard**, weekly LLM summary, optional "Ask Tippy", session and daily limits.
8. **Polish:** accessibility options, performance, German/English localisation, full README, packaging tips, and final review against the checklist below.

## 13. Definition of done

- Starts with one double-click from a fresh checkout after I add my OpenRouter key.
- A 6-year-old can start playing and complete a lesson **without adult help** and without needing to read much.
- Fully usable offline using fallback content; graceful behaviour on API errors or slow responses.
- No personal information leaves the machine; no raw LLM output reaches the child unvalidated.
- The parent area works and is PIN-protected; exit requires the PIN.
- Tests pass; README lets a non-developer set up, run, configure and troubleshoot the app.

Begin with Section 3, step 1: ask your clarifying questions.
---

# Project conventions (added by Claude during the build)

- Run tests: `source .venv/bin/activate && python -m pytest`. Run the app: `python scripts/launch.py` or `start.command`.
- Backend in `backend/` (FastAPI, `create_app()` in `app.py`). Frontend in `frontend/` is plain JS, no build step. All screen text lives in `frontend/js/i18n.js` (en and de must stay in sync). Mascot name and colours: `frontend/js/config.js`.
- Text from the LLM goes through `backend/validators.py` before use, and is rendered only with `textContent` (helper `el()` in `app.js`), never `innerHTML`.
- Parent-only endpoints live under `/api/parent/` and require the `X-Parent-Token` header from `PinGuard`.
- The child's name is never sent to the LLM. Prompts use the `{child}` placeholder, substituted in the browser.
- Decisions with the parent: UI in English and German (switchable, both from the start); interests animals, space, dinosaurs, vehicles; speakers only, no microphone; developing in `LLM_MODE=mock` until Milestone 4.
- Extra `settings` table (key/value) holds parent settings, a small addition to the Section 10 table list.

## Milestone status

- [x] 1 Skeleton
- [x] 2 Mouse Meadow + stickers
- [x] 3 Keyboard Kingdom + Letter Land
- [x] 4 OpenRouter integration
- [x] 5 Word Woods + Sentence Sky
- [x] 6 Computer Basics Cove + Free Play
- [x] 7 Parent dashboard
- [x] 8 Polish

## Milestone 3 notes

- Keyboard screens: `keyboard.js` (on-screen keyboard, finger colours, `softMiss`), `kingdom.js`, `letters.js`. A running game sets the global `keyHandler` in `app.js`; `setScreen()` clears it.
- Adaptive difficulty lives in `backend/difficulty.py` (start with A and S, +1 letter at 80% over the last 20 presses, -1 below 50%, never below 2). Only Letter Land sends `adaptive: true`.
- CSS class `.target` is the Mouse Meadow click target. The glowing keyboard key is `.goal` (they clashed once).
- Testing UI without a browser tester: headless Chrome with `--dump-dom` plus a throwaway `sim.js` that dispatches `keydown` events (kept out of the repo).

## Milestone 4 notes

- All internet access is in `backend/llm/client.py` (`LLMClient`). Prompts come only from `backend/llm/prompts.py`, which has no parameter for a name. Models: default `nvidia/nemotron-3-super-120b-a12b:free`, fallback `deepseek/deepseek-v4-flash-0731:free`. Compared live on 2026-09-19 with `scripts/try_models.py`: Nemotron fastest and best for German words; DeepSeek best for English words/sentences; both Gemma 4 free models returned HTTP 429. LLM sentences mostly fail the 12-letter restriction and fall back to the bank (by design). Free accounts: 20 req/min, 50 req/day (1000/day with 10+ USD credit), so `DAILY_REQUEST_CAP` defaults to 45 and failed refills back off for 10 minutes. Requests send `reasoning: {effort: none}` so thinking models do not use up `max_tokens`. Each request: 8 s timeout, at most 2 tries (main, then fallback), every try logged to `llm_usage`, daily cap `DAILY_REQUEST_CAP`. Cost comes from `usage.cost` in the response.
- `backend/content.py` (`ContentService`) serves words, sentences and mascot lines: cache first, then the built-in bank (`backend/bank.py`, files `content/fallback_*.json`), then a background thread refills the cache. The child's request never waits on the network.
- LLM output is parsed with Pydantic (`backend/llm/schemas.py`), then filtered by `clean_words` / `clean_sentences` / `clean_mascot_lines` in `validators.py`. A batch with fewer than 3 good items is dropped. Blocklists are per language (German "die" is fine).
- `LLM_MODE=mock` runs the same pipeline with `backend/llm/mock.py`. In tests use `httpx.MockTransport` (see `tests/test_llm_client.py`); never call the real API from tests.
- Interests come from `child_profile.interests`, filtered to the four fixed themes in `bank.THEMES` (free text never goes into a prompt).
- Not built yet (later milestones): mascot lines from richer stats, Ask Tippy, weekly summary, a model picker and interests editor in the parent area, Word Woods and Sentence Sky which will use `/api/content/words` and `/api/content/sentences`.
- Never run anything that uses the parent's real OpenRouter key (the shell may already contain `OPENROUTER_API_KEY`) without asking first; test with `LLM_MODE=mock` or `httpx.MockTransport`.
- API tests force `LLM_MODE=mock` and an empty key in the `client` fixture (`tests/test_api.py`), because the real `.env` may be live. Keep it that way.

## Milestone 5 notes

- `frontend/js/typing.js` (`typingRound`) is the shared typing engine (ghost letters, next key glows, sound per letter, read aloud on success). `words.js` and `sentences.js` only prepare the items. Punctuation is removed from what the child types (`typingText`); text with characters the keyboard cannot produce is skipped (`isTypable`). Ä, Ö, Ü count only with the QWERTZ layout; ß is never asked for.
- Word Woods needs pictures: `content/word_pictures.json` (word to emoji, en and de). `ContentService.pictured_words()` returns only words with a picture. Add a picture there when adding a word to the bank.
- Word Woods and Sentence Sky draw from at least the first 16 letters (`MIN_PRACTICE_LETTERS` in `content.py`), otherwise there would be almost no real words. They use the cache and the bank like everything else; cache level key is `max(unlocked, 16)`.
- Child name and favourite word are settings (`child_name`, `favorite_word`) set in the parent area, used only in the browser (`settings.child_name` replaces `{child}` in mascot lines). Never add them to a prompt.
- `sfx(name, arg)` now takes an argument (`sfx("note", i)` plays step i of the scale).

## Milestone 6 notes

- `frontend/js/basics.js`: lessons are data-driven through `chooseSteps()` (picture + big choices; a wrong choice only wobbles and points at the right one). The window lesson is a small custom simulation. Add a lesson by adding steps, an i18n entry pair (en and de) and raising `LEVEL_COUNTS["basics"]` in `backend/progress.py`.
- `frontend/js/freeplay.js`: typed text is never sent anywhere (no LLM, no server). Word to emoji comes from `/api/pictures` = `content/free_play.json` plus `content/word_pictures.json`. Free Play has one "level": the first time the child makes 3 scenes it earns the Painter sticker.
- Basics unlocks after Sentence Sky is complete, Free Play after Basics is complete (parent can unlock all).
- Screens with the on-screen keyboard are tight at 720 px height: check new screens at 1280x720 (see the screenshot approach in the Milestone 3 notes).

## Milestone 7 notes

- Parent area is `frontend/js/dashboard.js` (tabs: progress, settings, helper, data). Charts follow the dataviz skill: one blue (#2a78d6), thin marks, quiet grid, no legend for one series, a "Show as table" `<details>` under each chart, heat map = share of mistakes on the blue ramp (grey = no data). Light theme only.
- `backend/dashboard.py` holds the numbers (key report, accuracy trend, play minutes, limits, export, reset) and the template summary. `backend/summary.py` asks the LLM for the weekly summary (cached per ISO week and language in the `weekly_summary` setting, validated, falls back to the template). The summary uses anonymous statistics only.
- `/api/settings` returns only `db.CHILD_SETTINGS`. Anything private (summary text, model override, letter counters) must stay out of that list.
- Play time: `frontend/js/limits.js` counts active seconds (visible window, input within 30 s, no modal open) and reports every 15 s to `/api/session/heartbeat` (max 60 s per call). Break suggestion after `session_minutes`; daily stop at `daily_limit_minutes` (0 = off). `closeModal()` re-shows the goodnight screen while `limitReached`; the parent gear has z-index above overlays.
- Ask Tippy is picture-only by design (`content/ask_tippy.json` has topics, icons, built-in answers). The topic list must match `ASK_TOPICS` in `frontend/js/ask.js`. The LLM never sees anything the child typed. LLM answers for "password" are always rejected by the blocklist, so that topic always uses the built-in answer.
- The parent can override the main model in the parent area (`openrouter_model` setting, read by `LLMClient.model`).

## Milestone 8 notes

- Accessibility: settings `font_scale` (1, 1.125, 1.25; drives the CSS variable `--font-scale`, capped at 1.25 because larger sizes push the world map and Free Play off a 720 px screen) and `reduce_motion` (adds the class `reduce-motion` to `body`). Both are applied by `applyLook()` in `app.js`. The child's 🔊 button (`muted` in `app.js`) is per-run and silences `sfx` and `speak`.
- `#screen` scrolls (`overflow-y: auto`, `justify-content: safe center`) as a safety net. Welcome and world-map sizes are capped with `vh` so they fit 1280x720 even at the biggest text size. Check new screens at 1280x720 with font_scale 1.25.
- Localisation review: en and de have the same 162 keys and every `t("...")` key exists. Keep it that way (a small node script that loads `i18n.js` and diffs the keys is enough).

## Distribution notes (after Milestone 8)

- Decisions with the parent: share as a zip first (`scripts/make_zip.py`, tracked files only, refuses anything that looks like an API key), standalone Mac/Windows builds later as a separate milestone; the shared version is offline only.
- `LLM_MODE` now has `off` (default: built-in content only, no helper tab), `mock` (development) and `live`. The parent's own `.env` may keep `live`.
- First start with no PIN: `setup_needed` is true in `/api/settings`, and `frontend/js/setup.js` runs the wizard (language, PIN, name, daily limit, default 30 min) via `POST /api/setup` (works once). The PIN is stored as a salted PBKDF2 hash in the `pin_hash` setting (private, not in `CHILD_SETTINGS`); `PARENT_PIN` in `.env` is optional and the saved hash wins. Change PIN: `POST /api/parent/pin`.
- Keep `.env.example` free of secrets and with `LLM_MODE=off`.
