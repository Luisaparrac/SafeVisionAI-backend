"""The object uvicorn loads, built from the same variables the hosting platform has."""

import importlib

import pytest

from safevision.config.settings import ConfigurationError

PRODUCTION_VARIABLES = {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "IOT_API_KEY": "test-key",
    "FRONTEND_ORIGINS": "http://localhost:5173",
    "TIMEZONE": "America/Bogota",
}


@pytest.fixture
def app_module(monkeypatch):
    module = importlib.import_module("safevision.adapters.inbound.http.app")
    # Tests never read a local .env file.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    for name in ("HISTORY_CAPACITY", "DEDUP_WINDOW_SECONDS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in PRODUCTION_VARIABLES.items():
        monkeypatch.setenv(name, value)
    yield module
    module.__dict__.pop("app", None)


def test_app_is_built_from_the_platform_variables_only(app_module):
    app = app_module.app
    paths = set(app.openapi()["paths"])
    assert {"/health", "/api/eventos", "/api/alertas/pendientes", "/api/metricas"} <= paths
    container = app.state.container
    assert container.iot_api_key == "test-key"
    assert container.cors_origins == ("http://localhost:5173",)


def test_app_is_built_once(app_module):
    assert app_module.app is app_module.app


def test_importing_the_factory_does_not_build_the_app(app_module):
    assert "app" not in app_module.__dict__


@pytest.mark.parametrize("missing", ["DATABASE_URL", "IOT_API_KEY"])
def test_missing_required_variable_stops_startup(app_module, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(ConfigurationError, match=missing):
        app_module.app  # noqa: B018


@pytest.mark.parametrize("optional", ["FRONTEND_ORIGINS", "TIMEZONE"])
def test_optional_variables_have_defaults(app_module, monkeypatch, optional):
    monkeypatch.delenv(optional)
    assert app_module.app.state.container is not None


def test_other_attributes_still_fail(app_module):
    with pytest.raises(AttributeError):
        app_module.no_such_thing  # noqa: B018
