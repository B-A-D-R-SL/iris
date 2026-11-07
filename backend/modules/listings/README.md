# Listings module

**Owner pair:** Goods
**Status:** Posting (US-33) and safety checks (US-34) implemented

## Responsibility

Own the listings feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

- `services.post_listing(store, user, data)`: publish a listing for the user's
  assigned active store after the posting checks (US-33) and the safety checks
  (US-34).
- `queries.categories_for_posting(at=...)`: the active categories a store may
  post in, with prohibited codes left out (US-34).
- `queries.pickup_listings(store_id)`: the store's listings as plain values
  (title, unit, pickup window) for pickup lookup and confirmation (US-44).

## Endpoints

- `POST /api/store/listings/`: post a listing (store staff and managers).
- `GET /api/store/listings/categories/`: categories for the posting form
  (store staff and managers).

## Business rules

- `domain/posting.py`: field limits from rule type `listing_posting` (US-33).
- `domain/safety.py`: safety rules from rule type `listing_safety` (US-34): the
  safe-and-allowed tick, the food best-before date, and prohibited categories.
  See `docs/guides/listing-posting.md`, section 10.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
