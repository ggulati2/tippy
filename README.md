# Tippy: a computer and typing helper for a 6-year-old

Runs only on your computer and works fully offline. By default nothing is ever sent anywhere. (Developers can optionally switch on an online helper, see the end of this file.)

## Start it (macOS)

1. Install Python 3.11 or newer (check with `python3 --version` in Terminal).
2. Install Google Chrome (Tippy opens it fullscreen). Without Chrome or Edge it uses your normal browser.
3. Double-click **start.command**. The first time, macOS may say it cannot be opened: right-click the file, choose **Open**, then **Open** again.
4. The first start takes about a minute and needs internet once (it installs what it needs). After that it works offline and starts in seconds.
5. On the very first start Tippy asks you, the parent, to pick a language, choose a **parent PIN** (4 to 8 digits, keep it secret from the child), and set the child's first name and a **daily play limit** (30 minutes suggested). You can change all of it later.

Windows: double-click `start.bat`. Linux: run `./start.sh`.

## Use it

- The child taps **Play** and sees the world map. **Mouse Meadow** is playable (4 short games: pop balloons, drag shapes into baskets, double-click eggs, scroll to a treasure). Each finished game gives stars and sometimes a sticker. **Keyboard Kingdom** (find the glowing key, then games for Space, Enter, Backspace and Shift) and **Letter Land** (type the big letter, guided by an on-screen keyboard with a colour for each finger) are playable too. **Word Woods** (type short words that have a picture: a cat, a sun, a dog) and **Sentence Sky** (type short sentences, then their own name and a favourite word) are playable too. Words and sentences are read aloud after each success, and tapping the picture reads the word again. **Computer Cove** (six tiny lessons: screen, mouse and keyboard; opening and closing a window; files and folders; screen breaks; asking a grown-up before clicking; keeping name, address and passwords secret online) and the **Free Play Studio** (type any word, press Enter or ✨, and Tippy turns it into a scene of dancing stickers; unknown words make the letters dance) are playable too. Everything typed in Free Play stays on this computer.
- The map shows total stars, the sticker album (📖) and, after 2 days in a row, a streak (🔥). Missing a day just restarts the streak quietly.
- In the parent area, type the child's **first name** and a **favourite word**. Sentence Sky asks the child to type them, and Tippy uses the name in greetings. Both stay on this computer and are never sent to the online helper. If they are empty, Sentence Sky uses "Tippy" and "fun".
- Letter Land starts with just A and S. New letters appear by themselves when the child gets about 80% of the last 20 keys right, and the newest letter quietly goes away again if things get hard. Wrong keys only get a friendly hint.
- Finishing all the games of a world unlocks the next world. In the parent area, **Unlock all worlds** opens everything.
- **Ask Tippy** (off by default; switch it on in the parent area under Settings) adds a 💬 button on the map. The child taps a picture (computer, internet, Wi-Fi, mouse, keyboard, screen, password, app, email, cloud) and Tippy answers in a few short sentences, read aloud. There is no typing box on purpose, so nothing personal can ever be sent to the online helper.
- **Breaks and limits:** after 10 minutes of active play (changeable) Tippy suggests a break, and the child can keep playing 5 more minutes. An optional daily limit stops play for the day; only the parent can lift it (gear icon, PIN, Settings).
- **Parent area:** tap the small pale gear in the top-right corner and enter your PIN (change it under Settings, *Parent PIN*). It has four tabs. **Progress:** streak, stars, stickers, minutes played, accuracy over time, a keyboard heat map of which keys cause mistakes (darker means more mistakes), and a weekly summary written from those numbers (by the online helper if it is on, otherwise by Tippy). Every chart has a *Show as table* option. **Settings:** language, keyboard shape, letters, voice, sounds, the child's name and favourite word, interests, break and daily limits, Ask Tippy, and which worlds are open. **Online helper:** status, model choice, cost and *Test connection*. **Data:** save a backup as a JSON file, or reset progress. **Exit Tippy** is always at the bottom.
- **Accessibility:** in the parent area under Settings you can make all text bigger (three sizes) and switch animations off (Tippy also follows the computer's own "reduce motion" setting). The 🔊 button next to the gear silences sound and voice at once for the child, until Tippy is restarted. Voice and sounds can be switched off for good in Settings.
- The app can only be closed with the PIN. If it ever gets stuck: press `Ctrl+C` in the Terminal window that opened.

## Online helper (optional, for developers)

The version you share is offline only: there is no online helper tab and no key to enter. The rest of this section is for people who want the LLM features and are comfortable editing `.env`.

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
| `PARENT_PIN` | Optional. Normally leave it out: Tippy asks the parent to choose a PIN on the first start (saved as a hash). |
| `APP_LANGUAGE` | `en` or `de` for the first start |
| `LLM_MODE` | `off` (default) = built-in content only, nothing leaves the computer. `live` = real OpenRouter (needs a key). `mock` = fake, for development |
| `OPENROUTER_API_KEY` | Your key. Stays on this computer, never shown in the browser. |
| `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODEL` | Main and backup model. The defaults are free models; any id from openrouter.ai/models that supports JSON output works. |
| `DAILY_REQUEST_CAP` | Most requests Tippy sends per day (default 45, just under the free limit of 50) |

Change the mascot's name and colours in `frontend/js/config.js`.

## Sharing Tippy with other families

1. Commit your changes, then run `python scripts/make_zip.py` (inside the activated `.venv`). It creates `Tippy-<date>.zip`.
2. The zip contains only what git tracks, so **your `.env`, your API key and your child's progress are never included** (the script also refuses to pack anything that looks like an API key).
3. Send the zip. Each family follows "Start it" above: install Python 3.11+ and Chrome, unzip, double-click the start file. Everything else (PIN, language, name, daily limit) is asked on their first start, and their progress stays on their own computer.
4. Tell them: internet is needed once for the first start; after that Tippy works offline.

## Keeping it tidy and safe

- **Back up:** the parent area, tab *Data*, saves a JSON file with all progress. Or copy the `data/` folder while Tippy is closed.
- **Move to another computer:** copy the whole folder (or `git clone` it), copy your `.env` by hand, and double-click the start file. Progress moves with the `data/` folder.
- **Update:** with git, `git pull`, then restart. Your `.env` and `data/` are never touched.
- **Forgot the PIN:** stop Tippy and delete the `data/` folder. Tippy then asks for a new PIN on the next start (this also erases progress; save a backup first if you can still reach the parent area).
- **Privacy:** everything stays on this computer. Only when a developer sets `LLM_MODE=live`, short practice requests (letters, theme, language; never the child's name) go to OpenRouter. The server listens on 127.0.0.1 only, so other computers on your network cannot reach it. Do not commit `.env` (it is in `.gitignore`).
- **Sharing your key:** do not paste your key into chats or screenshots. If it leaks, delete it under Keys on openrouter.ai and create a new one.

## Troubleshooting

- **Nothing opens:** open http://127.0.0.1:8765 in any browser while the Terminal window is running.
- **"Address already in use":** Tippy is already running. Close it from the parent area, or quit the old Terminal window.
- **Something went wrong:** details are in `logs/tippy.log`. The child only sees a smiley.
- **Test connection says `HTTP 401`:** the key is wrong. **`HTTP 402`:** the model needs credit (a `:free` model does not). **`HTTP 429`:** the free daily or per-minute limit is used up; Tippy uses built-in content until it resets. **`no API key`:** `.env` is missing the key or `LLM_MODE` is still `mock`. **`ReadTimeout`:** slow internet; Tippy keeps using built-in content.
- **Text too small or animations too busy:** parent area, Settings, *Text size* and *Animations*.
- **No sound or voice:** check the 🔊 button is not showing 🔇, the Mac volume, and Settings *Voice* / *Sounds*. Voices come from macOS (System Settings, Accessibility, Spoken Content); a German voice must be installed to hear German.
- **Reset everything (stars, stickers, settings):** stop Tippy and delete the `data/` folder.

## Limits to know about

- One child profile per copy of Tippy (progress is shared by everyone who uses that computer's Tippy).
- Languages: English and German. Keyboard shapes: QWERTY and QWERTZ (no AZERTY yet).
- Tested with Chrome. Without Chrome or Edge Tippy opens your normal browser (not fullscreen; voices differ).

## Testing

`python -m pytest` runs the automatic tests. `TEST-CHECKLIST.md` lists what only a person can check (sound, real typing, fullscreen, a real child).

## For developers

```
source .venv/bin/activate
pip install -r requirements-dev.txt   # adds pytest
python -m pytest
```
