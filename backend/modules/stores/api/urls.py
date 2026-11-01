# AI contribution: 50% or more AI-generated
"""Public partner application route; staff review routes arrive with US-13."""

from django.urls import path

from modules.stores.api.views import PartnerApplicationCreateView

urlpatterns = [
    path("", PartnerApplicationCreateView.as_view(), name="partner-application-create")
]
