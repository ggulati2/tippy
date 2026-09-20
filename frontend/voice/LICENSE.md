# Licence of the voice recordings

The audio files in this folder (`*.ogg`) are speech made with free voices for **Piper** (a text-to-speech program by the
Rhasspy / Open Home Foundation project; voices from https://huggingface.co/rhasspy/piper-voices) and then raised a little
in pitch. Each language has its own voice and its own licence:

| Folder | Voice | Made from | Licence |
| --- | --- | --- | --- |
| `en/` | `en_US-hfc_female-medium` | HiFi-CAPTAIN corpus (Mike Ng) | **CC BY-NC-SA 4.0** (https://creativecommons.org/licenses/by-nc-sa/4.0/) |
| `de/` | `de_DE-thorsten-high` | Thorsten-Voice (Thorsten Müller, https://github.com/thorstenMueller/Thorsten-Voice) | **CC0** (public domain) |
| `es/` | `es_ES-sharvard-medium`, speaker 1 | Sharvard corpus, University of Edinburgh (https://datashare.ed.ac.uk/handle/10283/574; Aubanel et al., 2014) | **CC BY 3.0** (http://creativecommons.org/licenses/by/3.0/) |

What this means for you:

- **English recordings:** free to use, copy and share for **non-commercial** use, if you keep this notice and share any
  changes under the same licence. You may **not sell** Tippy together with these recordings.
- **German recordings:** no restrictions (a credit to Thorsten Müller is appreciated).
- **Spanish recordings:** free to use and share, even commercially, if you credit the Sharvard corpus as above.
- The rest of Tippy (the program code) is under the MIT licence in the main LICENSE file; this folder is the exception.

If Tippy is ever to be sold, delete `en/` (Tippy then uses the computer's voice for English) or record a new English
voice with a permissively licensed model using `scripts/make_voice.py`.
