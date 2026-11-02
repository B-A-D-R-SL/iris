# AI contribution: 50% or more AI-generated
"""Database-backed tests for the eligibility decision service."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from modules.eligibility.models import EligibilityDecision
from modules.eligibility.services import (
    EligibilityEvidenceUnavailable,
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
    return household_model.objects.create(
        channel="walk-in",
        status="draft",
        street_number="100",
        street_name="Rue Exemple",
        city="Montr?al",
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
        EligibilityEvidenceUnavailable,
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

    with pytest.raises(EligibilityEvidenceUnavailable):
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

    with pytest.raises(EligibilityEvidenceUnavailable):
        decide_for_household(household.pk, staff)

    assert not EligibilityDecision.objects.exists()
