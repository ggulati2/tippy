# Tippy Revamp Brief — "Mein erster Computer" (branch: `revamp/erster-computer`)

> **How to use this file:** Saved as `docs/REVAMP_BRIEF.md` on this branch, with the branch's `CLAUDE.md` replaced by a short pointer to it (see §14). The original Tippy on `main` stays untouched.

You are an expert full-stack developer and children's learning-software designer. You are working on an **existing, working app called Tippy**: a local educational app that teaches young children to use a computer and type. It has a Python (FastAPI) backend, a plain HTML/CSS/JavaScript frontend, SQLite, and optional OpenRouter LLM integration. Tippy also has seven learning worlds, a PIN-protected parent area, and a mock LLM mode.

Your job is to **revamp it on a separate git branch** into a product with a clear market fit, without breaking the original. I am an AWS cloud architect with limited development experience, so explain decisions briefly, comment code for a non-expert, and stop after each milestone so I can test.

---

## 1. Git rules (non-negotiable)

1. Before any change, confirm the working tree is clean and you are on `main`. Then run:
   `git checkout -b revamp/erster-computer`
2. **Never commit to, rebase, or force-push `main`.** All work happens on the revamp branch or on short-lived feature branches off it (`revamp/feat-<name>`), merged back into the revamp branch.
3. Tag the starting point: `git tag tippy-v1-baseline main` so the original is always recoverable.
4. Commit in small, logical steps with clear messages (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). Tag each finished milestone: `revamp-m1`, `revamp-m2`, and so on.
5. If you fix a genuine bug that also exists on `main`, isolate it in its own commit and list it in `docs/BACKPORT_CANDIDATES.md`, so I can cherry-pick it into the original later. Do not apply it to `main` yourself.
6. Keep `.env`, the SQLite database, and any child data out of git. Verify `.gitignore` covers them.

---

## 2. Why we are revamping (product context)

Market research showed the following:

- **Typing tutors for ages 8+ are a saturated, free market** (TypingClub, Typing.com, keybr, Tipp10). Competing on typing speed is pointless.
- **Ages 5–7 are underserved.** The classic option for this age (BBC Dance Mat Typing) died with Flash, and most remaining options are shallow web games or touch-typing drills.
- **Touch typing at 6 is developmentally contested.** Guidance suggests roughly a 7-year-old spelling level before touch typing works well. Kindergarten and first-grade goals are simpler: find letters on the keyboard, know the left and right sides, and use the space bar, Enter, and the mouse.
- **The German market has a clear gap.** Teachers report that good tools are partly English-only, too expensive, or browser-only, and that there is **no suitable locally installed program for Grundschule**. Parents complain that existing tools are dull and obsessed with keystrokes per minute and error rates.
- **Parents want safety:** single-player only, no chat, no ads, no accounts, no aggressive paywalls.

**New positioning:** *"Mein erster Computer — mouse, keyboard and safety for ages 5–7."*
It is a **computer-readiness** app, not a typing-speed tutor. It is **German-first and bilingual (DE/EN)**, **offline-first**, **private by design**, and usable **at home and in Grundschule classrooms**. Touch typing becomes an optional later track for ages 7+.

---

## 3. Step zero: audit before changing anything

Before writing new code:

1. Read the whole existing codebase and the original `CLAUDE.md`.
2. Write `docs/AUDIT.md` covering the following:
   - the current architecture (a short diagram in Mermaid or ASCII)
   - what each of the seven worlds actually implements, and how completely
   - where content comes from (LLM, fallback JSON, hard-coded)
   - the test coverage that exists
   - known bugs and technical debt
   - which parts can be **kept**, **refactored**, or **replaced** for this brief
3. Propose a concrete migration plan mapped to the milestones in §12, and **stop and wait for my approval**.

Reuse working code wherever possible. Do not rewrite for the sake of it.

---

## 4. Architecture changes

### 4.1 Offline-first core, AI as an optional add-on
- The **entire core curriculum must work with no network and no API key.** All core content comes from versioned local **content packs** (JSON), not the LLM.
- Put the LLM behind a single provider interface with three modes: `LLM_MODE=off` (the default for new installs), `mock`, and `openrouter`. Every AI feature must degrade gracefully to local content.
- AI features are clearly labelled "Extra" in the parent area, off by default, and enabled only after an explicit parent consent screen that says in plain language what is sent (never personal data) and what it may cost.

