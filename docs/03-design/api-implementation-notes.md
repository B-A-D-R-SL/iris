<!-- AI contribution: 50% or more AI-generated -->

# API implementation notes

> **Release 1 boundary:** the API catalog spans multiple releases.
> **Future / non-R1** entries describe designs outside the reviewed Release 1
> implementation; they are not deployed or promised Release 1 endpoints.
> Release 1 notice handling is staff-led walk-in upload/manual entry, with no
> household online upload or runtime AI reader. See the
> [scope distinction below](#release-scope) and the
> [architecture scope](../04-architecture/architecture.md#scope).

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
and response fields are therefore not a global guarantee: implemented views
select their pagination classes. Browse fixes the page size at 20; staff lists
use their own paging rules. Consult each implemented endpoint's contract.
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

DRF defaults to `IsAuthenticated`; implemented business views additionally
check roles and ownership. The endpoint access inventory is in
`backend/tests/test_endpoint_access.py`. Future endpoints must implement their
own checks before activation; the draft's `Who` column is not proof of a working
endpoint. See the [business rules permission matrix](../02-requirements/business-rules.md).

### Dates, money, and languages

The backend has `USE_TZ=True` and `TIME_ZONE="America/Montreal"`. DRF uses
ISO 8601, but its default datetime field converts values to the current
timezone rather than enforcing UTC output. With the current settings,
`2026-10-21T20:00:00Z` serializes as `2026-10-21T16:00:00-04:00`.
Business datetime responses now exist. For example, browse and reservation
serializers explicitly select UTC; the DRF default is not a guarantee that every
view uses that representation.

Date-only fields, such as dates of birth and best-before dates documented in
[forms and fields](../02-requirements/forms-and-fields.md), remain calendar dates;
they are not timestamps to convert between timezones.

Integer cents and `*_cents` naming align with the existing
[review rules](../05-process/review-rules.md) and field design. Staff notice and
decision-summary APIs already expose integer-cent amounts; their presence does
not enable the future household online application or reporting APIs.

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

RuleSetVersion, AuditEvent and HouseholdDraftEvent retain bigint primary keys;
the UUID convention is not a claim that every supporting record has a UUID.

### Draft path ambiguities

The following draft entries are preserved exactly pending clarification:

- `/api/staff/reports/export.csv?start=&end=` has no trailing slash, although
  the general path rule requires one.
- Resolved for categories (US-35, #501): `GET`/`POST /api/staff/categories/`
  and `PATCH /api/staff/categories/{code}/`. The code identifies a category
  because the public API exposes no database IDs; there is no `DELETE`.
- Household reactivation is implemented at
  `POST /api/staff/households/{id}/reactivate/`; an abbreviated `/reactivate/`
  beside the suspension entry refers to that full staff path.

**Future/non-R1 decision pending:** confirm the reporting export-path exception
and method-to-path mapping before implementing that reporting API.

### Release scope

The catalog spans more than the current
[Release 1 architecture scope](../04-architecture/architecture.md#scope).
The catalog and [household API tables](household-api.md) label unimplemented
entries **Planned — future/non-R1**. Mixed rows distinguish the implemented
method from future methods. Scope and implementation status are separate from
deployment status: an implemented endpoint is not proof that staging is live.

| Area | Release 1 implementation | Future/non-R1 design |
| --- | --- | --- |
| Registration and notices | Staff creates/edits walk-in drafts, uploads adult notices or records non-filing reasons, submits and requests a decision | Beneficiary online application/upload, AI-read-value confirmation, automatic online approval and renewal APIs |
| Eligibility and review | Staff-requested eligibility decision; a flagged file can remain `review_required` | Review-case queue/decision API, priority scores, tiers, overrides and strikes |
| Rules | Versioned rules, seed/publish services and audited rule history | Staff rule-management/preview HTTP endpoints |
| Listings and reservations | Posting, staff safety checks, approved-household browse/reserve and store pickup confirmation | Listing-detail HTTP endpoint, listing editing/self-service, household cancellation, late confirmation and strike/tier behavior |
| Staff insight | Audit search and email delivery services | Reporting/export and failed-email administration APIs |
| Privacy and stretch modules | Baseline access/privacy controls still apply | Privacy-rights APIs, needs, resource assistant and furniture APIs |

No release number or delivery date is assigned here to unscheduled future
entries. Do not treat their presence in the design catalog, or a related model,
status or template, as an implemented Release 1 workflow.

## Implementation references

- [Backend URL configuration](../../backend/iris/urls.py)
- [Django and DRF settings](../../backend/iris/settings/base.py)
- [Health endpoint](../../backend/iris/views.py)
- [Partner application endpoint](../../backend/modules/stores/api/views.py)
- [API generation and drift checks](../guides/api-generation.md)
