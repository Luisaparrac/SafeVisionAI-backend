"""The test user of the reference rows, with a password hashed quickly.

The production hasher runs 600 000 iterations; tests hash with very few, which
the hasher accepts because the iterations travel inside each stored hash.
"""

from safevision.adapters.outbound.pbkdf2_password_hasher import Pbkdf2PasswordHasher

FAST_HASHER = Pbkdf2PasswordHasher(iterations=1_000)

TEST_NAME = "Usuario de prueba"
TEST_EMAIL = "usuario@example.com"
TEST_PASSWORD = "clave-de-prueba"
TEST_PASSWORD_HASH = FAST_HASHER.hash(TEST_PASSWORD)
