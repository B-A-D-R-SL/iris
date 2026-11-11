# Notifications module

**Owner pair:** Platform & setup
**Status:** Implemented for household status notices

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

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

The Compose `worker` service runs queued jobs separately from HTTP requests.
