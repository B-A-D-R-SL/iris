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
Human actors must be saved users. Automatic eligibility decisions use a null
actor and `actor_role="system"`; no artificial user account is created. A null
actor is refused for other audit events. Target types use lowercase identifiers such as
`household`; target IDs accept strings, integers, or UUIDs (stored as strings).
Valid household UUID strings are normalized to lowercase with hyphens so they
match household search. Other target identifiers are preserved.

The supported actions are `view`, `create`, `update`, `submit`, `decision`,
`rule_published`, `suspend`, and `reactivate`.
Household views, creation, edits and submission accept only empty metadata.
Existing decisions accept `{}` or
`{"outcome": "approved" | "rejected" | "review_required"}`.
Eligibility decisions target the household (so household audit search includes
them) and require exactly `{"decision_id": "<canonical UUID>", "outcome":
"eligible" | "ineligible", "rule_version": <positive integer>}`. Names, contact
details, dates of birth, income amounts, thresholds and document text are refused
as additional metadata. This shape is also required for system decisions.
For `rule_published` on `rule_set_version`, metadata instead contains the supported
`rule_type` and positive integer `version`. Suspension and reactivation accept a
`reason` validated against the configured length limit and sensitive-data checks.
Each action accepts only its defined metadata keys.
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
Migration `0006_household_events_and_system_actor` adds household actions and
permits null system actors, preserving existing rows and the append-only trigger.
Reversing it restores Django's earlier model state but deliberately leaves the
database actor column nullable. Existing system events survive rollback without
deletion or reassignment, and the foreign key and append-only trigger remain in
place. Reapplying the migration is safe with those preserved rows.
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
