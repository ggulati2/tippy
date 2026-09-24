"""Makes Tippy licence files (docs/REVAMP_BRIEF.md section 8). A DEVELOPER tool for the owner, not part of the app.

A licence is a small JSON file: which tiers it unlocks ("plus", "school"), who it was issued to, and a signature. Tippy
checks the signature with the public key built into backend/licence.py, fully offline. Only the matching private key,
kept in ~/.config/tippy/licence-signing-key (never in the project), can make a licence Tippy accepts.

One-time: make the key pair (prints the public key to paste into PUBLIC_KEY in backend/licence.py):
    python scripts/make_licence.py --init
Then, for each licence:
    python scripts/make_licence.py --tiers plus,school --to "Grundschule am See" -o licence.json
"""
import argparse
import base64
import json
import sys
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import licence  # noqa: E402

KEY_FILE = Path.home() / ".config" / "tippy" / "licence-signing-key"


def sign(payload: dict, private_key: Ed25519PrivateKey) -> dict:
    return {"licence": payload, "signature": base64.b64encode(private_key.sign(licence.canonical(payload))).decode()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Make a signed Tippy licence file.")
    parser.add_argument("--init", action="store_true", help="make the signing key pair (once)")
    parser.add_argument("--tiers", default="", help="comma-separated: plus, school")
    parser.add_argument("--to", default="", help="who the licence is for (shown in the parent area)")
    parser.add_argument("-o", "--output", default="licence.json")
    args = parser.parse_args()

    if args.init:
        if KEY_FILE.exists():
            sys.exit(f"{KEY_FILE} already exists; delete it first to make a new pair (old licences then stop working).")
        key = Ed25519PrivateKey.generate()
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(base64.b64encode(key.private_bytes_raw()).decode())
        KEY_FILE.chmod(0o600)
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        print(f"Private key saved to {KEY_FILE} (keep it safe, never commit it).")
        print(f'Public key for backend/licence.py:\nPUBLIC_KEY = "{base64.b64encode(public).decode()}"')
        return

    tiers = [t for t in args.tiers.split(",") if t]
    unknown = [t for t in tiers if t not in licence.TIERS or t == "core"]
    if not tiers or unknown:
        sys.exit(f"--tiers must list some of: plus, school (got {args.tiers!r})")
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(KEY_FILE.read_text()))
    payload = {"tiers": tiers, "issued_to": args.to, "issued": date.today().isoformat()}
    Path(args.output).write_text(json.dumps(sign(payload, key), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {', '.join(tiers)} for {args.to or '(no name)'}.")


if __name__ == "__main__":
    main()
