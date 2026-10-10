# AI contribution: 50% or more AI-generated
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@iris.local")

# Expose Iris's development-only management commands in local settings.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
