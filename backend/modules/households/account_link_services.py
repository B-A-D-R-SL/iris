# AI contribution: 50% or more AI-generated
"""Link a walk-in household to its Iris account (US-93).

The holder account is `Household.holder`. It is set when the walk-in set-password
invitation is accepted (`link_invited_account`, a receiver of
`accounts.services.invitation_accepted`), or by staff at the counter for an
account that already exists (`link_existing_account`). Each link is audited and
logged with the household ID only.
"""

import logging
from typing import Any, Literal
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from modules.accounts import queries as account_queries
from modules.accounts import services as account_services
from modules.audit import services as audit_services
from modules.households import account_link_queries
from modules.households.models import Household, Member
from modules.households.policies import require_walk_in_staff
from modules.notifications import services as notification_services

logger = logging.getLogger("iris.households")

NOT_APPROVED = _("Only an approved file can be linked to an account.")
NO_EMAIL = _("This file has no email address. The household is served at the counter.")
ALREADY_LINKED = _("This file is already linked to an account.")
NO_ACCOUNT = _("No Iris account uses this file's email address.")
HAS_HOUSEHOLD = _("This account is already linked to another household.")
ACCOUNT_EXISTS = _(
    "This email address already has an Iris account. "
    "Link that account instead of sending an invitation."
)
REFUSALS = {
    "not_beneficiary": _("Staff and store accounts cannot be linked to a household."),
    "inactive": _("This account is deactivated and cannot be linked."),
    "has_household": HAS_HOUSEHOLD,
}


def _locked_walk_in(household_id: UUID) -> Household:
    """Lock a visible walk-in file for the caller's transaction.

    Raises Household.DoesNotExist for unknown, online or anonymized files.
    """
    return Household.objects.select_for_update().get(
        pk=household_id,
        channel=Household.Channel.WALK_IN,
        anonymized_at__isnull=True,
    )


def _require_unlinked_approved_with_email(household: Household) -> str:
    """The checks shared by linking and re-inviting; returns the file's email."""
    if household.status != Household.Status.APPROVED:
        raise ValidationError(NOT_APPROVED, code="not_approved")
    if not household.email:
        raise ValidationError(NO_EMAIL, code="no_email")
    if household.holder_id is not None:
        raise ValidationError(ALREADY_LINKED, code="household_already_linked")
    return household.email


def _save_holder(
    household: Household,
    user_id: UUID,
    actor: Any,
    method: Literal["invitation", "counter"],
) -> None:
    """Set the holder account, then audit and log the link.

    The one-to-one column refuses an account that already holds another file,
    including one linked by a concurrent request after our checks.
    """
    household.holder_id = user_id
    try:
        with transaction.atomic():
            household.save(update_fields=["holder", "updated_at"])
    except IntegrityError as exc:
        raise ValidationError(HAS_HOUSEHOLD, code="has_household") from exc
    audit_services.record(
        actor, "link_account", "household", household.pk, {"method": method}
    )
    household_id = household.pk
    transaction.on_commit(
        lambda: logger.info(
            "walk_in_account_linked",
            extra={"event": "walk_in_account_linked", "household_id": household_id},
        )
    )


def link_invited_account(*, user: Any, household_id: UUID, **kwargs: Any) -> None:
    """Make the account created from a walk-in invitation the file's holder.

    Runs inside the acceptance transaction: a refusal undoes the new account and
    leaves the invitation unused.
    """
    try:
        household = _locked_walk_in(household_id)
    except Household.DoesNotExist as exc:
        # The file was anonymized since the invitation was sent.
        raise ValidationError(
            _("This invitation link is invalid."), code="invitation_invalid"
        ) from exc
    if household.holder_id is not None:
        raise ValidationError(ALREADY_LINKED, code="household_already_linked")
    _save_holder(household, user.pk, user, "invitation")


@transaction.atomic
def link_existing_account(household_id: UUID, staff: AbstractBaseUser) -> Household:
    """Link the account that already uses the file's email (US-93).

    Staff call this only after comparing the person's ID with the name on the
    account, which the staff screen shows. Only an active beneficiary account
    without a household can be linked. Raises Household.DoesNotExist for an
    unknown, online or anonymized file.
    """
    require_walk_in_staff(staff)
    household = _locked_walk_in(household_id)
    email = _require_unlinked_approved_with_email(household)
    account = account_queries.account_for_email(email)
    if account is None:
        raise ValidationError(NO_ACCOUNT, code="no_account")
    reason = account_link_queries.link_refusal(account)
    if reason is not None:
        raise ValidationError(REFUSALS[reason], code=reason)
    _save_holder(household, account.id, staff, "counter")
    return household


@transaction.atomic
def resend_invitation(household_id: UUID, staff: AbstractBaseUser) -> Household:
    """Send a new set-password link when the email failed or the link expired.

    Earlier links for the file stop working. The email is queued after commit.
    Raises Household.DoesNotExist for an unknown, online or anonymized file.
    """
    require_walk_in_staff(staff)
    household = _locked_walk_in(household_id)
    email = _require_unlinked_approved_with_email(household)
    holder = household.members.get(relation=Member.Relation.HOLDER)
    try:
        token = account_services.reissue_household_invitation(
            household_id=household.pk,
            email=email,
            first_name=holder.first_name,
            last_name=holder.last_name,
            invited_by=staff,  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        if exc.code != "email_already_registered":
            raise
        raise ValidationError(ACCOUNT_EXISTS, code="account_exists") from exc
    notification_services.queue_set_password_email(
        email=email, token=token, language=household.preferred_language
    )
    audit_services.record(staff, "invite", "household", household.pk, {})
    transaction.on_commit(
        lambda: logger.info(
            "walk_in_invitation_resent",
            extra={"event": "walk_in_invitation_resent", "household_id": household_id},
        )
    )
    return household
