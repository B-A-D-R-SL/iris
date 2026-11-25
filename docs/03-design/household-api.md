<!-- AI contribution: 50% or more AI-generated -->
# Household and notice API

> **Release 1:** staff-led walk-in registration and notice upload/manual entry.
> Beneficiary online application, notice upload/AI-read-value confirmation,
> renewal and alternate-management endpoints below are **future/non-R1** designs.
> They are not enabled by the implemented staff notice API. See the
> [release boundaries](api-implementation-notes.md#release-scope).

| Method     | Path                                                    | Who                  | Purpose                                           | Status  |
| ---------- | ------------------------------------------------------- | -------------------- | ------------------------------------------------- | ------- |
| GET        | `/api/households/me/`                                   | Beneficiary          | Status, expiry, members (names), alternate        | Planned — future/non-R1 |
| GET/PUT    | `/api/households/me/application/`                       | Beneficiary          | Draft application, steps 1 to 3                   | Planned — future/non-R1 |
| POST       | `/api/households/me/notices/`                           | Beneficiary          | Upload a notice for a member (multipart)          | Planned — future/non-R1 |
| PATCH      | `/api/households/me/notices/{id}/`                      | Beneficiary          | Confirm or correct read values, or `did_not_file` | Planned — future/non-R1 |
| POST       | `/api/households/me/application/submit/`                | Beneficiary          | Submit                                            | Planned — future/non-R1 |
| PATCH      | `/api/households/me/alternate/`                         | Beneficiary          | Alternate for pickups                             | Planned — future/non-R1 |
| POST       | `/api/households/me/renewal/`                           | Beneficiary          | Start a renewal                                   | Planned — future/non-R1 |
| GET        | `/api/staff/households/?q=`                             | Intake worker, admin | Partial, accent-insensitive search; authorized non-anonymized files, pagination, audits and server-derived `can_resume` and `can_open` | Implemented (US-63, US-32) |
| POST/PATCH | `/api/staff/households/`, `/api/staff/households/{id}/` | Intake worker, admin | Walk-in create and edit (drafts only)             | Implemented (US-17) |
| POST | `/api/staff/households/{id}/submit/` | Intake worker, admin | Submit saved walk-in registration; possible duplicates go to review | Implemented (US-25) |
| GET | `/api/staff/households/{id}/notices/` | Intake worker, admin | Current notice of each member of a walk-in (no storage reference), so staff can resume the notices screen; audited | Implemented (US-18) |
| POST | `/api/staff/households/{id}/notices/` | Intake worker, admin | Walk-in notice (scan + typed values) or non-filing reason, multipart, for an adult of a draft; audited | Implemented (T-03.18.2) |
| POST       | `/api/staff/households/{id}/approve/`                   | Intake worker, admin | Approve a walk-in (eligibility runs): 200 `{id, status, status_reason, approved_at, expires_at, invitation_not_sent}` (`invitation_not_sent` is true when the email already has an account) whether approved, rejected or sent to review; 400 if incomplete, still a draft (submit first) or already in review; a sent invitation is audited `invite` | Implemented (US-18, US-93) |
| GET        | `/api/staff/households/{id}/decision-summary/`          | Intake worker, admin | Read-only summary before the decision: 200 `{household_size, adult_count, total_income_cents, threshold_cents, ready_for_decision, will_go_to_review, eligible, approved_months, valid_until, adult_member_ids, notice_rules}` (income and threshold are null until every adult has a notice the rules can add up; `eligible` is null when the file goes to review; `approved_months` and `valid_until` come from `file_validity` and are set only when approving would approve the file; `adult_member_ids` lists the members who need a notice and `notice_rules` the `notice_upload` limits the cards check; 503 when that rule is missing); 404 unknown ID; audited | Implemented (US-18) |
| GET        | `/api/staff/households/{id}/`                           | Intake worker, admin | Read any non-anonymized online or walk-in file in any status, including status reason, expiry, member number, server-derived actions and the `account` block (`status`: `linked`, `can_link`, `cannot_link`, `invited`, `no_email` or `not_applicable`; `reason` for `cannot_link`: `not_beneficiary`, `inactive` or `has_household`; `account_first_name`/`account_last_name` only for `can_link`, for the ID check) | Implemented (US-17, US-32, US-93) |
| POST       | `/api/staff/households/{id}/link-account/`              | Intake worker, admin | Body `{identity_confirmed: true}` after comparing the person's ID with the name on the account. Links the active beneficiary account that uses an approved walk-in's email and has no household; 200 the new `account` block; 400 with the reason (not approved, no email, already linked, no account, staff or store account, deactivated, account already holds a household, ID check not confirmed); 404 unknown, online or anonymized; audited `link_account` | Implemented (US-93) |
| POST       | `/api/staff/households/{id}/resend-invitation/`         | Intake worker, admin | Body `{}`. New set-password link for an approved walk-in with an email and no linked account; earlier links stop working; email queued after commit; 200 `account` block; 400 when not approved, no email, already linked or the email now has an account (link it instead); audited `invite` | Implemented (US-93) |
| GET        | `/api/staff/notices/{id}/file/`                         | Intake worker, admin | `{url, expires_at}`: link to Iris signed for this user, valid `notice_upload.link_minutes` (5); audited | Implemented (T-03.18.2) |
| GET        | `/api/staff/notice-files/{token}/`                      | Intake worker, admin | The file, for the user the link was issued to; attachment, `nosniff`, `no-store`; invalid or expired link 404 | Implemented (T-03.18.2) |
| POST       | `/api/staff/households/{id}/suspend/`, `/reactivate/`   | Admin                | With `reason`; preserves expiry                    | Implemented (US-32) |
| GET/POST   | `/api/staff/households/{id}/notes/`                     | Intake worker, admin | Staff notes                                       | Planned — future/non-R1 |

FIX-08 (SEC-08/SEC-09) records walk-in create, update and submission actions
with actor, household ID and empty metadata in the same transaction as each
change. Detail GET records a view before disclosure and returns
`Cache-Control: private, no-store`; failed audits prevent disclosure. HEAD probes
create no events. Eligibility decisions also join their write transaction to a
household audit event containing only decision UUID, eligible/ineligible outcome
and LICO rule version. Audit search returns `actor: null` and `actor_role: "system"`
for automatic decisions; existing staff actor IDs remain UUID strings.
The walk-in detail query disables focus/reconnect refetching and automatic
retries so background browser events do not append extra access records. Explicit
reads remain audited. System-event references are checked against a saved
automatic decision; PostgreSQL also enforces actor/role consistency.

US-32 suspension/reactivation emails include the reason after household-service
whitespace normalization, active RuleSet length validation and sensitive-data
refusal. The default limit is 500 characters; the schema permits up to 2,000.
The existing 500-character model bound still applies when suspension stores the
status reason; this email change does not enlarge that field. Reactivation clears
the stored field and can retain a longer validated reason in its audit/email.
The shared notification templates preserve the accepted text with HTML escaping,
without copying it into EmailLog or application logs. Households without email
still change status normally. Known-template email validation/configuration
problems are recorded as delivery failures and do not undo a valid status
change; household authorization and reason validation remain enforced.

Active intake workers and admins may read, edit and submit shared,
non-anonymized walk-in files, including another worker's and unassigned files.
Edits and submissions still require a draft. `created_by` records provenance,
not exclusive ownership.

Submission accepts `{}`. It needs an address, one holder, an identity check, and
consent. The household limit comes from `household_size.max_people`; the seed
default is 15 people, including the holder. Approval is separate.

Success returns 200 with `{id, status, status_reason, submitted_at}`. A clean file
is `submitted`; a possible duplicate is `review_required` with reason
`POSSIBLE_DUPLICATE`. Details of matching files are not returned.
Suspended files remain duplicate candidates. Files whose `expires_at` is in the
past are excluded from both address and person matching.
Invalid or repeated submission returns 400; signed-out or deactivated sessions,
401; refused signed-in roles, 403; anonymized, online or unknown files, 404.
Access is checked before request validation.
Create, edit and submit return 503 with code `household_unavailable` and a generic
retry message when required household-size rules are missing or invalid.
Submission also returns this response if a duplicate advisory lock times out;
the draft and its members remain unchanged. The positive setting
`HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS` defaults to 5000 milliseconds and applies
only while acquiring those advisory locks. See the
[households module](../../backend/modules/households/README.md) for candidate
statuses and locking steps.

See the [API conventions](api.md#conventions) for shared request and response rules.
