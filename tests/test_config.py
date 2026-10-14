import importlib

import pytest

import app.config


@pytest.fixture
def reload_config(monkeypatch):
    yield lambda: importlib.reload(app.config)
    monkeypatch.undo()
    importlib.reload(app.config)  # restore the test values for other tests


@pytest.mark.parametrize("value", ["", "   "])
def test_missing_iot_api_key_prevents_startup(monkeypatch, reload_config, value):
    monkeypatch.setenv("IOT_API_KEY", value)
    with pytest.raises(RuntimeError, match="IOT_API_KEY"):
        reload_config()


def test_iot_api_key_is_trimmed(monkeypatch, reload_config):
    monkeypatch.setenv("IOT_API_KEY", "  some-key  ")
    assert reload_config().IOT_API_KEY == "some-key"
