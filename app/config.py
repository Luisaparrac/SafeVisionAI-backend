import os


def _list(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IOT_API_KEY = os.getenv("IOT_API_KEY", "").strip()
FRONTEND_ORIGINS = _list(os.getenv("FRONTEND_ORIGINS", "http://localhost:5173"))
TIMEZONE = os.getenv("TIMEZONE", "America/Bogota")
SEED_DEMO_EVENTS = os.getenv("SEED_DEMO_EVENTS", "true").lower() == "true"
HISTORY_CAPACITY = int(os.getenv("HISTORY_CAPACITY", "100"))
