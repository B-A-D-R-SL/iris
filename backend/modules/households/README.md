<!-- AI contribution: 50% or more AI-generated -->
# Households module — implementation for T-03.17.2 and T-03.17.3

**Owner pair:** Registration

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
  "identity_checked_in_person": true,
  "consent_data_processing": true
}
```

The staff user sets identity verification; the backend stores only a boolean,
verifier and timestamp. The `holder` is automatically member one. A draft can
be created before address collection and later patched step by step.

`consent_data_processing: true` stores when consent was given
(`consent_data_processing_at`) and which text was read (`consent_text_version`,
currently `2026-11-v1`); sending it again keeps the first time, and `false`
clears both. US-20 may move consents to `privacy.ConsentRecord` later.

## Migrations and the SET-18 seed

SET-18 (#617) created the first `households` table (`0001_initial`) so
`manage.py seed` could store fictional files, and the reservations migration
depends on it. As decided on #461, that migration is kept and US-17 builds on
it: `0002_walk_in_registration` aligns the table with the walk-in model, adds
`Member` and `HouseholdDraftEvent`, and converts existing seeded rows (channel
`walk-in` to `walk_in`, empty `unit` instead of NULL); `0003_household_consent`
adds the consent fields. `HouseholdStatus` and `HouseholdChannel` remain as
aliases of `Household.Status` and `Household.Channel` for the seed.
Seeded files have no holder `Member` yet; saving one with complete holder
details creates it, and incomplete details return a `holder` field error.

## Audit integration / US-62 dependency

`HouseholdDraftEvent` currently captures a **minimal internal audit trail** of
create/update actions, actor ID, role at the moment of action, and timestamp,
without personal-data payloads. It is an interim solution because `audit` is a
SET-14 scaffold on `main` (as observed 2026-10-31). **Coordinate with the US-62
owner before merging**: when the central `audit.services.record()` supports
household creation/edit events, replace the local event implementation with it,
and decide whether to migrate existing local event history. Do not send action
names unsupported by the current US-62 branch, which only handles view/decision.

The walk-in screens (T-03.17.4) are in `frontend/src/areas/staff/pages/WalkIn/`.
Approval, income notices, status transitions and the set-password email belong
to US-18 and US-57; none of them are implemented here.
