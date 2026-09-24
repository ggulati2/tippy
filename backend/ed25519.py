"""Checking an Ed25519 signature, in plain Python (used by backend/licence.py).

This is the verification half of the reference code published in the Ed25519 standard itself (RFC 8032, section 6),
with its names kept so it can be compared line by line. It exists so the app needs no compiled crypto library: the
`cryptography` package broke the packaged Mac app (on Intel Macs pip builds it from source against Homebrew's
OpenSSL, and the app then carries a different one). Signing licences still uses `cryptography`
(scripts/make_licence.py, a developer tool). tests/test_ed25519.py checks this file against the RFC's test vectors
and against signatures made by `cryptography`.
"""
import hashlib

p = 2 ** 255 - 19
q = 2 ** 252 + 27742317777372353535851937790883648493


def _modp_inv(x: int) -> int:
    return pow(x, p - 2, p)


d = -121665 * _modp_inv(121666) % p
_modp_sqrt_m1 = pow(2, (p - 1) // 4, p)


def _point_add(P, Q):
    A, B = (P[1] - P[0]) * (Q[1] - Q[0]) % p, (P[1] + P[0]) * (Q[1] + Q[0]) % p
    C, D = 2 * P[3] * Q[3] * d % p, 2 * P[2] * Q[2] % p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F, G * H, F * G, E * H)


def _point_mul(s: int, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q


def _point_equal(P, Q) -> bool:
    return (P[0] * Q[2] - Q[0] * P[2]) % p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % p == 0


def _recover_x(y: int, sign: int):
    if y >= p:
        return None
    x2 = (y * y - 1) * _modp_inv(d * y * y + 1)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (p + 3) // 8, p)
    if (x * x - x2) % p != 0:
        x = x * _modp_sqrt_m1 % p
    if (x * x - x2) % p != 0:
        return None
    if (x & 1) != sign:
        x = p - x
    return x


_g_y = 4 * _modp_inv(5) % p
_g_x = _recover_x(_g_y, 0)
_G = (_g_x, _g_y, 1, _g_x * _g_y % p)


def _point_decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % p)


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """True only if `signature` is a valid Ed25519 signature of `message` by the owner of `public`."""
    if len(public) != 32 or len(signature) != 64:
        return False
    A = _point_decompress(public)
    R = _point_decompress(signature[:32])
    if not A or not R:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % q
    return _point_equal(_point_mul(s, _G), _point_add(R, _point_mul(h, A)))
