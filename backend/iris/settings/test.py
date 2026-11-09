# AI contribution: Below 50% AI-generated
from .base import *

DEBUG = False
FRONTEND_URL = "https://iris.example.test"

# Register the command package for isolated tests; command itself refuses non-debug use.
INSTALLED_APPS = [*INSTALLED_APPS, "iris"]

# Tests never reach Azure Blob Storage (review rule 9): they use the in-memory fake.
FILE_STORE_BACKEND = "adapters.file_store.memory.InMemoryFileStore"
