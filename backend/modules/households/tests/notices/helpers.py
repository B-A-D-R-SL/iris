# AI contribution: 50% or more AI-generated
"""Request builders and the notice rule for the walk-in notice tests."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

CONTENT = b"%PDF-1.7 walk-in"
NOTICE_FIELDS = (
    "tax_year",
    "total_income_cents",
    "name_on_notice",
    "postal_code_on_notice",
    "notice_date",
    "seen_in_person",
)


# Fixed, not relative to timezone.now(): tests that pin the clock still find the rule.
RULE_EFFECTIVE_FROM = datetime(2020, 1, 1, tzinfo=UTC)


def publish_notice_rule(**changes: Any) -> None:
    values = deepcopy(DEFAULT_RULE_VALUES["notice_upload"]) | changes
    # A version with changes takes effect after the default one.
    effective = RULE_EFFECTIVE_FROM + timedelta(minutes=len(changes))
    publisher: Any = UserFactory(role="admin")
    publish("notice_upload", values, publisher, effective_from=effective)


def api_client(user: Any | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def pdf_upload(content: bytes = CONTENT, name: str = "scan.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def filed_notice(member: Any, **changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "member": str(member.pk),
        "file": pdf_upload(),
        "tax_year": "2025",
        "total_income_cents": "2345600",
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": "2026-04-30",
        "seen_in_person": "true",
    }
    values.update(changes)
    return {key: value for key, value in values.items() if value is not None}


def post_notice(
    client: APIClient, household: Any, data: dict[str, Any], **extra: Any
) -> Any:
    url = reverse("staff-households-notices", kwargs={"id": household.pk})
    return client.post(url, data, format="multipart", **extra)


def make_user(role: str, *, active: bool = True) -> Any:
    store = StoreFactory() if role.startswith("store_") else None
    return UserFactory(role=role, is_active=active, store=store)
