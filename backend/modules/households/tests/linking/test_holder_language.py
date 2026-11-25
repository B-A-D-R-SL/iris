# AI contribution: 50% or more AI-generated
"""US-08: a linked household file follows its holder's language, emails included."""

from datetime import timedelta
from typing import Any

import pytest
from rest_framework.test import APIClient

from modules.accounts import services as account_services
from modules.accounts.tests.factories import UserFactory
from modules.households import services
from modules.households.account_link_services import link_existing_account
from modules.households.models import Household
from modules.households.tests.approval.helpers import NOW
from modules.households.tests.linking.helpers import PASSWORD, account, approved_walk_in
from modules.notifications.models import EmailLog
from modules.rules.services import publish

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


def language_of(household: Any) -> str:
    return Household.objects.values_list("preferred_language", flat=True).get(
        pk=household.pk
    )


# rule: BR-LANG-003, BR-HH-ACCOUNT-001
def test_an_invited_account_starts_in_the_files_language(
    household: Any, invitation_token: str
) -> None:
    """Staff recorded English on the file (see the invitation_token fixture)."""
    user = account_services.accept_invitation(invitation_token, PASSWORD)
    user.refresh_from_db()
    assert user.preferred_language == "en"
    assert language_of(household) == "en"


# rule: BR-LANG-003, BR-HH-ACCOUNT-002
def test_a_file_linked_at_the_counter_takes_the_accounts_language(staff: Any) -> None:
    household = approved_walk_in(staff, preferred_language="fr")
    holder = account(preferred_language="en")
    linked = link_existing_account(household.pk, staff)
    assert linked.preferred_language == "en"
    assert language_of(household) == "en"
    holder.refresh_from_db()
    assert holder.preferred_language == "en"


# rule: BR-LANG-003, BR-NOTIF-003
def test_the_holders_choice_is_used_for_the_households_emails(staff: Any) -> None:
    holder = account()
    household = approved_walk_in(staff, holder=holder, preferred_language="fr")
    other = approved_walk_in(staff, email="other@example.test", preferred_language="fr")

    client = APIClient()
    client.force_authenticate(holder)
    response = client.patch("/api/me/", {"language": "en"}, format="json")
    assert response.status_code == 200

    assert language_of(household) == "en"
    assert language_of(other) == "fr"
    admin: Any = UserFactory(role="admin")
    publish(
        "household_suspension",
        {"reason_max_length": 500},
        admin,
        effective_from=NOW - timedelta(days=1),
    )
    services.change_suspension(household.pk, "Safety review", admin, reactivate=False)
    log = EmailLog.objects.get(template_key="household_suspended")
    assert (log.to_email, log.language) == (household.email, "en")


# rule: BR-LANG-003
def test_an_anonymized_file_is_left_alone(staff: Any) -> None:
    holder = account()
    household = approved_walk_in(staff, holder=holder, preferred_language="fr")
    Household.objects.filter(pk=household.pk).update(
        anonymized_at=household.approved_at
    )
    account_services.change_language(holder, "en")
    assert language_of(household) == "fr"
