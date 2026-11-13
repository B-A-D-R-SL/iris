<!-- AI contribution: 50% or more AI-generated -->
# Notifications module

**Owner pair:** Platform & setup
**Status:** Implemented for household status notices and the US-18 set-password email

## Responsibility

Own the notifications feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

- `queue_household_status_email`: after the caller commits, enqueue a localized
  suspend or reactivate notice. Files without email are skipped.
- `send_household_status_email`: Procrastinate worker task that delivers through
  the mail adapter and records a privacy-safe failure event.
- `queue_set_password_email(email=..., token=..., language=..., mailer=None)`:
prepares a French or English setup email and registers delivery after the caller's
transaction commits. It uses `FRONTEND_URL` to reach `/invitation/:token`.
The SMTP adapter handles delivery; tests use a fake or Django's local-memory mailer.
The message contains no income amounts or notice details.
Configure `FRONTEND_URL` with the public HTTPS website address in production.
Only loopback URLs may use HTTP. Console and file email backends are refused
because they would save the secret link in logs or files; use SMTP/Mailpit locally.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

The Compose `worker` service runs queued jobs separately from HTTP requests.

## Future implementation

Delivery currently runs in an after-commit callback, not a durable background
queue. A failed send emits only `set_password_email_failed`; it does not expose
the address, token or provider error and does not undo approval. Durable retries
and a staff resend workflow remain unimplemented.

## Audit events

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
