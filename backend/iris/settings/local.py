# AI contribution: 50% or more AI-generated
from .base import *

DEBUG = True
DATABASES["default"]["CONN_MAX_AGE"] = 0
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
# Optional phone testing: set exact tunnel host/origin in the root .env.
ALLOWED_HOSTS += env.list("IRIS_TUNNEL_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS += env.list("IRIS_TUNNEL_ORIGINS", default=[])
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@iris.local")

# Expose Iris's development-only management commands in local settings.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
