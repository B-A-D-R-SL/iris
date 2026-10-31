<!-- AI contribution: 50% or more AI-generated -->
# Households module — implementation for T-03.17.2 and T-03.17.3

The module owns `Household` and `Member` records. The holder is a `Member` with
`relation=holder`; an online `accounts.User` is **not** created for a walk-in draft.
`email` on `Household` is optional so counter-only beneficiaries do not need an
account. The record also preserves staff verification and creation timestamps.

## Public interfaces

- `services.create_walk_in(data, staff_user) -> Household`
- `services.update_draft(household_id, data, staff_user) -> Household`
- `queries.walk_in_for_staff(household_id) -> Household | None`
- `domain/address.py`: `normalize_address`, `normalize_postal_code`
- `domain/person.py`: `normalize_person`, age/name validation

Services are transactional, enforce active staff roles, and call `full_clean()`
before persistence. Editing is restricted to drafts; member replacement cannot
remove a record referenced by another module. No form can set the status,
creator, verifier or internal keys directly.

## API routes

- `POST /api/staff/households/`: create a draft and holder member
- `GET /api/staff/households/{uuid}/`: read draft and who created it
- `PATCH /api/staff/households/{uuid}/`: patch draft steps, including members

Errors use `{ "code", "message", "fields" }`; nested form field paths are
reported as dotted keys such as `address.postal_code`.

All require a session for an active `intake_worker` or `admin`. Other signed-in
roles are rejected with HTTP 403. The API contains no ID document information.

### Example request

```json
{
  "holder": {
    "first_name": "Example", "last_name": "Person",
    "date_of_birth": "1998-05-15",
    "email": null,
    "phone": "(514) 555-0123",
    "preferred_language": "fr"
  },
  "address": {
    "street_number": "123", "street_name": "rue Exemple",
    "unit": "4", "city": "Montréal", "postal_code": "H2X 1Y4"
  },
  "members": [
    { "first_name": "Example", "last_name": "Child", "date_of_birth": "2017-01-03", "relation": "child" }
  ],
  "identity_checked_in_person": true
}
```

The staff user sets identity verification; the backend stores only a boolean,
verifier and timestamp. The `holder` is automatically member one. A draft can
be created before address collection and later patched step by step.

## Audit integration / US-62 dependency

`HouseholdDraftEvent` currently captures a **minimal internal audit trail** of
create/update actions, actor ID, role at the moment of action, and timestamp,
without personal-data payloads. It is an interim solution because `audit` is a
SET-14 scaffold on `main` (as observed 2026-10-31). **Coordinate with the US-62
owner before merging**: when the central `audit.services.record()` supports
household creation/edit events, replace the local event implementation with it,
and decide whether to migrate existing local event history. Do not send action
names unsupported by the current US-62 branch, which only handles view/decision.

Approval, income notices, status transitions, set-password email and the walk-in
screen belong to **other US-17 tasks**; none of them are implemented here.
