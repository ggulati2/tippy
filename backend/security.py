"""Parent PIN check.

The PIN protects the parent area and the "Exit" button. After a correct PIN the
browser gets a random token that it sends with later parent requests.
Tokens live only in memory, so restarting the app logs the parent out.
"""
import hashlib
import hmac
import secrets
import time


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    """Return "salt:hash" (hex). Only this is stored on disk, never the PIN itself."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def check_pin(pin: str, stored: str) -> bool:
    salt_hex, _, _ = stored.partition(":")
    # compare_digest takes the same time for right and wrong PINs.
    return hmac.compare_digest(hash_pin(pin, bytes.fromhex(salt_hex)), stored)


class PinGuard:
    def __init__(self, pin: str | None = None, max_failures: int = 5, lockout_seconds: int = 30, stored: str | None = None):
        # Either a plain PIN (tests, the .env PIN) or an already hashed one from the database.
        self._stored = stored or (hash_pin(pin) if pin else None)
        self._max_failures = max_failures
        self._lockout_seconds = lockout_seconds
        self._failures = 0
        self._locked_until = 0.0
        self._tokens: set[str] = set()

    @property
    def has_pin(self) -> bool:
        return self._stored is not None

    def set_pin(self, pin: str) -> str:
        """Change the PIN. Returns the hashed form so the caller can save it."""
        self._stored = hash_pin(pin)
        self._tokens.clear()  # everyone has to sign in again with the new PIN
        return self._stored

    def seconds_locked(self) -> int:
        """How many seconds until the next try is allowed (0 = allowed now)."""
        return max(0, int(self._locked_until - time.monotonic() + 0.999))

    def verify(self, pin: str) -> str | None:
        """Return a new token if the PIN is right, otherwise None.

        After several wrong tries we pause for a while, so a curious child
        cannot just guess all 10,000 combinations.
        """
        if self.seconds_locked() > 0 or self._stored is None:
            return None
        if check_pin(pin, self._stored):
            self._failures = 0
            token = secrets.token_urlsafe(24)
            self._tokens.add(token)
            return token
        self._failures += 1
        if self._failures >= self._max_failures:
            self._failures = 0
            self._locked_until = time.monotonic() + self._lockout_seconds
        return None

    def forget(self) -> None:
        """No PIN any more ("delete everything"): the next start asks for a new one, like a fresh install."""
        self._stored = None
        self._tokens.clear()
        self._failures = 0

    def is_valid_token(self, token: str | None) -> bool:
        return bool(token) and token in self._tokens

    def revoke(self, token: str | None) -> None:
        self._tokens.discard(token)
