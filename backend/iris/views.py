"""Basic API endpoints for Iris."""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    """Return the backend availability status."""
    return JsonResponse({"status": "ok"})