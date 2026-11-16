# AI contribution: 50% or more AI-generated
"""Shared clock and queries for the US-18 approval tests."""

from datetime import UTC, datetime
from typing import Any

from django.apps import apps

from modules.households.approval_services import approve_walk_in
from modules.households.services import submit_walk_in

NOW = datetime(2026, 11, 8, 15, tzinfo=UTC)
# Direct task calls run without a native worker's injected JobContext.
DIRECT_CONTEXT: Any = None


def records(model: str, household: Any) -> Any:
    return apps.get_model(model).objects.filter(household=household)


def notices(household: Any) -> Any:
    return apps.get_model("documents.IncomeNotice").objects.filter(
        member__household=household
    )


def decisions(household: Any) -> Any:
    return records("eligibility.EligibilityDecision", household)


def audit_events(household: Any) -> Any:
    """Oldest first: without an order, PostgreSQL may return rows in any order."""
    return (
        apps.get_model("audit.AuditEvent")
        .objects.filter(target_id=str(household.pk))
        .order_by("created_at", "pk")
    )


def approval_events(household: Any) -> Any:
    """Select the outcome event separately from submission and eligibility."""
    return audit_events(household).filter(
        action="decision",
        metadata__outcome__in=["approved", "rejected", "review_required"],
    )


def assert_approval_audit_chain(household: Any, actor: Any) -> None:
    """One submission, one eligibility snapshot and one staff outcome survive."""
    events = list(audit_events(household).order_by("id"))
    decision = decisions(household).get()
    assert [event.action for event in events] == ["submit", "decision", "decision"]
    assert events[0].metadata == {}
    assert events[1].metadata == {
        "decision_id": str(decision.pk),
        "outcome": "eligible" if decision.eligible else "ineligible",
        "rule_version": decision.ruleset_version.version,
    }
    assert events[2].metadata == {"outcome": household.status}
    assert events[1].actor_id == events[2].actor_id == actor.pk


def invitations() -> Any:
    return apps.get_model("accounts.Invitation").objects.all()


def assert_unapproved(household: Any, status: str) -> None:
    household.refresh_from_db()
    assert household.status == status
    assert household.approved_at is None
    assert household.expires_at is None
    assert not invitations().exists()


def submit(household: Any) -> None:
    """Press Submit as staff do: approval follows submission (BR-DUP-002)."""
    submit_walk_in(household.pk, household.created_by)


def submit_and_approve(household: Any, actor: Any) -> Any:
    submit(household)
    return approve_walk_in(household, actor)
