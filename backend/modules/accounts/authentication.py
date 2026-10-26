# AI contribution: 50% or more AI-generated
from drf_spectacular.authentication import SessionScheme
from rest_framework.authentication import (
    SessionAuthentication as DRFSessionAuthentication,
)
from rest_framework.request import Request


class SessionAuthentication(DRFSessionAuthentication):
    def authenticate_header(self, request: Request) -> str:
        return "Session"


class SessionAuthenticationScheme(SessionScheme):
    target_class = "modules.accounts.authentication.SessionAuthentication"
