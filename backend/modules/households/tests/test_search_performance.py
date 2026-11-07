# AI contribution: 50% or more AI-generated
"""US-63: fully evaluated searches and authenticated API reads at 5,000 files."""

import json
from statistics import median, quantiles
from time import perf_counter

import pytest
from django.db import connection
from django.urls import reverse

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, Member
from modules.households.queries import search
from modules.households.tests.search_dataset import seed_search_dataset

pytestmark = pytest.mark.django_db
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
    assert Household.objects.count() == 5000
    assert cold_api_ms < 1000, {"cold_api_ms": round(cold_api_ms, 2)}


def test_search_counts_are_correct_with_5000_households(client, seeded_search_dataset):
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


def test_search_and_api_requests_are_under_one_second_with_5000_households(
    client, cold_api_ms
):
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
    print(json.dumps(timings))
    assert max(query_times) < 1, timings
    assert max(api_times) < 1, timings
    assert quantiles(api_times, n=100)[94] < 0.5, timings
