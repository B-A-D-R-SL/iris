# AI contribution: 50% or more AI-generated
"""Log completed session changes for browser and admin sign-ins."""

import logging
from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

logger = logging.getLogger("iris.auth")


@receiver(user_logged_in, dispatch_uid="accounts.sign_in_succeeded")
def sign_in_succeeded(user: AbstractBaseUser, **kwargs: Any) -> None:
    """Log a completed sign-in using only the user ID."""
    logger.info(
        "Sign-in succeeded", extra={"event": "sign_in_succeeded", "user_id": user.pk}
    )


@receiver(user_logged_out, dispatch_uid="accounts.signed_out")
def signed_out(user: AbstractBaseUser | None, **kwargs: Any) -> None:
    """Log an authenticated sign-out using only the user ID."""
    if user is not None and user.is_authenticated:
        logger.info("Signed out", extra={"event": "signed_out", "user_id": user.pk})
