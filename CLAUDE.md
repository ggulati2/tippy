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
- [ ] 4 OpenRouter integration
- [ ] 5 Word Woods + Sentence Sky
- [ ] 6 Computer Basics Cove + Free Play
- [ ] 7 Parent dashboard
- [ ] 8 Polish

## Milestone 3 notes

- Keyboard screens: `keyboard.js` (on-screen keyboard, finger colours, `softMiss`), `kingdom.js`, `letters.js`. A running game sets the global `keyHandler` in `app.js`; `setScreen()` clears it.
- Adaptive difficulty lives in `backend/difficulty.py` (start with A and S, +1 letter at 80% over the last 20 presses, -1 below 50%, never below 2). Only Letter Land sends `adaptive: true`.
- CSS class `.target` is the Mouse Meadow click target. The glowing keyboard key is `.goal` (they clashed once).
- Testing UI without a browser tester: headless Chrome with `--dump-dom` plus a throwaway `sim.js` that dispatches `keydown` events (kept out of the repo).