### 4.2 Content packs
- Folder: `content/packs/<pack_id>/` with a `manifest.json` (id, version, language, age range, licence, author) plus data files (words, sentences, tasks, audio prompts).
- Ship built-in packs:
  - `core-de`
  - `core-en`
  - `grundwortschatz-de-1`: **our own** first-grade word list, written by us. Do not copy copyrighted school lists or Anlauttabellen; design an original letter-picture table.
  - `family-words`: generated locally from profile data.
- Write a JSON Schema for packs and a validator test that runs in CI and fails on invalid packs or on words outside the allowed character set.
- Parents and teachers can add a **custom word list** (for example, "this week's spelling words") through the UI. It is stored as a local pack and validated with the same rules.

### 4.3 Internationalisation
- Put every UI string in `frontend/i18n/de.json` and `en.json`. There must be no hard-coded user-facing text in HTML or JS.
- Add a test that fails if any key is missing in either language.
- Keep UI language and practice language as separate settings, so a German UI can be used with English practice words and vice versa.
- Voice narration uses the OS/browser speech engine (Web Speech API) with a language-matched voice. Pre-recorded audio can replace it later. Fail silently if no voice is available.

### 4.4 Keyboard layouts
- **Default: German QWERTZ**, with dedicated mini-lessons for **ä, ö, ü, ß**, the Shift key for capital letters (important because German nouns are capitalised), and Z/Y swapped relative to QWERTY.
- Also support US and UK QWERTY. Store the layout as data (`frontend/layouts/*.json`) so the on-screen keyboard, finger zones, and lessons all read from one source.
- Detect likely layout mismatches (for example, the child presses the physical Z key while a QWERTY layout is selected) and gently suggest that the parent check the setting.

### 4.5 Profiles
- Support multiple child profiles (siblings) on one machine, with a picture-based profile picker (the child taps their own avatar; no reading required).
- A profile stores only a first name or nickname, an avatar, an age band (5, 6, 7, 8+), interests, language, and layout. **No surnames, birthdates, photos, or school names.**

### 4.6 Packaging
- The goal is a **one-click install for non-technical parents and school IT**.
- Package with PyInstaller, and open the frontend in a native window via `pywebview`, falling back to the default browser in kiosk-style fullscreen.
- Produce a Windows `.exe` first; add macOS and Linux after. Document the build in `docs/BUILD.md`.
- Also support a **portable mode** (runs from a USB stick, with data in a folder next to the executable), which is useful for schools.

### 4.7 Branding
- Put the product name, mascot name, colours, and logo in one file (`branding.json`) and read them everywhere from there. The name "Tippy" must be checked for trademark conflicts before any public release, so renaming must be a one-file change.

---

## 5. Curriculum redesign (ages 5–7)

Replace speed-oriented progression with **readiness milestones**. **Remove WPM from the child's view entirely.** Children see stars, stickers, and Tippy's reactions; parents see plain-language progress.

| Stage | Name (DE / EN) | Skills |
|---|---|---|
| 1 | Mauswiese / Mouse Meadow | Move, point, click, double-click, drag and drop, scroll. Large targets that shrink gradually. |
| 2 | Tastaturland / Keyboard Land | Find letters (not touch typing), left vs right side, Space, Enter, Backspace, Shift. Colour-coded **rows** first, finger zones only later. |
| 3 | Mein Name / My Name | Type own name, then family words (Mama, Papa, Oma, siblings, pet). Highest-motivation content comes first. |
| 4 | Wörterwald / Word Woods | Short words from the school pack and the parent list, with picture support for pre-readers. |
| 5 | Computer-Alltag / Everyday Computer | Real-world tasks in a **safe simulated desktop** (see §6.2). |
| 6 | Sicher im Netz / Safe & Smart | Age-appropriate safety concepts, taught through stories and choices (see §6.3). |
| 7 | Malen & Schreiben / Create Studio | Free play: draw, type a caption, make a card, save and reopen it. |
| Optional, 7+ | Zehn-Finger-Pfad / Ten-Finger Path | Gentle intro to home-row touch typing, **locked by default**; the parent enables it. |

