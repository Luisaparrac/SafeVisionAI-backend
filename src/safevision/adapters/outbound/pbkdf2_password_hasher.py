"""PasswordHasher implemented with PBKDF2-HMAC-SHA256 from the standard library.

Stored format, one text value per user (``users.password_hash``)::

    pbkdf2_sha256$<iterations>$<salt>$<hash>

``salt`` and ``hash`` are standard base64. The iterations travel with each
hash, so raising them later keeps the older hashes valid. A value in any other
format never verifies: that account cannot log in until it receives a new hash
generated with ``scripts/hash_password.py``.
"""

import base64
import binascii
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
# Recommendation of OWASP (2023) for PBKDF2-HMAC-SHA256.
DEFAULT_ITERATIONS = 600_000
# A corrupted or hostile stored value must not keep a request busy for minutes.
MAX_ITERATIONS = 10_000_000
SALT_BYTES = 16


class Pbkdf2PasswordHasher:
    def __init__(self, iterations: int = DEFAULT_ITERATIONS) -> None:
        if not 1 <= iterations <= MAX_ITERATIONS:
            raise ValueError(f"iterations must be between 1 and {MAX_ITERATIONS}")
        self._iterations = iterations

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(SALT_BYTES)
        digest = _derive(password, salt, self._iterations)
        return "$".join([ALGORITHM, str(self._iterations), _b64(salt), _b64(digest)])

    def verify(self, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
            iterations = int(iterations_text)
            salt = base64.b64decode(salt_text, validate=True)
            expected = base64.b64decode(digest_text, validate=True)
        except (ValueError, binascii.Error):
            return False
        if algorithm != ALGORITHM or not 1 <= iterations <= MAX_ITERATIONS or not expected:
            return False
        # Constant-time comparison: the time does not reveal how many bytes matched.
        return hmac.compare_digest(_derive(password, salt, iterations, len(expected)), expected)


def _derive(password: str, salt: bytes, iterations: int, length: int | None = None) -> bytes:
    # "surrogatepass": any text that reaches the API can be hashed, even invalid UTF-16 halves.
    data = password.encode("utf-8", "surrogatepass")
    return hashlib.pbkdf2_hmac("sha256", data, salt, iterations, dklen=length)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")
