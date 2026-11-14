# AI contribution: 50% or more AI-generated
"""Production settings for the CI security scan only (FIX-17, SEC-10).

The ZAP baseline job starts the backend on the CI runner, which has no TLS.
Everything else stays as in production, so the scan sees production headers
and cookies. Never use this module on a deployed environment.
"""

from .production import *
from .production import INSTALLED_APPS

# Plain HTTP on localhost; production redirects to HTTPS at this point.
SECURE_SSL_REDIRECT = False

# The seed command lives in the project package; it refuses to create accounts
# without SEED_PASSWORD when DEBUG is off.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
