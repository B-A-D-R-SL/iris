# AI contribution: 50% or more AI-generated
from .base import *

DEBUG = True
DATABASES["default"]["CONN_MAX_AGE"] = 0
# Subdomains for phone testing via Cloudflare / ngrok quick tunnels.
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "backend",
    ".trycloudflare.com",
    ".ngrok-free.app",
    ".ngrok.io",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://*.trycloudflare.com",
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
]
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@iris.local")

# Expose Iris's development-only management commands in local settings.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
