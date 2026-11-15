# Privacy module

**Owner pair:** Staff & insight
**Status:** Started: one shared privacy check

## Responsibility

Privacy checks shared by other modules, and the privacy rights households can use (Law 25).

## Planned work

- US-73 (#566): plain-language privacy page
- US-74 (#567): scheduled deletion
- US-75 (#568): download my data
- US-76 (#569): withdraw optional consents
- US-77 (#570): ask a person to review an automated decision
- US-78 (#571): ask for a correction
- US-79 (#572): close my account and delete my data
- US-80 (#573): confidentiality incident register

A module adds its files (`models.py`, `services.py`, `queries.py`,
`domain/`, `api/`, `tasks.py`, `tests/`) when the story that needs them
starts. See [the reference module](../../../docs/guides/reference-module.md)
for what each file holds.

## Public functions

- `services.household_reason_contains_sensitive_data(reason)`: finds
  personal, identity, document or financial details in a free-text reason.
  Used by audit and households.

## Architectural rules

Other modules must communicate through public services or queries.
Do not import another module's models or internal domain code.

## Audit events

None yet. Document emitted event names here when the module's
workflows are built.
