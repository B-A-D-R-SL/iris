# Categories module

**Owner pair:** Goods (reference module built by Platform)
**Status:** Reference module implemented (#377); SET-14 architecture complete

## Responsibility

Own the categories feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

- `services.save_category(category)`
- `services.get_or_create_category(category)`
- `services.deactivate_category(category_id)`
- `queries.list_active_categories()`
- `queries.get_active_category(code)`
- `queries.list_all_categories()` and `queries.get_category(code)` (admin, active or not)
- `services.create_category(values, admin)` and `services.update_category(code, values, admin)`
  (US-35; admin only; the default value follows `listing_posting.estimated_value_max_cents`)

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Implemented functionality

- Category model with stable codes, bilingual names, food classification,
  default values in cents, and active status.
- Public read-only `GET /api/categories/` endpoint.
- Admin endpoints (US-35): `GET`/`POST /api/staff/categories/` and
  `PATCH /api/staff/categories/{code}/`; no delete, French and English errors.
- Validated service operations for saving and deactivating categories.
- Pure Python food best-before-date validation.
- Idempotent category seed command using the reviewed YAML data.
- Automated domain, service, API, seed, and frontend tests.
- Read-only staff Categories page; editing belongs to US-35.

## Audit events

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
