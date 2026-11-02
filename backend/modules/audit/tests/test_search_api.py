# AI contribution: 50% or more AI-generated
"""Admin authorization, filtering and pagination of audit records."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from django.urls import reverse

from modules.audit.services import record
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(django_user_model):
    return django_user_model.objects.create_user(
        "admin-search@example.test", role="admin"
    )


@pytest.mark.parametrize(
    "role", ["beneficiary", "store_staff", "store_manager", "intake_worker"]
)
def test_other_roles_cannot_search(client, django_user_model, role):
    store = StoreFactory() if role in {"store_staff", "store_manager"} else None
    user = django_user_model.objects.create_user(
        f"{role}@example.test", role=role, store=store
    )
    client.force_login(user)
    assert client.get(reverse("audit-search")).status_code == 403


def test_signed_out_cannot_search(client):
    assert client.get(reverse("audit-search")).status_code in (401, 403)


def test_filters_and_montreal_date_boundaries(
    client, admin, django_user_model, monkeypatch
):
    staff = django_user_model.objects.create_user(
        "staff-search@example.test", role="intake_worker"
    )
    other = django_user_model.objects.create_user(
        "other-search@example.test", role="intake_worker"
    )
    household, other_household = uuid4(), uuid4()
    # 03:30 UTC is October 30 in Montreal; 04:30 UTC is October 31.
    monkeypatch.setattr(
        "django.utils.timezone.now", lambda: datetime(2026, 10, 31, 3, 30, tzinfo=UTC)
    )
    record(staff, "view", "household", household, {})
    monkeypatch.setattr(
        "django.utils.timezone.now", lambda: datetime(2026, 10, 31, 4, 30, tzinfo=UTC)
    )
    expected = record(staff, "view", "household", household, {})
    record(staff, "view", "household", other_household, {})
    record(other, "view", "household", household, {})
    record(staff, "view", "store", household, {})
    client.force_login(admin)
    response = client.get(
        reverse("audit-search"),
        {
            "household": str(household),
            "actor": str(staff.pk),
            "from": "2026-10-31",
            "to": "2026-10-31",
        },
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == expected.pk
    assert response.json()["results"][0]["actor"] == str(staff.pk)
    assert "email" not in response.content.decode()


@pytest.mark.parametrize(
    "query",
    [
        {"household": "not-a-uuid"},
        {"actor": "bad"},
        {"from": "2026-02-30"},
        {"from": "2026-11-02", "to": "2026-11-01"},
    ],
)
def test_invalid_filters_are_rejected(client, admin, query):
    client.force_login(admin)
    assert client.get(reverse("audit-search"), query).status_code == 400


def test_pagination_and_read_only(client, admin):
    for _ in range(3):
        record(admin, "view", "household", uuid4(), {})
    client.force_login(admin)
    first = client.get(reverse("audit-search"), {"page_size": 2}).json()
    second = client.get(reverse("audit-search"), {"page_size": 2, "page": 2}).json()
    assert first["count"] == 3
    assert len(first["results"]) == 2 and first["next"]
    assert len(second["results"]) == 1 and second["previous"]
    assert {e["id"] for e in first["results"]}.isdisjoint(
        e["id"] for e in second["results"]
    )
    assert client.post(reverse("audit-search"), {}).status_code == 405
