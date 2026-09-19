"""Parent PIN check.

The PIN protects the parent area and the "Exit" button. After a correct PIN the
browser gets a random token that it sends with later parent requests.
Tokens live only in memory, so restarting the app logs the parent out.
"""
import hmac
import secrets
import time


class PinGuard:
    def __init__(self, pin: str, max_failures: int = 5, lockout_seconds: int = 30):
        self._pin = pin
        self._max_failures = max_failures
        self._lockout_seconds = lockout_seconds
        self._failures = 0
        self._locked_until = 0.0
        self._tokens: set[str] = set()

    def seconds_locked(self) -> int:
        """How many seconds until the next try is allowed (0 = allowed now)."""
        return max(0, int(self._locked_until - time.monotonic() + 0.999))

    def verify(self, pin: str) -> str | None:
        """Return a new token if the PIN is right, otherwise None.

        After several wrong tries we pause for a while, so a curious child
        cannot just guess all 10,000 combinations.
        """
        if self.seconds_locked() > 0:
            return None
        # compare_digest takes the same time for right and wrong PINs.
        if hmac.compare_digest(pin.encode(), self._pin.encode()):
            self._failures = 0
            token = secrets.token_urlsafe(24)
            self._tokens.add(token)
            return token
        self._failures += 1
        if self._failures >= self._max_failures:
            self._failures = 0
            self._locked_until = time.monotonic() + self._lockout_seconds
        return None

    def is_valid_token(self, token: str | None) -> bool:
        return bool(token) and token in self._tokens

    def revoke(self, token: str | None) -> None:
        self._tokens.discard(token)
