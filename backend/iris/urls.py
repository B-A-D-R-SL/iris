from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from iris.views import health

urlpatterns = [
    # Health check
    path("api/health/", health, name="health"),

    # Django admin
    path("admin/", admin.site.urls),

    # Authentication
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]