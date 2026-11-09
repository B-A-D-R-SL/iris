# AI contribution: 50% or more AI-generated
"""US-63: fully evaluated searches and authenticated API reads at 5,000 files."""

import json
import logging
from statistics import median, quantiles
from time import perf_counter

import pytest
from django.db import connection
from django.db.models import Count, Window
from django.urls import reverse

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, Member
from modules.households.queries import search
from modules.households.tests.search_dataset import seed_search_dataset

pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)
SEARCH_CASES = (
    ("Élod", None),
    ("Exemple", 5000),
    ("Exemple Élo", None),
    ("foyer-04234@example.test", 1),
    ("IR-004234", 1),
    ("(514) 555-0123", 50),
    ("rue emile", 3334),
    ("not-a-matching-file", 0),
    ("Él", None),
    ("%", 0),
)


@pytest.fixture
def seeded_search_dataset(client):
    """Create only fictional rows and a session in pytest's disposable database."""
    staff = UserFactory(role="intake_worker")
    seed_search_dataset(staff)
    client.force_login(staff)
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE households_household")
        cursor.execute("ANALYZE households_member")


@pytest.fixture
def cold_api_ms(client, seeded_search_dataset) -> float:
    """Measure the first authenticated request after URL configuration is ready."""
    url = reverse("staff-households-create")
    started = perf_counter()
    response = client.get(url, {"q": "IR-004234"})
    elapsed = (perf_counter() - started) * 1000
    assert response.status_code == 200
    return elapsed


def test_first_authenticated_search_is_under_one_second_with_5000_households(
    cold_api_ms,
):
    """Check cold API latency after seeding the required household population."""
    assert Household.objects.count() == 5000
    assert cold_api_ms < 1000, {"cold_api_ms": round(cold_api_ms, 2)}


def test_search_counts_are_correct_with_5000_households(client, seeded_search_dataset):
    """Check exact counts and supported search fields independently of timing."""
    assert Household.objects.count() == 5000
    assert Member.objects.count() > 5000
    url = reverse("staff-households-create")
    for term, expected_count in SEARCH_CASES:
        response = client.get(url, {"q": term})
        assert response.status_code == 200
        if expected_count is None:
            assert response.json()["results"], term
        else:
            assert response.json()["count"] == expected_count, term


def _household_scans(plan):
    return int(plan.get("Relation Name") == "households_household") + sum(
        _household_scans(child) for child in plan.get("Plans", [])
    )


@pytest.mark.parametrize("term", ["Élod", "IR-004234", "rue emile", "missing-file"])
def test_search_plan_does_not_scan_households_twice(term, seeded_search_dataset):
    query = search(term).annotate(_search_total=Window(Count("pk")))[:20]
    plan = json.loads(query.explain(format="json"))[0]["Plan"]
    assert _household_scans(plan) == 1, plan


def test_search_and_api_requests_are_under_one_second_with_5000_households(
    client, cold_api_ms
):
    """Fully evaluate database and API searches before enforcing latency limits."""
    url = reverse("staff-households-create")
    query_times, api_times = [], []
    for term, _ in SEARCH_CASES:
        for _ in range(3):
            started = perf_counter()
            list(search(term)[:20])  # Force Django's lazy queryset to execute.
            query_times.append(perf_counter() - started)
            started = perf_counter()
            response = client.get(url, {"q": term})
            api_times.append(perf_counter() - started)
            assert response.status_code == 200
    timings = {
        "households": 5000,
        "cold_api_ms": round(cold_api_ms, 2),
        "samples": len(api_times),
        "query_max_ms": round(max(query_times) * 1000, 2),
        "api_median_ms": round(median(api_times) * 1000, 2),
        "api_p95_ms": round(quantiles(api_times, n=100)[94] * 1000, 2),
        "api_max_ms": round(max(api_times) * 1000, 2),
    }
    logger.info(
        "Household search sequential requests measured",
        extra={"event": "household_search_sequential_measured", "metrics": timings},
    )
    assert max(query_times) < 1, timings
    assert max(api_times) < 1, timings
    assert quantiles(api_times, n=100)[94] < 0.5, timings
