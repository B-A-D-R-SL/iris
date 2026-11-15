# AI contribution: 50% or more AI-generated
# Read-only audit search. Dates use the configured Montreal timezone

from datetime import date, datetime, time, timedelta
from uuid import UUID

from django.db.models import QuerySet
from django.utils import timezone

from modules.audit.models import AuditEvent


def _start_of(day: date) -> datetime:
    """Midnight starting ``day`` in Montreal; clocks never change at midnight."""
    return timezone.make_aware(datetime.combine(day, time.min))


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
    # Compare created_at itself, not its date, so the indexes can be used.
    if date_from is not None:
        events = events.filter(created_at__gte=_start_of(date_from))
    if date_to is not None:
        events = events.filter(created_at__lt=_start_of(date_to + timedelta(days=1)))
    return events.order_by("-created_at", "-pk")
