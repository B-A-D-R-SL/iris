# AI contribution: 50% or more AI-generated
"""Store pickup routes under /api/store/pickups/ (US-44)."""

from django.urls import path

from modules.reservations.api.pickup_views import PickupConfirmView, PickupLookupView

urlpatterns = [
    path("lookup/", PickupLookupView.as_view(), name="store-pickup-lookup"),
    path(
        "<uuid:id>/confirm/", PickupConfirmView.as_view(), name="store-pickup-confirm"
    ),
]
