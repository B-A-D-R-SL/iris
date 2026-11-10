<!-- AI contribution: 50% or more AI-generated -->
# Audit module

Owner pair: Staff & insight.

Records who acted, their role at that time, the action, target, and timestamp.

Public API: `modules.audit.services.record(actor, action, target_type, target_id, metadata)`.
Returns an `AuditEvent`; invalid inputs raise Django `ValidationError`.
Database errors propagate to the caller.

Staff household search uses
`record_household_views(actor, household_ids: Iterable[UUID])` to append one
`view` event per returned file with a single INSERT. It validates the saved actor,
role and UUIDs; action/target type/empty metadata are fixed. Foreign keys remain
database-enforced. Batch inserts join the caller's transaction and roll back with
it. This avoids repeated actor lookups and never accepts search text as metadata.
The actor must be a saved user. Target types use lowercase identifiers such as
`household`; target IDs accept strings, integers, or UUIDs (stored as strings).
Valid household UUID strings are normalized to lowercase with hyphens so they
match household search. Other target identifiers are preserved.

Supported actions: `view`, `decision`, and `rule_published`.
Metadata accepts `{}` or `{"outcome": "approved" | "rejected" | "review_required"}`.
For `rule_published` on `rule_set_version`, metadata instead contains the supported
`rule_type` and positive integer `version`. No names, contact details, SINs, income, immigration status, document contents,
free text, nested values, or other metadata keys are accepted.
Callers must supply record identifiers rather than personal data as targets.

```python
from modules.audit.services import record

record(request.user, "view", "household", household.pk, {})
```

Recording joins the caller's transaction and rolls back with it.
PostgreSQL rejects UPDATE and DELETE through both ORM and SQL; actors referenced
by events cannot be deleted. Writes from other modules use these public services.

Apply migrations in an existing Docker environment:

```bash
docker compose exec backend python manage.py migrate --noinput
```

Requires the US-01 accounts migrations. Audit setup needs no manual SQL.
## Admin search

`GET /api/staff/audit/` is restricted to active administrators.
Administrators can search all audit events across households and staff; events
are not restricted to those created by the requesting administrator. Optional
`household` and `actor` parameters are UUIDs; `from` and `to` are inclusive
ISO dates in the America/Montreal timezone. Household filtering matches only
events with target type `household`. Results are newest first, with ID used as
a tie-breaker. Pagination uses `page` and `page_size` (default 20, maximum 100)
and returns `count`, `next`, `previous` and `results`. Dates in event responses
are UTC; the screen displays Montreal time. Invalid identifiers, dates and
reversed date ranges return HTTP 400. Search accepts IDs; name-based lookup is
not part of this endpoint.
