# AI contribution: 50% or more AI-generated
"""The supported duplicate check keeps the caller's write inside its locks."""

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.services import locked_duplicate_check
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("duplicate", [False, True])
def test_check_returns_an_evaluated_result_inside_a_transaction(
    duplicate, ready_household_factory, submission_worker
):
    """The caller writes while the context still holds the locks."""
    source = ready_household_factory()
    if duplicate:
        HouseholdFactory(status=Household.Status.APPROVED)
    assert not connection.in_atomic_block
    with locked_duplicate_check(source.pk, submission_worker) as (household, matched):
        assert type(matched) is bool and matched is duplicate
        assert connection.in_atomic_block
        household.status = (
            Household.Status.REVIEW_REQUIRED if matched else Household.Status.SUBMITTED
        )
        household.save()
    assert not connection.in_atomic_block
    source.refresh_from_db()
    assert source.status == (
        Household.Status.REVIEW_REQUIRED if duplicate else Household.Status.SUBMITTED
    )


def test_check_rolls_back_caller_changes(ready_household_factory, submission_worker):
    source = ready_household_factory()
    with (
        pytest.raises(RuntimeError, match="abort"),
        locked_duplicate_check(source.pk, submission_worker) as (household, matched),
    ):
        assert matched is False
        household.status = Household.Status.SUBMITTED
        household.save()
        raise RuntimeError("abort")
    source.refresh_from_db()
    assert source.status == Household.Status.DRAFT


def test_check_cannot_bypass_staff_permissions(ready_household_factory):
    source = ready_household_factory()
    with (
        pytest.raises(PermissionDenied),
        locked_duplicate_check(source.pk, UserFactory(role="beneficiary")),
    ):
        pytest.fail("Unauthorized code entered the locked context")
    source.refresh_from_db()
    assert source.status == Household.Status.DRAFT
