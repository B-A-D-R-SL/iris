# Rules module

**Owner pair:** Fairness & partners
**Status:** SET-14 architecture skeleton

## Responsibility

Own the rules feature boundary within the Iris modular monolith.

## Layers

- `api/`: HTTP validation, permissions, and routing
- `domain/`: Pure Python business rules; no Django dependencies
- `services.py`: Public write operations and transactions
- `queries.py`: Public read-only operations
- `models.py`: Module-owned Django models
- `tasks.py`: Background jobs when necessary
- `tests/`: Domain, service, and API tests

## Public functions

- `services.publish(rule_type, values, user, ...)`
- `queries.active(rule_type, at=None)`

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Future implementation

TODO: Module owner defines business operations, model ownership,
API endpoints, tests, and applicable audit events.

Do not treat this scaffold as implemented business functionality.

## Audit events

Publishing records a `rule_published` audit event with the rule type, version,
actor, and rule-version identifier in the same transaction. After commit, it logs
the static `rule_published` event without account identifiers or rule values.
