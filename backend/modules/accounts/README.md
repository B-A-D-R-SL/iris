<!-- AI contribution: 50% or more AI-generated -->
# Accounts module

**Owner pair:** Platform & setup
**Status:** US-01 browser sign-in, sign-out, and current-user endpoint implemented; other account workflows pending

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
the `User` model, serves the authenticated `GET /api/me/` endpoint, and enforces
browser sign-in limits through its allauth adapter. Public signup remains closed
until US-02 adds email verification.
The `AuthCache` stores failed-attempt counters in PostgreSQL so workers share
the five-attempt, 15-minute lockout. The Django admin uses
`RateLimitedAdminAuthenticationForm` and shares that limit with browser sign-in.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Future implementation

TODO: Define further business operations, API endpoints, and applicable audit events.

Other accounts workflows remain scaffolds.

## Audit events

Authentication logs `sign_in_failed` and `sign_in_rate_limited` without account
identifiers. Document later business audit events when their workflows are added.
