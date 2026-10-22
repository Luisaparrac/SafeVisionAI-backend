"""Application settings read from environment variables.

Missing or invalid values stop the application at startup (fail fast) instead
of failing later on the first request. Secrets have no default values.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
SAME_SITE_VALUES = ("none", "lax")
# HMAC-SHA256 keys shorter than this are easy to guess offline from one signed cookie.
MIN_SESSION_SECRET_LENGTH = 32


class ConfigurationError(RuntimeError):
    """An environment variable is missing or has an invalid value."""


@dataclass(frozen=True)
class Settings:
    """DATABASE_URL, IOT_API_KEY and SESSION_SECRET are required; the rest have safe defaults.

    ``dedup_window_seconds`` defaults to 60: the window counts from the first
    detection of a situation, so a short window would raise a new alert every
    few seconds while the same situation lasts. 0 disables deduplication.

    ``session_cookie_samesite`` defaults to "none" because the panel calls the
    API from another site; "lax" is enough when the frontend proxies the API
    under its own domain. Browsers only accept "none" on Secure cookies, which
    the session cookie always is.
    """

    database_url: str = field(repr=False)
    iot_api_key: str = field(repr=False)
    session_secret: str = field(repr=False)
    frontend_origins: tuple[str, ...] = ("http://localhost:5173",)
    timezone: str = "America/Bogota"
    history_capacity: int = 100
    dedup_window_seconds: float = 60.0
    log_level: str = "INFO"
    session_ttl_hours: float = 8.0
    session_cookie_samesite: str = "none"

    def __post_init__(self) -> None:
        for name in ("database_url", "iot_api_key", "session_secret"):
            if not getattr(self, name).strip():
                raise ConfigurationError(f"{name.upper()} es obligatoria")
        if len(self.session_secret) < MIN_SESSION_SECRET_LENGTH:
            raise ConfigurationError(
                f"SESSION_SECRET debe tener al menos {MIN_SESSION_SECRET_LENGTH} caracteres"
            )
        if "*" in self.frontend_origins:
            # Session cookies travel with every request: each origin must be named.
            raise ConfigurationError("FRONTEND_ORIGINS no admite '*': indica cada origen")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ConfigurationError(f"TIMEZONE inválida: {self.timezone!r}") from None
        if self.history_capacity < 1:
            raise ConfigurationError("HISTORY_CAPACITY debe ser mayor que cero")
        if self.dedup_window_seconds < 0:
            raise ConfigurationError("DEDUP_WINDOW_SECONDS no puede ser negativa")
        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError(f"LOG_LEVEL debe ser uno de {', '.join(LOG_LEVELS)}")
        if self.session_ttl_hours <= 0:
            raise ConfigurationError("SESSION_TTL_HOURS debe ser mayor que cero")
        if self.session_cookie_samesite not in SAME_SITE_VALUES:
            raise ConfigurationError(
                f"SESSION_COOKIE_SAMESITE debe ser uno de {', '.join(SAME_SITE_VALUES)}"
            )

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> "Settings":
        """Reads the variables documented in .env.example."""
        defaults = cls.__dataclass_fields__

        def text(name: str, default: str = "") -> str:
            return environ.get(name, default).strip()

        def number(name: str, kind: type[int] | type[float]) -> int | float:
            raw = text(name)
            if not raw:
                return defaults[name.lower()].default
            try:
                return kind(raw)
            except ValueError:
                raise ConfigurationError(f"{name} debe ser un número, no {raw!r}") from None

        origins = text("FRONTEND_ORIGINS")
        return cls(
            database_url=text("DATABASE_URL"),
            iot_api_key=text("IOT_API_KEY"),
            session_secret=text("SESSION_SECRET"),
            frontend_origins=_origins(origins) if origins else defaults["frontend_origins"].default,
            timezone=text("TIMEZONE") or defaults["timezone"].default,
            history_capacity=number("HISTORY_CAPACITY", int),
            dedup_window_seconds=number("DEDUP_WINDOW_SECONDS", float),
            log_level=text("LOG_LEVEL").upper() or defaults["log_level"].default,
            session_ttl_hours=number("SESSION_TTL_HOURS", float),
            session_cookie_samesite=text("SESSION_COOKIE_SAMESITE").lower()
            or defaults["session_cookie_samesite"].default,
        )


def _origins(value: str) -> tuple[str, ...]:
    """Comma separated list; a trailing slash would never match the browser's Origin."""
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
