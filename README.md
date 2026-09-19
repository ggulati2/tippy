# Tippy: a computer and typing helper for a 6-year-old

Runs only on your computer. Nothing is sent anywhere except (from Milestone 4, optional) short practice requests to OpenRouter, and those never contain the child's name.

## Start it (macOS)

1. Install Python 3.11 or newer (check with `python3 --version` in Terminal).
2. Install Google Chrome (Tippy opens it fullscreen). Without Chrome or Edge it uses your normal browser.
3. Double-click **start.command**. The first time, macOS may say it cannot be opened: right-click the file, choose **Open**, then **Open** again.
4. The first start takes about a minute (it installs what it needs). After that it starts in seconds.

Windows: double-click `start.bat`. Linux: run `./start.sh`.

## Use it

- The child taps **Play** and sees the world map. **Mouse Meadow** is playable (4 short games: pop balloons, drag shapes into baskets, double-click eggs, scroll to a treasure). Each finished game gives stars and sometimes a sticker. **Keyboard Kingdom** (find the glowing key, then games for Space, Enter, Backspace and Shift) and **Letter Land** (type the big letter, guided by an on-screen keyboard with a colour for each finger) are playable too. **Word Woods** (type short words that have a picture: a cat, a sun, a dog) and **Sentence Sky** (type short sentences, then their own name and a favourite word) are playable too. Words and sentences are read aloud after each success, and tapping the picture reads the word again. **Computer Cove** (six tiny lessons: screen, mouse and keyboard; opening and closing a window; files and folders; screen breaks; asking a grown-up before clicking; keeping name, address and passwords secret online) and the **Free Play Studio** (type any word, press Enter or ✨, and Tippy turns it into a scene of dancing stickers; unknown words make the letters dance) are playable too. Everything typed in Free Play stays on this computer.
- The map shows total stars, the sticker album (📖) and, after 2 days in a row, a streak (🔥). Missing a day just restarts the streak quietly.
- In the parent area, type the child's **first name** and a **favourite word**. Sentence Sky asks the child to type them, and Tippy uses the name in greetings. Both stay on this computer and are never sent to the online helper. If they are empty, Sentence Sky uses "Tippy" and "fun".
- Letter Land starts with just A and S. New letters appear by themselves when the child gets about 80% of the last 20 keys right, and the newest letter quietly goes away again if things get hard. Wrong keys only get a friendly hint.
- Finishing all the games of a world unlocks the next world. In the parent area, **Unlock all worlds** opens everything.
- **Ask Tippy** (off by default; switch it on in the parent area under Settings) adds a 💬 button on the map. The child taps a picture (computer, internet, Wi-Fi, mouse, keyboard, screen, password, app, email, cloud) and Tippy answers in a few short sentences, read aloud. There is no typing box on purpose, so nothing personal can ever be sent to the online helper.
- **Breaks and limits:** after 10 minutes of active play (changeable) Tippy suggests a break, and the child can keep playing 5 more minutes. An optional daily limit stops play for the day; only the parent can lift it (gear icon, PIN, Settings).
- **Parent area:** tap the small pale gear in the top-right corner and enter the PIN (default `1234`, change it in `.env`). It has four tabs. **Progress:** streak, stars, stickers, minutes played, accuracy over time, a keyboard heat map of which keys cause mistakes (darker means more mistakes), and a weekly summary written from those numbers (by the online helper if it is on, otherwise by Tippy). Every chart has a *Show as table* option. **Settings:** language, keyboard shape, letters, voice, sounds, the child's name and favourite word, interests, break and daily limits, Ask Tippy, and which worlds are open. **Online helper:** status, model choice, cost and *Test connection*. **Data:** save a backup as a JSON file, or reset progress. **Exit Tippy** is always at the bottom.
- The app can only be closed with the PIN. If it ever gets stuck: press `Ctrl+C` in the Terminal window that opened.

## Turn on the online helper (optional, can be free)

