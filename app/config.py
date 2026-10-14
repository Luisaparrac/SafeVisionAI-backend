import os

from dotenv import load_dotenv

# Loads .env when running locally; on Render the variables come from the dashboard.
load_dotenv()


def _list(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set. Define it in .env or in the service environment.")
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Without a key anyone could create events, so the app refuses to start.
IOT_API_KEY = _required("IOT_API_KEY")
FRONTEND_ORIGINS = _list(os.getenv("FRONTEND_ORIGINS", "http://localhost:5173"))
TIMEZONE = os.getenv("TIMEZONE", "America/Bogota")
HISTORY_CAPACITY = int(os.getenv("HISTORY_CAPACITY", "100"))
