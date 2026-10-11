# AI contribution: Below 50% AI-generated
from .base import *

DEBUG = False

# Register the command package for isolated tests; command itself refuses non-debug use.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]
