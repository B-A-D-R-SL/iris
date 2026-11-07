# AI contribution: 50% or more AI-generated
"""Uninstrumented loopback WSGI server restricted to pytest's temporary database."""

import json
import os
import sys

import django
from django.conf import settings
from django.core.servers.basehttp import ThreadedWSGIServer
from django.core.wsgi import get_wsgi_application
from django.test.testcases import QuietWSGIRequestHandler


def serve() -> None:
    options = json.load(sys.stdin)
    database = options["database"]
    if not database["NAME"].startswith("test_"):
        raise ValueError("Load tests must use a disposable test_ database.")
    os.environ["DJANGO_SETTINGS_MODULE"] = "iris.settings.test"
    settings.DATABASES = {"default": database}
    settings.SECRET_KEY = options["secret_key"]
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
    django.setup()
    server = ThreadedWSGIServer(("127.0.0.1", 0), QuietWSGIRequestHandler)
    server.set_app(get_wsgi_application())
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}"}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
