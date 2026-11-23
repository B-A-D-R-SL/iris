# AI contribution: 50% or more AI-generated
"""Link a walk-in household to its Iris account (US-93).

The holder account is `Household.holder`. It is set when the walk-in set-password
invitation is accepted (`link_invited_account`, a receiver of
`accounts.services.invitation_accepted`). Each link is audited and logged with
the household ID only.
"""

import logging
from typing import Any, Literal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from modules.audit import services as audit_services
from modules.households.models import Household

logger = logging.getLogger("iris.households")

ALREADY_LINKED = _("This file is already linked to an account.")
HAS_HOUSEHOLD = _("This account is already linked to another household.")


def _locked_walk_in(household_id: UUID) -> Household:
    """Lock a visible walk-in file for the caller's transaction.

    Raises Household.DoesNotExist for unknown, online or anonymized files.
    """
    return Household.objects.select_for_update().get(
        pk=household_id,
        channel=Household.Channel.WALK_IN,
        anonymized_at__isnull=True,
    )


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


def link_invited_account(
    sender: Any, *, user: Any, household_id: UUID, **kwargs: Any
) -> None:
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
