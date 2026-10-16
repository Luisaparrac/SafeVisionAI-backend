"""Shared test configuration.

Fictitious environment values are forced before any application module is
imported, so tests never pick up a local .env or reach a real database.
"""

import os

os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
os.environ["IOT_API_KEY"] = "test-key"
os.environ["FRONTEND_ORIGINS"] = "http://localhost:5173"
os.environ["TIMEZONE"] = "America/Bogota"

# PostgreSQL fixtures; tests that use them are skipped without TEST_DATABASE_URL.
pytest_plugins = ["tests.integration.postgres"]
