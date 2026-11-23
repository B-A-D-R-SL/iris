# AI contribution: 50% or more AI-generated
"""US-93 fixtures: the US-18 approval set-up and the emailed set-password token."""

from typing import Any

import pytest

from adapters.mailer.fake import get_fake_mailer
from modules.households.models import Household
from modules.households.tests.approval import conftest as approval
from modules.households.tests.approval.helpers import (
    DIRECT_CONTEXT,
    submit_and_approve,
)
from modules.households.tests.linking.helpers import HOLDER_EMAIL
from modules.notifications.tasks import send_email

# The approval rules (autouse), staff, a ready walk-in and the email queue (US-18).
rules = approval.rules
staff = approval.staff
household = approval.household
email_jobs = approval.email_jobs


def emailed_token(job: dict[str, Any]) -> str:
    """Deliver one queued set-password email and read the token from its link."""
    send_email(DIRECT_CONTEXT, **job)
    message = get_fake_mailer().sent[-1]
    return str(message["text"].split("/invitation/", 1)[1].strip())


@pytest.fixture
def invitation_token(
    household: Any,
    staff: Any,
    settings: Any,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
    notification_rules: Any,
) -> str:
    """Approve the walk-in with an email, as staff do, and return its token."""
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"
    Household.objects.filter(pk=household.pk).update(
        email=HOLDER_EMAIL, preferred_language="en"
    )
    with django_capture_on_commit_callbacks(execute=True):
        submit_and_approve(household, staff)
    return emailed_token(email_jobs[-1])
