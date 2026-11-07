# Reservations module

**Owner pair:** Goods
**Status:** Reservation table added for the SET-18 seed. Pickup lookup and confirmation implemented (US-44).

## Responsibility

Own the reservations feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

`Reservation` stores the columns from the database design so `manage.py seed` can insert fictional reservations.

- `queries.lookup_pickup(staff, code, now=...)`: the reservation a typed or
  scanned code names at the staff member's store, as a `Pickup` (first name and
  last initial only). Raises `domain.pickup.PickupRefused` with a code such as
  `wrong_store` or `already_picked_up` (US-44).
- `services.confirm_pickup(reservation_id, staff, now=None)`: mark it picked up
  with who and when, once, under a row lock (US-44).
- `permissions.pickup_store_id(user)`: the store whose pickups the user may
  confirm; raises `PermissionDenied` for everyone else.

Pickup endpoints (store staff and managers): `POST /api/store/pickups/lookup/`
and `POST /api/store/pickups/{id}/confirm/`, in `api/store_urls.py`. Rules
BR-RES-001 to BR-RES-005 are in `docs/02-requirements/business-rules.md`.
Confirming does not change listing stock.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Future implementation

TODO: Module owner defines business operations, model ownership,
API endpoints, tests, and applicable audit events.

Do not treat this scaffold as implemented business functionality.

## Audit events

No audit events yet: `AuditEvent` has no pickup action, so the reservation row
keeps who confirmed and when (`confirmed_by`, `picked_up_at`). A confirmed
pickup logs `pickup_confirmed` after the commit, with no names or codes.
