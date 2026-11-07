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
| Results below one second with 5,000 households | `test_search_performance.py` evaluates real queries and authenticated API responses against 5,000 households. |
| Partial names and accents | `test_search_query.py` checks partial names, case, accents, reversed name order and French ligatures. |
| Allowed/refused access for every role | `test_search_api.py` allows intake workers/admins; refuses beneficiaries, store staff/managers, anonymous callers and inactive staff. |
| Edge/error case | `test_search_api.py` covers invalid input, empty/no matches, page boundaries and failed auditing; query tests cover literal SQL/LIKE metacharacters. |
| API/database integration | `test_staff_searches_through_session_authentication` uses a real session, PostgreSQL household/member records and persisted audit events. |
| At least 70% changed-code coverage; domain at least 90% | The focused household/audit run passed 175 tests with 93.81% coverage. Household domain coverage is 93% for person validation and 100% for address validation. Changed frontend source files have 92.31–100% line coverage. No domain rules were changed. |

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
Cold first-request initialization is reported separately.

The HTTP check sends 300 requests at a scheduled 100 requests/second, using
session cookies and reused connections. Both the load client and loopback WSGI
server run in separate processes, so the client's GIL and coverage instrumentation
do not distort server runtime. The server refuses a database name without the
`test_` prefix. Its credentials/session cookie travel through stdin, never command
arguments or report output. Latency includes client queueing, response transfer
and JSON decoding. The threshold stays p95 below 500 ms. Startup is reported
separately, and every request must succeed.

The frontend tests cover exact debounce timing, old-request cancellation, page
reset, empty/error/refused states, both languages, role guards, keyboard clearing
and axe accessibility checks. Search responses bypass HTTP caching; React Query
discards unused results and the existing auth provider clears them at sign-out.

## Scope and remaining environment checks

Local verification on 2026-11-07: all 915 backend tests passed (93.30% total
coverage), and all 431 frontend tests passed (94.55% line coverage). The latest
full-suite HTTP benchmark offered 100 requests/second across 5,000 households:
300 successful responses, p95 87.78 ms, maximum 129.82 ms. Cold HTTP initialization
was reported separately at 1,196.69 ms, exceeding one second. The warm checks do
not establish a first-request time below one second. Sequential query maximum
was 14.58 ms and authenticated API maximum was 31.10 ms. These numbers describe
this local run.

The local benchmark establishes behavior on the tested development machine.
Repeat it on staging with its actual worker configuration before claiming the
deployment meets NFR-04. First page load below three seconds on a representative
phone/4G connection and manual browser/contrast checks remain deployment/device
checks; API timing and jsdom tests do not establish those results.

The future full household page belongs to US-64. Search links only to the existing
walk-in draft screen when that action is applicable.
