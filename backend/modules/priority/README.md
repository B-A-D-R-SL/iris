# Priority module

**Owner pair:** Fairness & partners
**Status:** Not started

## Responsibility

Score households, place them in tiers and give earlier access to the tiers that need it most.

## Planned work

- US-50 (#530): score and tier every household
- US-51 (#531): early access by tier
- US-52 (#532): never show scores to households
- US-53 (#533): explain a household's tier
- US-54 (#534): strikes for no-shows
- US-55 (#535): forgive a strike or override a tier
- US-56 (#536): change priority rules in settings

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
