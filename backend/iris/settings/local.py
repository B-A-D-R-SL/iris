# AI contribution: 50% or more AI-generated
from .base import *

DEBUG = True
DATABASES["default"]["CONN_MAX_AGE"] = 0
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]

# Expose Iris's development-only management commands in local settings.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
