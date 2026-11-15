# AI contribution: 50% or more AI-generated
"""FIX-19: audit search query count, index use and timing on a year of events."""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from statistics import quantiles
from time import perf_counter
from unittest import mock
from uuid import UUID, uuid4

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.audit.queries import search_events
from modules.audit.services import record

pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)

# About 100,000 events: a year of pilot activity at 274 events a day, spread
# over 5,000 households (the NFR-04 search population) and 20 staff members.
DAYS, EVENTS_PER_DAY, HOUSEHOLDS, ACTORS = 365, 274, 5000, 20
FIRST_DAY = datetime(2026, 1, 1, 15, tzinfo=UTC)
TABLE = AuditEvent._meta.db_table


def _household(number: int) -> UUID:
    return UUID(int=number % HOUSEHOLDS + 1)


def _seed_year(actors: list) -> None:
    """Create fictional view events; ``created_at`` follows the patched clock."""
    number = 0
    for day in range(DAYS):
        events = []
        for _ in range(EVENTS_PER_DAY):
            number += 1
            events.append(
                AuditEvent(
                    actor=actors[number % len(actors)],
                    actor_role="intake_worker",
                    action=AuditEvent.Action.VIEW,
                    target_type="household",
                    target_id=str(_household(number)),
                )
            )
        moment = FIRST_DAY + timedelta(days=day)
        with mock.patch("django.utils.timezone.now", return_value=moment):
            AuditEvent.objects.bulk_create(events)


@pytest.fixture
def api():
    client = APIClient()
    client.force_authenticate(user=UserFactory(role="admin"))
    return client


@pytest.fixture
def actors():
    return [UserFactory(role="intake_worker") for _ in range(ACTORS)]


@pytest.fixture
def year_of_events(actors):
    """Seed in pytest's disposable database; seeding is never timed."""
    _seed_year(actors)
    with connection.cursor() as cursor:
        cursor.execute(f"ANALYZE {TABLE}")  # Fixed table name, no user input.


@pytest.mark.parametrize("events", [1, 25])
def test_search_page_takes_two_queries_whatever_the_number_of_events(
    api, actors, django_assert_num_queries, events
):
    # Events by different staff members: reading the actor must not add queries.
    for number in range(events):
        record(actors[number % ACTORS], "view", "household", uuid4(), {})
    with django_assert_num_queries(2):  # COUNT for the pager, then one page.
        response = api.get(reverse("audit-search"), {"page_size": 20})
    assert response.status_code == 200
    assert len(response.json()["results"]) == min(events, 20)


def _plan_nodes(plan: dict) -> list[dict]:
    return [plan] + [
        node for child in plan.get("Plans", []) for node in _plan_nodes(child)
    ]


def _audit_scans(**filters) -> list[tuple[str, str | None]]:
    """(node type, index name) of every read of the audit table for one page."""
    query = search_events(**filters)[:20]
    plan = json.loads(query.explain(format="json"))[0]["Plan"]
    return [
        (node["Node Type"], node.get("Index Name"))
        for node in _plan_nodes(plan)
        if node.get("Relation Name") == TABLE
    ]


@pytest.mark.parametrize(
    ("filters", "index"),
    [
        ({"household": _household(42)}, "audit_target_created_idx"),
        (
            {"date_from": date(2026, 6, 1), "date_to": date(2026, 6, 7)},
            "audit_created_idx",
        ),
        ({}, "audit_created_idx"),
    ],
)
def test_search_reads_the_audit_table_through_an_index(year_of_events, filters, index):
    scans = _audit_scans(**filters)
    assert scans and all(name == index for _, name in scans), scans


def _searches(actor) -> list[dict[str, str | int]]:
    """Each filter alone and combined, the first page and a deep page."""
    week: dict[str, str | int] = {"from": "2026-06-01", "to": "2026-06-07"}
    # A household seen that week, so the combined search has a page to read.
    june_3 = date(2026, 6, 3)
    household = search_events(date_from=june_3, date_to=june_3).values_list(
        "target_id", flat=True
    )[0]
    return [
        {"household": household},
        {"household": household, **week},
        {"actor": str(actor.pk)},
        week,
        {},
        {"page": 50},
    ]


def _timed_search(api, params) -> float:
    """Seconds for one authenticated API search that returns a page of events."""
    started = perf_counter()
    response = api.get(reverse("audit-search"), params)
    elapsed = perf_counter() - started
    assert response.status_code == 200, params
    assert response.json()["results"], params
    return elapsed


def test_audit_searches_are_under_half_a_second_with_a_year_of_events(
    api, actors, year_of_events
):
    searches = _searches(actors[3])
    # The first request also loads the URL configuration: logged, not asserted.
    cold = _timed_search(api, searches[0])
    times = [_timed_search(api, params) for params in searches for _ in range(3)]
    p95 = quantiles(times, n=20, method="inclusive")[18]
    timings = {
        "events": AuditEvent.objects.count(),
        "samples": len(times),
        "cold_ms": round(cold * 1000, 2),
        "p95_ms": round(p95 * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
    }
    logger.info(
        "Audit search requests measured",
        extra={"event": "audit_search_measured", "metrics": timings},
    )
    assert timings["events"] == DAYS * EVENTS_PER_DAY
    assert p95 < 0.5, timings  # NFR-04: 95% of data requests under 500 ms.
    assert max(times) < 1, timings
