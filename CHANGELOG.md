# Changelog

All notable changes to Tippy. Format: [Keep a Changelog](https://keepachangelog.com), versions: [Semantic Versioning](https://semver.org).

## [Unreleased]

### Added
- Security scans in CI (`security.yml`): pip-audit on every pinned package, bandit on our code, dependency review on pull requests, and an OWASP ZAP attack on a running server (report only). All also run every Monday.
- Performance tests in CI (`performance.yml`): a server load test (20 children at once, a year of saved play, memory growth; `scripts/loadtest.py`) and browser speed tests (first screen, key-to-screen delay, smooth animation, no memory leaks; `pytest -m perf`). Results show on the run's summary page.
- Security regression tests (`tests/test_security.py`) and a browser test that the page policy is really enforced.

### Changed
- Every response now carries protective headers (a strict Content-Security-Policy, no framing, no sniffing) and API answers are never cached; requests above the backup size limit are refused early.
- The parent PIN check now runs before anything else on every parent endpoint, and a test fails if a new parent endpoint forgets it.
- Faster: the database uses write-ahead logging (no slow saves while a child types), word filtering is cached, and the audio engine is warmed up while the welcome screen is idle (the first tap no longer freezes for about half a second).

- Standalone Mac app: `scripts/build_mac.sh` builds `Tippy.app` (PyInstaller) with icon; family data lives in `~/Library/Application Support/Tippy`; the app quits when its window is closed. `TIPPY_BROWSER` chooses another browser, `TIPPY_HOME` another data folder. The browser test suite can run against the packaged app (`TIPPY_APP_BINARY`).

## [0.11.0] - 2026-09-19

More to learn, in three languages: a Number Land, Spanish, many bonus levels and German-specific content.

**Upgrading:** nothing to do. Existing progress is untouched. Bonus levels never change what is unlocked, and Number Land opens after Keyboard Kingdom, so children who are further on keep everything open.

### Added
- **Number Land**, a new world with six games and an on-screen number pad (find the number, count, in order, add up, big numbers, countdown). The setting *This computer has a number pad* makes it ask for the pad keys; the digit row always works too. Digit statistics appear in the parent's heat map.
- **Spanish (Spain)**: screen text, the es-ES voice, words, sentences, pictures, Free Play words, Ask Tippy answers, mascot lines, stickers, the safety word list and the parent's weekly summary. New keyboard shape QWERTY with Ñ; accented letters are typed with the plain letter. The Spanish and German texts have not been checked by a native speaker yet.
- **Bonus levels** (a ✨ Bonus row in the level pickers; optional, they give stars and stickers):
  - Letter Land: top row, bottom row, big and small letters.
  - Word Woods: longer words, and word sets for animals, space, dinosaurs and vehicles.
  - Sentence Sky: longer sentences, questions, and sentences about what the child likes.
  - Keyboard Kingdom: arrow keys (a bunny hops to the carrot) and Caps Lock.
  - Computer Cove: the internet, saving a picture, being kind online, using the touchpad.
- **Germany-specific content** (German only): words and sentences about Germany and the year's festivals, an Ä Ö Ü ß typing level (the German keyboard now has its ß key), and lessons on the emergency numbers 112 and 110 and on traffic lights and the zebra crossing.
- 15 new stickers (7 of them German-only). More built-in content in every language: longer pictured words, themed words, longer sentences, question sentences.
- One server-side list of languages (`backend/languages.py`) drives the setup wizard, the settings and the Children tab. Adding a language is data plus texts, and the tests and `scripts/check.sh` fail if a language is incomplete or not typable on its keyboard.

### Changed
- Worlds can have optional bonus levels and their own prerequisite world; language-specific levels, stickers, content sets and screen texts are supported (see `CLAUDE.md`).

## [0.10.0] - 2026-09-19

Several children per computer, restoring backups, and a much stronger test pipeline.

**Upgrading:** nothing to do. On the first start Tippy moves your existing progress into the first child automatically and keeps a safety copy named `tippy.db.before-profiles-<time>` in the `data` folder.

### Added
- Several children: a Children tab in the parent area (add up to 6, rename, change picture, remove, choose which child to show), a "Who is playing?" screen at start-up with a switch button, separate progress, language and play limits per child, and a switch button on the goodnight screen so a sibling can still play.
- Restore a backup (parent area, Data tab): into the shown child or as a new child. The file is checked strictly (bad rows are skipped and counted, no PIN or household setting can come in), a safety copy of the replaced data is kept, and the replacement is all-or-nothing. Backups from 0.9.x still work.
- Saved browser test suite (`tests/browser`, `pytest -m browser`) that plays every level in English and German, stresses the app like a child would, and checks limits, children, restore and the parent area. Runs in CI.
- CI: tests on Windows, CodeQL scanning, security policy, code owners, issue templates.

### Changed
- Storage is one database per child (`data/profiles/<id>.db`) plus a family database (`data/family.db`) for the PIN, the helper model and the shared online-helper usage counter.
- Importing `backend.app` no longer creates the app or opens the data folder, so tests can never touch real data.

### Fixed
- Database connections were never closed at the end of a `with` block, which on Windows blocked moving a damaged database aside.

## [0.9.1] - 2026-09-19

No change to how Tippy plays. Packaging, licensing and process improvements after the 0.9.0 test pass.

### Changed
- Release pipeline: a version tag builds and checks the zip and creates a draft GitHub release; zip checks live in `scripts/check_zip.sh`.
- Python packages are pinned to exact tested versions (Dependabot proposes bumps, CI must pass).

### Added
- MIT license, and the SIL Open Font License text for the bundled Nunito font.
- CI pipeline (GitHub Actions): checks on Linux and macOS, zip build and content check, Dependabot, pull request template.

## [0.9.0] - 2026-09-19

First feature-complete version. Everything below was built in eight milestones and then tested with scripted browser play-throughs; the manual checks in `TEST-CHECKLIST.md` are still open.

### Added
- Worlds: Mouse Meadow, Keyboard Kingdom, Letter Land (adaptive letters), Word Woods, Sentence Sky, Computer Basics Cove, Free Play Studio.
- Stars, stickers, daily streak, sticker album; no punishment for mistakes.
- English and German interface and voice; QWERTY and QWERTZ keyboards; finger-zone colours.
- Parent area behind a PIN: progress charts, keyboard heat map, weekly summary, settings, backup, reset.
- Break suggestions and a daily play limit that only the parent can lift.
- Text size, reduced motion and a quick mute button.
- Ask Tippy (picture questions, off by default).
- Optional online helper (OpenRouter, free models) with validation, caching and a built-in fallback bank; the shared version is offline only (`LLM_MODE=off`).
- First-run setup (language, PIN, name, daily limit), PIN stored as a salted hash, change PIN.
- One-click start for macOS, Windows and Linux; zip builder (`scripts/make_zip.py`).
- Git workflow: commit-message convention, hooks, shared `scripts/check.sh`, `CONTRIBUTING.md`.

### Fixed (found by the test pass)
- Double-clicking the window lesson's close button crashed the lesson.
- Leaving a game with Home could pop up a stale "level done" screen later.
- Names with accents were silently refused.
- The backup file contained the PIN hash.
- The goodnight screen never cleared when a new day began.
- Start scripts needed internet on every start.
- A damaged database stopped Tippy from starting.
- Layouts overflowed on short screens.
