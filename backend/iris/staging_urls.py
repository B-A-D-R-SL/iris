# AI contribution: 50% or more AI-generated
"""Release routes: API URLs retain their normal 404 and method behavior."""

from django.urls import path, re_path

from iris.staging_views import ready, spa
from iris.urls import urlpatterns as api_patterns

urlpatterns = [
    path("api/ready/", ready, name="staging-ready"),
    *api_patterns,
    re_path(
        r"^(?!(?:api|admin|accounts|static|assets)(?:/|$))(?P<path>.*)$",
        spa,
        name="staging-spa",
    ),
]
