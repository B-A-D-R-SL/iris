# Reporting module

**Owner pair:** Staff & insight
**Status:** Not started

## Responsibility

Staff dashboards and exports built from listings, reservations and households.

## Planned work

- US-70 (#562): dashboard for any date range
- US-71 (#563): export reports to CSV
- US-72 (#564): estimated value redistributed
- US-83 (#577): unmet needs by category

A module adds its files (`models.py`, `services.py`, `queries.py`,
`domain/`, `api/`, `tasks.py`, `tests/`) when the story that needs them
starts. See [the reference module](../../../docs/guides/reference-module.md)
for what each file holds.

## Public functions

None yet.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

None yet. Document emitted event names here when the module's
workflows are built.
