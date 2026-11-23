# AI contribution: 50% or more AI-generated
"""What a walk-in file's account looks like to staff (US-93). Read-only.

`link_refusal` is the one rule for which existing accounts may be linked; the
link service and the staff screen's state both use it.
"""

from dataclasses import dataclass
from uuid import UUID

from modules.accounts import queries as account_queries
from modules.accounts.queries import BENEFICIARY_ROLE, AccountSummary
from modules.households.models import Household


@dataclass(frozen=True)
class AccountLink:
    """The account state the staff screen shows, decided here, not in the screen.

    status: linked, can_link, cannot_link, invited, no_email or not_applicable.
    reason (cannot_link only): not_beneficiary, inactive or has_household.
    The account's names are given only for can_link, so staff can compare
    them with the person's ID before linking.
    """

    status: str
    reason: str
    account_first_name: str | None
    account_last_name: str | None


def holds_household(user_id: UUID) -> bool:
    """Whether this account already holds a household file."""
    return Household.objects.filter(holder_id=user_id).exists()


def link_refusal(account: AccountSummary) -> str | None:
    """Why this account cannot become a holder, or None when it can."""
    if account.role != BENEFICIARY_ROLE:
        return "not_beneficiary"
    if not account.is_active:
        return "inactive"
    if holds_household(account.id):
        return "has_household"
    return None


def account_link(household: Household) -> AccountLink:
    """The account state of one staff-visible file."""
    if household.holder_id is not None:
        return AccountLink("linked", "", None, None)
    approved_walk_in = (
        household.channel == Household.Channel.WALK_IN
        and household.status == Household.Status.APPROVED
    )
    if not approved_walk_in:
        return AccountLink("not_applicable", "", None, None)
    if not household.email:
        return AccountLink("no_email", "", None, None)
    account = account_queries.account_for_email(household.email)
    if account is None:
        return AccountLink("invited", "", None, None)
    reason = link_refusal(account)
    if reason is not None:
        return AccountLink("cannot_link", reason, None, None)
    return AccountLink("can_link", "", account.first_name, account.last_name)
