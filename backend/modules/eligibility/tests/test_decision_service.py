# AI contribution: 50% or more AI-generated
"""Database-backed tests for the eligibility decision service."""

import json
import logging
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from iris.observability import JsonLogFormatter
from modules.audit.queries import search_events
from modules.eligibility.models import EligibilityDecision
from modules.eligibility.services import (
    EligibilityEvidenceUnavailableError,
    decide_for_household,
)
from modules.households import queries as household_queries
from modules.rules.services import publish

pytestmark = pytest.mark.django_db

THRESHOLDS = {
    str(size): amount
    for size, amount in enumerate(
        [12_307, 24_819, 36_527, 45_193, 59_641, 68_273, 83_459],
        start=1,
    )
}


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_user(
        "eligibility-staff@example.test",
        role="intake_worker",
    )


@pytest.fixture
def household(staff):
    household_model = apps.get_model("households", "Household")
    walk_in_channel = next(
        value
        for value, _ in household_model._meta.get_field("channel").choices
        if value in {"walk-in", "walk_in"}
    )
    return household_model.objects.create(
        channel=walk_in_channel,
        status="draft",
        street_number="100",
        street_name="Rue Exemple",
        city="Montréal",
        postal_code="H2X 1Y4",
        address_key="100-rue-exemple-h2x1y4",
        phone="+15145550100",
        created_by=staff,
    )


