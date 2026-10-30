<!-- AI contribution: 50% or more AI-generated -->
# Accounts module

**Owner pair:** Platform & setup
**Status:** US-01 sign-in and current-user endpoint implemented; other account workflows pending

## Responsibility

Own the accounts feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

No cross-module service or query functions are implemented yet. The module owns
the `User` model and serves the authenticated `GET /api/me/` endpoint.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Future implementation

TODO: Define further business operations, API endpoints, and applicable audit events.

Other accounts workflows remain scaffolds.

## Audit events

No audit events are implemented as part of SET-14.
Document emitted event names here when the module's
business workflows are implemented.