Rules:
- Lessons last **2–5 minutes**. A session defaults to **10 minutes** (parent-adjustable, 5–20), then Tippy suggests a movement break with a short animated stretch.
- There is a posture and hand reminder at the start of each session (a quick animation, skippable after first view).
- Mistakes are **never punished**: no buzzers, no red screens, no lost stars. Show the correct key softly highlighted and let the child retry.
- Difficulty adapts per key and per skill (reuse the existing adaptive logic if it is sound), but **never auto-advances to the next stage**. The child chooses their next adventure from unlocked options.
- Instructions must work for **non-readers**: every instruction is spoken and shown with an icon or animation.

---

## 6. New features

### 6.1 Name & family mode
- During profile setup, the parent enters up to about eight family words.
- These feed the `family-words` pack locally and **are never sent to the LLM**.

### 6.2 Everyday-computer tasks (simulated desktop)
Build a **fake, sandboxed "Tippy Desktop"** inside the app. It must never touch the real file system beyond the app's data folder. Tasks include:
- Write a birthday card, then press "Save".
- Find your saved drawing in a folder and open it.
- Close a window, and minimise and restore a window.
- "Log in" with a picture password (choose three pictures in order), which teaches that passwords are secret.
- Recognise and close a pop-up.
Each task has a clear goal, spoken instructions, and a celebratory ending.

### 6.3 Safe & Smart
Use short interactive stories with two choices each. Topics:
- a stranger asks your name
- a pop-up says you've won a prize
- someone asks for your password
- when to ask a grown-up

Keep the tone warm, not scary. The content lives in the content packs (reviewed text, not LLM-generated).

### 6.4 Parent area upgrades (PIN-protected)
- **Weekly report in plain language** — for example, "Ranvit can now find most letters on the left side and double-clicks confidently." Generate it from **templates by default**. The LLM may rephrase it only when AI is enabled, and it receives aggregated stats only, never names.
- **Custom word lists** (see §4.2).
- **Time controls:** session length, daily limit, and allowed time windows.
- **Printable extras:** a certificate per completed stage and a paper keyboard colouring sheet (generate PDF or print-friendly HTML).
- **Data controls:** export all data (JSON), delete a profile, delete everything. Deletions require PIN re-entry.

### 6.5 Classroom mode (Grundschule)
- A separate "teacher" setup flow with a teacher PIN.
- Up to 30 profiles, each identified by nickname or animal avatar. This mode is anonymous by default.
- Optional daily progress reset (as some schools require).
- A class overview screen (which stages each child has completed) with CSV export.
- It works fully offline and in portable mode (§4.6). **No cloud sync in this revamp.**

### 6.6 Optional AI extras (only when enabled)
- **Personalised practice words** based on stated interests (dinosaurs, space, football), validated against pack rules before use.
- **Tiny stories** of two or three sentences featuring Tippy and the child's interest, used as typing material in later stages.
- **"Ask Tippy"** as a scoped helper, off by default, kept from the original with the same strict filters.
- All output is validated server-side (character set, length, blocklist, JSON schema) and cached; on failure, fall back to local content silently.

---

## 7. Child safety, privacy and DSGVO/GDPR

- **No accounts, no telemetry, no analytics, no ads, no external links, no in-app browser, no social features, single-player only.**
- The server binds to `127.0.0.1` only. The only permitted outbound network call is to OpenRouter, and only when AI is enabled.
- **Never send any personal data to the LLM:** no names, family words, age, or location. Use placeholders and substitute locally.
- Data minimisation: store only what features need (§4.5).
- Write a plain-language `docs/PRIVACY.md` in German and English explaining what is stored, where it is stored, what (if anything) leaves the device, and how to delete it. Also add a "Datenschutz" screen in the parent area that shows the same text.
- Child-facing screens must never show error messages, stack traces, or technical text. They show a friendly fallback, and details are logged for the parent.

---

## 8. Monetisation readiness (build the switches, not the payment system)

- Add a feature-flag system with three tiers: `core` (free: all readiness stages, both languages, one custom list), `plus` (AI extras, unlimited custom lists, printable extras), and `school` (classroom mode, portable mode).
- For now, a simple **offline licence file** (signed JSON, verified with a bundled public key) unlocks the tiers. **Do not build payments, accounts, or any online licence check.**
- During development, a `DEV_UNLOCK_ALL=true` env flag enables everything.

---

## 9. UX and accessibility

- Big targets (at least 64 px), high contrast, and a font designed for early readers (bundle it locally; no web font loading).
- Settings for reduced motion, sound on/off, voice on/off, a left-handed mouse option, and larger text.
- The child view has no scroll-heavy pages and no small text links.
- The parent area uses a normal, calm adult UI. It does not need to be childish.

