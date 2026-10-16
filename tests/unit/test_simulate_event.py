"""The simulation script has no default URL or key (no network involved)."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "simulate_event.py"
spec = importlib.util.spec_from_file_location("simulate_event", SCRIPT)
simulate_event = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simulate_event)


def test_url_and_key_from_arguments():
    args = simulate_event.parse_args(["--url", "http://localhost:8000/", "--key", "k"], {})
    assert (args.url, args.key) == ("http://localhost:8000", "k")


def test_url_and_key_from_environment():
    environ = {"BACKEND_URL": "http://localhost:9000", "IOT_API_KEY": "test-key"}
    args = simulate_event.parse_args(["--camara", "2"], environ)
    assert (args.url, args.key, args.camara) == ("http://localhost:9000", "test-key", 2)


def test_arguments_win_over_the_environment():
    environ = {"BACKEND_URL": "http://localhost:9000", "IOT_API_KEY": "env-key"}
    args = simulate_event.parse_args(["--key", "arg-key"], environ)
    assert args.key == "arg-key"


@pytest.mark.parametrize(
    ("argv", "environ", "missing"),
    [
        ([], {}, "BACKEND_URL"),
        (["--url", "http://localhost:8000"], {}, "IOT_API_KEY"),
        ([], {"IOT_API_KEY": "k"}, "BACKEND_URL"),
    ],
)
def test_missing_url_or_key_stops_the_script(argv, environ, missing, capsys):
    with pytest.raises(SystemExit) as info:
        simulate_event.parse_args(argv, environ)
    assert info.value.code == 2
    assert missing in capsys.readouterr().err


def test_event_body_matches_the_contract():
    body = simulate_event.build_event(1, "Caída", None)
    assert set(body) == {
        "camera_id",
        "event_type",
        "subject_id",
        "detected_class",
        "confidence",
        "description",
    }
    assert 0.7 <= body["confidence"] <= 0.99
