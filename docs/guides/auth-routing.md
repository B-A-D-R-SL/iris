# Headless authentication routing (setup convention)

Iris's API draft uses `/api/auth/...` as its authentication prefix. The backend
uses **django-allauth headless**, whose own URLs contain versioned application and
browser paths (for example, `/api/auth/app/v1/auth/...` and
`/api/auth/browser/v1/auth/...`).

The backend mounts `allauth.headless.urls` **once**, at `/api/auth/`.
The former `/_allauth/` development route has been removed to avoid duplicate
Django URL namespaces. This is a routing change, **not** a new implementation
of login, logout, registration, password reset, or two-factor authentication.

**SET-15 follow-up:** Agree on the final public URL contract and whether to
expose allauth's versioned paths directly or wrap them. Confirm CSRF,
client authentication, cookies, and API schema support. The API reference ZIP
remains a proposal until adopted by the team.
