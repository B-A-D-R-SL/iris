<!-- AI contribution: 50% or more AI-generated -->
# Households module

**Owner pair:** Registration

The module owns `Household` and `Member` records. The holder is a `Member` with
`relation=holder`; an online `accounts.User` is **not** created for a walk-in draft.
`email` on `Household` is optional so counter-only beneficiaries do not need an
account. The record also preserves staff verification and creation timestamps.

## Public interfaces

- `services.create_walk_in(data, staff_user) -> Household`
- `services.update_draft(household_id, data, staff_user) -> Household`
- `services.approve_walk_in(household, staff) -> Household`: checks current
  evidence, records the outcome and prepares a beneficiary invitation when needed
- `services.record_walk_in_notice(household_id, data, staff_user) -> IncomeNotice`:
  checks the household is a draft walk-in and the member is one of its adults
  (BR-DOC-007), records the draft change, then calls
  `documents.services.record_staff_notice` (T-03.18.2)
- `queries.walk_in_for_staff(household_id) -> Household | None`
- `queries.eligibility_inputs(household_id) -> EligibilityInputs`: verified
  adult incomes and the full member count for the eligibility service
- `domain/address.py`: `normalize_address`, `normalize_postal_code`
- `domain/person.py`: `normalize_person`, age/name validation, `is_adult`

Services are transactional, enforce active staff roles, and call `full_clean()`
before persistence. Editing is restricted to drafts; member replacement cannot
remove a record referenced by another module. Members sent back
unchanged (same names, date of birth and relation) keep their record, so a
member with a notice can stay while others are added; removing or changing that
member is refused. The holder keeps one record and is edited in place, so their
notice stays linked when staff correct their name or date of birth; the notice
keeps the name it was recorded with. No form can set the status,
creator, verifier or internal keys directly.

## API routes

- `POST /api/staff/households/`: create a draft and holder member
- `GET /api/staff/households/{uuid}/`: read draft and who created it
- `PATCH /api/staff/households/{uuid}/`: patch draft steps, including members
- `GET /api/staff/households/{uuid}/notices/`: the current notice of each
  member (`queries.walk_in_notices`), without storage references, so the
  notices screen shows what was saved after a reload; unknown IDs 404.
- `POST /api/staff/households/{uuid}/notices/` (multipart): an adult's notice of
  assessment (`file`, `tax_year`, `total_income_cents`, `name_on_notice`,
  `postal_code_on_notice`, `notice_date`, `seen_in_person`) or
  `did_not_file` with `did_not_file_reason`; returns the notice without its
  storage reference. A second entry for the same adult replaces the current
  one. See `modules/documents/README.md` for the rules and file links.
- `POST /api/staff/households/{uuid}/approve/` (no body): calls
  `approve_walk_in` and returns `{ id, status, status_reason, approved_at,
  expires_at }` with 200, whether the file is approved, rejected or sent to
  review. An incomplete file, or one that cannot be decided in its status,
  answers 400 with the message in `fields.non_field_errors`; unknown IDs 404.

Errors use `{ "code", "message", "fields" }`; nested form field paths are
reported as dotted keys such as `address.postal_code`.
Messages follow the request language (French by default). `domain/` raises
specific error types, and `messages.py` gives each one its translated text.

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

`HouseholdDraftEvent` records create/update actions, actor ID, role and timestamp,
without personal-data payloads. The central audit service currently supports
view/decision only, so draft events remain local. Approval uses a central
decision event. Replacing the draft trail and migrating its history still needs
coordination with the US-62 owner.

The walk-in screens (T-03.17.4) are in `frontend/src/areas/staff/pages/WalkIn/`.
Income notices are recorded through the endpoint above (T-03.18.2).

## Walk-in approval (#469)

`approve_walk_in` accepts draft, submitted or review-required walk-ins from an
active intake worker or admin. It reloads and locks the saved file; it does not
trust unsaved changes on the argument. Anonymized files are hidden. The holder,
address, phone, consent and every adult's notice or non-filing reason must be
complete. Missing information raises validation errors without changing the file.

Only current notices count. Adult ages use Montreal's date at approval. Each
notice name is checked against the member's current first and last names, including
holder corrections made after recording the notice. Case and accents are ignored;
extra middle names are allowed. Postal codes must match the household address.

Review reasons are `NAME_MISMATCH`, `ADDRESS_MISMATCH`, `NOTICE_NOT_SEEN`,
`TAX_YEAR_NOT_ACCEPTED`, `DID_NOT_FILE` and `IDENTITY_NOT_VERIFIED`. Existing
review flags are preserved and take priority over rejection. Non-filing,
unaccepted or unverified evidence goes to review without an income decision;
it is never treated as zero. Accepted tax years come from
`auto_approval.accepted_tax_years`. The income-ratio rule for online automatic
approval does not apply to this staff workflow.

With complete verified income, `eligibility.services.decide_for_household`
records the calculation. Income above LICO gives `rejected` with
`INCOME_ABOVE_LICO`; an eligible file without review flags becomes `approved`.
Validity uses calendar months in Montreal from `file_validity.approved_months`
(seed default 12), including month-end clamping. Other outcomes have no approval
or expiry date. A final file cannot be approved again. The approval API is
`POST /api/staff/households/{uuid}/approve/`; the review queue UI remains a
separate task, and this service stores `review_required`.

Outcome, eligibility, audit and invitation writes share one transaction.
`audit.services.record` receives only the outcome, never notice or income data.
Approved files with email call the US-04 invitation service from `main`; existing
accounts are refused under its new-account-only policy and roll back approval.
Acceptance creates the account but does not yet link it to the household.

The French or English set-password email is sent through the mailer adapter only
after commit, using `FRONTEND_URL` and `/invitation/:token`. No email is sent on
rollback, rejection or review. Delivery failure is logged without recipient,
token or provider details and cannot undo approval. Durable retries and a resend
workflow remain for the notifications owner.
