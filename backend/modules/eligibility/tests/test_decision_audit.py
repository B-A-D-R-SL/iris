# AI contribution: 50% or more AI-generated
import logging

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction

from modules.audit.queries import search_events
from modules.eligibility.models import EligibilityDecision
from modules.eligibility.services import decide_for_household
from modules.eligibility.tests.fixtures import THRESHOLDS
from modules.rules.services import publish

pytestmark = pytest.mark.django_db


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
