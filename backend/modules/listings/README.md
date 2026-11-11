# Listings module

**Owner pair:** Goods
**Status:** Posting (US-33), safety checks (US-34) and browsing queries (US-36) implemented

Photo uploads use the configured private Azure/Azurite adapter (FIX-02), with
Pillow processing, compensating cleanup and five-minute read links on authorized
browse cards. See [configuration and verification](../../../docs/guides/listing-photo-storage.md).

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
- `queries.visible_listings(household_id, now)`: the listings a household can
  see (BR-LIST-004). This is the only place visibility is decided; tier delays
  (US-51) belong here. With no approved household (`None`) nothing is visible.
- `queries.browse_listings(household_id, now, category=, store=,
  pickup_today=)`: visible listings as card dictionaries, filtered and sorted
  by pickup start (US-36). The store's name and address come in the same query.

## Endpoints

- `POST /api/store/listings/`: post a listing (store staff and managers).
- `GET /api/store/listings/categories/`: categories for the posting form
  (store staff and managers).
- `GET /api/listings/` (US-36) is served by the reservations module, because
  only reservations may read both households (approval) and listings. It calls
  `browse_listings`.

## Business rules

- `domain/posting.py`: field limits from rule type `listing_posting` (US-33).
- `domain/safety.py`: safety rules from rule type `listing_safety` (US-34): the
  safe-and-allowed tick, the food best-before date, and prohibited categories.
  See `docs/guides/listing-posting.md`, section 10.
- `domain/browsing.py`: where "today" ends for the pickup-today filter
  (BR-LIST-005, US-36).

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
