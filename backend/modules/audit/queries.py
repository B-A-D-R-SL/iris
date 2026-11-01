#Read-only audit search. Dates use the configured Montreal timezone

from datetime import date
from uuid import UUID

from django.db.models import QuerySet

from modules.audit.models import AuditEvent


def search_events(
    *,
    household: UUID | None = None,
    actor: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[AuditEvent]:
    events = AuditEvent.objects.all()
    if household is not None:
        events = events.filter(target_type="household", target_id=str(household))
    if actor is not None:
        events = events.filter(actor_id=actor)
    if date_from is not None:
        events = events.filter(created_at__date__gte=date_from)
    if date_to is not None:
        events = events.filter(created_at__date__lte=date_to)
    return events.order_by("-created_at", "-pk")
