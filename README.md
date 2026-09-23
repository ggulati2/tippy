# Tippy

A friendly, offline, computer-skills app for young kids: mouse, keyboard, typing, and gentle first lessons on how a computer works. Runs only on your machine — nothing is sent anywhere unless a parent turns on an optional online helper (see [Advanced setup](docs/ADVANCED.md)). Available in English, German and Spanish.

## Get it

**Windows — no install needed:** download `Tippy-Setup-<version>.exe` from [Releases](https://github.com/ggulati2/tippy/releases), run it (Windows will show a blue "protected your PC" warning the first time — click **More info**, then **Run anyway**), and follow the installer. Prefer not to install anything? Use the `-windows-portable.zip` instead and double-click `Tippy.exe` inside it.

**Mac:** download the zip for your Mac from [Releases](https://github.com/ggulati2/tippy/releases) (`-macos-arm64` for Apple silicon, `-macos-x86_64` for Intel — Apple menu → About This Mac tells you which), unzip and double-click `Tippy.app`. Or build your own with `scripts/build_mac.sh` (needs Python 3.11+ and internet the first time). Either way, macOS will ask you to allow it once: **System Settings → Privacy & Security → Open Anyway**.

**From source (any OS):** install Python 3.11+ and Google Chrome, then double-click `start.command` (Mac), `start.bat` (Windows) or run `./start.sh` (Linux). The first start needs internet for a minute to set itself up; after that it's fully offline.

On the very first start, a parent picks a language, sets a **PIN**, the child's name and a daily play limit — all changeable later in the parent area.

## What's inside

Twelve "worlds," each a handful of short, playful levels that never punish a wrong answer — just a friendly hint and another try. A world unlocks once the skill before it is learned; a parent can unlock any of them by hand.

| World | Teaches |
| --- | --- |
| 🐭 Mouse Meadow | Click, drag, double-click, scroll |
| 🖌️ Paint Place | Painting with the mouse |
| ⌨️ Keyboard Kingdom | Finding keys: Space, Enter, Backspace, Shift, arrows |
| 🤖 Robot Helper | Simple arrow-card "programs" — a first taste of coding |
| 🔤 Letter Land | Typing letters, with on-screen finger guidance |
| 🔢 Number Land | Typing digits, counting, adding |
| 🌳 Word Woods | Typing short words with a picture |
| ☁️ Sentence Sky | Typing short sentences, their own name, a favourite word |
| 🌐 Internet Island | A safe pretend browser: links, search, spotting pop-ups |
| 🖥️ Computer Cove | What a screen, mouse, keyboard, window and file are; online safety |
| 🗂️ Desktop Dock | A pretend desktop: open, drag into folders, save, the trash bin |
| 🎨 Free Play Studio | Typing any word to make a sticker scene |

Progress, stars and a growing sticker album carry the child along; a small daily streak never guilts a missed day. Everything the child types stays on this computer.

## The parent area

Tap the small pale gear, enter the PIN. Four tabs: **Progress** (streak, accuracy, a per-key mistake heat map, a plain-language weekly summary), **Settings** (language, keyboard shape, voice, sounds, child's name, break and daily limits, which worlds are unlocked), **Online helper** (off by default — see [Advanced setup](docs/ADVANCED.md)), **Data** (backup, restore, reset). Up to 6 children can share one Tippy, each with their own progress and a "Who's playing?" picker. Exiting Tippy always needs the PIN.

## Privacy

Everything — progress, settings, backups — stays on this computer. The server only listens on `127.0.0.1`, so nothing on your network can reach it. Nothing is sent anywhere unless a parent explicitly turns on the online helper, and even then only a practice theme and language are sent, never the child's name or anything they typed.

## Troubleshooting

- **Nothing opens:** open http://127.0.0.1:8765 in any browser while Tippy is running.
- **"Address already in use":** Tippy is already running — close it from the parent area first.
- **Something went wrong:** the child only ever sees a smiley; details are in `logs/tippy.log`.
- **No sound or voice:** check the 🔊 button isn't showing 🔇, then Settings → *Voice* / *Sounds*.
- **Start over:** stop Tippy and delete the `data/` folder (this erases progress — back up first in the parent area's *Data* tab if you can).

More setup help, including the online helper, building your own Mac/Windows app, and backups, is in [Advanced setup](docs/ADVANCED.md).

## Limits to know about

Languages: English, German, Spanish (Spain). Keyboards: QWERTY, QWERTZ, QWERTY+Ñ. The German and Spanish texts haven't been checked by a native-speaker teacher yet. Best in Chrome; other browsers work but skip the fullscreen kiosk window.

## License

[MIT](LICENSE) — free to use, change and share, including with other families. The bundled font Nunito is under the SIL Open Font License (see `THIRD-PARTY-NOTICES.md`). Tippy's voice recordings have their own notice in `frontend/voice/LICENSE.md`. No warranty.

---

Contributing, testing and the release process: [CONTRIBUTING.md](CONTRIBUTING.md) · [TEST-CHECKLIST.md](TEST-CHECKLIST.md)
