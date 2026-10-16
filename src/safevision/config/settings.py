"""Application settings read from environment variables.

Missing or invalid values stop the application at startup (fail fast) instead
of failing later on the first request. Secrets have no default values.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(RuntimeError):
    """An environment variable is missing or has an invalid value."""


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    iot_api_key: str = field(repr=False)
    frontend_origins: tuple[str, ...] = ("http://localhost:5173",)
    timezone: str = "America/Bogota"
    history_capacity: int = 100
    dedup_window_seconds: float = 10.0

    def __post_init__(self) -> None:
        for name in ("database_url", "iot_api_key"):
            if not getattr(self, name).strip():
                raise ConfigurationError(f"{name.upper()} es obligatoria")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ConfigurationError(f"TIMEZONE inválida: {self.timezone!r}") from None
        if self.history_capacity < 1:
            raise ConfigurationError("HISTORY_CAPACITY debe ser mayor que cero")
        if self.dedup_window_seconds < 0:
            raise ConfigurationError("DEDUP_WINDOW_SECONDS no puede ser negativa")

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
            frontend_origins=_origins(origins) if origins else defaults["frontend_origins"].default,
            timezone=text("TIMEZONE") or defaults["timezone"].default,
            history_capacity=number("HISTORY_CAPACITY", int),
            dedup_window_seconds=number("DEDUP_WINDOW_SECONDS", float),
        )


def _origins(value: str) -> tuple[str, ...]:
    """Comma separated list; a trailing slash would never match the browser's Origin."""
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
