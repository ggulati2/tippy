# Building Tippy

How the downloadable apps are made (docs/REVAMP_BRIEF.md section 4.6). Families and schools do not need any of
this: they download a finished app from the Releases page. This page is for whoever builds a release.

## What gets built

| System | Built by | Result | Where the family's data goes |
|---|---|---|---|
| Windows | `.github/workflows/windows-app.yml` (or `windows\build.bat` on Windows) | `Tippy-Setup-<version>.exe` (installer) and a portable zip with `Tippy.exe` | `%APPDATA%\Tippy` |
| Mac, Apple silicon | `.github/workflows/mac-app.yml` | `Tippy-<version>-macos-arm64.zip` with `Tippy.app` | `~/Library/Application Support/Tippy` |
| Mac, Intel | `scripts/build_mac.sh` on an Intel Mac | `Tippy-<version>-macos-x86_64.zip` | as above |
| Linux (x86_64) | `.github/workflows/linux-app.yml` | `Tippy-<version>-linux-x86_64.tar.gz` with a `Tippy` folder | `~/.local/share/tippy` |

All of them are the same PyInstaller recipe (`packaging/tippy.spec`): a copy of Python, Tippy's libraries and its
`frontend/` and `content/` folders. Nothing needs to be installed, and the app works without internet. The data lives
outside the app, so installing a new version keeps every child's progress.

PyInstaller can only build for the system (and processor) it runs on, which is why each system has its own build.

## Making a release

1. Update `VERSION` and `CHANGELOG.md` on `main`, then push a tag with the same number, for example `git tag v0.15.0`
   and `git push origin v0.15.0`.
2. `release.yml` checks the tag, runs every test, and makes a **draft** release with the source zip.
3. The Windows, Mac (Apple silicon) and Linux workflows build their apps, test each one (below) and add them to the
   same draft.
4. Build the Intel Mac app by hand with `scripts/build_mac.sh` and add its zip to the draft.
5. Nothing is public until you open the draft on GitHub and press "Publish release".

A test build without a release: Actions tab → pick a workflow → "Run workflow". Its files are kept for 14 days.

## How a built app is tested

- **Smoke test** (every build, in CI): `packaging/smoke_mac.sh <path to the app's program>` (Mac and Linux) or
  `windows\smoke-test.ps1`. It starts the app without a window and checks it serves Tippy, its protective headers,
  the settings, the scripts, and the built-in content.
- **The whole browser test suite against the built app** (by hand, before a release):
  `TIPPY_APP_BINARY=dist/Tippy.app/Contents/MacOS/Tippy python -m pytest -m browser`. The same 22 tests that play
  every level and drive the parent area then run against the app instead of the source code.

## The window

The packaged app starts Tippy's small local server and opens it in Chrome or Edge in **kiosk mode** (fullscreen, no
address bar, closing the window quits Tippy). Without Chrome or Edge it opens the computer's normal browser.

The brief asks for a native window (`pywebview`) first, with the browser as fallback. That is **not switched on yet**,
on purpose: Tippy depends on things a browser window is known to do well and a native web view on each system does
not always do the same way — saving a backup or a CSV file (downloads), the print dialog for certificates, starting
the recorded voice before the first tap (autoplay), and a real fullscreen kiosk a child cannot leave. Each would need
checking by hand on real Windows and Mac machines. Until then the kiosk browser stays the default.

## Portable mode (schools, USB sticks)

Create an empty folder called `tippy-data` next to the program (next to `Tippy.exe` on Windows, next to `Tippy.app`
on a Mac) and put a *school* licence in `tippy-data/data/licence.json`. Tippy then keeps everything in that folder.
Without a school licence the folder is ignored and Tippy uses the normal user folder.

## Licences

`scripts/make_licence.py` makes licence files (see its header). It needs the private signing key in
`~/.config/tippy/licence-signing-key`, which is never part of the project, and the `cryptography` package from
`requirements-dev.txt`. The app itself checks signatures without `cryptography` (`backend/ed25519.py`): as a compiled
library it broke the Intel Mac build, and the check needs only a few lines of plain Python.

## Signing

The apps are not code-signed with paid certificates (an Apple Developer ID, a Windows code-signing certificate), so
the first start shows a warning: on a Mac "Open Anyway" in System Settings → Privacy & Security, on Windows "More info"
→ "Run anyway". The README explains both. Signing is worth doing before handing Tippy to schools, whose IT often blocks
unsigned programs.
