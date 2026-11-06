# AI contribution: 50% or more AI-generated
"""Database rules of IncomeNotice and the current-notice query (T-03.18.2, #467)."""

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone, translation

from modules.documents.models import IncomeNotice
from modules.documents.queries import current_notices
from modules.documents.tests.factories import (
    make_confirmed_notice,
    make_did_not_file_notice,
    make_member,
)

pytestmark = pytest.mark.django_db


def test_br_doc_005_one_current_notice_per_member() -> None:
    first = make_confirmed_notice()

    with pytest.raises(IntegrityError), transaction.atomic():
        make_confirmed_notice(member=first.member)

    first.superseded_at = timezone.now()
    first.save()
    second = make_confirmed_notice(member=first.member)

    assert second.pk != first.pk


def test_confirmed_notice_without_file_violates_the_shape() -> None:
    with pytest.raises(IntegrityError):
        make_confirmed_notice(file_ref="")


def test_confirmed_notice_with_a_reason_violates_the_shape() -> None:
    with pytest.raises(IntegrityError):
        make_confirmed_notice(did_not_file_reason="No income")


def test_did_not_file_with_income_violates_the_shape() -> None:
    with pytest.raises(IntegrityError):
        make_did_not_file_notice(total_income_cents=0)


def test_did_not_file_without_reason_violates_the_shape() -> None:
    with pytest.raises(IntegrityError):
        make_did_not_file_notice(did_not_file_reason="")


def test_did_not_file_seen_in_person_violates_the_shape() -> None:
    with pytest.raises(IntegrityError):
        make_did_not_file_notice(seen_in_person=True)


def test_member_with_a_notice_cannot_be_deleted() -> None:
    notice = make_confirmed_notice()

    with pytest.raises(ProtectedError):
        notice.member.delete()


def test_current_notices_returns_only_current_rows() -> None:
    old = make_confirmed_notice(superseded_at=timezone.now())
    current = make_did_not_file_notice(member=old.member)
    without_notice = make_member(household=old.member.household)

    notices = current_notices([old.member.pk, without_notice.pk])

    assert notices == {old.member.pk: current}


def test_has_file() -> None:
    assert make_confirmed_notice().has_file is True
    assert make_did_not_file_notice().has_file is False


def test_status_and_source_labels_are_translated() -> None:
    with translation.override("fr"):
        labels = [
            str(IncomeNotice.Status.CONFIRMED.label),
            str(IncomeNotice.Status.DID_NOT_FILE.label),
            str(IncomeNotice.Source.STAFF.label),
        ]

    assert labels == ["Confirmé", "N'a pas produit de déclaration", "Personnel"]
