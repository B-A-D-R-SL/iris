# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for income notices."""

from collections.abc import Iterable
from uuid import UUID

from modules.documents.models import IncomeNotice


def current_notices(member_ids: Iterable[UUID]) -> dict[UUID, IncomeNotice]:
    """The current (not superseded) notice of each member; members without one are absent."""
    notices = IncomeNotice.objects.filter(
        member_id__in=list(member_ids), superseded_at__isnull=True
    )
    return {notice.member_id: notice for notice in notices}
