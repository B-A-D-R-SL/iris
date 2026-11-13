<!-- AI contribution: 50% or more AI-generated -->
# Observability: structured logging and request IDs

This is a reference implementation for epic #373. Backend logs are JSON lines emitted to standard error. Each HTTP response includes a **server-generated** `X-Request-ID` (32 hexadecimal characters), and the same value appears on Iris request log events.

## Privacy

The JSON formatter deliberately **discards arbitrary log message text and exception details**. Its allowed keys are `timestamp`, `level`, `logger`, `event`, `request_id`, `method`, `route`, `status_code` and `duration_ms`. `route` is the matched Django *route pattern*, not a URL containing resource IDs. Requests that do not match a route use `unmatched`.

The `iris.auth` events `sign_in_succeeded` and `signed_out` also allow `user_id`,
validated as a UUID. This is the only account identifier allowed in logs;
failed sign-ins and lockouts do not identify the account.

Unsupported allauth mail prefixes produce the static INFO event
`authentication_email_skipped` on `iris.auth`. This event includes no recipient,
template prefix, context, token or exception information; the adapter returns
normally without a queue or transport call.

The `iris.eligibility` event `eligibility_decided` also allows exactly four
business fields: `decision_id` and `household_id` (validated UUIDs), `outcome`
(`eligible` or `ineligible`), and `rule_version` (the positive integer version
of the `lico_thresholds` rule). These fields are allowed only for that logger
and event. No names, income amounts, thresholds, evidence, or staff identifiers
are included. One event is emitted after the surrounding transaction commits;
failed saves and rolled-back workflows emit no success event. This application
log does not replace the append-only audit record tracked in FIX-08 (#634).

Application log events must use static event names, never personal information. **Do not log** bodies, query strings, raw URL paths, cookie or authorization headers, names, email addresses, document data, or other account identifiers. Do not pass such values into event labels. Third-party diagnostic output and Django debug exception pages are outside this formatter's control; production must run with `DEBUG=False`, and logging must be reviewed before handling real beneficiary data.

US-57 notification events use the static names `email_sent`,
`email_retry_scheduled`, `email_send_failed`, `email_queue_failed`,
`email_configuration_failed`, `email_outcome_unavailable` and
`email_cleanup_failed`, plus `email_invitation_unavailable` for stale invitation
preflight. No recipient, message
content, rendering context, one-use link or provider exception is attached.
Worker exceptions contain bounded internal error codes with the provider
exception chain suppressed. SMTP/Azure calls stay behind adapters; HTTP diagnostic
logging must not expose provider request bodies or credentials.

`EmailLog` is a protected database delivery record, separate from application
stdout logs. It retains recipient, optional user, template key, language, status,
attempts, a bounded error code and timestamps. It excludes subjects, bodies,
rendering context and tokens. `sent` means transport/provider acceptance, not
inbox receipt. Temporary one-use links belong only in the restricted queue
payload needed for asynchronous delivery. The bounded US-13 partner rejection
reason and producer-validated US-32 suspension/reactivation reasons are likewise
restricted to their temporary payload/email and are absent from EmailLog and
stdout; other template families do not accept reasons or case notes.
An hourly cleanup removes terminal
email jobs after the active retention threshold (24 hours by default), normally
within 24–25 hours with a healthy worker; pending/retrying jobs remain. Legacy
jobs on the default queue require the targeted rollout cleanup described in the
[module runbook](../../backend/modules/notifications/README.md#one-use-links-and-cleanup).

HTTP results: `INFO` for 2xx/3xx, `WARNING` for 4xx, and `ERROR` for 5xx. The default Django log handler also emits only the allowlisted JSON fields.

Inspect logs locally with `docker compose logs -f backend`. Trace an HTTP response by matching its `X-Request-ID` to a JSON log event. For example:

```json
{"timestamp":"2026-10-10T20:00:00.000+00:00","level":"INFO","logger":"iris.http","event":"http_request","request_id":"0123456789abcdef0123456789abcdef","method":"GET","route":"api/health/","status_code":200,"duration_ms":2}
```

The frontend has one logger at `frontend/src/shared/logger.ts`. It emits structured `INFO`, `WARNING` and `ERROR` events with a limited set of fixed event names. It never includes user-supplied values.
