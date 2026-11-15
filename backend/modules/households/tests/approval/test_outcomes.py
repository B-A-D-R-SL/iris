# AI contribution: 50% or more AI-generated
"""US-18 approval outcomes from real notices, eligibility and rules."""

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext

from modules.accounts.tests.factories import UserFactory
from modules.documents.tests.factories import IncomeNoticeFactory
from modules.households.models import Household
from modules.households.queries import HouseholdEvidenceUnavailable, eligibility_inputs
from modules.households.services import update_draft
from modules.households.tests.approval.helpers import (
    NOW,
    approval_events,
    assert_approval_audit_chain,
    assert_unapproved,
    audit_events,
    decisions,
    invitations,
    notices,
    submit_and_approve,
)
from modules.households.tests.factories import MemberFactory
from modules.rules import queries as rule_queries
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_eligible_walk_in_is_approved_for_twelve_months(
    household: Any,
    role: str,
) -> None:
    actor: Any = UserFactory(role=role, password=None)
    result = submit_and_approve(household, actor)
    household.refresh_from_db()
    assert result.pk == household.pk
    assert household.status == "approved"
    assert household.approved_at == NOW
    assert household.expires_at == NOW.replace(year=2027)
    assert household.status_reason == ""
    decision = decisions(household).get()
    assert decision.adult_incomes_cents == [1_234_500]
    assert decision.eligible is True
    event = approval_events(household).get()
    assert event.action == "decision"
    assert event.actor_role == role
    assert event.metadata == {"outcome": "approved"}
    assert_approval_audit_chain(household, actor)
    assert not invitations().exists()


def test_income_above_lico_is_rejected(household: Any, staff: Any) -> None:
    notices(household).update(total_income_cents=3_000_001)
    submit_and_approve(household, staff)
    assert_unapproved(household, "rejected")
    assert household.status_reason == "INCOME_ABOVE_LICO"
    assert decisions(household).get().eligible is False
    assert approval_events(household).get().metadata == {"outcome": "rejected"}


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"name_on_notice": "Different Person"}, "NAME_MISMATCH"),
        ({"postal_code_on_notice": "H3Z 2Y7"}, "ADDRESS_MISMATCH"),
        ({"seen_in_person": False}, "NOTICE_NOT_SEEN"),
        ({"tax_year": 2024}, "TAX_YEAR_NOT_ACCEPTED"),
    ],
)
def test_unverified_notice_requires_review(
    household: Any,
    staff: Any,
    changes: dict[str, Any],
    reason: str,
) -> None:
    notices(household).update(**changes)
    submit_and_approve(household, staff)
    assert_unapproved(household, "review_required")
    assert household.status_reason == reason
    assert not decisions(household).exists()
    assert approval_events(household).get().metadata == {"outcome": "review_required"}


def test_corrected_holder_name_is_compared_at_approval(
    household: Any, staff: Any
) -> None:
    update_draft(household.pk, {"holder": {"first_name": "Corrected"}}, staff)
    assert notices(household).get().name_on_notice == "Example Person"
    submit_and_approve(household, staff)
    assert_unapproved(household, "review_required")
    assert household.status_reason == "NAME_MISMATCH"


def test_case_accents_and_extra_middle_names_match(household: Any, staff: Any) -> None:
    update_draft(
        household.pk,
        {
            "holder": {
                "first_name": "Élodie",
                "last_name": "Côté",
            }
        },
        staff,
    )
    notices(household).update(name_on_notice="elodie Marie COTE")
    assert submit_and_approve(household, staff).status == "approved"


def test_each_adult_is_checked_but_children_need_no_notice(
    household: Any, staff: Any
) -> None:
    adult = MemberFactory(
        household=household, relation="spouse_partner", first_name="Other"
    )
    MemberFactory(household=household, date_of_birth="2016-01-01")
    IncomeNoticeFactory(member=adult, recorded_by=staff, name_on_notice="Wrong Person")
    submit_and_approve(household, staff)
    assert_unapproved(household, "review_required")
    assert household.status_reason == "NAME_MISMATCH"


def test_non_filer_requires_review_without_assuming_zero(
    household: Any, staff: Any
) -> None:
    adult = MemberFactory(household=household, relation="spouse_partner")
    IncomeNoticeFactory(member=adult, recorded_by=staff, did_not_file=True)
    with pytest.raises(HouseholdEvidenceUnavailable, match="DID_NOT_FILE"):
        eligibility_inputs(household.pk)
    submit_and_approve(household, staff)
    assert_unapproved(household, "review_required")
    assert household.status_reason == "DID_NOT_FILE"
    assert not decisions(household).exists()


