import pytest

from safevision.config.settings import ConfigurationError, Settings

SECRET = "test-session-secret-0123456789abcdef"
REQUIRED = {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "IOT_API_KEY": "test-key",
    "SESSION_SECRET": SECRET,
}


def test_defaults_when_only_required_variables_are_set():
    settings = Settings.from_env(REQUIRED)
    assert settings.database_url == REQUIRED["DATABASE_URL"]
    assert settings.iot_api_key == "test-key"
    assert settings.frontend_origins == ("http://localhost:5173",)
    assert settings.timezone == "America/Bogota"
    assert settings.history_capacity == 100
    assert settings.dedup_window_seconds == 60.0
    assert settings.log_level == "INFO"
    assert settings.session_secret == SECRET
    assert settings.session_ttl_hours == 8.0
    assert settings.session_cookie_samesite == "none"
    assert settings.registration_mode == "invite"
    assert settings.registration_code == ""
    assert settings.effective_registration_mode == "closed"
    assert settings.password_reset_url == ""
    assert settings.password_reset_ttl_minutes == 30


def test_password_reset_settings():
    settings = Settings.from_env(
        REQUIRED
        | {
            "PASSWORD_RESET_URL": "https://panel.example.com/restablecer",
            "PASSWORD_RESET_TTL_MINUTES": "45",
        }
    )
    assert settings.password_reset_url == "https://panel.example.com/restablecer"
    assert settings.password_reset_ttl_minutes == 45


@pytest.mark.parametrize("value", ["0", "-5"])
def test_password_reset_lifetime_must_be_positive(value):
    with pytest.raises(ConfigurationError, match="PASSWORD_RESET_TTL_MINUTES"):
        Settings.from_env(REQUIRED | {"PASSWORD_RESET_TTL_MINUTES": value})


def test_registration_settings():
    settings = Settings.from_env(
        REQUIRED | {"REGISTRATION_MODE": " Invite ", "REGISTRATION_CODE": " abc "}
    )
    assert settings.registration_mode == "invite"
    assert settings.registration_code == "abc"
    assert settings.effective_registration_mode == "invite"
    assert "abc" not in repr(settings)


@pytest.mark.parametrize("mode", ["closed", "open"])
def test_other_registration_modes_are_kept(mode):
    assert Settings.from_env(REQUIRED | {"REGISTRATION_MODE": mode}).registration_mode == mode


def test_unknown_registration_mode_stops_the_application():
    with pytest.raises(ConfigurationError, match="REGISTRATION_MODE"):
        Settings.from_env(REQUIRED | {"REGISTRATION_MODE": "a-veces"})


def test_every_variable_is_read():
    settings = Settings.from_env(
        REQUIRED
        | {
            "FRONTEND_ORIGINS": " https://a.example/ , ,https://b.example",
            "TIMEZONE": "UTC",
            "HISTORY_CAPACITY": "25",
            "DEDUP_WINDOW_SECONDS": "2.5",
            "SESSION_TTL_HOURS": "0.5",
            "SESSION_COOKIE_SAMESITE": "Lax",
        }
    )
    assert settings.session_ttl_hours == 0.5
    assert settings.session_cookie_samesite == "lax"
    assert settings.frontend_origins == ("https://a.example", "https://b.example")
    assert settings.timezone == "UTC"
    assert settings.tzinfo.key == "UTC"
    assert settings.history_capacity == 25
    assert settings.dedup_window_seconds == 2.5


@pytest.mark.parametrize("name", ["DATABASE_URL", "IOT_API_KEY", "SESSION_SECRET"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_variables_stop_startup(name, value):
    environ = dict(REQUIRED)
    if value is None:
        del environ[name]
    else:
        environ[name] = value
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_env(environ)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TIMEZONE", "Marte/Olympus"),
        ("HISTORY_CAPACITY", "0"),
        ("HISTORY_CAPACITY", "muchos"),
        ("DEDUP_WINDOW_SECONDS", "-1"),
        ("DEDUP_WINDOW_SECONDS", "diez"),
        ("LOG_LEVEL", "VERBOSE"),
        ("SESSION_SECRET", "x" * 31),
        ("SESSION_TTL_HOURS", "0"),
        ("SESSION_TTL_HOURS", "ocho"),
        ("SESSION_COOKIE_SAMESITE", "strict"),
        ("FRONTEND_ORIGINS", "*"),
        ("FRONTEND_ORIGINS", "http://localhost:5173,*"),
    ],
)
def test_invalid_values_stop_startup(name, value):
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_env(REQUIRED | {name: value})


def test_secrets_are_not_shown_in_repr():
    text = repr(Settings.from_env(REQUIRED))
    assert "test-key" not in text
    assert SECRET not in text
    assert "postgresql://" not in text


def test_deduplication_can_be_disabled():
    assert Settings.from_env(REQUIRED | {"DEDUP_WINDOW_SECONDS": "0"}).dedup_window_seconds == 0


def test_log_level_ignores_case():
    assert Settings.from_env(REQUIRED | {"LOG_LEVEL": "debug"}).log_level == "DEBUG"
