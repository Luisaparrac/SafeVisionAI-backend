"""Prints the hash to store in users.password_hash (PBKDF2-SHA256, 600 000 iterations).

Asks for the password twice without showing it and prints only the hash: it
never connects to a database and writes no file. Store the hash yourself, for
example from pgAdmin:

  UPDATE users SET password_hash = '<hash>' WHERE user_id = <id>;

Usage:
  python scripts/hash_password.py

Only uses the standard library and the hasher of this repository.
"""

import getpass
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safevision.adapters.outbound.pbkdf2_password_hasher import (  # noqa: E402
    Pbkdf2PasswordHasher,
)
from safevision.application.ports.password_hasher import PasswordHasher  # noqa: E402

MIN_LENGTH = 8


def main(ask: Callable[[str], str] = getpass.getpass, hasher: PasswordHasher | None = None) -> str:
    password = ask("Contraseña: ")
    if len(password) < MIN_LENGTH:
        sys.exit(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres")
    if ask("Repite la contraseña: ") != password:
        sys.exit("Las contraseñas no coinciden")
    return (hasher or Pbkdf2PasswordHasher()).hash(password)


if __name__ == "__main__":
    print(main())
