# AI contribution: 50% or more AI-generated
"""URL routes for account endpoints."""

from django.urls import path

from modules.accounts.api.views import AcceptInvitationView, current_user

urlpatterns = [
    path("me/", current_user, name="current-user"),
    path(
        "invitations/accept/",
        AcceptInvitationView.as_view(),
        name="invitation-accept",
    ),
]
