# AI contribution: 50% or more AI-generated
"""Production settings for Iris."""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import DATABASES, SECRET_KEY, env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be configured in production.")

if SECRET_KEY == "CHANGE_ME_LOCAL_ONLY":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be changed in production.")

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# Notice files go to private Azure Blob Storage; the connection string comes from
# the environment (App Service settings), never from the repository.
FILE_STORE_BACKEND = env(
    "FILE_STORE_BACKEND", default="adapters.file_store.azure_blob.from_settings"
)