def test_missing_adult_notice_leaves_draft_unchanged(
    household: Any, staff: Any
) -> None:
    MemberFactory(household=household, relation="spouse_partner")
    with pytest.raises(ValidationError) as error:
        submit_and_approve(household, staff)
    assert error.value.messages == [
        gettext("Record a notice or non-filing reason for every adult.")
    ]
    assert_unapproved(household, "draft")
    assert not decisions(household).exists()
    assert not audit_events(household).exists()


def test_current_notice_replaces_old_mismatch(household: Any, staff: Any) -> None:
    old = notices(household).get()
    old.superseded_at = NOW
    old.name_on_notice = "Wrong Person"
    old.save()
    IncomeNoticeFactory(member=old.member, recorded_by=staff)
    assert submit_and_approve(household, staff).status == "approved"


def test_income_snapshot_counts_adults_and_all_members(
    household: Any, staff: Any
) -> None:
    adult = MemberFactory(household=household, date_of_birth=date(2008, 11, 8))
    IncomeNoticeFactory(member=adult, recorded_by=staff, total_income_cents=100)
    MemberFactory(household=household, date_of_birth=date(2008, 11, 9))
    submit_and_approve(household, staff)
    decision = decisions(household).get()
    assert decision.household_size == 3
    assert sorted(decision.adult_incomes_cents) == [100, 1_234_500]
    assert decision.household_income_cents == 1_234_600
    assert decision.threshold_cents == 9_000_000


def test_unchecked_identity_is_refused_at_submission(
    household: Any, staff: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(
        identity_checked_in_person=False,
        verified_by=None,
        verified_at=None,
    )
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert_unapproved(household, "draft")


@pytest.mark.parametrize(
    "changes",
    [
        {"consent_data_processing_at": None},
        {"consent_text_version": ""},
        {"street_name": ""},
    ],
)
def test_incomplete_file_cannot_be_approved(
    household: Any, staff: Any, changes: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(**changes)
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert_unapproved(household, "draft")
    assert not decisions(household).exists()


@pytest.mark.parametrize(
    "status", ["approved", "rejected", "suspended", "renewal_needed", "awaiting_visit"]
)
def test_final_and_unrelated_states_are_not_reprocessed(
    household: Any, staff: Any, status: str
) -> None:
    Household.objects.filter(pk=household.pk).update(status=status)
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert not decisions(household).exists()


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_non_intake_roles_are_denied(household: Any, role: str) -> None:
    store = StoreFactory() if role.startswith("store_") else None
    actor: Any = UserFactory(role=role, store=store, password=None)
    with pytest.raises(PermissionDenied):
        submit_and_approve(household, actor)
    assert_unapproved(household, "submitted")


def test_anonymous_and_inactive_staff_are_denied(household: Any, staff: Any) -> None:
    staff.is_active = False
    actors: tuple[Any, ...] = (AnonymousUser(), staff)
    for actor in actors:
        with pytest.raises(PermissionDenied):
            submit_and_approve(household, actor)


@pytest.mark.parametrize("changes", [{"channel": "online"}, {"anonymized_at": NOW}])
def test_non_walk_in_and_anonymized_files_are_hidden(
    household: Any, staff: Any, changes: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(**changes)
    with pytest.raises(Household.DoesNotExist):
        submit_and_approve(household, staff)


def test_us18_file_validity_uses_active_rule(household: Any, staff: Any) -> None:
    values = deepcopy(DEFAULT_RULE_VALUES["file_validity"]) | {"approved_months": 1}
    publish("file_validity", values, staff, effective_from=NOW)
    assert submit_and_approve(household, staff).expires_at == datetime(
        2026, 12, 8, 15, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "rule_type", ["file_validity", "auto_approval", "lico_thresholds"]
)
def test_missing_rules_fail_closed(
    household: Any, staff: Any, rule_type: str, monkeypatch: Any
) -> None:
    active = rule_queries.active
    monkeypatch.setattr(
        rule_queries,
        "active",
        lambda kind, **kwargs: None if kind == rule_type else active(kind, **kwargs),
    )
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()
