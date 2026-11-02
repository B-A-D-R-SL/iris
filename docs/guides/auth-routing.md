<!-- AI contribution: 50% or more AI-generated -->

# Headless authentication routing

Iris's API draft uses `/api/auth/...` as its authentication prefix. The backend
uses **django-allauth headless**, whose own URLs contain versioned application and
browser paths (for example, `/api/auth/app/v1/auth/...` and
`/api/auth/browser/v1/auth/...`).

The backend mounts `allauth.headless.urls` **once**, at `/api/auth/`.
The former `/_allauth/` development route has been removed to avoid duplicate
Django URL namespaces. US-01 uses the browser sign-in and sign-out operations;
`/api/me/` supplies the current profile. Public registration stays closed until
US-02 adds email verification. Password reset and MFA enrollment remain later work.

The frontend calls `/api/auth/browser/v1/auth/login` and
`/api/auth/browser/v1/auth/session`. It sends the CSRF cookie value in
`X-CSRFToken` for state-changing requests, and the backend uses HttpOnly,
SameSite=Lax session cookies. `GET /api/me/` uses session authentication.
The allauth routes are not included in the DRF OpenAPI schema. The team still
needs to decide whether to expose allauth's versioned app paths publicly.
