<!-- AI contribution: 50% or more AI-generated -->
# Notifications module — US-57

Notifications owns bilingual email rendering, queued delivery and `EmailLog`.
Business modules decide when an event warrants email and call the public service;
external delivery goes through `adapters/mailer/`. There is no public send API.

## Public interface

```python
from modules.notifications import services as notifications

# A saved User supplies its address and preferred_language.
email_log = notifications.send(user, "file_approved", {})

# An applicant or walk-in contact need not have an account.
email_log = notifications.send(
    "applicant@example.test",
    "partner_application_received",
    {"language": "en", "business_name": "Commerce Exemple"},
)
```

`send(user_or_email, template_key, context)` validates the address and reviewed
context, creates an `EmailLog`, and registers queue insertion with
`transaction.on_commit`. Call it inside the business transaction. A rollback
removes the log and discards the callback. Outside an existing transaction, the
service commits its own transaction before enqueueing. Provider calls always run
in the worker.

A User supplies the persisted preferred language. Raw addresses use reserved
`context["language"]` (`fr` or `en`), defaulting to French. The chosen language is
saved in EmailLog; worker translation state cannot change it. The service copies
the rendering context and removes the reserved language field. It never queues a
User, request or allauth context object.

`queue_household_status_email(...)` remains the US-32 compatibility wrapper.
It skips files without email and maps suspension/reactivation to the shared
service. Reasons stay in Iris rather than in email. Household validation and
audit requirements remain with the household workflow.

## Template catalog

Every key has French and English subject/plain-text files under
`templates/notifications/{fr,en}/`. A shared HTML wrapper escapes the body and
action link. Context validation rejects unknown templates, missing required
fields, unreviewed context fields and unsafe URLs before queueing.

| Template key | Required context | Default action |
| --- | --- | --- |
| `account_confirmation` | `confirmation_url` | Supplied confirmation link |
| `password_reset` | `reset_url` | Supplied reset link |
| `invitation` | `invitation_url` | Supplied invitation link |
| `walk_in_set_password` | `invitation_url` | Supplied invitation link |
| `partner_application_received` | `business_name` | Public landing page |
| `partner_application_approved` | `invitation_url` | Supplied invitation link |
| `partner_application_rejected` | `reason` | Public landing page |
| `file_approved` | None | Sign-in |
| `file_in_review` | None | Sign-in |
| `file_invited_in_person` | None | Sign-in |
| `file_rejected` | None | Sign-in |
| `expiry_reminder` | None | Sign-in |
| `reservation_confirmed` | None | Sign-in |
| `pickup_window_open` | None | Sign-in |
| `reservation_cancelled_by_store` | None | Sign-in |
| `strike` | None | Sign-in |
| `digest` | None | Sign-in |
| `need_match` | None | Sign-in |
| `household_suspended` | None | Sign-in |
| `household_reactivated` | None | Sign-in |

Generic templates optionally accept `sign_in_url`, restricted to the configured
origin's `/` or `/sign-in`, without query or fragment. All URLs must use
`PUBLIC_APP_ORIGIN`. Invitation URLs use `/invitation/<43-character token>`;
confirmation/reset path contracts remain with accounts. HTTPS is required except
an explicitly configured loopback HTTP origin for local/tests. Production also
rejects local origins. `business_name` captures the original nonblank string up to
150 characters, matching the existing form contract; NUL and surrogate characters
remain invalid. The worker validates that snapshot again, then normalizes Unicode
whitespace and removes remaining
nonprintable characters from its display copy. A name with no visible characters
uses a generic receipt sentence in the recipient's language. Stored application
names and queued snapshots stay unchanged; controls never reach the email's
displayed name. Plain text uses the display copy and HTML escapes it once.

Messages contain a reviewed status/next step and a trusted link. The dedicated
partner rejection template preserves US-13's existing contract: required `reason`
is the stored, trimmed decision reason, at most 500 characters. It is passed
unchanged to the text template and escaped once in HTML. No other template accepts
reasons or case notes; arbitrary bodies, income/document fields and recipient
details are excluded. The rejection reason belongs only in the restricted
temporary rendering payload and email, never EmailLog or stdout. Digest/matching
selection, consent, visibility and schedulers remain
with their owning features. Reservation details/QR codes remain with their owning
story. Their templates currently point to Iris for details.

