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

Intake workers and administrators share access to every non-anonymized household,
regardless of creator, including unassigned files. This follows the team-pack
permission matrix. The actor is checked by `search_for_staff` before searching;
the object scope is applied before counting or pagination. The API returns a
`can_resume` boolean from the same policy used for editing, and the frontend
renders it without recomputing permission from household status or channel.

Numeric pages use a PostgreSQL window count to obtain the total and page in one
SELECT, rather than running the search twice for a separate COUNT and results.
Authentication and auditing still run normally: a matching request uses four SQL
statements in the load report. The optional `page=last` shortcut retains DRF's
count-first behavior. Invalid and excessively large page numbers are refused
with 404 before auditing; page sizes and response fields are unchanged.

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

The immutable normalization wrapper pins `public.unaccent`. Changes to that
dictionary require recomputing the generated keys in a migration. Reversal
removes derived search columns/indexes and the wrapper, preserves source records,
and retains the shared extensions for other modules.

## Issue #552 checklist

These tests were written alongside the search implementation and belong in the
same pull request as #553 and #554.

| Requirement | Evidence |
| --- | --- |
| Results below one second with 5,000 households | `test_search_performance.py` enforces the first authenticated response and sequential searches below one second; `test_search_load.py` also enforces the first real HTTP response below one second. |
| Partial names and accents | `test_search_query.py` checks partial names, case, accents, reversed name order and French ligatures. |
| Allowed/refused access for every role | API and access tests cover all roles, cross-creator/unassigned access, anonymized-file refusal before pagination, and resume flags matching actual edit permissions. |
| Edge/error case | `test_search_api.py` covers invalid input, empty/no matches, page boundaries and failed auditing; query tests cover literal SQL/LIKE metacharacters. |
| API/database integration | `test_staff_searches_through_session_authentication` uses a real session, PostgreSQL household/member records and persisted audit events. |
| At least 70% changed-code coverage; domain at least 90% | Added/modified executable lines: backend 100% (176/176), frontend 97.10% (67/69). Household domain coverage is 93% for person validation and 100% for address validation; no domain rules changed. |

Changed-line figures compare the candidate code, including new source files, with
the PR's original base `be4e22a`, using executable lines recorded by coverage.py
and V8. They differ from total coverage: 93.61% for the backend and 94.55% total
frontend line coverage. Generated declarations, migrations and non-executable
lines do not contribute to the changed-line denominators.

Frontend `Search.test.tsx` and `searchApi.test.ts` additionally cover the bilingual
screen, exact debounce timing, request cancellation, pagination, errors, role
guards, keyboard clearing and accessibility.

## Repeatable verification

```powershell
docker compose exec backend python -m pytest modules/households/tests modules/audit/tests -q
docker compose exec backend python -m pytest modules/households/tests/test_search_performance.py -q -s
docker compose exec backend python -m pytest modules/households/tests/test_search_load.py -q -s
```

pytest-django creates its own blank PostgreSQL database, normally `test_iris`,
applies migrations and removes it after the run. It does not seed the working
`iris` database or the preserved database from a local environment repair.

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
need 50 requests in flight, so the old 16-worker cap could queue requests before
they reached the server. Queue time remains included in the asserted latency.
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

The frontend tests cover exact debounce timing, old-request cancellation, page
reset, empty/error/refused states, both languages, role guards, keyboard clearing
and axe accessibility checks. Search responses bypass HTTP caching; React Query
discards unused results and the existing auth provider clears them at sign-out.

The load-driver regression tests check that 32 requests can be in flight, client
queue and request timings are measured separately, and connections are closed
when the cold request fails. The concurrency case fails with the old 16-worker
limit. These are tests of the driver; the real HTTP test still exercises session
authentication, database reads, serialization and audit writes.

## Scope and remaining environment checks

The latest provided GitHub CI run, for commit `2dc1e17`, passed 944 backend tests
and failed the HTTP load test. Its first request passed at 32.09 ms, but warm
p95 was 790.89 ms against the unchanged 500 ms target. Application p95 was
722.73 ms and SQL execution p95 302.64 ms; client queue p95 was 52.63 ms.
All 300 responses succeeded. That run's total backend coverage was 93.47%.

Profiling locally showed pagination repeating the search for the count and page.
The follow-up combines those reads with a window count and adds a regression
requiring one household SELECT for a normal page. It also tests invalid and
overflowing page numbers and preserves the last-page shortcut. The dataset,
100 requests/second rate, 300-request count and response-time limits are unchanged.

Local verification after this optimization on 2026-11-07: all 951 backend tests
passed with 93.61% total coverage. First API response: 14.67 ms; API maximum:
25.44 ms. First real HTTP response: 48.39 ms. The HTTP load run completed all
300 responses with p95 81.73 ms, maximum 119.84 ms, client queue p95 0.29 ms,
application p95 46.24 ms and SQL execution p95 21.89 ms. At most four SQL
statements were captured per request, including authentication and auditing.

Ruff, formatting, mypy, all three module-boundary contracts and API type/schema
consistency passed locally for this optimization. The API contract and frontend
code are unchanged; their preceding local verification passed 435 frontend tests
with 94.55% total line coverage, TypeScript, ESLint and the production build.
These are local results, not a passing GitHub CI run. CI must verify the new
optimization after committing and pushing. No Docker, database connection or CI
settings were changed.

The local benchmark establishes behavior on the tested development machine.
Repeat it on staging with its actual worker configuration before claiming the
deployment meets NFR-04. First page load below three seconds on a representative
phone/4G connection and manual browser/contrast checks remain deployment/device
checks; API timing and jsdom tests do not establish those results.

The future full household page belongs to US-64. Search links only to the existing
walk-in draft screen when that action is applicable.
