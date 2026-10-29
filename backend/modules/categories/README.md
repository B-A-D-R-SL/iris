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
- `services.deactivate_category(category_id)`
- `queries.list_active_categories()`
- `queries.get_active_category(code)`

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
