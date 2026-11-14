<!-- AI contribution: 50% or more AI-generated -->

# Headless authentication routing

Iris uses `/api/auth/...` as its authentication prefix. The backend uses
**django-allauth headless** with `HEADLESS_CLIENTS = ("browser",)`.
Only `/api/auth/browser/v1/...` routes are enabled. App-client routes under
`/api/auth/app/v1/...` are disabled and return 404.

The backend mounts `allauth.headless.urls` **once**, at `/api/auth/`.
The former `/_allauth/` development route has been removed to avoid duplicate
Django URL namespaces. US-01 uses the browser sign-in and sign-out operations;
`/api/me/` supplies the current profile. Public registration stays closed until
US-02 adds email verification. Password reset and MFA enrollment remain later work.

FIX-14 removes the dormant frontend two-factor API request and code-entry step
until US-09 supplies the server flow. `allauth.mfa` is not installed. An unexpected
`mfa_authenticate` challenge shows the translated unavailable error, leaves the
user on sign-in and sends no request to an unsupported two-factor endpoint.

The frontend calls `/api/auth/browser/v1/auth/login` and
`/api/auth/browser/v1/auth/session`. It sends the CSRF cookie value in
`X-CSRFToken` for state-changing requests, and the backend uses HttpOnly,
SameSite=Lax session cookies. `GET /api/me/` uses session authentication.
The allauth routes are not included in the DRF OpenAPI schema. Enabling app-client
authentication is a future team decision; its routes are unavailable today.

## Rate-limit responses

Authentication routes use allauth rather than DRF's shared exception handler.
The browser login action's IP limit returns HTTP 429 with `{"status": 429}`,
without a `Retry-After` header or the DRF `code/message/fields` envelope. The
frontend safely maps that response to its translated `unavailable` error.

Failed-credential lockouts are a different allauth response: HTTP 400 with
`status: 400` and an `errors` entry whose `code` is `too_many_login_attempts`.
The frontend maps that code to its translated `locked` error. Backend tests
exercise both response shapes; a frontend test covers the native HTTP 429.

Production's `ALLAUTH_TRUSTED_PROXY_COUNT` controls allauth's client IP selection
separately from DRF's `DRF_NUM_PROXIES`. See
[production proxy configuration](production-settings.md#https-and-trusted-proxies)
before deploying behind Azure.
