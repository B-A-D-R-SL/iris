<!-- AI contribution: 50% or more AI-generated -->
# Observability: structured logging and request IDs

This is a reference implementation for epic #373. Backend logs are JSON lines emitted to standard error. Each HTTP response includes a **server-generated** `X-Request-ID` (32 hexadecimal characters), and the same value appears on Iris request log events.

## Privacy

The JSON formatter deliberately **discards arbitrary log message text, exception messages and tracebacks**. Its allowed keys are `timestamp`, `level`, `logger`, `event`, `request_id`, `method`, `route`, `status_code`, `duration_ms`, `exc_type` and `reason`. `route` is the matched Django *route pattern*, not a URL containing resource IDs. Requests that do not match a route use `unmatched`.

The `iris.auth` events `sign_in_succeeded` and `signed_out` also allow `user_id`,
validated as a UUID. This is the only account identifier allowed in logs;
failed sign-ins and lockouts do not identify the account.

Application log events must use static event names, never personal information. **Do not log** bodies, query strings, raw URL paths, cookie or authorization headers, names, email addresses, document data, or other account identifiers. Do not pass such values into event labels. Third-party diagnostic output and Django debug exception pages are outside this formatter's control; production must run with `DEBUG=False`, and logging must be reviewed before handling real beneficiary data.

HTTP results: `INFO` for 2xx/3xx and the expected signed-out browser session check, `WARNING` for other 4xx, and `ERROR` for 5xx. The default Django log handler also emits only the allowlisted JSON fields.

Inspect logs locally with `docker compose logs -f backend`. Trace an HTTP response by matching its `X-Request-ID` to a JSON log event. For example:

```json
{"timestamp":"2026-10-10T20:00:00.000+00:00","level":"INFO","logger":"iris.http","event":"http_request","request_id":"0123456789abcdef0123456789abcdef","method":"GET","route":"api/health/","status_code":200,"duration_ms":2}
```

The frontend has one logger at `frontend/src/shared/logger.ts`. It emits structured `INFO`, `WARNING` and `ERROR` events with a limited set of fixed event names. It never includes user-supplied values.


## Failure diagnostics

`exc_type` is the exception class name only. Pass the class object in `extra`
(for example, `{"exc_type": type(exc)}`), not its message, instance or a string.
The formatter also extracts the class from standard `exc_info` records. It
never serializes the exception value, traceback, chained causes or message.
Django-caught view exceptions are emitted as `http_request_failed` through
`django.request`; exceptions reaching `RequestIdMiddleware` emit that event
through `iris.http` and are re-raised. The request ID correlates the failure
with the request's completion event.

`reason` accepts these registered codes only:

| Code | Meaning |
| --- | --- |
| `unhandled_exception` | An exception escaped the request handler |
| `smtp_error` | The SMTP transport rejected or failed delivery |
| `connection_error` | Connection, DNS, timeout or TLS failure during delivery |

Unknown codes and free text are dropped. Register additional static codes in
`iris.observability._REASON_CODES` with tests and documentation when a service
needs them; never derive a code from user input or an exception message.

`SmtpMailer.send` logs `email_send_failed` at ERROR for SMTP and connection
errors, with `exc_type` and `reason`, then raises
`adapters.mailer.base.MailerError("Email delivery failed.")`. The original
exception remains its cause for internal handling. Recipients, sender,
subject and body never enter the event. Caller validation errors remain
`ValueError`; existing queued-delivery and partner-confirmation consumers
continue to contain transport failures.

Only `GET /api/auth/browser/v1/auth/session` returning 401 is an expected
signed-out session check. Its Iris, Django request and development-server
records use INFO. Query strings are never logged. DELETE/sign-out requests,
other paths and other 4xx responses keep WARNING; 5xx responses keep ERROR.
`ExpectedSessionCheckFilter` is configured on `django.request` and
`django.server` in `iris/settings/base.py` to avoid duplicate warnings.
