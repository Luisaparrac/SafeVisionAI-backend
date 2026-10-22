"""Repository configuration files: local stack and dependency updates."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
EXAMPLE = dict(
    line.split("=", 1)
    for line in (ROOT / ".env.compose.example").read_text(encoding="utf-8").splitlines()
    if line and not line.startswith("#")
)


def test_database_loads_the_schema_and_then_the_sample_data():
    volumes = COMPOSE["services"]["db"]["volumes"]
    scripts = [v for v in volumes if "docker-entrypoint-initdb.d" in v]
    assert scripts == [
        "./tests/integration/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro",
        "./scripts/seed_dev.sql:/docker-entrypoint-initdb.d/02-seed_dev.sql:ro",
    ]
    for script in scripts:
        assert (ROOT / script.split(":")[0]).is_file()


def test_api_uses_the_image_of_this_repository_and_waits_for_the_database():
    api = COMPOSE["services"]["api"]
    assert api["build"] == "."
    assert api["depends_on"]["db"]["condition"] == "service_healthy"


def test_example_has_every_variable_the_backend_requires():
    required = {"DATABASE_URL", "IOT_API_KEY", "SESSION_SECRET", "FRONTEND_ORIGINS", "TIMEZONE"}
    assert required <= set(EXAMPLE)
    url = EXAMPLE["DATABASE_URL"]
    assert url == (
        f"postgresql://{EXAMPLE['POSTGRES_USER']}:{EXAMPLE['POSTGRES_PASSWORD']}"
        f"@db:5432/{EXAMPLE['POSTGRES_DB']}"
    )


def test_example_credentials_are_development_markers():
    assert EXAMPLE["POSTGRES_PASSWORD"].startswith("dev-only-")
    assert EXAMPLE["IOT_API_KEY"].startswith("dev-only-")
    assert EXAMPLE["SESSION_SECRET"].startswith("dev-only-")


def test_real_compose_values_stay_out_of_git():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env.compose" in ignored


def test_dependabot_watches_python_packages_and_actions():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {update["package-ecosystem"] for update in config["updates"]}
    assert ecosystems == {"pip", "github-actions"}
    assert all(update["directory"] == "/" for update in config["updates"])