## Jobs, retries and delivery metadata

New jobs use the `email` queue and `notifications.send_email` task. Payloads contain
an EmailLog UUID, an allowlisted rendering context and a captured retry policy.
The worker renders the saved language, selects the configured adapter, and
updates the same log for each attempt.

The active `notifications` RuleSet supplies exactly three retry delays. Defaults
are `[60, 300, 900]` seconds after successive failures: one initial attempt plus
three retries, at most four attempts. A send retains its captured list when a new
rule version is published. Confirmed permanent adapter failures stop immediately.
Retryable failures escape as sanitized exceptions so Procrastinate schedules
retries; returning normally would mark the job successful.

This retry budget follows Procrastinate's job executions. A database failure can
consume an execution without calling the provider. EmailLog's transport-attempt
counter is separate and can therefore be lower than the queue's execution count.

EmailLog records a UUID, recipient, optional user, template key, language, status,
attempt count, bounded error code, sending time and creation/update times.
Statuses are `pending`, `sending`, `retrying`, `sent` and `failed`; attempts count
transport attempts started by the worker. `sent`/`sent_at` mean provider
acceptance, rather than inbox delivery. Subject, bodies, context and tokens are
absent from this table.
Recipient addresses are permitted in this protected table, never stdout logs.
The staff failure/bounce interface is US-61. Provider delivery/bounce events are
not implemented here.

Missing/invalid notification rules produce a failed log with
`notification_rules_unavailable`; there is no runtime policy fallback. Queue
insertion failure records `queue_unavailable` when the database remains available.
Both preserve an already committed business action. A database outage can prevent
both queue insertion and the failure update.

After-commit queueing leaves a crash window before queue insertion. Per-log queue
locks and terminal-status checks reduce duplicates, but a crash after provider
acceptance can still cause a repeat send. This is neither an atomic outbox nor
exactly-once delivery.

## One-use links and cleanup

Accounts stores invitation token hashes. Asynchronous invitation delivery still
needs a raw link temporarily in its restricted queue context. Protect queue and
database access; never copy links into EmailLog, application events or raw
provider exceptions.

The worker uses the accounts public query to check invitation usability for
`invitation`, `walk_in_set_password` and `partner_application_approved`. If the
invitation is superseded, expired, accepted or missing, EmailLog becomes `failed`
with `invitation_unavailable`, and the job finishes without retry or a new
transport attempt. Never-sent logs
remain at zero attempts; earlier transport attempts remain counted. Reissue
atomically invalidates old unaccepted links and queues the fresh link. A token
can change state after preflight, and an in-flight email cannot be recalled;
an old link remains invalid in Iris even if that message reaches its recipient.

`notifications.cleanup_email_jobs` runs hourly on `maintenance`. It removes
terminal `email` jobs using the active `notifications.job_retention_hours` rule
(default 24), retaining EmailLog metadata. With a healthy worker, payload removal
normally occurs between 24 and 25 hours after the terminal event. A delayed or
stopped worker can extend that period. Pending/running/retrying jobs remain
available. This does not implement general EmailLog retention.

The old `notifications.send_household_status_email` task name remains callable
for previously queued email/subject/body arguments. New workflows never create
that payload. During rollout, drain and remove old terminal jobs on their original
queue too: pre-US-57 jobs may be on Procrastinate's default queue, outside the new
email-queue cleanup. Do not purge unrelated default-queue jobs.

## Operation and verification

```bash
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend python manage.py seed_rules
docker compose up -d worker mailpit
docker compose exec -T backend python -m pytest modules/notifications/tests -q
```

After configuration changes, recreate both application processes so they share
the same `PUBLIC_APP_ORIGIN` and provider settings:

```bash
docker compose up -d --build backend worker
```

`docker compose restart` retains the old container environment; it does not apply
changed Compose settings. A web/worker origin mismatch can invalidate queued
invitation rendering even when both processes individually start successfully.