---

## 10. Testing and quality

- **Unit tests:** pack validation, i18n completeness, adaptive difficulty, LLM output validation and fallback, feature flags, licence verification, PIN checks, and data export/delete.
- **End-to-end tests (Playwright):** a child completes one lesson in each stage with mock/off LLM; a parent changes settings and exports data; classroom mode creates 30 profiles and exports CSV.
- **Offline test:** the full core flow passes with networking disabled and `LLM_MODE=off`.
- Continue using `LLM_MODE=mock` for all AI-path tests. Tests must never spend API credits.
- Add a simple GitHub Actions workflow on the revamp branch running tests and pack validation.

---

## 11. Project structure (target)

```
backend/        FastAPI app, services, llm/ (provider interface), validators, db, licensing, flags
frontend/       HTML/CSS/JS, i18n/, layouts/, stages/<stage_id>/, desktop-sim/, parent/, classroom/
content/packs/  core-de, core-en, grundwortschatz-de-1, family-words (generated), custom/
docs/           REVAMP_BRIEF.md, AUDIT.md, PRIVACY.md, BUILD.md, BACKPORT_CANDIDATES.md, CHANGELOG.md
scripts/        build, validate-packs, dev-run
tests/          unit/, e2e/
branding.json, .env.example, requirements.txt, CLAUDE.md
```

Keep each stage as a self-contained module (`frontend/stages/<id>/`), with a small registry, so stages can be added, removed, or reordered without touching the others.

---

## 12. Milestones (stop after each; I test before you continue)

1. **Branch and audit:** create the branch and baseline tag, write `AUDIT.md` and the migration plan. *Stop for approval.*
2. **Foundations:** content-pack system and validator, i18n (DE/EN) with a completeness test, `branding.json`, `LLM_MODE=off` as default, and profiles with a picture picker.
3. **Keyboard layouts:** QWERTZ default with umlaut/ß/Shift lessons, layouts as data, and mismatch detection.
4. **Curriculum stages 1–4:** migrate the existing worlds into the new stage structure, remove child-facing WPM, and add session length, break, and posture reminders.
5. **Everyday Computer and Safe & Smart:** the simulated desktop tasks and interactive safety stories.
6. **Create Studio and optional Ten-Finger Path.**
7. **Parent area upgrades:** template reports, custom word lists, time controls, printables, and data export/delete, plus `PRIVACY.md` and the Datenschutz screen.
8. **Classroom mode and portable mode.**
9. **Feature flags and offline licence file.**
10. **Optional AI extras:** re-enable through the provider interface with the consent screen.
11. **Packaging:** Windows one-click build, then macOS/Linux, plus `BUILD.md`.
12. **Polish and review:** accessibility pass, performance, full tests green, CHANGELOG, and a final check against §13.

---

## 13. Definition of done

- The original Tippy on `main` is unchanged and still runs; `tippy-v1-baseline` exists.
- A fresh install on Windows starts with one double-click, **with no API key and no internet**.
- A 6-year-old who cannot read fluently can pick their profile, start, and finish a lesson in every core stage **without adult help**.
- The German UI is complete and the default QWERTZ layout works, including ä/ö/ü/ß.
- The child never sees WPM, error rates, error messages, ads, links, or chat.
- No personal data ever leaves the device. With AI off, there are zero outbound network calls (verified by test).
- Classroom mode handles 30 anonymous profiles and exports CSV, and it works from a USB stick.
- All tests pass, packs validate, and the docs (AUDIT, PRIVACY, BUILD, CHANGELOG) are complete.

---

## 14. Branch `CLAUDE.md` (replace the old one on this branch only)

```markdown
# CLAUDE.md (branch: revamp/erster-computer)
Follow docs/REVAMP_BRIEF.md. Never modify, rebase or push to `main`.
Stop after each milestone in §12 and wait for my test/approval.
Defaults: LLM_MODE=off, German UI, QWERTZ layout. Offline-first; no personal data to any API.
Explain changes briefly for a non-expert; comment the "why" in code.
```

---

## 15. Open questions to confirm with me during the audit

- Which of the original seven worlds are finished enough to migrate, and which should be rebuilt?
- Should the Ten-Finger Path ship in the first release or later?
- Should parent-survey results (I am collecting feedback from other parents) change the stage order or feature priority? I will paste the results when available. Keep the plan flexible enough to reorder milestones 5–10.
