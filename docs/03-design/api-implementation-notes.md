<!-- AI contribution: 50% or more AI-generated -->

# API implementation notes

The [API reference](api.md) contains the shared conventions and endpoint catalog.
This companion records implementation gaps, team decisions and source references.

## Implementation gaps and team decisions

The rules and endpoint catalog in the [API reference](api.md) preserve the team
draft. The following gaps are recorded for review; this publication does not
change backend or frontend behavior, select new routes, or change the release
scope.

### Errors and pagination

The shared DRF exception handler normalizes throttling responses only. A global
`code/message/fields` envelope for other errors is not configured; plain Django
and allauth retain their own response formats. DRF has no default
pagination class or page size configured. The draft's paging query, maximum,
and response fields are therefore a target contract, not verified behavior.
The paging response notation in the [conventions table](api.md#conventions)
lists keys rather than a complete JSON payload.

### Authentication and permissions

The backend mounts django-allauth headless once at `/api/auth/` with
`HEADLESS_CLIENTS = ("browser",)`. Only `/api/auth/browser/v1/...` routes are
enabled; app-client routes under `/api/auth/app/v1/...` are disabled and return 404.
The browser frontend uses the browser/v1 sign-in and session routes with a
session cookie and the CSRF cookie's value in `X-CSRFToken`. DRF uses the
accounts module's session authentication class; BasicAuthentication is disabled.

**Team decision pending:** whether to enable app-client authentication in a future
release. See [authentication routing](../guides/auth-routing.md).

DRF defaults to `IsAuthenticated`, but this is not the role-and-ownership
matrix required by the draft. The [business rules permission matrix](../02-requirements/business-rules.md)
defines the intended role and ownership checks for the
matrix remain dependencies of the planned endpoints. The draft's `Who`
column does not establish that framework authentication operations all have
identical access requirements.

### Dates, money, and languages

The backend has `USE_TZ=True` and `TIME_ZONE="America/Montreal"`. DRF uses
ISO 8601, but its default datetime field converts values to the current
timezone rather than enforcing UTC output. With the current settings,
`2026-10-21T20:00:00Z` serializes as `2026-10-21T16:00:00-04:00`.
There are no business datetime responses to verify yet.

**Team decision pending:** clarify how the draft's timezone rule applies to
date-only fields, such as dates of birth and best-before dates documented in
[forms and fields](../02-requirements/forms-and-fields.md). The UTC rule in the
draft is retained without choosing an interpretation or changing serializers.

Integer cents and `*_cents` naming align with the existing
[review rules](../05-process/review-rules.md) and field design. Money-bearing
business endpoints remain planned, so their serialization is not yet verified.

The backend configures Django's `LocaleMiddleware` for French and English.
A supported `django_language` cookie takes precedence over `Accept-Language`,
with French as the fallback. DRF throttling messages use the selected language;
`test_throttled_responses_are_translated` in `backend/tests/test_api.py` verifies
French and English request headers. This does not establish translation coverage
for every endpoint or change the error-format limitations described above.

### UUID identifiers

The draft specifies UUID strings. `accounts.User` uses a UUID primary key and
`GET /api/me/` serializes it as a UUID string. Rule versions retain integer
primary keys and do not expose a public business API yet.

**Team decision pending:** confirm how public UUID identifiers map to those
rule versions. This document does not authorize replacing their identifiers.

### Draft path ambiguities

The following draft entries are preserved exactly pending clarification:

- `/api/staff/reports/export.csv?start=&end=` has no trailing slash, although
  the general path rule requires one.
- Resolved for categories (US-35, #501): `GET`/`POST /api/staff/categories/`
  and `PATCH /api/staff/categories/{code}/`. The code identifies a category
  because the public API exposes no database IDs; there is no `DELETE`.
- `/reactivate/` is abbreviated alongside the household suspension path.

**Team decision pending:** confirm the export-path exception, method-to-path
mapping, and full reactivation path. No additional paths or methods are inferred.

### Release scope

The catalog spans more than the current
[Release 1 architecture scope](../04-architecture/architecture.md#scope).
That scope defers online registration, automatic approval, priority tiers,
strikes, the full review queue, privacy-rights workflows, reporting, and the
stretch modules. Some draft descriptions also depend on those deferred
features, such as tier timing, strikes, and opening a review case.

**Team decision pending:** reconcile endpoint milestones and those descriptions
with the release scope before implementing them. Their presence in this API
catalog does not make them implemented or add them to Release 1.

## Implementation references

- [Backend URL configuration](../../backend/iris/urls.py)
- [Django and DRF settings](../../backend/iris/settings/base.py)
- [Health endpoint](../../backend/iris/views.py)
- [Health frontend consumer](../../frontend/src/shared/api/health.ts)
- [Partner application endpoint](../../backend/modules/stores/api/views.py)
- [API generation and drift checks](../guides/api-generation.md)
