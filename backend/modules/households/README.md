<!-- AI contribution: 50% or more AI-generated -->
# Households module — walk-in drafts and US-25 duplicate checking

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
- `services.change_suspension(household_id, reason, actor, reactivate=...) -> Household`:
  administrators suspend approved files or reactivate unexpired suspended files
- `services.submit_walk_in(household_id, staff_user) -> Household`
- `services.locked_duplicate_check(household_id, staff_user)`: context for a
  checked draft and an evaluated duplicate flag; save inside the context.
- `queries.walk_ins_for_staff(staff_user) -> QuerySet[Household]`
- `queries.walk_in_for_staff(household_id, staff_user) -> Household | None`
- `queries.pickup_names(household_id)`: holder and alternate as first name and
  last initial for store pickups, or None once anonymized (US-44)
- `queries.any_visible_for_pickup(household_ids)`: whether any of the IDs is
  still on file for pickup (not anonymized); used when a code matches another
  store (US-44, BR-RES-003)
- `queries.household_for_staff(household_id, staff_user) -> Household | None`
- `queries.find_possible_duplicates(household) -> QuerySet[Household]`
- `queries.approved_household_id(user_id, at=...) -> UUID | None`: the
  household the user holds, if it is `approved` and not expired at `at`
  (expiry is checked even before the nightly job runs). Browsing (US-36) uses
  it and reserving (US-41) can too; only the ID leaves the module.
- `queries.search(q) -> QuerySet[Household]`: partial, accent-insensitive staff search;
  reads only and excludes anonymized files. Blank input returns no files.
- `queries.search_for_staff(q, actor) -> QuerySet[Household]`: the API entry point;
  validates shared staff permission before pagination.
- `domain/address.py`: `normalize_address`, `normalize_postal_code`
- `domain/person.py`: `normalize_person`, age/name validation, `is_adult`
- `domain/names.py`: `short_name`, `short_full_name` ("Fatou D.")

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
- `GET /api/staff/households/?q=...&page=1&page_size=20`: search household/member
  names, household email/phone, member number and address. Pages are capped at
  100 results. Names describe the holder even when another member matched.
- `GET /api/staff/households/{uuid}/`: read draft and who created it
- `PATCH /api/staff/households/{uuid}/`: patch draft steps, including members
- `POST /api/staff/households/{uuid}/submit/`: submit saved registration data,
  returning `{id, status, status_reason, submitted_at}`; request body is `{}`.
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
Intake workers and admins share non-anonymized walk-in files, including another
worker's and unassigned files. `created_by` records provenance, not ownership.
An anonymized, online or unknown file returns 404 through the walk-in endpoints;
signed-out or deactivated sessions return 401.

## Duplicate checking (US-25, #479 and #478)

Submission needs a complete address, one holder, an identity check, and consent.
The household limit comes from `household_size.max_people`; the seed default is
15 people, including the holder. Income notices and approval belong to US-18.

A clean file becomes `submitted`. A matching address (including unit) or person
(first name, last name and birth date) sends it to `review_required` with reason
`POSSIBLE_DUPLICATE`. Both files stay saved. Submitting the same file again
returns an error and leaves its status unchanged.

The search uses the existing `address_key` and `person_key` indexes. It skips
empty keys, the file itself, and files whose personal data was removed.

Duplicate candidates are `submitted`, `review_required`,
`awaiting_visit`, `approved`, `renewal_needed`, and `suspended`. Draft and rejected
files do not count. Files whose `expires_at` is in the past are excluded,
including suspended files. A missing or future expiry does not exclude a file.

`locked_duplicate_check()` locks the draft, address and people before evaluating
the match. Save the result inside its `with` block. PostgreSQL holds these locks
until the outer transaction commits or rolls back. The query alone is a preview.
Future approval code must use the same lock-and-check operation.
`HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS` sets a positive advisory-lock wait limit
(default 5000 milliseconds). Successful acquisition restores the caller's
previous timeout. A timeout rolls back the submission and returns 503 with code
`household_unavailable` and a generic retry message. Other database errors are
not converted to this response.

Draft, submission and serializer checks read `household_size.max_people` through
`limits.py`. The seed default is 15 people total, including the holder.
This is the approved rule `BR-HH-001`.
Missing or invalid configuration is refused, not replaced with a runtime default.
Create, edit and submit return the same generic 503 response without exposing
configuration details. A privacy-safe event identifies the cause in server logs.
For existing databases, run `python manage.py seed_rules` after deployment.
It adds missing rule types without replacing existing versions. No data migration
is needed for this setting; normal schema migrations still apply.

Each submission records a `submitted` household event with its actor, actor role
and time, in the same transaction. Operational logs use `household_submitted` or
`household_duplicate_review` only after commit, with no personal data or IDs.

