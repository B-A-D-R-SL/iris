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

`send(user_or_email, template_key, context)` records the known template's delivery
outcome and registers valid queue insertion with `transaction.on_commit`. Call it
inside the business transaction. A rollback removes the log and discards the
callback. Outside an existing transaction, the service commits its own
transaction before enqueueing. Provider calls always run in the worker.

Known-template recipient, context and runtime email-configuration problems return
a failed EmailLog with zero attempts and no job, preserving the business
transaction. An unknown template key remains a programmer error and raises
`ValueError`. Essential business validation and authorization remain with callers.

A User supplies the persisted preferred language. Raw addresses use reserved
`context["language"]` (`fr` or `en`), defaulting to French. The chosen language is
saved in EmailLog; worker translation state cannot change it. The service copies
the rendering context and removes the reserved language field. It never queues a
User, request or allauth context object.

`queue_household_status_email(...)` remains the US-32 compatibility wrapper.
It skips files without email and maps suspension/reactivation to the shared
service, including the normalized, privacy-validated reason. The household
workflow's `_status_reason` remains responsible for the active RuleSet limit
and sensitive-data validation before audit or email queueing.

`queue_set_password_email(email=..., token=..., language=...)` is the US-18
walk-in approval wrapper. It builds `PUBLIC_APP_ORIGIN/invitation/<token>` and
sends `walk_in_set_password` through `send`. A missing or invalid origin becomes
a failed EmailLog (`email_configuration_invalid`) rather than undoing approval.

## Template catalog

