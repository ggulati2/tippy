# Changelog

All notable changes to Tippy. Format: [Keep a Changelog](https://keepachangelog.com), versions: [Semantic Versioning](https://semver.org).

## [Unreleased]

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