Local web/worker processes select SMTP through Mailpit. The worker must run to
send mail and execute cleanup. The `fake` adapter records messages only in the
test process; reset it between cases. Transport tests mock SMTP/Azure, without
provider calls.

Implemented producers are partner receipt, approval, rejection and invitation
reissue, plus household suspension/reactivation.
The allauth bridge maps confirmation/reset mail to this service without opening
signup or implementing those account workflows. Walk-in approval remains US-18;
other producers and reminder/digest/matching schedulers remain with their stories.
Template coverage does not establish that their business triggers exist.

Staging selects `MAILER_ADAPTER=azure`, an ACS connection string and the verified
domain MailFrom address. See [production email configuration](../../../docs/guides/production-settings.md#email-delivery-us-57).
A separate synthetic ACS smoke send remains necessary before claiming live Azure
delivery.

## PR verification and SET-17 handoff

The results below describe verification before integrating main's US-13 review
workflows. Subsequent approval/rejection/reissue integration uses the same
templates, queue, fake and EmailLog; its verification must be recorded separately.

The implementation is ready for code review before App Service and the staging
worker exist. Local evidence covers the complete database/job/worker/Mailpit path,
both template languages, retries, metadata and privacy; ACS adapter tests replace
the Azure transport. The recorded full backend run had 2,159 passed, five skipped,
one slow-expiry test deselected and 95.51% coverage. Its only failure was the
existing household-search capacity benchmark, reproduced on the unchanged base.
Lint/format, typing, import boundaries, migrations, dependency audit and generated
API comparisons passed. Review corrected retry-attempt accounting, removed ORM
access from the async retry callback and filtered raw queue diagnostic records.

The review against Ammar's clarification covered all 134 changed/added files,
including 81 templates. It corrected a business-name validation regression while
preserving the existing application field contract. The follow-up runs passed
268 core tests and 155 rendering/partner regressions. After restarting the local
worker, two additional synthetic Mailpit messages verified normalized names and
the generic receipt fallback; both logs reached `sent` on their first attempt.

After merging main's US-13 workflows, approval, rejection and operator reissue
now use the shared template/queue/fake/EmailLog path and `PUBLIC_APP_ORIGIN`.
The owner chose to preserve the stored rejection reason under the existing
500-character trimmed limit, only in the dedicated partner rejection email;
other reasons remain excluded. Invitation preflight stops already invalid links
without another transport attempt. Targeted merged-tree checks passed **916
backend tests** (722 core/accounts/configuration/access and 194 store cases) and
**44 frontend staff/routing tests**. Ruff lint/format passed for 437 files, mypy
passed for 421 source files, all four import contracts passed, and the migration
check found no drift. These are targeted integration checks, separate from the
historical 134-file review and full-run results above.

The first native worker smoke run encountered old containers with different web
and worker origins (5173 versus 5174); invitation jobs were refused as invalid
configuration. Rebuilding and recreating both processes applied the matching
5174 origin and resolved the mismatch. The native PostgreSQL/queue/worker/Mailpit
rerun delivered three messages covering approval, recovery and rejection, with
three EmailLog records reaching `sent` on their first transport attempt. An
initial invitation superseded before delivery was marked `failed` with
`invitation_unavailable`, zero attempts and no email. Delivered approval/recovery
tokens were usable, and the French rejection email contained the requested
stored reason. This is local integration evidence; no deployed Iris-to-ACS
delivery is claimed.

The later FIX-17 CI merge passed 116 configuration tests and 46 CI-script tests.
The strict production deployment check passed, and the CI-scan settings served
health and admin login with secure cookies retained. Workflow YAML and all 31
shell steps passed syntax checks. These checks used synthetic email settings;
full gitleaks and ZAP execution remains part of published CI.

Ammar reports successful delivery using Azure's portal Try Email. This is
provider-side evidence; an Iris-to-ACS staging send has not been performed.
After SET-17 deploys the application and persistent worker, configure the settings
in the [production handoff](../../../docs/guides/production-settings.md#email-delivery-us-57)
and verify a controlled queued email, its metadata and inbox receipt. Log-stream
and heartbeat checks apply once that hosting exists. Keep this follow-up visible
in the PR without describing local tests as a live staging test.
