# AI contribution: 50% or more AI-generated
"""US-12 database rules for PartnerApplication and the Store link."""

from typing import Any, cast

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from modules.accounts.tests.factories import UserFactory
from modules.stores.models import ApplicationStatus, PartnerApplication, Store
from modules.stores.tests.factories import PartnerApplicationFactory, StoreFactory

pytestmark = pytest.mark.django_db


def _violates(**values: Any) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        PartnerApplicationFactory(**values)


def test_new_application_starts_submitted() -> None:
    application = cast(PartnerApplication, PartnerApplicationFactory())
    assert application.status == ApplicationStatus.SUBMITTED
    assert application.decided_by is None and application.decided_at is None


def test_one_open_application_per_email_is_a_database_rule() -> None:
    # rule: BR-PARTNER-01 (AC3), enforced by a partial unique index
    PartnerApplicationFactory(contact_email="owner@example.test")
    _violates(contact_email="owner@example.test")


def test_open_application_email_ignores_letter_case() -> None:
    # rule: BR-PARTNER-01, contact email uniqueness is case-insensitive
    PartnerApplicationFactory(contact_email="owner@example.test")
    _violates(contact_email="Owner@EXAMPLE.test")


@pytest.mark.parametrize(
    "decided", [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]
)
def test_decided_application_does_not_block_a_new_one(decided: str) -> None:
    # rule: BR-PARTNER-01, only submitted applications block another submission
    PartnerApplicationFactory(
        contact_email="owner@example.test",
        status=decided,
        decision_reason="Generated reason",
        decided_by=UserFactory(role="admin"),
    )
    PartnerApplicationFactory(contact_email="owner@example.test")
    assert (
        PartnerApplication.objects.filter(contact_email="owner@example.test").count()
        == 2
    )


def test_application_without_consent_cannot_be_saved() -> None:
    _violates(consent_contact=False)


def test_application_needs_a_goods_category() -> None:
    _violates(goods_categories=[])


@pytest.mark.parametrize("reason", [None, ""])
def test_rejection_needs_a_reason(reason: str | None) -> None:
    _violates(status=ApplicationStatus.REJECTED, decision_reason=reason)


@pytest.mark.parametrize(
    "values",
    [
        {"status": "pending"},
        {"business_type": "casino"},
        {"expected_frequency": "yearly"},
        {"language": "de"},
    ],
)
def test_choices_are_checked_by_the_database(values: dict[str, str]) -> None:
    _violates(**values)


def test_store_application_link_is_optional() -> None:
    store = cast(Store, StoreFactory())
    assert store.application is None


def test_one_application_creates_at_most_one_store() -> None:
    application = cast(PartnerApplication, PartnerApplicationFactory())
    store = cast(Store, StoreFactory(application=application))
    assert store.application == application
    assert application.store == store
    with pytest.raises(IntegrityError), transaction.atomic():
        StoreFactory(application=application)


def test_linked_application_cannot_be_deleted() -> None:
    application = cast(PartnerApplication, PartnerApplicationFactory())
    StoreFactory(application=application)
    with pytest.raises(ProtectedError):
        application.delete()
    assert Store.objects.filter(application=application).exists()
