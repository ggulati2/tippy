"""Feature tiers and the offline licence file (docs/REVAMP_BRIEF.md section 8: "build the switches, not the payment
system"). No payments, no accounts, no online check: a licence is a signed JSON file, verified here with the public key
below. Without one, Tippy is the free "core" tier. DEV_UNLOCK_ALL=true (environment or .env) switches everything on.
"""
import base64
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# core: every readiness stage, all languages, one own word list. plus: the online helper, printables.
# school: classroom mode and portable mode. (There is only one own word list, so "unlimited lists" has nothing to gate yet.)
TIERS = {"core": set(), "plus": {"ai_extras", "printables"}, "school": {"classroom", "portable"}}
ALL_FEATURES = set().union(*TIERS.values())
FILE_NAME = "licence.json"

# The owner's public key. The matching private key never leaves the owner's computer (scripts/make_licence.py).
PUBLIC_KEY = "DLIjzW6lLYXZoY+gE6G5enUm6WqDToGwlXOpiCbzykU="


class LicenceError(ValueError):
    """The file is not a licence Tippy can accept. The message is safe to show to the parent."""


def canonical(payload: dict) -> bytes:
    """The exact bytes that are signed: the same JSON, whatever the spacing or key order in the file."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify(data) -> dict:
    """Return the licence's payload if its signature is right, otherwise raise LicenceError."""
    if not isinstance(data, dict) or not isinstance(data.get("licence"), dict) or not isinstance(data.get("signature"), str):
        raise LicenceError("not-a-licence")
    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY))
        key.verify(base64.b64decode(data["signature"], validate=True), canonical(data["licence"]))
    except (InvalidSignature, ValueError):
        raise LicenceError("bad-signature")
    tiers = data["licence"].get("tiers")
    if not isinstance(tiers, list) or not all(isinstance(t, str) for t in tiers):
        raise LicenceError("not-a-licence")
    return data["licence"]


def dev_unlock() -> bool:
    return os.environ.get("DEV_UNLOCK_ALL", "").lower() in ("1", "true", "yes")


def read(folder: Path) -> dict | None:
    """The valid licence saved in `folder`, or None (no file, or one that does not check out)."""
    try:
        return verify(json.loads((folder / FILE_NAME).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def features(folder: Path) -> set[str]:
    if dev_unlock():
        return set(ALL_FEATURES)
    found = read(folder)
    return set().union(*(TIERS.get(t, set()) for t in found["tiers"])) if found else set()