Migration `0004_normalize_duplicate_keys` updates old search keys and clears keys
for missing or removed personal data. Names and addresses stay unchanged.
Rollback keeps the updated keys because older schemas also accept them.
The migration has only been run on test databases.

Tests cover matches, permissions, French/English errors, the API and database,
and two submissions at once. They check that the second submission waits, then
sees the first file only if its transaction commits.

## Search pagination

Numeric search pages fetch the exact total and results in one query using a
PostgreSQL window count. This avoids executing the same match twice, and keeps
the count and results in one database snapshot. The response envelope, ordering,
20-result default and 100-result cap are unchanged. Invalid/overflowing page
numbers return 404; DRF's optional `page=last` shortcut remains supported.

## Example draft request

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

`HouseholdDraftEvent` stores create, update and submission actions with the actor,
role and time. It has no personal-data payload. Events are saved in the same
transaction as the household change. The central audit service currently accepts
view and decision actions, so registration actions remain in the household history.
Approval records a central decision event.

The walk-in screens (T-03.17.4) are in `frontend/src/areas/staff/pages/WalkIn/`.
Income notices are recorded through the endpoint above (T-03.18.2).

## Walk-in approval (#469)

`approve_walk_in` accepts submitted or review-required walk-ins from an active
intake worker or admin; a draft is refused with "Submit the file before approving
it." (BR-DUP-002: the US-25 submission runs the duplicate check first). It reloads and locks the saved file; it does not
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

The French or English set-password email uses US-57's `walk_in_set_password`
template through `notifications.services.queue_set_password_email`, which calls
the shared queued `send` service. The link is `PUBLIC_APP_ORIGIN` plus
`/invitation/:token`. The job is queued only after commit, so no email is sent on
rollback, rejection or review. Configuration or delivery failure is recorded in
`EmailLog` without the token and cannot undo approval; retries follow the
`notifications` RuleSet. A staff resend workflow remains unimplemented.

## Staff search (US-63, #553 and #554)

Intake workers and admins see all non-anonymized files, including another
worker's and unassigned files. Anonymized records are excluded before counts,
pagination and audits; resume actions use the same staff edit rule as drafts.

Migration `0004_staff_search_indexes` enables `pg_trgm` and `unaccent`, adds
stored PostgreSQL generated keys and GIN trigram indexes, and backfills existing
rows. PostgreSQL maintains the keys for normal saves, updates and bulk writes.
Existing extensions retain their installed schemas; new extensions use `public`.
The wrapper pins the installed unaccent function and dictionary. Dictionary
changes require a migration that recomputes the stored keys. Reversing removes
the derived keys/indexes and module function, preserves source records, and
leaves shared extensions installed.

Migration `0006_merge_duplicate_and_search` joins the search and duplicate-check
migration branches without changing data.

Search never searches the DOB-containing `person_key`. Its explicit response
contains only holder names, contact/address fields, member number, channel and
status. The collection's existing POST registration operation is preserved.
Responses use `Cache-Control: private, no-store`; search text is excluded from
logs. Each disclosed household ID is recorded through
`audit.services.record_household_views` in one atomic batch, with empty metadata.
Audit failure prevents the response from exposing results. HEAD creates no events.

The screen replaces the staff placeholder at `/staff/households`. It supports
French/English, a 300 ms debounce, cancelled superseded requests, paginated
results and links to resume existing walk-in drafts. US-64 owns the later full
household page; this change does not create that page or approval workflows.

See [search verification](../../../docs/guides/household-search.md) for database
isolation, repeatable benchmarks and the remaining staging/device checks.

## Suspension (US-32)

The suspend and reactivate endpoints require an administrator and a reason. They
preserve `expires_at`; an expired suspended file cannot be reactivated. Suspension
cancels every reserved reservation without a late-cancellation strike and returns
the units to its listing in the same transaction. Both actions are audited with
the reason. A localized holder email is queued after commit; counter-only files
without email still change status.

The suspension/reactivation email includes the same normalized, privacy-validated
reason recorded by this workflow, preserving US-32's existing behavior. Household
`_status_reason` remains authoritative: it normalizes whitespace, applies the
active `household_suspension.reason_max_length` (default 500; schema maximum
2,000), and refuses personal, identity, document or financial details before
audit or queueing. Model validation still limits a suspended file's stored
`status_reason` to 500 characters; the larger RuleSet ceiling does not change
that column. Reactivation clears the stored status reason and can carry a longer
validated email/audit reason when permitted by the active rule. The notification
template captures the accepted text up to
the schema ceiling rather than reapplying a later RuleSet version. Plain text
preserves the captured reason and HTML escapes it once. EmailLog and stdout do
not retain it. This decision is recorded in the US-57 PR #697 review follow-up.
Known-template email validation/configuration failures become failed delivery
records and do not undo a valid suspension/reactivation. The household's own
reason, privacy and authorization checks still refuse invalid business actions.
