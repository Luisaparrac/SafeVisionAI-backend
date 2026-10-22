"""Shared test configuration.

Fictitious environment values are forced first, so a test that builds the
application from the environment never picks up a local .env (load_dotenv
does not override variables that are already set) or reaches a real database.
"""

import os

os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test"
os.environ["IOT_API_KEY"] = "test-key"
os.environ["SESSION_SECRET"] = "test-session-secret-0123456789abcdef"
os.environ["FRONTEND_ORIGINS"] = "http://localhost:5173"
os.environ["TIMEZONE"] = "America/Bogota"

# PostgreSQL fixtures; tests that use them are skipped without TEST_DATABASE_URL.
pytest_plugins = ["tests.integration.postgres"]
