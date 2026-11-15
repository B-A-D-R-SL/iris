# Rules module

**Owner pair:** Fairness & partners
**Status:** Rule versions, schemas and seed command built; no API yet

## Responsibility

Versioned business rule values (limits, durations, thresholds) that other modules read.

## Layers

- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tests/`: Domain, service, and API tests

## Public functions

- `services.publish(rule_type, values, user, ...)`
- `queries.active(rule_type, at=None)`

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Planned work

- US-69 (#560): rule settings screens. Adds the staff `api/` for reading and
  publishing rule values.

The module adds `api/` and `tasks.py` when a story needs them.

## Audit events

Publishing records a `rule_published` audit event with the rule type, version,
actor, and rule-version identifier in the same transaction. After commit, it logs
the static `rule_published` event without account identifiers or rule values.
