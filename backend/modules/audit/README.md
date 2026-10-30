<!-- AI contribution: 50% or more AI-generated -->
# Audit module

Owner pair: Staff & insight.

Records who acted, their role at that time, the action, target, and timestamp.

Public API: `modules.audit.services.record(actor, action, target_type, target_id, metadata)`.
Returns an `AuditEvent`; invalid inputs raise Django `ValidationError`.
Database errors propagate to the caller.
The actor must be a saved user. Target types use lowercase identifiers such as
`household`; target IDs accept strings, integers, or UUIDs (stored as strings).

Supported actions: `view` and `decision`.
Metadata accepts `{}` or `{"outcome": "approved" | "rejected" | "review_required"}`.
No names, contact details, SINs, income, immigration status, document contents,
free text, nested values, or other metadata keys are accepted.
Callers must supply record identifiers rather than personal data as targets.

```python
from modules.audit.services import record

record(request.user, "view", "household", household.pk, {})
```

Recording joins the caller's transaction and rolls back with it.
PostgreSQL rejects UPDATE and DELETE through both ORM and SQL; actors referenced
by events cannot be deleted. Writes from other modules must use `record()`.

Apply migrations in an existing Docker environment:

```bash
docker compose exec backend python manage.py migrate --noinput
```

Requires the US-01 accounts migrations. Audit setup needs no manual SQL.
The search API and screen belong to #550.
