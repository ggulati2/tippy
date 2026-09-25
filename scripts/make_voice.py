"""Records Tippy's voice: every sentence the app can say, as small audio files in frontend/voice/<language>/.

This is a DEVELOPER tool. It is not needed to run Tippy and is not part of the app or the zip; only the finished
recordings (frontend/voice) are. The recordings are made with Piper (a free offline neural voice) and pitched up a
little so the voice sounds lighter and friendlier for a child.

One-time setup (in a folder outside the project; Piper is GPL software, so it is never added to requirements.txt):
    python3 -m venv ~/tippy-tts && ~/tippy-tts/bin/pip install piper-tts imageio-ffmpeg
    (download a voice: the .onnx and .onnx.json files from https://huggingface.co/rhasspy/piper-voices)

Record (about 20 to 30 minutes for English; it can be stopped and started again, finished clips are kept):
    ~/tippy-tts/bin/python scripts/make_voice.py --lang en --model en_US-hfc_female-medium.onnx --pitch 1.12

How Tippy finds a recording: the text is tidied (extra spaces removed, lower case), turned into a number with
the small hash in frontend/js/voice.js (the same one is written here) and the file is named after that number.
index.json lists the numbers that exist, so the browser knows without asking the server for each one.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def cyrb53(text: str) -> int:
    """The same 53-bit hash as `cyrb53` in frontend/js/voice.js (tests/test_voice.py checks they agree)."""
    m32 = 0xFFFFFFFF
    h1, h2 = 0xDEADBEEF, 0x41C6CE57
    units = text.encode("utf-16-le")
    for i in range(0, len(units), 2):                     # JavaScript works on UTF-16 units, so we do too
        ch = units[i] | (units[i + 1] << 8)
        h1 = ((h1 ^ ch) * 2654435761) & m32
        h2 = ((h2 ^ ch) * 1597334677) & m32
    h1 = (((h1 ^ (h1 >> 16)) * 2246822507) & m32) ^ (((h2 ^ (h2 >> 13)) * 3266489909) & m32)
    h2 = (((h2 ^ (h2 >> 16)) * 2246822507) & m32) ^ (((h1 ^ (h1 >> 13)) * 3266489909) & m32)
    return 4294967296 * (2097151 & h2) + (h1 & m32)


def normalise(text: str) -> str:
    """Same tidy-up as `voiceKey` in voice.js: no soft hyphens, single spaces, no spaces at the ends, lower case."""
    return " ".join(text.replace("\u00ad", "").split()).lower()


def clip_name(text: str) -> str:
    n, digits = cyrb53(normalise(text)), "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


# The pieces around a child's name in a mascot line ("Hi {child}! Let's play!" -> "Hi", "Let's play!").
def split_template(line: str) -> tuple[str, str]:
    before, after = line.split("{child}", 1)
    return re.sub(r"[\s]+$", "", before), re.sub(r"^[\s!,.?;:¡¿]+", "", after)


def load_strings(lang: str) -> dict:
    """Everything Tippy may say in this language: {"texts": [...], "templates": [[before, after], ...]}."""
    from backend import bank

    texts: set[str] = set()
    templates: list[tuple[str, str]] = []

    # 1. Every screen text (instructions, lessons, facts). Read from the real file with node.
    script = ("global.window={};require('./frontend/js/i18n.js');try{require('./frontend/js/i18n-es.js')}catch(e){}"
              "console.log(JSON.stringify(window.STRINGS['%s']))" % lang)
    ui = json.loads(subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, encoding="utf-8", check=True).stdout)   # utf-8: on Windows the default would garble umlauts
    friend = ui.get("friend", "friend")
    texts.update(ui.values())

    # 2. Words and sentences from the built-in content bank.
    def walk(node):
        if isinstance(node, str):
            texts.add(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(value)

    walk(bank.WORDS.get(lang, {}))
    walk(bank.SENTENCES.get(lang, {}))
    texts.update(bank.FREE_PLAY.get(lang, {}))                # these are word -> picture
    texts.update(bank.PICTURES.get(lang, {}))
    for spec in bank.SPECIAL.get(lang, {}).values():
        walk(list(spec["items"]) if spec["type"] == "words" else spec["items"])
    texts.update(bank.ASK["answers"].get(lang, {}).values())
    if lang == "en":
        texts.update(bank.ASK["questions"].values())
    texts.add(bank.ASK_REDIRECT[lang])

    # 3. Tippy's own lines. Lines with the child's name are recorded with "friend" and also in two pieces.
    for lines in bank.MASCOT_LINES[lang].values():
        for line in lines:
            if "{child}" in line:
                texts.add(line.replace("{child}", friend))
                before, after = split_template(line)
                templates.append((before, after))
                texts.update(piece for piece in (before, after) if piece)
            else:
                texts.add(line)

    # 4. Single letters and numbers (the big letter and number buttons read them out).
    texts.update("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    texts.update(str(n) for n in range(0, 21))
    texts.add("Tippy")

    clean = {" ".join(t.split()) for t in texts if re.search(r"[^\W\d_]|\d", t) and "{" not in t}
    return {"texts": sorted(clean), "templates": sorted(set(templates))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--lang", required=True, choices=["en", "de", "es"])
    parser.add_argument("--model", required=True, help="the Piper .onnx voice file")
    parser.add_argument("--speaker", type=int, default=None, help="for voices with several speakers")
    parser.add_argument("--pitch", type=float, default=1.12, help="1.0 = as recorded; 1.12 = a lighter, friendlier voice")
    parser.add_argument("--length", type=float, default=1.1, help="above 1 = slower and clearer")
    parser.add_argument("--noise", type=float, default=None, help="how much the intonation varies (Piper default 0.667; higher = livelier)")
    parser.add_argument("--noisew", type=float, default=None, help="how much the rhythm varies (Piper default 0.8)")
    parser.add_argument("--limit", type=int, default=0, help="only record this many clips (for a quick try)")
    args = parser.parse_args()

    import imageio_ffmpeg
    from piper import PiperVoice, SynthesisConfig

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    voice = PiperVoice.load(args.model)
    rate = voice.config.sample_rate
    out_dir = ROOT / "frontend" / "voice" / args.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    strings = load_strings(args.lang)
    todo = strings["texts"][: args.limit or None]
    names: dict[str, str] = {}
    for text in todo:
        name = clip_name(text)
        if name in names and names[name] != normalise(text):
            sys.exit(f"Two texts have the same file name: {names[name]!r} and {text!r}")
        names[name] = normalise(text)

    # Raise the pitch without changing the speed, trim silence at both ends, save as small mono Opus.
    cleanup = (f"asetrate={round(rate * args.pitch)},aresample=24000,atempo={1 / args.pitch:.4f},"
               "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
               "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse")
    tempdir = tempfile.TemporaryDirectory()
    made = 0
    for number, text in enumerate(todo, 1):
        target = out_dir / (clip_name(text) + ".ogg")
        if target.exists():
            continue
        wav = Path(tempdir.name) / "clip.wav"
        with wave.open(str(wav), "wb") as w:
            voice.synthesize_wav(text, w, syn_config=SynthesisConfig(speaker_id=args.speaker, length_scale=args.length,
                                                                  noise_scale=args.noise, noise_w_scale=args.noisew))
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-af", cleanup, "-ac", "1", "-c:a", "libopus", "-b:a", "24k", str(target)], check=True)
        made += 1
        if made % 50 == 0:
            print(f"{number}/{len(todo)} clips ...", flush=True)

    (out_dir / "index.json").write_text(json.dumps({"clips": sorted(names), "templates": [list(t) for t in strings["templates"]]},
                                                   ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in out_dir.glob("*.ogg"))
    print(f"Done: {len(names)} clips for {args.lang}, {total // 1024} KB.")


if __name__ == "__main__":
    main()
