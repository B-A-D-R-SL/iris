# AI contribution: 50% or more AI-generated
"""URL routes for account endpoints."""

from django.urls import path

from modules.accounts.api.views import current_user

urlpatterns = [path("me/", current_user, name="current-user")]
