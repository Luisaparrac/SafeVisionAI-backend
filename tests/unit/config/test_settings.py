import pytest

from safevision.config.settings import ConfigurationError, Settings

REQUIRED = {"DATABASE_URL": "postgresql://test:test@localhost/test", "IOT_API_KEY": "test-key"}


def test_defaults_when_only_required_variables_are_set():
    settings = Settings.from_env(REQUIRED)
    assert settings.database_url == REQUIRED["DATABASE_URL"]
    assert settings.iot_api_key == "test-key"
    assert settings.frontend_origins == ("http://localhost:5173",)
    assert settings.timezone == "America/Bogota"
    assert settings.history_capacity == 100
    assert settings.dedup_window_seconds == 60.0
    assert settings.log_level == "INFO"


def test_every_variable_is_read():
    settings = Settings.from_env(
        REQUIRED
        | {
            "FRONTEND_ORIGINS": " https://a.example/ , ,https://b.example",
            "TIMEZONE": "UTC",
            "HISTORY_CAPACITY": "25",
            "DEDUP_WINDOW_SECONDS": "2.5",
        }
    )
    assert settings.frontend_origins == ("https://a.example", "https://b.example")
    assert settings.timezone == "UTC"
    assert settings.tzinfo.key == "UTC"
    assert settings.history_capacity == 25
    assert settings.dedup_window_seconds == 2.5


@pytest.mark.parametrize("name", ["DATABASE_URL", "IOT_API_KEY"])
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
    ],
)
def test_invalid_values_stop_startup(name, value):
    with pytest.raises(ConfigurationError, match=name):
        Settings.from_env(REQUIRED | {name: value})


def test_secrets_are_not_shown_in_repr():
    text = repr(Settings.from_env(REQUIRED))
    assert "test-key" not in text
    assert "postgresql://" not in text


def test_deduplication_can_be_disabled():
    assert Settings.from_env(REQUIRED | {"DEDUP_WINDOW_SECONDS": "0"}).dedup_window_seconds == 0


def test_log_level_ignores_case():
    assert Settings.from_env(REQUIRED | {"LOG_LEVEL": "debug"}).log_level == "DEBUG"