@pytest.fixture
def lico(staff):
    return publish(
        "lico_thresholds",
        {
            "year": 2025,
            "source_url": "https://www.statcan.gc.ca/",
            "retrieved_on": "2026-10-01",
            "thresholds": THRESHOLDS.copy(),
        },
        staff,
        effective_from=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def confirmed_inputs(household, monkeypatch):
    snapshot = SimpleNamespace(
        household=household,
        household_size=3,
        adult_count=2,
        adult_incomes_cents=[12_345, 20_000],
    )
    monkeypatch.setattr(
        household_queries,
        "eligibility_inputs",
        lambda household_id: snapshot if household_id == household.pk else None,
        raising=False,
    )
    return snapshot


@pytest.mark.parametrize(
    ("incomes", "eligible"),
    [
        ([12_345, 20_000], True),
        ([30_000, 20_000], False),
    ],
)
def test_staff_decision_persists_complete_snapshot(
    staff, household, lico, confirmed_inputs, incomes, eligible
):
    confirmed_inputs.adult_incomes_cents = incomes

    decision = decide_for_household(household.pk, staff)
    saved = EligibilityDecision.objects.get(pk=decision.pk)

    assert saved.household_id == household.pk
    assert saved.household_size == 3
    assert saved.adult_incomes_cents == incomes
    assert saved.household_income_cents == sum(incomes)
    assert saved.threshold_cents == THRESHOLDS["3"]
    assert saved.threshold_year == 2025
    assert saved.ruleset_version_id == lico.pk
    assert saved.eligible is eligible
    assert saved.decided_by_type == "staff"
    assert saved.decided_by_id == staff.pk
    assert saved.created_at is not None


def test_new_rule_version_creates_new_decision_without_rewriting_old(
    staff, household, lico, confirmed_inputs
):
    first = decide_for_household(household.pk, staff)

    updated_thresholds = {**THRESHOLDS, "3": 30_000}
    newer_rule = publish(
        "lico_thresholds",
        {
            **lico.values,
            "thresholds": updated_thresholds,
        },
        staff,
        effective_from=timezone.now() - timedelta(minutes=1),
    )

    second = decide_for_household(household.pk, staff)
    first.refresh_from_db()

    assert first.eligible is True
    assert first.threshold_cents == THRESHOLDS["3"]
    assert first.ruleset_version_id == lico.pk
    assert second.eligible is False
    assert second.threshold_cents == 30_000
    assert second.ruleset_version_id == newer_rule.pk
    assert EligibilityDecision.objects.filter(household=household).count() == 2


def test_missing_evidence_reader_fails_closed(staff, household, lico, monkeypatch):
    monkeypatch.delattr(household_queries, "eligibility_inputs", raising=False)

    with pytest.raises(
        EligibilityEvidenceUnavailableError,
        match="evidence is not available",
    ):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()


def test_beneficiary_cannot_record_staff_decision(
    django_user_model, household, lico, confirmed_inputs
):
    beneficiary = django_user_model.objects.create_user(
        "beneficiary@example.test",
        role="beneficiary",
    )

    with pytest.raises(PermissionDenied):
        decide_for_household(household.pk, beneficiary)

    assert not EligibilityDecision.objects.exists()


@pytest.mark.parametrize(
    "statement",
    [
        (
            "UPDATE eligibility_eligibilitydecision "
            "SET eligible = NOT eligible WHERE id = %s"
        ),
        "DELETE FROM eligibility_eligibilitydecision WHERE id = %s",
    ],
)
def test_database_rejects_sql_mutations(
    staff, household, lico, confirmed_inputs, statement
):
    decision = decide_for_household(household.pk, staff)

    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(statement, [decision.pk])

    decision.refresh_from_db()
    assert decision.eligible is True
    assert EligibilityDecision.objects.filter(pk=decision.pk).exists()


def test_orm_rejects_changes_to_decision_history(
    staff, household, lico, confirmed_inputs
):
    decision = decide_for_household(household.pk, staff)

    decision.eligible = False
    with pytest.raises(ValidationError, match="cannot be updated"):
        decision.save()

    with pytest.raises(ValidationError, match="cannot be updated"):
        EligibilityDecision.objects.filter(pk=decision.pk).update(eligible=False)

    with pytest.raises(ValidationError, match="cannot be deleted"):
        decision.delete()

    with pytest.raises(ValidationError, match="cannot be deleted"):
        EligibilityDecision.objects.filter(pk=decision.pk).delete()

    decision.refresh_from_db()
    assert decision.eligible is True


@pytest.mark.parametrize(
    ("household_size", "incomes"),
    [
        (0, [100]),
        (2, []),
        (1, [100, 200]),
        (2, [-1]),
        (2, [True]),
    ],
)
def test_invalid_income_evidence_creates_no_decision(
    staff, household, lico, confirmed_inputs, household_size, incomes
):
    confirmed_inputs.household_size = household_size
    confirmed_inputs.adult_incomes_cents = incomes

    with pytest.raises(EligibilityEvidenceUnavailableError):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()


def test_missing_active_lico_rule_creates_no_decision(
    staff, household, confirmed_inputs
):
    with pytest.raises(ValidationError, match="No active LICO"):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()


def test_automatic_decision_has_no_staff_actor(household, lico, confirmed_inputs):
    decision = decide_for_household(household.pk, None)

    assert decision.decided_by_type == "automatic"
    assert decision.decided_by_id is None
    assert decision.eligible is True


@pytest.mark.parametrize(
    ("adult_count", "incomes"),
    [
        (None, [100, 200]),
        (0, [100, 200]),
        (1, [100, 200]),
        (3, [100, 200]),
        (True, [100, 200]),
    ],
)
def test_incomplete_adult_evidence_is_rejected(
    staff, household, lico, confirmed_inputs, adult_count, incomes
):
    confirmed_inputs.adult_count = adult_count
    confirmed_inputs.adult_incomes_cents = incomes

    with pytest.raises(EligibilityEvidenceUnavailableError):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()


def test_official_2024_lico_seed_drives_persisted_decisions(
    staff, household, confirmed_inputs
):
    from django.core.management import call_command

    from modules.rules.queries import active

    call_command("seed_rules", verbosity=0)

    rule = active("lico_thresholds")
    assert rule is not None
    assert rule.values["year"] == 2024
    assert rule.values["thresholds"]["3"] == 4_785_100

    confirmed_inputs.adult_incomes_cents = [2_000_000, 2_785_100]
    at_threshold = decide_for_household(household.pk, staff)

    assert at_threshold.eligible is True
    assert at_threshold.household_income_cents == 4_785_100
    assert at_threshold.threshold_cents == 4_785_100
    assert at_threshold.threshold_year == 2024
    assert at_threshold.ruleset_version_id == rule.pk

    confirmed_inputs.adult_incomes_cents = [2_000_000, 2_785_101]
    above_threshold = decide_for_household(household.pk, staff)

    assert above_threshold.eligible is False
    assert above_threshold.household_income_cents == 4_785_101

    at_threshold.refresh_from_db()
    assert at_threshold.eligible is True
    assert EligibilityDecision.objects.filter(household=household).count() == 2


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize(
    ("incomes", "outcome"),
    [([12_345, 20_000], "eligible"), ([30_000, 20_000], "ineligible")],
)
def test_committed_decision_logs_only_safe_references(
    staff,
    household,
    lico,
    confirmed_inputs,
    caplog,
    django_capture_on_commit_callbacks,
    automatic,
    incomes,
    outcome,
):
    confirmed_inputs.adult_incomes_cents = incomes
    caplog.set_level(logging.INFO, logger="iris.eligibility")

    with django_capture_on_commit_callbacks(execute=True):
        decision = decide_for_household(household.pk, None if automatic else staff)
        assert caplog.record_tuples == []

    assert caplog.record_tuples == [
        ("iris.eligibility", logging.INFO, "eligibility_decided")
    ]
    record = caplog.records[0]
    assert record.decision_id == decision.pk
    assert record.household_id == household.pk
    assert record.outcome == outcome
    assert record.rule_version == lico.version
    # Check the actual JSON output too: unallowlisted extras disappear there.
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "INFO",
        "logger": "iris.eligibility",
        "event": "eligibility_decided",
        "decision_id": str(decision.pk),
        "household_id": str(household.pk),
        "outcome": outcome,
        "rule_version": lico.version,
    }
    assert set(record.__dict__) - set(logging.makeLogRecord({}).__dict__) - {
        "message",
        "asctime",
    } == {
        "event",
        "decision_id",
        "household_id",
        "outcome",
        "rule_version",
    }


