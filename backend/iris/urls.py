# AI contribution: 50% or more AI-generated
"""URL routes for the Iris backend."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from iris.views import health
from modules.accounts.admin import RateLimitedAdminAuthenticationForm

admin.site.login_form = RateLimitedAdminAuthenticationForm

urlpatterns = [
    # Health check
    path("api/health/", health, name="health"),
    path("api/", include("modules.accounts.api.urls")),
    # Public listing categories
    path("api/categories/", include("modules.categories.api.urls")),
    # Django admin
    path("admin/", admin.site.urls),
    # Authentication: allauth's own versioned app/browser subpaths live here.
    path("api/auth/", include("allauth.headless.urls")),
    path("accounts/", include("allauth.urls")),
    path("api/store/", include("modules.listings.api.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
