# Reservations module

**Owner pair:** Goods
**Status:** Reservation table added for the SET-18 seed. The browse endpoint (US-36) is here. Reserving and pickup workflows are still open.

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

No public write functions yet. `Reservation` stores the columns from the database design so `manage.py seed` can insert fictional reservations. Pickup services are still to be added.

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

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
