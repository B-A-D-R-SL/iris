# Observability: structured logging and request IDs

This is a reference implementation for epic #373. Backend logs are JSON lines emitted to standard error. Each HTTP response includes a **server-generated** `X-Request-ID` (32 hexadecimal characters), and the same value appears on Iris request log events.

## Privacy

The JSON formatter deliberately **discards arbitrary log message text and exception details**. Its allowed keys are `timestamp`, `level`, `logger`, `event`, `request_id`, `method`, `route`, `status_code` and `duration_ms`. `route` is the matched Django *route pattern*, not a URL containing resource IDs. Requests that do not match a route use `unmatched`.

Application log events must use static event names, never personal information. **Do not log** bodies, query strings, raw URL paths, cookie or authorization headers, names, email addresses, document data, or account identifiers. Do not pass such values into event labels. Third-party diagnostic output and Django debug exception pages are outside this formatter's control; production must run with `DEBUG=False`, and logging must be reviewed before handling real beneficiary data.

HTTP results: `INFO` for 2xx/3xx, `WARNING` for 4xx, and `ERROR` for 5xx. The default Django log handler also emits only the allowlisted JSON fields.

Inspect logs locally with `docker compose logs -f backend`. Trace an HTTP response by matching its `X-Request-ID` to a JSON log event. For example:

```json
{"timestamp":"2026-10-10T20:00:00.000+00:00","level":"INFO","logger":"iris.http","event":"http_request","request_id":"0123456789abcdef0123456789abcdef","method":"GET","route":"api/health/","status_code":200,"duration_ms":2}
```

The frontend has one logger at `frontend/src/shared/logger.ts`. It emits structured `INFO`, `WARNING` and `ERROR` events with a limited set of fixed event names. It never includes user-supplied values.
