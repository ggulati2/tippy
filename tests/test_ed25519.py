"""backend/ed25519.py against the official test vectors of RFC 8032 (section 7.1) and against the `cryptography` package."""
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend import ed25519

# RFC 8032, section 7.1, TEST 1 (empty message) and TEST 2 (one byte).
VECTORS = [
    ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
]


def test_the_rfc_test_vectors():
    for public, message, signature in VECTORS:
        assert ed25519.verify(bytes.fromhex(public), bytes.fromhex(message), bytes.fromhex(signature))


def test_agrees_with_the_cryptography_package_and_rejects_every_change():
    for _ in range(10):
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        message = os.urandom(40)
        signature = key.sign(message)
        assert ed25519.verify(public, message, signature)
        assert not ed25519.verify(public, message + b"x", signature)                      # the message changed
        assert not ed25519.verify(public, message, signature[:-1] + bytes([signature[-1] ^ 1]))   # the signature changed
        other = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        assert not ed25519.verify(other, message, signature)                              # someone else's key


def test_malformed_input_is_refused_not_crashing():
    public, message, signature = (bytes.fromhex(v) for v in VECTORS[0])
    assert not ed25519.verify(public[:31], message, signature)
    assert not ed25519.verify(public, message, signature[:63])
    too_big_s = signature[:32] + (ed25519.q).to_bytes(32, "little")                    # s must be below q
    assert not ed25519.verify(public, message, too_big_s)
    assert not ed25519.verify(b"\xff" * 32, message, signature)
