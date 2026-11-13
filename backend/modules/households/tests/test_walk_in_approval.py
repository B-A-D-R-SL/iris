# AI contribution: 50% or more AI-generated
"""US-18 approval with real notices, eligibility, audit and invitations."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from threading import Barrier
from typing import Any

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.translation import gettext

from adapters.mailer.fake import get_fake_mailer
from modules.accounts import services as account_services
from modules.accounts.tests.factories import UserFactory
from modules.audit import services as audit_services
from modules.documents.tests.factories import IncomeNoticeFactory
from modules.households.models import Household
from modules.households.queries import HouseholdEvidenceUnavailable, eligibility_inputs
from modules.households.services import approve_walk_in, update_draft
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email
from modules.rules import queries as rule_queries
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]
NOW = datetime(2026, 11, 8, 15, tzinfo=UTC)
# Direct task calls run without a native worker's injected JobContext.
DIRECT_CONTEXT: Any = None


@pytest.fixture(autouse=True)
def rules(monkeypatch: Any) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    admin: Any = UserFactory(role="admin", password=None)
    for rule_type in ("auto_approval", "file_validity", "invitations"):
        publish(
            rule_type,
            deepcopy(DEFAULT_RULE_VALUES[rule_type]),
            admin,
            effective_from=NOW - timedelta(days=1),
        )
    publish(
        "lico_thresholds",
        {
            "year": 2025,
            "source_url": "https://www.statcan.gc.ca/",
            "retrieved_on": "2026-10-01",
            "thresholds": {str(size): 3_000_000 * size for size in range(1, 8)},
        },
        admin,
        effective_from=NOW - timedelta(days=1),
    )


@pytest.fixture
def staff() -> Any:
    return UserFactory(role="intake_worker", password=None)


@pytest.fixture
def household(staff: Any) -> Any:
    household = HouseholdFactory(
        created_by=staff,
        identity_checked_in_person=True,
        verified_by=staff,
        verified_at=NOW,
        consent_data_processing_at=NOW,
        consent_text_version="2026-11-v1",
    )
    holder = MemberFactory(household=household, relation="holder")
    IncomeNoticeFactory(member=holder, recorded_by=staff)
    return household


def records(model: str, household: Any) -> Any:
    return apps.get_model(model).objects.filter(household=household)


def notices(household: Any) -> Any:
    return apps.get_model("documents.IncomeNotice").objects.filter(
        member__household=household
    )


def decisions(household: Any) -> Any:
    return records("eligibility.EligibilityDecision", household)


def audit_events(household: Any) -> Any:
    return apps.get_model("audit.AuditEvent").objects.filter(
        target_id=str(household.pk)
    )


def invitations() -> Any:
    return apps.get_model("accounts.Invitation").objects.all()


def assert_unapproved(household: Any, status: str) -> None:
    household.refresh_from_db()
    assert household.status == status
    assert household.approved_at is None
    assert household.expires_at is None
    assert not invitations().exists()


def submit(household: Any) -> None:
    """Stand in for the Submit button: approval follows submission (BR-DUP-002)."""
    Household.objects.filter(pk=household.pk, status="draft").update(
        status="submitted", submitted_at=NOW
    )


def submit_and_approve(household: Any, actor: Any) -> Any:
    submit(household)
    return approve_walk_in(household, actor)


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
    event = audit_events(household).get()
    assert event.action == "decision"
    assert event.actor_role == role
    assert event.metadata == {"outcome": "approved"}
    assert not invitations().exists()


def test_income_above_lico_is_rejected(household: Any, staff: Any) -> None:
    notices(household).update(total_income_cents=3_000_001)
    submit_and_approve(household, staff)
    assert_unapproved(household, "rejected")
    assert household.status_reason == "INCOME_ABOVE_LICO"
    assert decisions(household).get().eligible is False
    assert audit_events(household).get().metadata == {"outcome": "rejected"}


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
    assert audit_events(household).get().metadata == {"outcome": "review_required"}


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
    assert_unapproved(household, "submitted")
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


def test_existing_review_flag_takes_priority_over_rejection(
    household: Any, staff: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(
        status="review_required",
        status_reason="DUPLICATE_PERSON",
    )
    notices(household).update(total_income_cents=9_000_000)
    assert submit_and_approve(household, staff).status_reason == "DUPLICATE_PERSON"
    assert_unapproved(household, "review_required")
    assert decisions(household).get().eligible is False


def test_unchecked_identity_requires_review(household: Any, staff: Any) -> None:
    Household.objects.filter(pk=household.pk).update(
        identity_checked_in_person=False,
        verified_by=None,
        verified_at=None,
    )
    assert submit_and_approve(household, staff).status_reason == "IDENTITY_NOT_VERIFIED"
    assert_unapproved(household, "review_required")


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
    assert_unapproved(household, "submitted")
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


@pytest.fixture
def email_jobs(monkeypatch: Any) -> list[dict[str, Any]]:
    """Capture the post-commit queue arguments without running a worker."""
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    return queued


def test_email_is_sent_after_commit_and_accepts_invitation(
    household: Any,
    staff: Any,
    settings: Any,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"
    Household.objects.filter(pk=household.pk).update(
        email="holder@example.test", preferred_language="en"
    )
    with django_capture_on_commit_callbacks(execute=True):
        submit_and_approve(household, staff)
        assert email_jobs == []
        invitation = invitations().get()
        assert invitation.role == "beneficiary"
        assert invitation.invited_by_id == staff.pk
    [job] = email_jobs
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert message["to"] == ["holder@example.test"]
    assert message["subject"] == "Set up your Iris access"
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert (log.template_key, log.status) == ("walk_in_set_password", "sent")
    token = message["text"].split("/invitation/", 1)[1].strip()
    assert token not in repr(EmailLog.objects.values().get(pk=log.pk))
    assert sha256(token.encode()).hexdigest() == invitation.token_hash
    assert token not in str(list(invitations().values()))
    user = account_services.accept_invitation(token, "Uncommon-secret-9146!")
    assert user.email == "holder@example.test"
    assert user.role == "beneficiary"


def test_invitation_failure_rolls_back_all_writes(household: Any, staff: Any) -> None:
    Household.objects.filter(pk=household.pk).update(email=staff.email)
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()
    assert not audit_events(household).exists()


def test_audit_failure_rolls_back_all_writes(
    household: Any, staff: Any, monkeypatch: Any
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise ValidationError("Audit unavailable")

    monkeypatch.setattr(audit_services, "record", fail)
    with pytest.raises(ValidationError, match="Audit unavailable"):
        submit_and_approve(household, staff)
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()


def test_outer_rollback_sends_no_email(
    household: Any,
    staff: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    Household.objects.filter(pk=household.pk).update(email="holder@example.test")
    submit(household)
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError, match="Cancel"),
        transaction.atomic(),
    ):
        approve_walk_in(household, staff)
        raise RuntimeError("Cancel")
    assert callbacks == []
    assert not EmailLog.objects.exists()
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()
    assert not audit_events(household).exists()


def test_repeated_stale_request_does_not_duplicate_approval(
    household: Any, staff: Any
) -> None:
    submit_and_approve(household, staff)
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert decisions(household).count() == 1
    assert audit_events(household).count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_approvals_create_one_decision_and_invitation(
    household: Any,
    staff: Any,
    email_jobs: list[dict[str, Any]],
) -> None:
    Household.objects.filter(pk=household.pk).update(email="holder@example.test")
    submit(household)
    barrier = Barrier(2)

    def approve() -> str:
        close_old_connections()
        try:
            actor = get_user_model().objects.get(pk=staff.pk)
            stale = Household.objects.get(pk=household.pk)
            barrier.wait(timeout=10)
            try:
                return approve_walk_in(stale, actor).status
            except ValidationError:
                return "refused"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: approve(), range(2)))

    assert sorted(results) == ["approved", "refused"]
    assert decisions(household).count() == 1
    assert audit_events(household).count() == 1
    assert invitations().count() == 1
    assert EmailLog.objects.filter(template_key="walk_in_set_password").count() == 1
    assert len(email_jobs) == 1


# rule: BR-DUP-002
def test_a_draft_must_be_submitted_before_approval(household: Any, staff: Any) -> None:
    with pytest.raises(ValidationError) as refused:
        approve_walk_in(household, staff)
    assert refused.value.messages == [gettext("Submit the file before approving it.")]
    assert_unapproved(household, "draft")
    assert not decisions(household).exists()


# rule: BR-DUP-002
def test_a_possible_duplicate_stays_in_review(household: Any, staff: Any) -> None:
    Household.objects.filter(pk=household.pk).update(
        status="review_required", status_reason="POSSIBLE_DUPLICATE"
    )
    decided = approve_walk_in(household, staff)
    assert decided.status == "review_required"
    assert "POSSIBLE_DUPLICATE" in decided.status_reason
    assert decided.approved_at is None