Every key has French and English subject/plain-text files under
`templates/notifications/{fr,en}/`. A shared HTML wrapper escapes the body and
action link. Context validation rejects unknown templates, missing required
fields, unreviewed context fields and unsafe URLs before queueing.
Final French/English wording remains subject to the sponsor review recorded in
[PR #697](https://github.com/B-A-D-R-SL/iris/pull/697#pullrequestreview-5886577453).

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
| `household_suspended` | `reason` | Sign-in |
| `household_reactivated` | `reason` | Sign-in |

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
unchanged to the text template and escaped once in HTML. The two household status
templates preserve US-32's normalized, privacy-validated `reason`; the producer
checks the active `household_suspension.reason_max_length` (default 500). Their
queued snapshot supports the RuleSet schema ceiling of 2,000 characters, so a
later, lower rule does not invalidate a previously accepted reason. This capture
ceiling does not enlarge the household model's 500-character stored status-reason
limit; suspension still passes model validation. Reactivation clears that stored
field and may have a longer validated reason under its active rule. Rendering
escapes it once for HTML without changing the captured text. These three
templates are the only reason-bearing families. Case notes, arbitrary bodies,
income/document fields and recipient details remain excluded. Reasons belong
only in the restricted temporary payload and email, never EmailLog or stdout.
Digest/matching selection, consent, visibility and schedulers remain
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

Validation failures use `email_recipient_invalid` for invalid/unrepresentable
recipients and `email_configuration_invalid` for rendering context, action URL
or runtime origin problems. A malformed recipient is retained only if it fits
the database field safely (string, at most 254 characters, no NUL or surrogate);
otherwise `to_email` is empty on that failed record. Neither case queues a job.
Only the static `email_configuration_failed` event is emitted after commit; raw
recipient/context/error values are absent. A secondary failure to record an
enqueue outcome emits `email_outcome_unavailable`, without provider/DB details.
Production startup validation still rejects unsafe deployment configuration.

Invalid or nonfinite Azure `Retry-After` metadata uses a one-second polling
delay and emits the static warning `azure_retry_after_invalid`, without the
header value or raw provider formatting arguments. This diagnostic follows the
same privacy boundary as adapter failures.

Review traceability uses the existing rule catalog: BR-PARTNER-05 covers recovery
and invitation preflight; BR-PARTNER-02 remains the public application IP throttle.
The notification policy tests cite BR-NOTIF-001 through BR-NOTIF-004. Rule IDs
retain their existing meanings.

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

Ammar's PR #697 review records retention and duplicate/stuck-send recovery as
nonblocking follow-ups for the next release. EmailLog has no scheduled deletion
yet, so its `to_email` persists and the `retention.email_logs_months` setting is
not applied. Terminal job payloads can retain invitation links and validated
decision/status reasons until the hourly cleanup threshold. There is no watchdog
to recover logs left in `pending` or `sending`, nor a guarantee against duplicate
sends across the provider-acceptance/log-update crash window. These follow-ups
do not change the current queue cleanup or delivery guarantees.

PR #697's three inline review fixes preserve valid business decisions when a
known-template email input/configuration fails, restore the validated US-32
reason in both household status emails, and skip unsupported allauth prefixes
with a static event. The related regression results are recorded separately from
earlier merge verification below. Ammar's template/system-file review remains
pending, and final wording will be confirmed with the sponsor.

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
signup or implementing those account workflows. Unsupported allauth prefixes
return normally with `authentication_email_skipped`; they do not queue or fall
back to direct SMTP. Supported prefixes with missing/non-string/invalid action
URLs use the shared `email_configuration_invalid` failed-log path, without an
early adapter exception or queue insertion. Walk-in approval remains US-18;
other producers and reminder/digest/matching schedulers remain with their stories.
Template coverage does not establish that their business triggers exist.

Staging selects `MAILER_ADAPTER=azure`, an ACS connection string and the verified
domain MailFrom address. See [production email configuration](../../../docs/guides/production-settings.md#email-delivery-us-57).
A separate synthetic ACS smoke send remains necessary before claiming live Azure
delivery.

## PR verification and SET-17 handoff

The initial full-run and 134-file-review records below precede main's US-13
integration. Later paragraphs record merged-workflow and PR #697 review-fix
verification separately; historical run counts are not added together.

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
500-character trimmed limit in the dedicated partner rejection email. At this
verification stage, household reasons were still excluded; the PR review
follow-up restores their validated US-32 behavior. Invitation preflight stops
already invalid links without another transport attempt. Targeted merged-tree
checks passed **916
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

Latest PR #697 review-fix validation passed **735 unique targeted backend tests**:
447 notification/account/notification-rule cases and 288 store/suspension-API/
mailer cases, using `-W error --no-cov`. Full Ruff lint/format passed for 438 files,
mypy passed for 422 source files, all four import contracts passed, and migration
checks found no drift. This is targeted regression evidence, without a new
full-suite or coverage claim.

With the worker restarted on the latest code, native PostgreSQL/queue/worker/
Mailpit verification delivered four household status emails (suspension and
reactivation, each in French and English), all `sent` on their first attempt.
The captured reason appeared in text and was escaped once in HTML. Two malformed
recipient/context cases produced failed logs with zero attempts and no jobs;
unsupported allauth mail was skipped without an EmailLog. The operator recovery
command now reports reissue and directs staff to EmailLog without promising
queue insertion or delivery. Recent worker stdout contained no synthetic reason
or recipient-address prefixes in the privacy check.

The subsequent CodeRabbit follow-up passed **316 targeted backend tests**
(notifications, rules, recovery, mailers and observability, `-W error --no-cov`)
and the copied ZAP gate suite's **10 tests with 20 subtests**. Ruff lint/format
passed for 438 files, mypy for 422 source files, and all four import contracts.
An independent AST comparison confirmed that 11 other changed Python files had
comments-only changes. A full PR size scan found adjacent technical rationales
for all four changed functions above 50 lines and four files above 500 lines;
the ZAP `alerts` rationale addresses CodeRabbit's reported complexity of 16. A targeted
Ruff C901 scan of mailer, notification, account, rule, store, observability and
ZAP code found no issues at a complexity limit of 15.

No new online CodeRabbit result was recorded for this follow-up. Its displayed
automatic review selection contains 149 files, above the 100-file review limit;
this does not establish a fresh pass or prevent separate custom-check review.
Published review/check results still need to be assessed on the updated commit.

Ammar reports successful delivery using Azure's portal Try Email. This is
provider-side evidence; an Iris-to-ACS staging send has not been performed.
After SET-17 deploys the application and persistent worker, configure the settings
in the [production handoff](../../../docs/guides/production-settings.md#email-delivery-us-57)
and verify a controlled queued email, its metadata and inbox receipt. Log-stream
and heartbeat checks apply once that hosting exists. Keep this follow-up visible
in the PR without describing local tests as a live staging test.