def test_rolled_back_decision_emits_no_success_event(
    staff,
    household,
    lico,
    confirmed_inputs,
    caplog,
    django_capture_on_commit_callbacks,
):
    caplog.set_level(logging.INFO, logger="iris.eligibility")

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(ValueError, match="Cancel workflow"),
        transaction.atomic(),
    ):
        decide_for_household(household.pk, staff)
        raise ValueError("Cancel workflow")

    assert not EligibilityDecision.objects.exists()
    assert caplog.record_tuples == []


def test_failed_decision_save_emits_no_success_event(
    staff,
    household,
    lico,
    confirmed_inputs,
    monkeypatch,
    caplog,
    django_capture_on_commit_callbacks,
):
    def fail_save(*args, **kwargs):
        raise IntegrityError("Decision insert failed")

    monkeypatch.setattr(EligibilityDecision, "save", fail_save)
    caplog.set_level(logging.INFO, logger="iris.eligibility")

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(IntegrityError, match="Decision insert failed"),
    ):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()
    assert caplog.record_tuples == []


@pytest.mark.parametrize("evidence", [None, "wrong_household", "invalid_incomes"])
def test_unusable_evidence_emits_no_success_event(
    staff,
    household,
    lico,
    confirmed_inputs,
    monkeypatch,
    caplog,
    django_capture_on_commit_callbacks,
    evidence,
):
    if evidence == "wrong_household":
        confirmed_inputs.household = SimpleNamespace(pk=None)
    elif evidence == "invalid_incomes":
        confirmed_inputs.adult_incomes_cents = (12_345, 20_000)
    else:
        monkeypatch.setattr(household_queries, "eligibility_inputs", lambda _: None)
    caplog.set_level(logging.INFO, logger="iris.eligibility")

    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(EligibilityEvidenceUnavailableError),
    ):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()
    assert caplog.record_tuples == []


def test_each_decision_keeps_its_own_event_until_commit(
    staff,
    household,
    lico,
    confirmed_inputs,
    caplog,
    django_capture_on_commit_callbacks,
):
    caplog.set_level(logging.INFO, logger="iris.eligibility")

    with django_capture_on_commit_callbacks(execute=True):
        first = decide_for_household(household.pk, staff)
        confirmed_inputs.adult_incomes_cents = [30_000, 20_000]
        second = decide_for_household(household.pk, None)
        # The callback must retain the persisted result, even if the caller
        # later changes the returned in-memory instance.
        first.eligible = False
        assert caplog.record_tuples == []

    assert [(r.decision_id, r.outcome) for r in caplog.records] == [
        (first.pk, "eligible"),
        (second.pk, "ineligible"),
    ]
    first.refresh_from_db()
    assert first.eligible is True


