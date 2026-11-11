# Reservations module

**Owner pair:** Goods
**Status:** Reservation table added for the SET-18 seed. The browse endpoint (US-36) and pickup lookup/confirmation (US-44) are implemented. Reserving is still open.

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
- `services.cancel_open_for_household(household_id)`: cancel reserved claims for
  a household without a late-cancellation strike (must run in a transaction).
- `permissions.pickup_store_id(user)`: the store whose pickups the user may
  confirm; raises `PermissionDenied` for everyone else.

Pickup endpoints (store staff and managers): `POST /api/store/pickups/lookup/`
and `POST /api/store/pickups/{id}/confirm/`, in `api/store_urls.py`. Rules
BR-RES-001 to BR-RES-005 are in `docs/02-requirements/business-rules.md`.
Confirming does not change listing stock.

## Endpoints

- `GET /api/listings/?category=&store=&today=` (US-36): the listings the
  signed-in household can see, always 20 a page (`?page=`; `page_size` is
  ignored, as #506 asks), sorted by pickup start. Signed out gets 401. Any role other than an active
  `beneficiary` gets 403 (`permission_denied`), and so does a household that is
  not approved or has expired (`household_not_approved`). Invalid filters get
  400.

The view is here, not in `listings/api/`, because reservations is the module
allowed to read both `households.queries` (is the household approved?) and
`listings.queries` (what can it see?), as `[tool.importlinter]` in
`pyproject.toml` and the module diagram in `docs/04-architecture` show. The
view only checks permission, validates the filters, calls those two queries and
pages the result. Visibility itself is decided in
`listings.queries.visible_listings`.

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
