# AI contribution: 50% or more AI-generated
"""An invalid route configuration must fail at startup, before serving HTTP."""

from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from iris.wsgi import _checked_application


def test_wsgi_rejects_invalid_routes_before_accepting_requests():
    invalid_routes = ModuleType("invalid_wsgi_test_routes")
    invalid_routes.urlpatterns = ["not-a-url-pattern"]
    with (
        override_settings(ROOT_URLCONF=invalid_routes),
        pytest.raises(ImproperlyConfigured, match="urls.E004"),
    ):
        _checked_application()
