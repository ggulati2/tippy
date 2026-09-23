# Advanced setup

Optional extras for parents comfortable editing a file or a terminal. Nothing here is needed to use Tippy day to day; see the main [README](../README.md) for that.

## Online helper (optional)

The version you download or unzip is offline only: no online-helper tab, no key to enter. This section is for turning it on yourself, on a source checkout.

Tippy works fully without it, using its built-in words and sentences. With it, Tippy also gets fresh practice words themed on animals, space, dinosaurs and vehicles, plus varied encouragement lines. Everything it writes is checked before the child sees it, and the child's name is never sent — only letters, theme, language and the moment ("finished a game").

By default Tippy uses **free** OpenRouter models, so no credit card is needed:

1. Go to https://openrouter.ai and sign in.
2. Open **Keys**, click **Create Key**, and copy it (starts with `sk-or-`).
3. In the Tippy folder, open the hidden `.env` file (Finder: `Cmd+Shift+.` to show hidden files, or `open -e .env` in Terminal from the Tippy folder) and set:
   ```
   OPENROUTER_API_KEY=sk-or-...your key...
   LLM_MODE=live
   ```
4. Restart Tippy, open the parent area and press **Test connection**.

**Free limits:** a free OpenRouter account allows 20 requests a minute and 50 a day; Tippy requests in batches and caches them, so this is normally plenty. `DAILY_REQUEST_CAP=45` in `.env` keeps it under that, and a failed request backs off for 10 minutes. Adding 10+ USD of credit raises the daily limit to 1000 and unlocks paid models (a few cents a month for Tippy's tiny requests).

**Choosing a model:** the defaults are `nvidia/nemotron-3-super-120b-a12b:free` (main) and `deepseek/deepseek-v4-flash-0731:free` (backup). To compare models on Tippy's own tasks with your key (4 requests per model):
```
source .venv/bin/activate
python scripts/try_models.py
```
It prints how many items from each model passed Tippy's safety checks and how long each took. Put the winner in `OPENROUTER_MODEL` in `.env`.

If the internet is down or the key stops working, the child notices nothing — Tippy falls back to its built-in content.

### `.env` settings

| Setting | Meaning |
| --- | --- |
| `PARENT_PIN` | Optional; normally left out, since Tippy asks for a PIN on first start. |
| `APP_LANGUAGE` | `en` or `de`, used only for the first start. |
| `LLM_MODE` | `off` (default), `live` (real OpenRouter), `mock` (fake, for development). |
| `OPENROUTER_API_KEY` | Your key. Stays on this computer. |
| `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL` | Main and backup model; any id from openrouter.ai/models with JSON output works. |
| `DAILY_REQUEST_CAP` | Requests per day (default 45). |

Change the mascot's name and colours in `branding.json`, then run `python scripts/sync_branding.py` (it writes `frontend/js/config.js`, which is what the app actually loads).

## Building the packaged apps yourself

The Mac and Windows apps you can download from Releases are ready to use; these are the commands behind them, for building your own.

- **Mac** (build on the Mac it should run on): `scripts/build_mac.sh` → `dist/Tippy.app` and a zip. Runs on the CPU it was built on (Intel or Apple silicon). The Apple silicon build on the Releases page is built by `.github/workflows/mac-app.yml`, since this project's own Mac is Intel.
- **Windows**: `windows\build.bat` (needs Python and, for the single installer file, Inno Setup) → `dist\Tippy\Tippy.exe` and, if Inno Setup is installed, `Tippy-Setup-<version>.exe`. GitHub Actions builds this automatically on every release; see `.github/workflows/windows-app.yml`.

Both bundle the same code and content; nothing about the child's data lives inside either app (see the README's Mac and Windows sections for where it does live).

## Sharing a source zip with other families

```
python scripts/make_zip.py
```
(inside the activated `.venv`). It packs only what git tracks — your `.env`, API key and a child's progress are never included, and it refuses to pack anything that looks like an API key. Send the zip; each family follows the README's "Get it → From source" steps.

## Tippy's voice

The recordings in `frontend/voice` are one AI-generated voice (OpenAI text-to-speech) per language; see `frontend/voice/LICENSE.md`. The child's own name and a few unusual words are still read by the computer's own voice. To record more, or a different voice: `scripts/make_voice_cloud.py` (needs an OpenAI key) — see the notes at the top of that file.

## Backups and moving to another computer

- **Back up:** parent area → *Data* → save a JSON file (progress, stickers, settings; no PIN, no keys). *Restore* reads it back into the same child or a new one. A safety copy of the previous data is kept automatically.
- **Move to another computer:** unzip Tippy there, then either copy the `data/` folder over (Tippy closed) or restore a saved backup.
- **Forgot the PIN:** stop Tippy and delete the `data/` folder — this also erases progress, so back up first if you can still reach the parent area.

## Contributing

Git workflow, commit rules and the release process: see [CONTRIBUTING.md](../CONTRIBUTING.md).
