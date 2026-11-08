# AI contribution: 50% or more AI-generated

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.services import submit_walk_in
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


# rule: BR-DUP-002
def test_clean_draft_is_saved_as_submitted(ready_household_factory, submission_worker):
    household = ready_household_factory(status_reason="old draft note")
    result = submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert result.pk == household.pk
    assert household.status == Household.Status.SUBMITTED
    assert household.status_reason == ""
    assert household.submitted_at is not None
    assert household.approved_at is None
    assert household.expires_at is None


# rule: BR-DUP-001, BR-DUP-002
@pytest.mark.parametrize("match", ["address", "person"])
def test_duplicate_is_saved_for_review_without_changing_existing_file(
    match, ready_household_factory, submission_worker
):
    household = ready_household_factory()
    other = HouseholdFactory(
        street_number="100" if match == "address" else "200",
        status=Household.Status.APPROVED,
    )
    if match == "person":
        holder = household.members.get(relation=Member.Relation.HOLDER)
        MemberFactory(
            household=other,
            first_name=holder.first_name,
            last_name=holder.last_name,
            date_of_birth=holder.date_of_birth,
        )
    submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    other.refresh_from_db()
    assert household.status == Household.Status.REVIEW_REQUIRED
    assert household.status_reason == "POSSIBLE_DUPLICATE"
    assert household.submitted_at is not None
    assert other.status == Household.Status.APPROVED
    assert other.status_reason == ""
    assert Household.objects.count() == 2


@pytest.mark.parametrize("candidate_status", ["approved", "suspended"])
@pytest.mark.parametrize("expired", [False, True])
@pytest.mark.parametrize("match", ["address", "person"])
def test_duplicate_review_respects_candidate_expiry(
    candidate_status, expired, match, ready_household_factory, submission_worker
):
    household = ready_household_factory()
    other = HouseholdFactory(
        street_number="100" if match == "address" else "200",
        status=candidate_status,
        expires_at=timezone.now() + timedelta(days=-1 if expired else 1),
    )
    if match == "person":
        holder = household.members.get(relation=Member.Relation.HOLDER)
        MemberFactory(
            household=other,
            first_name=holder.first_name,
            last_name=holder.last_name,
            date_of_birth=holder.date_of_birth,
        )
    submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == (
        Household.Status.SUBMITTED if expired else Household.Status.REVIEW_REQUIRED
    )
    assert household.status_reason == ("" if expired else "POSSIBLE_DUPLICATE")
    other.refresh_from_db()
    assert other.status == candidate_status


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_service_refuses_nonstaff(role, ready_household_factory):
    household = ready_household_factory()
    values = {"store": StoreFactory()} if role.startswith("store_") else {}
    user = UserFactory(role=role, **values)
    with pytest.raises(PermissionDenied):
        submit_walk_in(household.pk, user)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None


def test_service_refuses_inactive_staff(ready_household_factory):
    household = ready_household_factory()
    with pytest.raises(PermissionDenied):
        submit_walk_in(household.pk, UserFactory(role="intake_worker", is_active=False))
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


@pytest.mark.parametrize("status", [s for s in Household.Status.values if s != "draft"])
def test_non_draft_files_cannot_be_resubmitted(
    status, ready_household_factory, submission_worker
):
    household = ready_household_factory(status=status, status_reason="keep this reason")
    with pytest.raises(ValidationError) as exc:
        submit_walk_in(household.pk, submission_worker)
    assert "status" in exc.value.message_dict
    household.refresh_from_db()
    assert household.status == status
    assert household.status_reason == "keep this reason"
    assert household.submitted_at is None


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"street_number": ""}, "address"),
        ({"consent_data_processing_at": None}, "consent_data_processing"),
        ({"consent_text_version": ""}, "consent_data_processing"),
        (
            {
                "identity_checked_in_person": False,
                "verified_by": None,
                "verified_at": None,
            },
            "identity_checked_in_person",
        ),
    ],
)
def test_incomplete_registration_stays_a_draft(
    changes, field, ready_household_factory, submission_worker
):
    household = ready_household_factory(**changes)
    with pytest.raises(ValidationError) as exc:
        submit_walk_in(household.pk, submission_worker)
    assert field in exc.value.message_dict
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None


def test_holder_is_required(ready_household_factory, submission_worker):
    household = ready_household_factory()
    household.members.all().delete()
    with pytest.raises(ValidationError, match="holder"):
        submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


def test_anonymized_draft_cannot_be_submitted(
    ready_household_factory, submission_worker
):
    from django.utils import timezone

    household = ready_household_factory(anonymized_at=timezone.now())
    with pytest.raises(ValidationError) as exc:
        submit_walk_in(household.pk, submission_worker)
    assert "status" in exc.value.message_dict
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


# rule: BR-HH-001
def test_more_than_fifteen_members_cannot_be_submitted(
    ready_household_factory, submission_worker
):
    household = ready_household_factory()
    MemberFactory.create_batch(15, household=household)
    with pytest.raises(ValidationError) as exc:
        submit_walk_in(household.pk, submission_worker)
    assert "members" in exc.value.message_dict
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
    assert not household.draft_events.filter(
        action=HouseholdDraftEvent.Action.SUBMITTED
    ).exists()


# rule: BR-HH-001
def test_exactly_fifteen_people_can_submit(ready_household_factory, submission_worker):
    household = ready_household_factory()
    MemberFactory.create_batch(14, household=household)
    result = submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.members.count() == 15
    assert household.status == result.status == Household.Status.SUBMITTED
    assert household.submitted_at is not None


def test_submission_revalidates_member_data(ready_household_factory, submission_worker):
    household = ready_household_factory()
    household.members.update(first_name="123")
    with pytest.raises(ValidationError, match="first_name"):
        submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


def test_online_file_is_not_accessible_to_walk_in_service(
    submission_worker,
):
    household = HouseholdFactory(channel=Household.Channel.ONLINE)
    with pytest.raises(Household.DoesNotExist):
        submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


def test_search_failure_rolls_back_key_repairs_and_submission(
    ready_household_factory, submission_worker
):
    household = ready_household_factory()
    household.members.update(person_key="stale-key")
    with (
        patch(
            "modules.households.services.find_possible_duplicates",
            side_effect=RuntimeError("unavailable"),
        ),
        pytest.raises(RuntimeError, match="unavailable"),
    ):
        submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
    assert household.members.get().person_key == "stale-key"


def test_outer_transaction_rollback_restores_draft(
    ready_household_factory, submission_worker
):
    household = ready_household_factory()
    with pytest.raises(RuntimeError, match="abort"), transaction.atomic():
        submit_walk_in(household.pk, submission_worker)
        raise RuntimeError("abort")
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
