# Names vulture reports as unused but that are used by frameworks or by the
# database. Anything else it reports is dead code and fails CI.
# ruff: noqa

# FastAPI calls the route functions; uvicorn reads the module attribute "app".
__getattr__
root
ready
recent_events
pending_alerts
alerts_feed
by_event_type
by_camera

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

# Parameters of protocol (port) methods and of __exit__, which only declare a signature.
exc_type
traceback
notification

# Enum members created from database values with parse().
INACTIVE
DISCONNECTED
MAINTENANCE
CHILD
ELDERLY
PET

# logging.Logger attribute set to silence the uvicorn access log.
_.disabled
