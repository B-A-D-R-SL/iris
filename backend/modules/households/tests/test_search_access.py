# AI contribution: 50% or more AI-generated
"""Staff search refuses unauthorized callers and anonymized files."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.households.policies import can_resume_walk_in
from modules.households.queries import search_for_staff
from modules.households.tests.factories import HouseholdFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("query", ["", "Exemple"])
@pytest.mark.parametrize(
    "kind", ["beneficiary", "store_staff", "store_manager", "inactive", "anonymous"]
)
def test_search_query_refuses_unauthorized_actors_even_without_results(kind, query):
    # rule: BR-HH-ACCESS-001
    if kind == "anonymous":
        actor = AnonymousUser()
    elif kind == "inactive":
        actor = UserFactory(role="intake_worker", is_active=False)
    else:
        store = StoreFactory() if kind.startswith("store_") else None
        actor = UserFactory(role=kind, store=store)
    with pytest.raises(PermissionDenied):
        search_for_staff(query, actor)


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_anonymized_walk_in_draft_never_advertises_a_resume_action(role):
    """Refuse resuming anonymized drafts for every otherwise authorized staff role."""
    # rule: BR-HH-ACCESS-002
    staff = UserFactory(role=role)
    household = HouseholdFactory(anonymized_at=timezone.now())
    assert can_resume_walk_in(household, staff) is False
