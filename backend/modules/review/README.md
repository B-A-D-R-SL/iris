# Review module

**Owner pair:** Staff & insight
**Status:** Not started

## Responsibility

Staff review of household files that automatic approval did not settle.

## Planned work

- US-64 (#555): household page
- US-65 (#556): staff notes
- US-66 (#557): review queue
- US-67 (#558): notice beside the read values
- US-68 (#559): approve, reject or invite in person

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
