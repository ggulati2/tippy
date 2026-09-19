# Tippy: a computer and typing helper for a 6-year-old

Runs only on your computer. Nothing is sent anywhere except (from Milestone 4, optional) short practice requests to OpenRouter, and those never contain the child's name.

## Start it (macOS)

1. Install Python 3.11 or newer (check with `python3 --version` in Terminal).
2. Install Google Chrome (Tippy opens it fullscreen). Without Chrome or Edge it uses your normal browser.
3. Double-click **start.command**. The first time, macOS may say it cannot be opened: right-click the file, choose **Open**, then **Open** again.
4. The first start takes about a minute (it installs what it needs). After that it starts in seconds.

Windows: double-click `start.bat`. Linux: run `./start.sh`.

## Use it

- The child taps **Play** and sees the world map. **Mouse Meadow** is playable (4 short games: pop balloons, drag shapes into baskets, double-click eggs, scroll to a treasure). Each finished game gives stars and sometimes a sticker. **Keyboard Kingdom** (find the glowing key, then games for Space, Enter, Backspace and Shift) and **Letter Land** (type the big letter, guided by an on-screen keyboard with a colour for each finger) are playable too. The other worlds say "Coming soon!".
- The map shows total stars, the sticker album (📖) and, after 2 days in a row, a streak (🔥). Missing a day just restarts the streak quietly.
- Letter Land starts with just A and S. New letters appear by themselves when the child gets about 80% of the last 20 keys right, and the newest letter quietly goes away again if things get hard. Wrong keys only get a friendly hint.
- Finishing all the games of a world unlocks the next world. In the parent area, **Unlock all worlds** opens everything.
- **Parent area:** tap the small pale gear in the top-right corner and enter the PIN (default `1234`, change it in `.env`). There you can switch English/German, the keyboard shape (QWERTY/QWERTZ), voice and sounds, uppercase or lowercase letters, and **Exit Tippy**.
- The app can only be closed with the PIN. If it ever gets stuck: press `Ctrl+C` in the Terminal window that opened.

## Turn on the online helper (optional)

Tippy works fully without it, using its built-in words and sentences. With it, Tippy also gets fresh practice words themed on animals, space, dinosaurs and vehicles, plus varied encouragement lines. Everything the LLM writes is checked before the child sees it, and the child's name is never sent.

1. Go to https://openrouter.ai and sign in.
2. Open **Credits** and add a small amount (for example 5 USD). Tippy's requests are tiny, so this should last a very long time.
3. Open **Keys**, click **Create Key**, and copy the key (it starts with `sk-or-`).
4. In the Tippy folder, open the hidden `.env` file. In Finder press `Cmd+Shift+.` to show hidden files, or run this in Terminal from the Tippy folder: `open -e .env`
5. Set these two lines (paste your key after the `=`), then save:
   ```
   OPENROUTER_API_KEY=sk-or-...your key...
   LLM_MODE=live
   ```
6. Restart Tippy, open the parent area and press **Test connection**. You should see a green tick with the model name.

`DAILY_REQUEST_CAP` in `.env` (default 200) is a safety brake: Tippy never sends more requests than that per day. The parent area shows today's requests and cost. If the internet is down or the key runs out of credit, the child notices nothing: Tippy switches to the built-in content.

## Configure

Edit the `.env` file in this folder (created from `.env.example` on first start), then restart.

| Setting | Meaning |
| --- | --- |
| `PARENT_PIN` | PIN for the parent area and exit. **Change it.** |
| `APP_LANGUAGE` | `en` or `de` for the first start |
| `LLM_MODE` | `mock` = no internet, no cost. `live` = real OpenRouter |
| `OPENROUTER_API_KEY` | Your key. Stays on this computer, never shown in the browser. |
| `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL` | Main and backup model. The defaults are cheap and fast; any id from openrouter.ai/models that supports JSON output works. |
| `DAILY_REQUEST_CAP` | Most requests per day (default 200) |

Change the mascot's name and colours in `frontend/js/config.js`.

## Troubleshooting

- **Nothing opens:** open http://127.0.0.1:8765 in any browser while the Terminal window is running.
- **"Address already in use":** Tippy is already running. Close it from the parent area, or quit the old Terminal window.
- **Something went wrong:** details are in `logs/tippy.log`. The child only sees a smiley.
- **Test connection says `HTTP 401`:** the key is wrong. **`HTTP 402`:** no credit left. **`no API key`:** `.env` is missing the key or `LLM_MODE` is still `mock`. **`ReadTimeout`:** slow internet; Tippy keeps using built-in content.
- **Reset everything (stars, stickers, settings):** stop Tippy and delete the `data/` folder.

## For developers

```
source .venv/bin/activate
python -m pytest
```
