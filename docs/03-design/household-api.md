<!-- AI contribution: 50% or more AI-generated -->
# Household and notice API

| Method     | Path                                                    | Who                  | Purpose                                           | Status  |
| ---------- | ------------------------------------------------------- | -------------------- | ------------------------------------------------- | ------- |
| GET        | `/api/households/me/`                                   | Beneficiary          | Status, expiry, members (names), alternate        | Planned |
| GET/PUT    | `/api/households/me/application/`                       | Beneficiary          | Draft application, steps 1 to 3                   | Planned |
| POST       | `/api/households/me/notices/`                           | Beneficiary          | Upload a notice for a member (multipart)          | Planned |
| PATCH      | `/api/households/me/notices/{id}/`                      | Beneficiary          | Confirm or correct read values, or `did_not_file` | Planned |
| POST       | `/api/households/me/application/submit/`                | Beneficiary          | Submit                                            | Planned |
| PATCH      | `/api/households/me/alternate/`                         | Beneficiary          | Alternate for pickups                             | Planned |
| POST       | `/api/households/me/renewal/`                           | Beneficiary          | Start a renewal                                   | Planned |
| GET        | `/api/staff/households/?q=`                             | Intake worker, admin | Partial, accent-insensitive search; authorized non-anonymized files, pagination, audits and server-derived `can_resume` and `can_open` | Implemented (US-63, US-32) |
| POST/PATCH | `/api/staff/households/`, `/api/staff/households/{id}/` | Intake worker, admin | Walk-in create and edit (drafts only)             | Implemented (US-17) |
| POST       | `/api/staff/households/{id}/submit/`                    | Intake worker, admin | Submit saved walk-in registration; possible duplicates go to review | Implemented (US-25; proposed endpoint for review) |
| POST       | `/api/staff/households/{id}/notices/`                   | Intake worker, admin | Walk-in notice (scan + typed values)              | Planned |
| POST       | `/api/staff/households/{id}/approve/`                   | Intake worker, admin | Approve a walk-in (eligibility runs)              | Planned |
| GET        | `/api/staff/households/{id}/`                           | Intake worker, admin | Read any non-anonymized online or walk-in file in any status, including status reason, expiry, member number and server-derived actions | Implemented (US-17, US-32) |
| GET        | `/api/staff/notices/{id}/file/`                         | Intake worker, admin | Signed URL valid 5 minutes (audited)              | Planned |
| POST       | `/api/staff/households/{id}/suspend/`, `/reactivate/`   | Admin                | With `reason`; preserves expiry                    | Implemented (US-32) |
| GET/POST   | `/api/staff/households/{id}/notes/`                     | Intake worker, admin | Staff notes                                       | Planned |

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
