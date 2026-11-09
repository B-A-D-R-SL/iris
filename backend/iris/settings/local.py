# AI contribution: 50% or more AI-generated
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@iris.local")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5174")

# Expose Iris's development-only management commands in local settings.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]

# Notice files go to Azurite in Docker Compose.
FILE_STORE_BACKEND = env(
    "FILE_STORE_BACKEND", default="adapters.file_store.azure_blob.from_settings"
)
