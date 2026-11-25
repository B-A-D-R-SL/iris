# AI contribution: 50% or more AI-generated
"""Saved notices: member edits keep them and staff can list them (T-03.18.2)."""

from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from modules.documents.queries import current_notices
from modules.households.tests.factories import MemberFactory
from modules.households.tests.notices.helpers import (
    api_client,
    filed_notice,
    make_user,
    post_notice,
)

pytestmark = pytest.mark.django_db


SPOUSE = {
    "first_name": "Example",
    "last_name": "Spouse",
    "date_of_birth": "1985-02-03",
    "relation": "spouse_partner",
}


def _spouse_with_notice(household: Any, worker: Any) -> Any:
    spouse: Any = MemberFactory(household=household, **SPOUSE)
    data = {
        "member": str(spouse.pk),
        "did_not_file": "true",
        "did_not_file_reason": "No income in 2025",
    }
    assert post_notice(api_client(worker), household, data).status_code == 201
    return spouse


def _save_members(worker: Any, household: Any, members: list[dict[str, Any]]) -> Any:
    url = reverse("staff-households-detail", kwargs={"id": household.pk})
    return api_client(worker).patch(url, {"members": members}, format="json")


def test_adding_a_member_keeps_members_with_notices(
    household: Any, holder: Any, worker: Any
) -> None:
    spouse = _spouse_with_notice(household, worker)
    newborn = {
        "first_name": "Example",
        "last_name": "Baby",
        "date_of_birth": "2026-01-15",
        "relation": "child",
    }

    response = _save_members(worker, household, [SPOUSE, newborn])

    assert response.status_code == 200, response.data
    assert household.members.count() == 3
    assert household.members.filter(pk=spouse.pk).exists()
    assert spouse.pk in current_notices([spouse.pk])


def test_removing_a_member_with_a_notice_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    spouse = _spouse_with_notice(household, worker)

    response = _save_members(worker, household, [])

    assert response.status_code == 400
    assert "members" in response.data["fields"]
    assert household.members.filter(pk=spouse.pk).exists()


@pytest.mark.parametrize(
    ("field", "value"), [("first_name", "Corrected"), ("date_of_birth", "1986-02-03")]
)
def test_editing_a_member_by_id_keeps_their_notice(
    household: Any, holder: Any, worker: Any, field: str, value: str
) -> None:
    spouse: Any = MemberFactory(household=household, **SPOUSE)
    notice = post_notice(
        api_client(worker),
        household,
        filed_notice(spouse, name_on_notice="Example Spouse"),
    )
    assert notice.status_code == 201, notice.data

    response = _save_members(
        worker, household, [SPOUSE | {"id": str(spouse.pk), field: value}]
    )

    assert response.status_code == 200, response.data
    member = next(m for m in response.data["members"] if m["id"] == str(spouse.pk))
    assert member[field] == value
    assert household.members.count() == 2
    current = current_notices([spouse.pk])[spouse.pk]
    assert str(current.pk) == notice.data["id"]
    assert current.name_on_notice == "Example Spouse"


@pytest.mark.parametrize("case", ["holder", "another_household", "duplicate"])
def test_member_update_refuses_invalid_ids(
    household: Any, holder: Any, worker: Any, case: str
) -> None:
    if case == "holder":
        members = [SPOUSE | {"id": str(holder.pk)}]
    elif case == "another_household":
        other: Any = MemberFactory()
        members = [SPOUSE | {"id": str(other.pk)}]
    else:
        spouse: Any = MemberFactory(household=household, **SPOUSE)
        members = [SPOUSE | {"id": str(spouse.pk)}] * 2

    response = _save_members(worker, household, members)

    assert response.status_code == 400
    assert "members" in response.data["fields"]


# rule: BR-DOC-007
def test_member_with_a_notice_cannot_be_changed_to_a_minor(
    household: Any, holder: Any, worker: Any
) -> None:
    spouse = _spouse_with_notice(household, worker)
    notice = current_notices([spouse.pk])[spouse.pk]

    response = _save_members(
        worker,
        household,
        [SPOUSE | {"id": str(spouse.pk), "date_of_birth": "2016-03-01"}],
    )

    assert response.status_code == 400
    assert "members" in response.data["fields"]
    spouse.refresh_from_db()
    assert spouse.date_of_birth.isoformat() == SPOUSE["date_of_birth"]
    assert current_notices([spouse.pk])[spouse.pk].pk == notice.pk


def test_missing_notice_settings_answer_503_even_without_a_file(
    household: Any, holder: Any, worker: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("modules.rules.queries.active", lambda rule_type, at=None: None)
    data = {
        "member": str(holder.pk),
        "did_not_file": "true",
        "did_not_file_reason": "No income in 2025",
    }

    response = post_notice(
        api_client(worker), household, data, HTTP_ACCEPT_LANGUAGE="fr"
    )

    assert response.status_code == 503
    assert response.data["code"] == "notice_settings_missing"
    assert "administrat" in response.data["message"]
    assert not current_notices([holder.pk])


def _list(client: APIClient, household_id: Any) -> Any:
    url = reverse("staff-households-notices", kwargs={"id": household_id})
    return client.get(url)


def test_list_returns_only_the_current_notice_of_each_member(
    household: Any, holder: Any, worker: Any
) -> None:
    """Staff resuming the file see what was saved; a replaced entry is not shown."""
    client = api_client(worker)
    post_notice(client, household, filed_notice(holder))
    replacement = post_notice(
        client,
        household,
        {
            "member": str(holder.pk),
            "did_not_file": "true",
            "did_not_file_reason": "No income in 2025",
        },
    )

    response = _list(client, household.pk)

    assert response.status_code == 200
    assert [notice["id"] for notice in response.data] == [replacement.data["id"]]
    assert response.data[0]["member"] == str(holder.pk)
    assert "file_ref" not in response.data[0]


def test_list_is_empty_before_any_notice(household: Any, worker: Any) -> None:
    response = _list(api_client(worker), household.pk)

    assert response.status_code == 200
    assert response.data == []


def test_list_of_an_unknown_household_is_404(worker: Any) -> None:
    response = _list(api_client(worker), "00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404


@pytest.mark.parametrize("role", ["beneficiary", "store_manager"])
def test_list_is_refused_to_other_roles(household: Any, role: str) -> None:
    response = _list(api_client(make_user(role)), household.pk)

    assert response.status_code == 403


def test_list_is_refused_to_signed_out_visitors(household: Any) -> None:
    response = _list(api_client(None), household.pk)

    assert response.status_code == 401
