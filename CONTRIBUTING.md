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
6. **You cannot commit straight to `main`.** GitHub branch protection on `main` requires a pull request, four green CI checks (Python 3.11 and 3.13 on Linux, 3.13 on macOS, and the zip build), an up-to-date branch and a linear history. Force-pushes and deleting `main` are blocked, and the rules apply to the repository owner too. Only squash merging is enabled, and merged branches are deleted automatically.

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

## Browser tests

`python -m pytest -m browser -v` (about a minute, needs Chrome, Chromium or Edge) plays the real app in headless Chrome, each test on its own fresh server: every level in English and German (with mistakes, double-clicks and a check that every screen fits the window), a "child cannot break it" stress test (Home at any moment, key mashing, shortcuts), the break and daily limit, and the whole parent area. The scripts are in `tests/browser/js`; add a `T.check(...)` there when you fix a bug that only shows in the browser. Set `CHROME_PATH` if Chrome is somewhere unusual. They are left out of the normal quick run (`pytest.ini`) and run in CI as *Browser tests (Chrome)*.

## What the CI pipeline checks

On every pull request and every push to `main`, GitHub Actions (`.github/workflows/ci.yml`) runs `scripts/check.sh` on a clean machine (Python 3.11 and 3.13 on Linux, 3.13 on macOS), then plays the app in headless Chrome, runs the tests on Windows, builds the zip and checks that it contains the app and nothing private. CodeQL scans the code for vulnerabilities (Security tab). Look at the **Actions** tab, or the green tick or red cross on your pull request. Fix red before merging. The built zip is kept for 14 days under the run's *Artifacts*.

## Security and performance checks

- `.github/workflows/security.yml`: pip-audit (known vulnerabilities in `requirements*.txt`), bandit (`bandit -r backend scripts -ll`; add `# nosec Bxxx - reason` only with a real reason), dependency review on pull requests, OWASP ZAP against a running server (report only, download the *zap-report* artifact). Run the first two locally with `pip install -r requirements-security.txt`.
- `.github/workflows/performance.yml`: `python scripts/loadtest.py` (server; budgets at the top of the file, `TIPPY_BUDGET_FACTOR=2` for slow machines) and `pip install -r requirements-perf.txt && python -m pytest -m perf -v` (browser speed; budgets in `tests/perf/test_browser_perf.py`). Both are left out of the quick run.
- `tests/test_security.py` runs with the normal tests: headers, private files, PIN on every parent endpoint, hostile input, no dangerous JavaScript patterns.

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

## Dependencies

`requirements.txt` (what Tippy needs) and `requirements-dev.txt` (plus test tools) use **exact versions** (`==`). Dependabot opens a monthly pull request with newer versions; CI runs the tests on it. Merge it when green and, for big jumps (a new major version), also click through the app once. To update a pin by hand: change the number, run `pip install -r requirements-dev.txt` and `scripts/check.sh`.

## Versions and releases

- Version numbers follow [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`. The current one is in the `VERSION` file.
  - PATCH (0.9.1): bug fixes only. MINOR (0.10.0): new features that keep saved data working. MAJOR (1.0.0): changes that break saved data or settings.
- **To release** (the pipeline does the building; you only prepare the version and publish):
  1. Branch `chore/release-0.9.1`. Set `VERSION` to `0.9.1`. In `CHANGELOG.md` rename *Unreleased* to `[0.9.1] - <date>` and add a fresh empty *Unreleased* above it.
  2. Pull request `chore(release): 0.9.1`, wait for green checks, squash-merge.
  3. Tag the merge commit on `main` and push the tag: `git switch main && git pull && git tag -a v0.9.1 -m "Tippy 0.9.1" && git push origin v0.9.1`
  4. The **Release** workflow runs all checks, builds `Tippy-0.9.1.zip`, checks its contents and creates a **draft** GitHub release with the zip, a `SHA256SUMS.txt` file and the changelog text.
  5. Open the draft on GitHub (Releases), read it, and click **Publish release**. Nothing is public before that click. Versions below 1.0.0 are marked as pre-releases.
  - Dry run any time: Actions tab, *Release*, *Run workflow*. It builds everything and publishes nothing.
- `python scripts/make_zip.py` builds `Tippy-<version>.zip` from what git tracks.

## Where things are

`backend/` server, `frontend/` screens, `content/` built-in words, `tests/` automatic tests, `scripts/` launcher and tools, `windows/` the Windows installer (built in CI), `packaging/` the app recipe, `TEST-CHECKLIST.md` manual checks, `CLAUDE.md` design notes for the AI assistant.
