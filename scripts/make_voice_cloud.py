"""Records Tippy's voice with OpenAI's text-to-speech (gpt-4o-mini-tts), which can be told HOW to speak ("cheerful, like a
children's TV presenter"). A DEVELOPER tool, like make_voice.py: it is not part of the app; only the recordings are.

It needs an OpenAI API key with a little credit. The key is read from the environment variable OPENAI_API_KEY or from a
file (--key-file, default ~/.config/tippy/openai-key). It is never printed, never written into the project.

1. Samples (a few cents): the same greeting in several voices, to choose from. Listen to the files it writes.
       python scripts/make_voice_cloud.py --samples
2. Record everything for one language (finished clips are kept, so it can be stopped and started again):
       python scripts/make_voice_cloud.py --lang de --voice coral --replace
   `--replace` records a complete new set next to the old one and swaps it in only when all clips are done (a stopped run
   continues from where it stopped when started again with --replace; leave it out to only fill in what is missing).
   `--dry-run` only counts the texts and estimates the cost.

Same file names, index.json and licence rules as make_voice.py, so the app needs no change.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_voice  # noqa: E402  (text list, file names and tidy-up shared with the free-voice tool)

URL = "https://api.openai.com/v1/audio/speech"
MODEL = "gpt-4o-mini-tts"
PRICE_PER_MINUTE = 0.015        # US dollars, about (OpenAI lists $0.60 per million input tokens, $12 per million audio tokens)

# How the voice should sound. Written in the language of the recording so the accent comes out right.
INSTRUCTIONS = {
    "en": ("Voice of an excited, giggly, cheerful young girl in a cartoon for small children. Very high, bright and bubbly. Big "
           "exaggerated up-and-down intonation, joyful, smiling and laughing a little between phrases. Fast and lively, never calm "
           "or serious, never like a narrator. American English."),
    "de": ("Die Stimme eines aufgeregten, kichernden, fröhlichen kleinen Mädchens in einem Zeichentrickfilm für kleine Kinder. Sehr "
           "hell, hoch und sprudelnd. Große übertriebene Melodie beim Sprechen, voller Freude, lächelnd und zwischendurch ein "
           "bisschen lachend. Schnell und lebhaft, nie ruhig oder ernst, nie wie ein Erzähler. Deutsches Hochdeutsch."),
    "es": ("La voz de una niña pequeña emocionada, risueña y alegre en unos dibujos animados para niños pequeños. Muy aguda, "
           "brillante y burbujeante. Entonación muy exagerada y cantarina, llena de alegría, sonriendo y riéndose un poquito entre "
           "frases. Rápida y viva, nunca tranquila ni seria, nunca como un narrador. Español de España."),
}
# The voice is also raised by 15% (pitch only, not speed) to sound more like a child: the owner chose this from samples.
PITCH = 1.15
MIN_CLIP_BYTES = 300            # a real clip is always bigger; an empty one (only the file header) is redone
SAMPLE_TEXT = {
    "en": "Hi! I am Tippy. Let's learn to type together! Press the glowing key. Great job, that was super!",
    "de": "Hallo! Ich bin Tippy. Lass uns zusammen tippen lernen! Drücke die leuchtende Taste. Toll gemacht, das war super!",
    "es": "¡Hola! Soy Tippy. ¡Vamos a aprender a escribir juntos! Pulsa la tecla que brilla. ¡Muy bien, eso fue genial!",
}
SAMPLE_VOICES = ["coral", "shimmer", "nova", "marin"]


def api_key(path: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key and Path(path).expanduser().exists():
        key = Path(path).expanduser().read_text(encoding="utf-8").strip()
    if not key:
        sys.exit("No OpenAI key found. Set OPENAI_API_KEY or put the key in ~/.config/tippy/openai-key (see the top of this file).")
    return key


def speak(client: httpx.Client, key: str, text: str, voice: str, instructions: str) -> bytes:
    """One request. Waits and retries a few times when OpenAI says 'slow down' (429) or has a hiccup (5xx)."""
    payload = {"model": MODEL, "voice": voice, "input": text, "instructions": instructions, "response_format": "wav"}
    for attempt in range(600):                 # (waiting for the allowance to refill can take many rounds)
        try:
            response = client.post(URL, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=90)
        except httpx.TransportError:                # a network hiccup (timeout, connection reset): wait a little and try again
            time.sleep(min(2 ** min(attempt, 5), 30))
            continue
        if response.status_code == 200:
            return response.content
        if response.status_code == 429 and ("per day" in response.text or "insufficient_quota" in response.text):
            # Out of credit, or the daily allowance is used up. OpenAI says how long until the next request is allowed:
            # a few seconds (the allowance refills all day) means we simply wait; anything longer means stop and say so.
            message = response.json().get("error", {}).get("message", "limit reached")
            match = re.search(r"try again in (?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", message)
            wait = int(match.group(1) or 0) * 60 + float(match.group(2) or 0) if match else 1e9
            if "insufficient_quota" in response.text or wait > 300:
                sys.exit("OpenAI says: " + message[:300])
            time.sleep(wait + 1)
            continue
        if response.status_code in (429, 500, 502, 503, 504):
            time.sleep(min(2 ** min(attempt, 6), 60))
            continue
        sys.exit(f"OpenAI refused the request ({response.status_code}): {response.text[:200]}")     # the key is never in this text
    sys.exit("OpenAI kept saying 'try again later'. Run the command again; finished clips are kept.")


def ffmpeg_path() -> str:
    import imageio_ffmpeg          # only needed when recording (pip install imageio-ffmpeg)
    return imageio_ffmpeg.get_ffmpeg_exe()


def to_opus(ffmpeg: str, wav: bytes, target: Path, pitch: float = 1.0) -> None:
    """Raise the pitch (OpenAI gives 24 kHz), trim the silence at both ends and save as small mono Opus."""
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "clip.wav"
        source.write_bytes(wav)
        cleanup = (f"asetrate={round(24000 * pitch)},aresample=24000,atempo={1 / pitch:.4f},"
                   "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
                   "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse")
        for filters in (cleanup, cleanup.split("silenceremove")[0].rstrip(",") or "anull"):     # second try: without trimming
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), "-af", filters, "-ar", "24000", "-ac", "1",
                            "-c:a", "libopus", "-b:a", "32k", str(target)], check=True)
            if target.stat().st_size > MIN_CLIP_BYTES:              # very short sounds ("S", "OK") were once trimmed away completely
                return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--samples", action="store_true", help="make a few sample greetings to choose a voice")
    parser.add_argument("--lang", choices=["en", "de", "es"])
    parser.add_argument("--voice", default="coral")
    parser.add_argument("--key-file", default="~/.config/tippy/openai-key")
    parser.add_argument("--dry-run", action="store_true", help="only count and estimate the cost")
    parser.add_argument("--limit", type=int, default=0, help="only record this many clips (a quick try)")
    parser.add_argument("--replace", action="store_true", help="delete this language's existing recordings first (to switch to a new voice)")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not args.samples and not args.lang:
        parser.error("use --samples, or --lang with --voice")

    if args.samples:
        key = api_key(args.key_file)
        ffmpeg = ffmpeg_path()
        out = ROOT / "dist" / "voice-samples-cloud"
        out.mkdir(parents=True, exist_ok=True)
        with httpx.Client() as client:
            for lang in ("en", "de", "es"):
                for voice in SAMPLE_VOICES:
                    to_opus(ffmpeg, speak(client, key, SAMPLE_TEXT[lang], voice, INSTRUCTIONS[lang]), out / f"{lang}-{voice}.ogg", PITCH)
                    print(f"{lang}-{voice}", flush=True)
        print(f"Samples are in {out}")
        return

    strings = make_voice.load_strings(args.lang)
    todo = strings["texts"][: args.limit or None]
    out_dir = ROOT / "frontend" / "voice" / args.lang
    final_dir = out_dir
    if args.replace and not args.dry_run:
        out_dir = final_dir.with_name(final_dir.name + "-new")     # the old recordings stay until the new ones are complete
        out_dir.mkdir(parents=True, exist_ok=True)
    names: dict[str, str] = {}
    for text in todo:
        names[make_voice.clip_name(text)] = make_voice.normalise(text)
    def missing(t):
        path = out_dir / (make_voice.clip_name(t) + ".ogg")
        return not path.exists() or path.stat().st_size <= MIN_CLIP_BYTES

    pending = [t for t in todo if missing(t)] if (args.replace and out_dir.name.endswith("-new")) or not args.replace else todo
    minutes = sum(max(1.0, len(t) / 14) for t in pending) / 60          # about 14 characters per second of speech
    print(f"{len(todo)} texts, {len(pending)} still to record: about {minutes:.0f} minutes of audio, roughly ${minutes * PRICE_PER_MINUTE:.2f}.")
    if args.dry_run:
        return
    key = api_key(args.key_file)
    ffmpeg = ffmpeg_path()
    out_dir.mkdir(parents=True, exist_ok=True)
    done = 0

    def record(text: str) -> None:
        nonlocal done
        to_opus(ffmpeg, speak(client, key, text, args.voice, INSTRUCTIONS[args.lang]), out_dir / (make_voice.clip_name(text) + ".ogg"), PITCH)
        done += 1
        if done % 50 == 0:
            print(f"{done}/{len(pending)} clips ...", flush=True)

    with httpx.Client() as client, ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(record, pending))
    (out_dir / "index.json").write_text(json.dumps({"clips": sorted(names), "templates": [list(t) for t in strings["templates"]]},
                                                   ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    if out_dir != final_dir:                                        # everything is recorded: swap the folders
        import shutil
        shutil.rmtree(final_dir)
        out_dir.rename(final_dir)
        out_dir = final_dir
    total = sum(f.stat().st_size for f in out_dir.glob("*.ogg"))
    print(f"Done: {len(names)} clips for {args.lang}, {total // 1024} KB.")


if __name__ == "__main__":
    main()