@pytest.mark.parametrize("automatic", [False, True])
@pytest.mark.parametrize(
    "incomes,outcome",
    [([12_345, 20_000], "eligible"), ([30_000, 20_000], "ineligible")],
)
@pytest.mark.django_db(transaction=True)
def test_every_decision_has_one_durable_safe_household_audit(
    staff, household, lico, confirmed_inputs, automatic, incomes, outcome
):
    # rule: SEC-08, SEC-09
    confirmed_inputs.adult_incomes_cents = incomes
    decision = decide_for_household(household.pk, None if automatic else staff)
    event = search_events(household=household.pk).get()
    assert event.action == "decision"
    assert event.actor_id == (None if automatic else staff.pk)
    assert event.actor_role == ("system" if automatic else "intake_worker")
    assert event.metadata == {
        "decision_id": str(decision.pk),
        "outcome": outcome,
        "rule_version": lico.version,
    }
    # Exact keys and values exclude all incomes, thresholds and personal evidence.
    assert event.target_type == "household"
    assert event.target_id == str(household.pk)


@pytest.mark.parametrize("automatic", [False, True])
def test_failed_audit_rolls_back_decision_and_success_log(
    staff,
    household,
    lico,
    confirmed_inputs,
    monkeypatch,
    caplog,
    django_capture_on_commit_callbacks,
    automatic,
):
    def fail(*args, **kwargs):
        raise IntegrityError("Audit insert failed")

    monkeypatch.setattr("modules.audit.services.AuditEvent.save", fail)
    caplog.set_level(logging.INFO, logger="iris.eligibility")
    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(IntegrityError, match="Audit insert failed"),
    ):
        decide_for_household(household.pk, None if automatic else staff)
    assert not EligibilityDecision.objects.exists()
    assert not search_events(household=household.pk).exists()
    assert caplog.record_tuples == []


def test_failed_decision_write_records_no_durable_audit(
    staff, household, lico, confirmed_inputs, monkeypatch
):
    def fail(*args, **kwargs):
        raise IntegrityError("Decision insert failed")

    monkeypatch.setattr(EligibilityDecision, "save", fail)
    with pytest.raises(IntegrityError, match="Decision insert failed"):
        decide_for_household(household.pk, staff)
    assert not search_events(household=household.pk).exists()


def test_outer_rollback_removes_decision_and_durable_audit(
    staff, household, lico, confirmed_inputs
):
    with pytest.raises(RuntimeError, match="abort"), transaction.atomic():
        decide_for_household(household.pk, staff)
        assert search_events(household=household.pk).count() == 1
        raise RuntimeError("abort")
    assert not EligibilityDecision.objects.exists()
    assert not search_events(household=household.pk).exists()


def test_redeciding_preserves_each_audit_and_its_original_rule_version(
    staff, household, lico, confirmed_inputs
):
    first = decide_for_household(household.pk, staff)
    newer = publish(
        "lico_thresholds",
        {**lico.values, "thresholds": {**THRESHOLDS, "3": 30_000}},
        staff,
    )
    second = decide_for_household(household.pk, None)
    assert list(
        search_events(household=household.pk).values_list("metadata", flat=True)
    ) == [
        {
            "decision_id": str(second.pk),
            "outcome": "ineligible",
            "rule_version": newer.version,
        },
        {
            "decision_id": str(first.pk),
            "outcome": "eligible",
            "rule_version": lico.version,
        },
    ]


def test_unsaved_staff_cannot_be_misattributed_to_an_automatic_decision(
    django_user_model, household, lico, confirmed_inputs
):
    unsaved = django_user_model(email="unsaved@example.test", role="intake_worker")
    with pytest.raises(PermissionDenied):
        decide_for_household(household.pk, unsaved)
    assert not EligibilityDecision.objects.exists()
    assert not search_events(household=household.pk).exists()