Tippy works fully without it, using its built-in words and sentences. With it, Tippy also gets fresh practice words themed on animals, space, dinosaurs and vehicles, plus varied encouragement lines. Everything the LLM writes is checked before the child sees it, and the child's name is never sent. Only letters, themes, language and the moment ("finished a game") are sent, nothing personal.

By default Tippy uses **free** OpenRouter models (their ids end in `:free`), so no credit card is needed:

1. Go to https://openrouter.ai and sign in.
2. Open **Keys**, click **Create Key**, and copy the key (it starts with `sk-or-`).
3. In the Tippy folder, open the hidden `.env` file. In Finder press `Cmd+Shift+.` to show hidden files, or run this in Terminal from the Tippy folder: `open -e .env`
4. Set these two lines (paste your key after the `=`), then save:
   ```
   OPENROUTER_API_KEY=sk-or-...your key...
   LLM_MODE=live
   ```
5. Restart Tippy, open the parent area and press **Test connection**. You should see a green tick with the model name.

**Free limits:** OpenRouter allows a free account 20 requests a minute and 50 a day. Tippy asks for whole batches and remembers them, so this is normally plenty. `DAILY_REQUEST_CAP=45` in `.env` keeps Tippy safely under it, and if a request fails Tippy waits 10 minutes before trying again. Adding at least 10 USD of credit under **Credits** raises the free-model limit to 1000 a day. It is optional, and it also lets you use paid models (a few cents a month for Tippy's tiny requests).

**Which model is best?** The defaults are `nvidia/nemotron-3-super-120b-a12b:free` (main) and `deepseek/deepseek-v4-flash-0731:free` (backup). In our test on 19 Sep 2026 Nemotron was fastest and best in German, DeepSeek got the most English words through, and Google's free Gemma models were refused with `HTTP 429` (no free capacity). Free capacity changes, so re-run the script now and then. To compare models on Tippy's real tasks with your own key, run this in Terminal from the Tippy folder (it uses 4 requests per model):
```
source .venv/bin/activate
python scripts/try_models.py
```
It prints how many items from each model passed Tippy's safety checks and how long each answer took. Put the winner in `OPENROUTER_MODEL` in `.env`.

If the internet is down or the key stops working, the child notices nothing: Tippy switches to the built-in content.

## Configure

Edit the `.env` file in this folder (created from `.env.example` on first start), then restart.

| Setting | Meaning |
| --- | --- |
| `PARENT_PIN` | PIN for the parent area and exit. **Change it.** |
| `APP_LANGUAGE` | `en` or `de` for the first start |
| `LLM_MODE` | `mock` = no internet, no cost. `live` = real OpenRouter |
| `OPENROUTER_API_KEY` | Your key. Stays on this computer, never shown in the browser. |
| `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL` | Main and backup model. The defaults are free models; any id from openrouter.ai/models that supports JSON output works. |
| `DAILY_REQUEST_CAP` | Most requests Tippy sends per day (default 45, just under the free limit of 50) |

Change the mascot's name and colours in `frontend/js/config.js`.

## Troubleshooting

- **Nothing opens:** open http://127.0.0.1:8765 in any browser while the Terminal window is running.
- **"Address already in use":** Tippy is already running. Close it from the parent area, or quit the old Terminal window.
- **Something went wrong:** details are in `logs/tippy.log`. The child only sees a smiley.
- **Test connection says `HTTP 401`:** the key is wrong. **`HTTP 402`:** the model needs credit (a `:free` model does not). **`HTTP 429`:** the free daily or per-minute limit is used up; Tippy uses built-in content until it resets. **`no API key`:** `.env` is missing the key or `LLM_MODE` is still `mock`. **`ReadTimeout`:** slow internet; Tippy keeps using built-in content.
- **Reset everything (stars, stickers, settings):** stop Tippy and delete the `data/` folder.

## For developers

```
source .venv/bin/activate
python -m pytest
```
