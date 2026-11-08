<!-- AI contribution: 50% or more AI-generated -->
# Household search — US-63

Issues: [backend #553](https://github.com/B-A-D-R-SL/iris/issues/553),
[frontend #554](https://github.com/B-A-D-R-SL/iris/issues/554),
[tests #552](https://github.com/B-A-D-R-SL/iris/issues/552).

## Run locally

Apply committed migrations with the usual Docker startup, then sign in as an
intake worker or administrator and open `/staff/households`:

```powershell
docker compose up --watch
```

If the backend is already running, apply the new migration once:

```powershell
docker compose exec backend python manage.py migrate
```

Search by partial member name (either order), household email, formatted phone,
member number or address. Names and addresses ignore case/accents. Results show
the holder, regardless of which member matched. Empty input returns no files.
The existing walk-in draft POST/PATCH endpoints remain supported.

Intake workers can search their own non-anonymized walk-in files and online files.
Admins can search all non-anonymized files, including unassigned files. The scope is defined
in BR-HH-ACCESS-001 in [business rules](../02-requirements/business-rules.md).
The actor is checked by `search_for_staff` before searching;
the object scope is applied before counting or pagination. The API returns a
`can_resume` boolean from the same policy used for editing, and the frontend
renders it without recomputing permission from household status or channel.

Numeric pages use a PostgreSQL window count to obtain the total and page in one
SELECT, rather than running the search twice for a separate COUNT and results.
Authentication and auditing run normally for every request. The optional
`page=last` shortcut retains DRF's
count-first behavior. Invalid and excessively large page numbers are refused
with 404 before auditing; page sizes and response fields are unchanged.

WSGI workers reuse healthy PostgreSQL connections for up to 60 seconds, controlled
by `DATABASE_CONN_MAX_AGE`. A health check precedes reuse. Local settings disable
persistence for runserver. The ASGI entry point sets `IRIS_SERVER_INTERFACE=asgi`
before Django initializes; base settings then disable persistence without
overwriting `DATABASE_CONN_MAX_AGE`. Each WSGI worker thread can hold one
connection; size the database connection limit for the deployed worker/thread
count. Set the lifetime to `0` to disable reuse. This is application configuration;
the load server inherits it without a test-only connection override. See
[Django's connection guidance](https://docs.djangoproject.com/en/6.1/ref/databases/#persistent-connections).

Results include contact details and status, never dates of birth, income, notices,
duplicate keys or staff verification data. Anonymized files are excluded. All
roles are checked server-side. Returned file IDs generate append-only `view`
events with empty metadata, using a single batch insert. The query function is
independently tested inside a PostgreSQL READ ONLY transaction.

## Migration

`households.0004_staff_search_indexes` installs the trusted PostgreSQL `pg_trgm`
and `unaccent` extensions, the module normalization function, five stored generated
search columns and six GIN indexes (phone uses its existing normalized column).
Existing records are backfilled; writes maintain the keys automatically. Runtime
search does not update household/member rows. Migration execution needs the
appropriate schema/extension privileges; normal search needs SELECT plus the
existing audit INSERT permission.

New extensions are installed in `public`. If either extension already exists in
another schema, the migration reuses it there without relocating shared objects.
The normalization function remains in `public`; it pins the installed unaccent
function and dictionary. The migration resolves the existing trigram operator
class while building the indexes and restores normal schema lookup at commit.
Dictionary changes require recomputing the generated keys in a migration. Reversal
removes derived search columns/indexes and the wrapper, preserves source records,
and retains the shared extensions for other modules.

## Issue #552 checklist

These tests were written alongside the search implementation and belong in the
same pull request as #553 and #554.

| Requirement | Evidence |
| --- | --- |
| Results below one second with 5,000 households | `test_search_performance.py` enforces the first authenticated response and sequential searches below one second; `test_search_load.py` also enforces the first real HTTP response below one second. |
| Partial names and accents | `test_search_query.py` checks partial names, case, accents, reversed name order and French ligatures. |
| Allowed/refused access for every role | API and access tests cover all roles, creator-only intake access, admin access to other-worker/unassigned files, anonymized-file refusal before pagination, and resume flags matching actual edit permissions. |
| Edge/error case | `test_search_api.py` covers invalid input, empty/no matches, page boundaries and failed auditing; query tests cover literal SQL/LIKE metacharacters. |
| API/database integration | `test_staff_searches_through_session_authentication` uses a real session, PostgreSQL household/member records and persisted audit events. |
| At least 70% changed-code coverage; domain at least 90% | Use the current CI coverage reports to assess the changed code and household domain; this guide does not retain run-specific coverage snapshots. |

Frontend `Search.test.tsx` and `searchApi.test.ts` additionally cover the bilingual
screen, exact debounce timing, request cancellation, pagination, errors,
API-driven screen access, keyboard clearing and accessibility.

## Repeatable verification

```powershell
docker compose exec -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest modules/households/tests modules/audit/tests -q
docker compose exec -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest modules/households/tests/test_search_performance.py -q --log-cli-level=INFO
docker compose exec -e DJANGO_SETTINGS_MODULE=iris.settings.test backend python -m pytest modules/households/tests/test_search_load.py -q --log-cli-level=INFO
```

pytest-django creates its own blank PostgreSQL database, normally `test_iris`,
applies migrations and removes it after the run. It does not seed the working
`iris` database or the preserved database from a local environment repair.
The explicit settings override replaces Compose's `iris.settings.local`, whose
development-only database lifetime is zero, with the same test settings as CI.

The performance fixture deterministically inserts 5,000 fictional households and
1–7 members per household, with accented names, different statuses, null emails,
member numbers, fictional phones and `example.test` email addresses. It uses the
existing person/address normalizers. Data setup and ANALYZE finish before timing.

The sequential check evaluates real querysets and authenticated API responses,
including pagination, serialization and audits. It covers broad/short names,
accents, each search field, literal wildcard characters and unmatched queries.
It checks search/API responses below one second and warm API p95 below 500 ms.
Correctness/count checks are separate from timing checks. The dataset fixture
only seeds and signs in; `cold_api_ms` explicitly measures the first API request
after URL configuration is loaded and asserts its duration below one second.

The HTTP check sends 300 requests at a scheduled 100 requests/second, using
session cookies and reused connections. Both the load client and loopback WSGI
server run in separate processes, so the client's GIL and coverage instrumentation
do not distort server runtime. The server refuses a database name without the
`test_` prefix. Its credentials/session cookie travel through stdin, never command
arguments or report output. Latency includes client queueing, response transfer
and JSON decoding. The client has 64 workers: 100 requests/second at 500 ms may
need 50 requests in flight, so the driver leaves concurrency headroom. Queue time remains included in the asserted latency.
The report separates client queue, HTTP request, application and SQL execution
timings, plus the maximum SQL statement count. SQL timing excludes connection
setup and transaction commit; those remain included in application/HTTP timing.
Diagnostic headers exist only on the disposable test server and contain numbers,
never SQL, credentials or personal data. The threshold stays p95 below 500 ms.
The first HTTP request is separately reported and required to finish below one
second; every request must succeed.

The benchmark uses the actual `iris.wsgi` entry point. It loads and validates URL
configuration during application startup, before accepting requests, as Django's
development server does. There is no HTTP warm-up or household query before the
first timed request. Process initialization is separate from request latency;
the first real search still includes authentication, queries, serialization and
audit persistence. Invalid routes prevent the WSGI application from starting.

The frontend checks access with an authenticated HEAD request to the search API
before rendering the screen. A refusal or failed check withholds the screen;
requests can be retried after a service failure. The API independently enforces
permissions on every subsequent search. This check returns no household data
and creates no view events. Other application routes keep their existing guards.

The frontend tests cover exact debounce timing, old-request cancellation, page
reset, empty/error/refused states, both languages, API-driven access, keyboard clearing
and axe accessibility checks. Search responses bypass HTTP caching; React Query
discards unused results and the existing auth provider clears them at sign-out.

The load-driver regression tests check that 32 requests can be in flight, client
queue and request timings are measured separately, and connections are closed
when the cold request fails. These are tests of the driver; the real HTTP test still exercises session
authentication, database reads, serialization and audit writes.

A real HTTP regression also sends two searches over the same HTTP connection and
checks the PostgreSQL backend PID in a test-only response header. It fails when
`DATABASE_CONN_MAX_AGE=0`, independently of machine speed. A separate subprocess
test checks that the ASGI entry point disables WSGI connection persistence.

## Remaining environment checks

Run the repeatable checks above and use their current output and CI artifacts.
The performance tests attach numeric reports to structured log records and to
failed assertions. This guide records requirements and commands, without storing
benchmark snapshots, test totals, coverage results or PR iteration history.

Repeat the load test on staging with its actual worker and database connection
configuration before claiming the deployment meets NFR-04. First page load below
three seconds on a representative phone/4G connection and manual browser/contrast
checks remain deployment/device checks; API timing and jsdom tests do not
establish those results.

Search results disclose household details, so BR-HH-AUDIT-001 requires auditing
returned files before disclosure. Keep those events until an audit/privacy policy
defines any retention, archival or change to the disclosure logging requirements.

The future full household page belongs to US-64. Search links only to the existing
walk-in draft screen when that action is applicable.
