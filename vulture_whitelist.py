# Names vulture reports as unused but that are used by frameworks or by the
# database. Anything else it reports is dead code and fails CI.
# ruff: noqa

# FastAPI calls the route functions; uvicorn reads the module attribute "app".
__getattr__
root
ready
recent_events
pending_alerts

# Pydantic reads these class attributes to build and serialize the models.
model_config
id_alerta
nivel
pendientes
alto

# The users table is referenced by foreign keys and filled by the integration tests.
UserRow
email
password_hash

# Context manager protocol: __exit__ receives these arguments.
exc_type
traceback

# Enum members created from database values with parse().
INACTIVE
DISCONNECTED
MAINTENANCE
CHILD
ELDERLY
PET

# logging.Logger attribute set to silence the uvicorn access log.
_.disabled
