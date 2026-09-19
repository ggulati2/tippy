# Working on Tippy: the git workflow

This page is the "how we change the code" rulebook. It is short on purpose. The same checks will later run in the CI pipeline, so what passes here passes there.

## One-time setup

```
git clone <repository-url> && cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
scripts/setup-dev.sh          # turns on the git hooks
```

## The everyday loop

1. **Start from an up-to-date `main`:** `git switch main && git pull`
2. **Make a branch for one change:** `git switch -c fix/window-lesson-double-click`
   Branch names: `feat/...`, `fix/...`, `docs/...`, `chore/...`.
3. **Work in small steps and commit often.** Each commit does one thing and leaves the app working.
4. **Check before you push:** `scripts/check.sh` (about 15 seconds; the hooks run it for you).
5. **Push the branch and open a pull request** into `main`. Fill in the checklist. Merge with *squash*, so `main` gets one clean commit per change.
6. **Never commit straight to `main`** once the repository is on a server (branch protection will enforce it).

## Commit messages (Conventional Commits)

The first line is checked by a hook:

```
type(scope): short summary in the imperative, at most 72 characters
```

| Type | Use it for |
| --- | --- |
| `feat` | something new the user or parent can do |
| `fix` | a bug fix |
| `docs` | README, comments, checklists |
| `refactor` | code change with no behaviour change |
| `test` | adding or fixing tests |
| `perf` | making it faster |
| `build` / `ci` | packaging, dependencies, pipeline |
| `chore` | anything else (housekeeping) |
| `style` | formatting only |
| `revert` | undoing an earlier commit |

Scope is optional and is the area: `typing`, `parent`, `limits`, `llm`, `setup`, `mouse`, `i18n`...
Add `!` after the type for a change that breaks existing data or settings: `feat(db)!: rename progress table`.

Good: `fix(basics): count a double-click on the close button once`
Bad: `fixed stuff`, `Update`, `wip`

The body (optional) says **why**, not what. Keep secrets, the child's name and real API keys out of messages and code.

## What the CI pipeline checks

On every pull request and every push to `main`, GitHub Actions (`.github/workflows/ci.yml`) runs `scripts/check.sh` on a clean machine (Python 3.11 and 3.13 on Linux, 3.13 on macOS), then builds the zip and checks that it contains the app and nothing private. Look at the **Actions** tab, or the green tick or red cross on your pull request. Fix red before merging. The built zip is kept for 14 days under the run's *Artifacts*.

## What the hooks check

| When | What | Command |
| --- | --- | --- |
| `git commit` | no secrets or private files, Python and JavaScript syntax, English and German texts match, message format | `scripts/check.sh fast` |
| `git push` | all of the above plus the automatic tests | `scripts/check.sh` |

If a hook stops you, read its message: it says what to fix. Do not bypass with `--no-verify`.

## Rules that keep the child safe (do not break these in any change)

- The child's name and anything typed by the child never go to the LLM or to a log.
- Text from the LLM is validated on the server and shown only with `textContent`.
- The server listens on `127.0.0.1` only. `.env`, databases and logs are never committed.
- Anything a game does after a delay uses `later()` (see `frontend/js/app.js`), so leaving a game cancels it.

## Versions and releases

- Version numbers follow [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`. The current one is in the `VERSION` file.
  - PATCH (0.9.1): bug fixes only. MINOR (0.10.0): new features that keep saved data working. MAJOR (1.0.0): changes that break saved data or settings.
- To release: update `VERSION` and `CHANGELOG.md`, commit as `chore(release): 0.9.1`, then tag it:
  `git tag -a v0.9.1 -m "Tippy 0.9.1" && git push --tags`
- `python scripts/make_zip.py` builds `Tippy-<version>.zip` from what git tracks.

## Where things are

`backend/` server, `frontend/` screens, `content/` built-in words, `tests/` automatic tests, `scripts/` launcher and tools, `TEST-CHECKLIST.md` manual checks, `CLAUDE.md` design notes for the AI assistant.
