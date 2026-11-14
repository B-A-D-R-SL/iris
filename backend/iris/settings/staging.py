# AI contribution: 50% or more AI-generated
"""Single-instance, fictional-data staging using the production security guards."""

from django.core.exceptions import ImproperlyConfigured

from .base import BASE_DIR, env
from .production import *
from .production import INSTALLED_APPS, MIDDLEWARE

INSTALLED_APPS = [*INSTALLED_APPS, "iris"]  # Owns the existing idempotent seed command.
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
ROOT_URLCONF = "iris.staging_urls"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
# Only public build output belongs here. Listing photos use the private Blob adapter.
WHITENOISE_ROOT = BASE_DIR / "frontend_dist"
WHITENOISE_MAX_AGE = 60

# An unresolved reference is public configuration, never a usable Django key/password.
for _secret_name in (
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
    "SEED_PASSWORD",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_COMMUNICATION_CONNECTION_STRING",
):
    if env(_secret_name, default="").strip().startswith("@Microsoft.KeyVault("):
        raise ImproperlyConfigured(f"{_secret_name} Key Vault reference must resolve.")
