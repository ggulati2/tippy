# Third-party material

Tippy's own code is under the [MIT License](LICENSE). It includes:

## Nunito (font)

`frontend/assets/fonts/Nunito.ttf`
Copyright 2014 The Nunito Project Authors (https://github.com/googlefonts/nunito).
Licensed under the SIL Open Font License, Version 1.1. The full license text is in `frontend/assets/fonts/OFL.txt`. The font is not covered by the MIT license.

## Twemoji (pictures)

`frontend/assets/twemoji/` — a picture for every emoji Tippy uses (`frontend/js/emoji-map.js` says which),
so the same colourful pictures show on every computer instead of the operating system's own emoji font
(which differs between computers, and on Windows is missing some pictures outright, such as flags).
Copyright the Twemoji contributors (https://github.com/jdecked/twemoji). Graphics licensed under
Creative Commons Attribution 4.0 International (CC BY 4.0); the parsing code Tippy itself uses
(`frontend/js/emoji.js`) is original and not from that project. Fetched with `scripts/fetch_emoji.py`.

## Python packages

Installed from PyPI when Tippy is set up, each under its own open-source license: FastAPI, Uvicorn, Pydantic and HTTPX (and the packages they need). See `requirements.txt` for the exact versions.
