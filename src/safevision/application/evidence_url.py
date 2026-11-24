"""Which evidence links may reach the panel.

The IoT module stores any text in ``events.evidence_url`` and the panel puts the
value in a ``src`` or an ``href``. Only absolute http(s) URLs with a host are
published; anything else (``javascript:``, ``data:``, local paths, malformed
values) is withheld so the panel never renders a dangerous link. The stored
value does not change, and it is never logged.
"""

from urllib.parse import urlsplit

_PUBLIC_SCHEMES = ("http", "https")


def public_evidence_url(value: str | None) -> str | None:
    """``value`` itself when it is an absolute http(s) URL with a host; otherwise None."""
    if not value or any(char.isspace() or not char.isprintable() for char in value):
        return None
    try:
        parts = urlsplit(value)
        valid_port = parts.port is None or parts.port > 0
    except ValueError:
        return None
    if parts.scheme.lower() not in _PUBLIC_SCHEMES or not parts.hostname or not valid_port:
        return None
    return value
