# AI contribution: 50% or more AI-generated
"""Draft services and serializers share the holder-inclusive limit."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import override
from rest_framework.test import APIClient

from modules.households.models import Household
from modules.households.services import submit_walk_in, update_draft
from modules.households.tests.factories import MemberFactory
from modules.rules.services import publish

pytestmark = pytest.mark.django_db


def _patch_members(household, members, worker):
    client = APIClient()
    client.force_authenticate(user=worker)
    return client.patch(
        reverse("staff-households-detail", kwargs={"id": household.pk}),
        {"members": members},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )


# rule: BR-HH-001
@pytest.mark.parametrize("limit", [15, 3])
@pytest.mark.parametrize("excess", [0, 1])
@pytest.mark.parametrize("entry", ["service", "api"])
def test_draft_limit_includes_the_holder(
    limit, excess, entry, ready_household_factory, submission_worker
):
    """Reject an extra person without replacing the saved members."""
    publish("household_size", {"max_people": limit}, submission_worker)
    additional = limit - 1 + excess
    household = ready_household_factory()
    members = [
        {
            "first_name": "Example",
            "last_name": "Child",
            "date_of_birth": date(2010, 1, 1),
            "relation": "child",
        }
        for _ in range(additional)
    ]
    with override("en"):
        if entry == "api":
            response = _patch_members(household, members, submission_worker)
            assert response.status_code == (400 if excess else 200)
            if excess:
                assert response.data["fields"]["members"] == [
                    f"Add at most {limit - 1} people besides the holder."
                ]
        elif not excess:
            update_draft(household.pk, {"members": members}, submission_worker)
        else:
            with pytest.raises(ValidationError) as exc:
                update_draft(household.pk, {"members": members}, submission_worker)
            assert exc.value.message_dict["members"] == [
                f"A household can have at most {limit} people including the holder."
            ]
    assert household.members.count() == (1 if excess else limit)


# rule: BR-HH-001
@pytest.mark.parametrize("total", [3, 4])
def test_submission_reads_configured_limit(
    total, ready_household_factory, submission_worker
):
    publish("household_size", {"max_people": 3}, submission_worker)
    household = ready_household_factory()
    MemberFactory.create_batch(total - 1, household=household)
    with override("en"):
        if total == 3:
            submit_walk_in(household.pk, submission_worker)
        else:
            with pytest.raises(ValidationError, match="at most 3 people"):
                submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.members.count() == total
    assert household.status == (
        Household.Status.SUBMITTED if total == 3 else Household.Status.DRAFT
    )
    assert household.draft_events.filter(action="submitted").count() == (total == 3)


# rule: BR-HH-001
@pytest.mark.parametrize("entry", ["service", "api", "submission"])
def test_missing_size_rules_prevent_writes(
    entry, ready_household_factory, submission_worker, monkeypatch
):
    household = ready_household_factory()
    monkeypatch.setattr("modules.households.limits.rule_queries.active", lambda _: None)
    with override("en"):
        if entry == "api":
            response = _patch_members(household, [], submission_worker)
            assert response.status_code == 400
            assert response.data["fields"]["members"] == [
                "Household size rules need configuration."
            ]
        else:
            with pytest.raises(ValidationError, match="rules need configuration"):
                if entry == "submission":
                    submit_walk_in(household.pk, submission_worker)
                else:
                    update_draft(household.pk, {"members": []}, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.members.count() == 1
    assert not household.draft_events.exists()
