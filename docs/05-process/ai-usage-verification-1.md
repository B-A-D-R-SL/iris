<!-- AI contribution: 50% or more AI-generated -->

# AI verification history, part 1

[Contribution inventory and declaration rules](../../AI_USAGE.md).

### US-25 Duplicate checking and tests (#479, #478)

- **AI help:** ChatGPT helped build the search, submission service, locks, staff API, translations, migration, tests, and docs.
- **Approved policy:** suspended files count as possible duplicates; files whose `expires_at` is in the past do not. Active intake workers and admins share non-anonymized walk-in files, including another worker's and unassigned files. `created_by` records provenance. Approval stays in US-18.
- **Initial checks:** 803 backend tests passed, with 93.21% coverage. The 120 household tests reached 93.49%, including six tests with two database connections. Domain coverage exceeds 90%. Lint, types, module rules, migration checks, schema generation, eight API-generator tests, and TypeScript checks passed.
- **Fixes:** migration 0004 updates old search keys. Rollback keeps those keys; names and addresses stay unchanged. The API keeps its existing status type name. The development database was not migrated.
- **PR review:** ChatGPT helped split the concurrency test, record submission actors, log outcomes after commit, and add the 15-person boundary test. Draft, submission and serializer checks share the household-size RuleSet; its approved seed default is 15 including the holder, with tests at a configured limit of 3 and for missing configuration (BR-HH-001). A public lock-and-check context keeps the caller's write in the transaction. French status labels follow the glossary.
- **Review checks:** 825 backend tests passed at 93.34% coverage; 142 household tests passed at 94.13%. All six concurrency cases, lint, formatting, typing, module boundaries, migration checks, API generation, eight generator tests, and TypeScript checks passed.
- **RuleSet update:** the full backend suite passed 840 tests at 93.38% coverage. Household and rule tests cover configured limits, missing configuration and idempotent seeding. Existing databases need `python manage.py seed_rules`; existing versions are kept.
- **Policy checks:** 303 household and RuleSet tests passed, including expiry boundaries, suspended candidates and staff permissions. Ruff lint and formatting, type checks for the changed views, queries and services, and diff checks passed.
- **Main integration:** ChatGPT resolved the search, invitation and settings conflicts while keeping the approved household rules. Search excludes anonymized files before counts, pages and audits; resume flags follow the walk-in edit rule. A merge migration joins the search and duplicate-check branches. API types were regenerated.
- **Merge checks:** 1,240 backend tests and 443 frontend tests passed. Ruff, backend/frontend type checks, frontend lint, module boundaries, migration checks, API types and diff checks passed.
- **CI load test:** ChatGPT found that the benchmark server's 10-connection queue could overflow under the 64-worker driver. A Linux regression failed with the original queue. The test server now queues 128 connections; the 100 requests/second and 500 ms p95 targets stay unchanged. Failed assertions include the complete timing report.
- **Load-test checks:** 1,241 backend tests passed with 93.95% coverage. All 16 load-server/client checks passed in a two-CPU Linux container. Ruff, targeted type checks and diff checks passed.
- **Final review fixes:** duplicate advisory locks use a positive, configurable wait limit and restore the caller's timeout after acquisition. A timeout rolls back before returning a generic 503. Missing or invalid size rules use the same translated response and a privacy-safe log event. Tests now use real deactivated sessions and verify transaction boundaries without Django's test wrapper. Staff access tests are grouped in `test_api.py`; repeated duplicate cases were removed.
- **Final checks:** 1,268 backend tests passed with 93.94% coverage, including 490 household, RuleSet and configuration tests. Ruff, backend/frontend type checks, module boundaries, migration checks, API drift checks, eight generator tests and diff checks passed.
- **Access-test follow-up:** ChatGPT split the API, query and service tests by operation, keeping all 64 staff-access cases. All 85 access tests and 1,268 backend tests passed; coverage stayed at 93.94%. Ruff, complexity checks, mypy and diff checks passed. The PR description and verified issue checkboxes were updated.
- **Search-load follow-up:** after CI exceeded the 500 ms p95 target, ChatGPT inspected query plans and removed a redundant household ID subquery that caused a second table scan. A regression failed on the old query and passed on the direct predicate. All 85 focused search tests passed. The two-CPU Linux HTTP tests passed at the unchanged 100 requests/second and 500 ms limits (56.71 ms p95); Ruff, mypy, module boundaries and diff checks passed.
- **Shared-access restoration:** following [MassPaol's confirmation with Mark](https://github.com/B-A-D-R-SL/iris/pull/660#issuecomment-6730240599), ChatGPT restored shared staff access in queries, resume permissions, tests and docs. Cross-worker submissions preserve the original creator and record the submitting actor. Anonymized files, inactive accounts and nonstaff roles remain refused. All 1,266 backend tests passed at 93.97% coverage; Ruff, mypy, module boundaries, migration checks, API drift and diff checks passed.

### US-63 Household search and tests (#552, #553, #554)

- **What the AI produced:** under Mark's direction, the staff search API,
  normalized search columns and indexes, migration, audit integration and
  French/English search screen with pagination and a typing delay. Search covers
  partial or accented member names, email, phone, address and member number.
  ChatGPT also helped write tests, generated API types and documentation.
- **Owner's decisions:** Mark requested the backend before the frontend and
  required the existing Docker setup to be preserved. For safety, he reviewed
  the database connection, backup and migration.
- **Verification:** Mark reviewed the implementation, saved-draft flow, local
  database, search fields and household/member links. Automated checks cover role
  permissions, shared staff access, anonymized-file refusal, read-only queries,
  API/database integration, accents, pagination, migration reversal, audit failure
  handling, response validation and search authorization in the frontend. Lint,
  formatting, type checks, module boundaries and migration checks are part of the
  verification workflow. Current test and coverage results belong in CI output;
  this record does not retain numerical performance or coverage snapshots for US-63.
- **Problems found and corrections:** normalized search columns and trigram
  indexes address broad searches, WSGI startup validates routes before accepting
  requests, and healthy database connection reuse avoids repeated connection
  setup. The ASGI entry point identifies its server interface before Django loads
  settings; settings disable persistence without rewriting the configured lifetime.
  Test diagnostics use structured logging; the subprocess JSON protocol remains
  separate. Existing PostgreSQL extensions are reused in their installed schemas.
  Search access is decided by the API, including the frontend screen's access
  probe. Mark confirmed shared staff access and accepted the central AI inventory's
  size. Staging and phone/4G checks remain deployment verification. Repeatable
  commands and thresholds are in the [verification guide](../../docs/guides/household-search.md).


### T-01.04.3 Invitation password page (#431)

- **What the AI produced:** under Leon's approved plan, the public
  `/invitation/:token` password-and-confirmation page, generated-type API
  helper, French/English messages, additional page/helper tests and updated
  API/module documentation. Confirmation stays in the browser; the backend
  remains responsible for token validation and the full password policy.
- **Owner's decisions:** successful anonymous acceptance opens `/sign-in`.
  An existing session is preserved, with completion guidance to use the
  existing sign-out control before signing into the new account. Issuing
  screens, email delivery and approval workflows remain in their own stories.
- **Initial implementation verification:** all **395 frontend tests across 28 files** passed,
  including 15 page cases and 21 API-helper cases. Added executable frontend
  lines have **100% coverage** (87/87); overall frontend line coverage is
  **94.37%**. The full run used two workers and a 15-second per-test timeout
  after existing listing cases exceeded the default five seconds; no tests
  were skipped or assertions changed to accommodate this. Frontend type
  checking, ESLint, Prettier and the production build passed.
  Disposable Chromium checks passed in French and English at
  360px and 1024px, including expiry/retry, CSRF bootstrap, live translation,
  navigation to sign-in and signed-in completion. Browser API responses were
  mocked; these checks did not write database data or replace #430's backend
  API-to-database tests.
- **Problems found and corrections:** focused tests exposed missing explicit
  `aria-invalid` on password controls for backend field errors and an ambiguous
  test status query. Both were corrected. Backend field text is hidden after
  a language switch until the visitor submits again; entered passwords remain.
- **PR #657 focus correction:** under Leon's direction, replaced error-object
  focus dependencies with a counter that advances only on failed submissions.
  Editing, blur validation and language changes keep the visitor's focus;
  repeated local or API failures still focus the summary. The temporary
  reproduction failed before the fix and passed afterward. All **38 invitation
  tests** passed (17 page cases and 21 API-helper cases), including two new
  focus regressions and a language-switch focus assertion. ESLint, Prettier,
  TypeScript and the production build passed for this correction.
- **PR #657 pre-merge corrections:** under Leon's approved scope, renamed the
  role/API tests to `test_api.py` and updated the import-boundary exception;
  added event-only backend logs after commit and frontend failure events;
  documented size exceptions for the shared references and test-registration
  callbacks. `.coderabbit.yaml` excepts only the file length of the two complete
  locale catalogs, without changing function or complexity limits. The accounts
  README documents the new commit-time events. Intentional translated password
  validation feedback remains available to users.
- **Review-fix verification:** 132 existing accounts/invitation-rule cases and
  all four new logging tests passed. The new tests inspect raw event records,
  verify deferred emission and rollback suppression, and reject recipient or
  secret data in logs. All 45 focused frontend tests passed with one worker and
  a 15-second test timeout, including real logger-output privacy assertions,
  the invitation page and translation parity. Ruff, mypy, module boundaries,
  ESLint, Prettier, TypeScript, production build, YAML parsing and individual
  function/test size checks passed. The four new logging cases were rerun with
  `iris.settings.test` after correcting their per-phase log-capture fixture.

- **PR #657 remaining error/size checks:** restored the ledger's adjacent size
  justification and extracted persisted-account assertions while retaining the
  API-to-database-to-sign-in path. Django password codes and safe parameters now
  survive service wrapping; approved invitation/password translations replace
  arbitrary exception text. Unknown codes and field names receive generic
  feedback. The French catalog was compiled from the updated `.po`. Unexpected
  page failures log only a fixed event, and handled API errors are not logged
  twice. The accounts README documents this behavior.
- **Final targeted verification:** all 129 invitation API, service, logging,
  error-mapping and RuleSet cases passed with `iris.settings.test`, including
  37 new mapping/privacy cases. All 47 focused frontend cases passed (19 page,
  21 helper, one logger and six translation cases), including two new page-error
  regressions. Ruff, mypy, module boundaries, ESLint, Prettier, TypeScript,
  production build and translation-catalog checks passed. Individual changed
  functions/tests satisfy 50 lines; the main integration test and its account
  helper have assertion-inclusive complexity scores of nine and eight.

### T-01.04.2 Invitation model, services and acceptance API (#430)

- **What the AI produced:** under Leon's approved plan, the Invitation model
  and incremental migration, secure token creation, atomic acceptance, the
  public API and translated errors, the invitation RuleSet schema/default,
  regenerated API types and documentation aligned with new accounts only.
- **Owner's decisions:** an existing active or inactive account is never
  overwritten. Tokens encode 32 random bytes and only their SHA-256 hash is
  stored. The saved expiry comes from `invitations.expires_after_days`, whose
  initial value is seven days. Acceptance does not sign in or switch sessions.
  Issuing screens, email delivery and other stories' approval workflows remain
  separate; the public password page is #431.
- **Verification:** all 88 invitation backend cases passed, including the
  #429 tests and additional malformed-configuration, database-constraint,
  rollback and competing-invitation cases. Ruff, mypy, module-boundary checks,
  Django system/migration checks, OpenAPI validation, API declaration drift
  checking and the frontend TypeScript/production build passed.
  The full backend suite passed **816 tests** with **92.96% overall coverage**.
  Added executable lines in changed production files have **97.42% coverage**
  (151/155); the modified RuleSet domain module has **100% coverage**.
  The local invitation migration applied cleanly. The idempotent rule seed
  added invitation version 1 and a previously missing `listing_posting`
  version 1 without rewriting existing versions.
- **Problems found and corrections:** the local backend image does not contain
  GNU `msgfmt`; the existing host Babel compiler produced the tracked French
  catalog without introducing a runtime dependency. Email uniqueness races
  are translated only for the known email constraints, and the tests verify
  that unrelated database failures roll back and propagate.

### T-01.04.1 Invitation acceptance tests (#429)

- **What the AI produced:** under Leon's approved plan, executable service,
  API-to-database, RuleSet and public-page tests, generated invitation inputs,
  deterministic clock fixtures and narrowly scoped test import exceptions.
- **Owner's decisions:** invitations create new accounts only; existing active
  and inactive accounts must never be overwritten. The initial invitation
  lifetime is seven days, configured as `invitations.expires_after_days` in
  RuleSet. Invitation issuing screens, email delivery, partner approval and
  household approval remain with their respective stories.
- **Verification at the tests-first commit:** all 74 backend cases collected
  without importing absent invitation symbols at module load. They failed
  because the Invitation model, acceptance endpoint and invitation RuleSet did
  not exist yet; all 11 frontend cases failed because the route/page did not
  exist. The existing 75 accounts/rules backend tests and 29 sign-in and
  translation frontend tests pass. Mypy, frontend type checking, Ruff, ESLint,
  formatting and module-boundary checks pass for the test changes.
- **Follow-up verification:** #430 supplied the backend implementation and
  passed 88 invitation cases. #431 supplied the public page and passed its
  original 11 cases plus four added page cases and 21 API-helper cases.
  No test is skipped or replaced with a fake implementation. Story PR checks
  and teammate review remain required before closing the task.

### T-09.62.3 Audit search API and screen (#550)

- **AI assistance:** ChatGPT/Codex helped write and review code for the
  admin-only search API, filters, pagination and bilingual screen, including
  implementation and tests, under Reuven's direction.
- **Verification:** The search integration tests were run against a temporary
  PostgreSQL 17 instance. Frontend tests, type checking, lint, build and schema
  generation were run locally; teammate review remains outstanding.
- **Limits:** Search accepts household and staff UUIDs rather than names. The
  audit service and accounts work live on the parent story branch.

At least half of the AI-assisted features need an example here. For each one:

- **Feature or task:** issue number and title
- **What the AI produced:** files, commit or pull request
- **How we verified it:** the automated tests or the review comment that checked it
- **Problems found and corrections:** what was wrong or rejected, and what we changed

### T-09.62.1–2 Audit tests and service (#548, #549)

- **What the AI produced:** the append-only AuditEvent model, public `record()` service, PostgreSQL trigger migrations, concise module README, and unit/integration tests. Existing accounts code was reused; #550 is excluded.
- **How we verified it:** 56 audit tests and all 185 backend tests passed in Docker with PostgreSQL. Audit coverage was 100%; total backend coverage was 89.30%. Ruff, mypy, all three module-boundary contracts, Django checks, and migration consistency checks passed. The current database migrated successfully; trigger reversal and reapplication were tested only on the isolated test database.
- **Problems found and corrections:** tightened target-type validation to reject a trailing newline and recorded the change in a migration. Local dependency caches required source-directory targets for lint and typing checks. No databases or volumes were recreated.
### T-02.12.3 Become a partner page (#446)

- **AI assistance:** ChatGPT helped write and review the form, API integration, translations and tests using the existing requirements and partner application API.
- **Verification:** the frontend suite passed 265 tests, the partner application backend API suite passed 61 tests, and a fictional application was submitted through the local frontend and backend. Teammate review is pending.
- **Dependency:** the backend is on the open US-12 pull request, #618.
### US-16 Eligibility engine (#457)

- **AI contribution:** I first designed the eligibility logic and wrote
  the initial pseudocode myself. I then used ChatGPT to help translate
  my pseudocode into working code, including the LICO rule, decision model,
  service, tests, migrations, and documentation. I reviewed and refined
  the implementation throughout development.
- **Verification:** 75 eligibility tests and 388 backend tests passed locally.
  Domain coverage reached 100%; Ruff, mypy and architecture checks passed.
- **Corrections:** Fixed PostgreSQL ArrayField configuration, type-checking
  and lint issues; added adult-count completeness validation and negative tests.
- **Outstanding:** Real household/notice integration, audit events,
  and end-to-end API verification.

### SET-18 Seed data generator (#409)

- **What the AI produced:** the `seed` command, the fixed fictional plan (seed 18), household and reservation tables taken from the published schema, and `docs/04-data/seed-data.md`.
- **How we verified it:** `test_seed_plan` checks the agreed counts, status spread, stock limits, and fictional contact details. `test_seed` runs `manage.py seed` on an empty database, checks 1 admin, 2 intake workers, B.A.D.R. plus 4 partner stores, 50 households, 30 listings, and 40 reservations, then runs it again and checks that edited rows are kept.
- **Problems found and corrections:** household and reservation models did not exist yet, so the seed could not insert those rows. The tables follow `docs/03-design/database-schema.md`. Registration and pickup workflows are still owned by their own stories.

### SET-33 Colour prototypes and design docs (#651)

- **Firas's direction:** keep the Step 4 repository file names so existing links still work, restore later-release grayscale exports, and replace the Theme section in `design-system.md` with the Foundations token table and status map. The wiki and the pull request stay with Firas.
- **What the AI produced:** the renames and restores under `docs/03-design/mockups/`, and the Theme section (token table, status colour map, colour rules, Foundations link).
- **How we verified it:** the mockups folder matches the Step 4 file list; later-release PNGs match `HEAD`; the Theme hex values and Mantine shade names match the Foundations export.
- **Problems found and corrections:** the first exports used Figma page names (`W4 · …`, `S2 · …`). Step 4 needs the old names (`Staff Review-partnership-application.png`, `Store - Confirm a pickup.png`, …), so the coloured files were copied onto those names and the Figma-named copies were removed.

### FIX-15 Seed command boundary and household expiry (#641)

- **Firas's direction:** keep the seed's direct writes as a documented exception rather than routing fictional rows through services that cannot create those states, and move the expiry rule into the households domain so US-18 can reuse it. Edits that would collide with open pull requests were left out (the households README).
- **What the AI produced:** the exception note at the top of `seed.py`; the import-linter contract "Only the seed command imports module models"; `households/domain/expiry.py` (calendar months, approved expiry, expiry per status); `test_expiry.py`; the seed changes; and the matching `test_seed.py`, `architecture.md` and model edits.
- **How we verified it:** 881 backend tests passed with 93% coverage; ruff, mypy, lint-imports (4 contracts kept) and `makemigrations --check` were clean. `manage.py seed` on a local database still gave 50 households, 30 listings and 40 reservations. Trial merges against the open pull requests found no new conflicts in code.
- **Problems found and corrections:**
  - CodeRabbit flagged a minimum-month module constant in `domain/` and a stale pull request link here; both were removed or updated.
  - MassPaol's review found that approved demo files lasted 12 months and 30 days, because the months were counted from the seed date instead of the backdated approval. `test_seed.py` built its expected value the same way, so it passed anyway. The seed now counts from the approval date, and the test fails on the old behaviour.
  - Months were counted on the UTC calendar: 30 January 22:00 in Montreal gave 27 February instead of 28 February. The seed now passes Montreal local time, and a test covers that case.
  - The seed caught every `ValueError` as a bad month count; the domain now raises `InvalidApprovedMonths` and only that is caught. Tests were added for a missing `file_validity` rule and a broken month count.
  - The contract covered `iris` only; it now covers `adapters` too. The three status names were duplicated in the domain and the model; `Household.Status` now builds them from the domain constants.

### T-01.01.1 Sign-in and sign-out tests (#423)

- **Leon's direction:** implement the approved test plan and use `/staff/households` as the staff landing path, as updated in US-01.
- **What the AI produced:** expanded account API tests to exercise real sign-in, current-user lookup, and sign-out for all five roles; added a shared-browser-session logout test; expanded the app routing test to cover every role's landing area.
- **How we verified it:** all 34 focused account tests and 54 focused app/navigation tests passed. The accounts module reached 100% coverage in the focused backend run; Ruff, ESLint, TypeScript, and formatting checks passed. Only test files changed for this task, so changed-production-code coverage does not apply.
- **Problems found and corrections:** the first routing expectations used a generic staff path; Leon supplied the updated `/staff/households` path from US-01, and the tests were corrected before the screen was built.
- **Follow-on screen work:** the form, localized errors, and sign-out controls were delivered in T-01.01.3.

### T-01.01.3 Sign-in screen and session handling (#425)

**Leon's direction and AI output:** Leon approved the frontend plan and specified `/staff/households` for staff. The AI built a bilingual sign-in form, CSRF-aware allauth requests, a conditional MFA code step, role redirects, a TanStack Query session provider, and sign-out controls. The `/api/me/` type comes from generated OpenAPI declarations; staff MFA enrollment belongs to US-09 (#436). The work is in [US-01 PR #610](https://github.com/B-A-D-R-SL/iris/pull/610).

**Verification, problems and corrections:** The first 183 frontend tests passed with 92.96% overall statement coverage; the sign-in page reached 93.61%. Review found an inaccessible live session after a failed profile lookup, stale cached data after sign-out, and missing deep-link handling; the AI added a profile-only retry, cache clearing, redirects, and tests. After these fixes, 202 frontend tests, TypeScript, ESLint, Prettier, and the build passed. Earlier corrections fixed a TypeScript parameter property, Fast Refresh lint, and translation-key shape.

### T-01.01.2 User model and authentication (#424)

**Leon's direction and AI output:** Leon approved the custom-user plan and reviewed the migration impact. The AI built `accounts.User`, the allauth adapter with a shared five-attempt lockout, PostgreSQL `AuthCache`, the rate-limited admin form, the `/api/me/` endpoint and serializer, and account tests. It also added `UserFactory` and generated `fr | en` API types in [US-01 PR #610](https://github.com/B-A-D-R-SL/iris/pull/610).

**Verification, problems and corrections:** The backend suite initially passed 129 tests against PostgreSQL; after review fixes, 135 passed. Ruff, mypy, import-linter, and API type drift checks passed. Leon backed up and recreated his local database after the custom-user migration changed its dependency order, then verified the admin, nine rule types, seven LICO sizes, and B.A.D.R. Store. Startup exposed a missing Argon2 lockfile entry; the AI regenerated `backend/uv.lock`. Review also found a dynamic cache-table SQL string and an admin lockout bypass; static SQL and a shared admin authentication form fixed them.

### T-00.01.4 Categories reference module (#377) and SET-14 Module skeletons (#405)

- **What the AI produced:** ChatGPT assisted with the Categories Django model, migration, services, queries, pure domain rules, REST API, seed command, React page, bilingual translations, tests, and reference documentation. It also assisted with scaffolding the 15 Django modules, registering their applications, documenting their interfaces, and configuring architectural dependency checks.
- **Developer involvement:** Reviewed GitHub acceptance criteria and Iris architecture requirements, executed the implementation and verification commands, identified gaps in the architectural enforcement, and validated the corrected configuration.
- **How we verified it:** The initial full regression run passed 91 backend tests with 86.86% coverage and 172 frontend tests with 94.32% statement coverage. Ruff, mypy, ESLint, TypeScript, migrations, frontend build, API type generation, and dependency security audits passed. All 15 module READMEs were checked for ownership, public-function, and audit-event sections.
- **Problems found and corrections:** The original Import Linter configuration allowed unauthorized cross-module imports through any public services or queries. Replaced the generic exceptions with the architecture's approved dependency whitelist. A negative test confirmed that Categories cannot import Stores services, a positive test confirmed that Listings can import Categories services, and the clean project passed all three Import Linter contracts.
- **Remaining verification:** Final regression checks after the documentation updates, GitHub Actions results, and teammate review are pending. The remaining modules are intentionally scaffolds; their business functionality belongs to separate backlog tasks.

### SET-15 OpenAPI and TypeScript generation (#406)

- **What the AI produced:** health response schema metadata and regression tests, a pinned openapi-typescript generator and generated declarations, temporary-copy drift tests, an added CI drift check, a generation guide, and the reviewed team API conventions document. The draft's conventions and endpoint catalog are preserved with implementation status and unresolved decisions identified.
- **How we verified it:** 13 focused backend tests and Ruff checks passed. Isolated frontend validation with pnpm 10.34.6 and TypeScript 6.0.3 passed type checking, ESLint, formatting, all 11 Vitest tests, production build, and the generation/drift regression test. Schema export passed validation. Existing lockfile entries and CI checks were compared and remain unchanged. Documentation validation checked all 10 convention rows and 69 endpoint rows against the supplied draft, plus Markdown formatting and local links/anchors.
- **Problems found and corrections:** openapi-typescript 7.13.0 requires a TypeScript 5 peer, so 6.7.6 was selected and tested without peer overrides or a compiler downgrade. Vitest initially collected the Node-only regression test; its filename was changed without altering Vitest configuration. The local backend environment uses Python 3.14.8 rather than CI's 3.13; CI execution and PostgreSQL-dependent backend tests remain to be verified. PR #604 review fixes add explicit UTF-8 Python output, remove the default subprocess buffer limit, and skip only symbolic-link creation on Windows. A schema-stdin mode supports generation and drift tests across the separate Docker containers; the README now lists both API checks and the command to copy regenerated declarations back to the checkout. Regression coverage includes Unicode schemas larger than 1 MiB through both Python and stdin.
- **PR #604 review verification:** all eight generator tests passed with local Python, and seven passed with a piped schema (the Python-only export test is skipped in that mode). Generated declarations match the validated schema. Four backend schema tests, all 11 Vitest tests, TypeScript checking, ESLint, and formatting of changed frontend files and the generation guide passed. Validation used Python 3.13 and Node 22.23.2; CI uses Node 24. Native Windows and the full container workflow were not run; the Docker daemon was stopped.
- **CI follow-up:** updated only `certifi` from 2026.7.22 to 2026.10.19 to address the dependency audit finding PYSEC-2026-4320. Merged current `main` so the PR base matches the newly introduced commit-policy workflow, and reworded the ten older SET-15 commit subjects to the required ID-first format while preserving each commit's tree, authorship, and merge structure. The original branch head is retained locally as `backup/SET-15-before-ci-fix-b9933c2`. Removed the empty `.github/workflows/story-test-task.yml`, which GitHub rejected before running any jobs. The locked dependency audit reports no known vulnerabilities after the update; 13 focused backend tests, all eight generator tests, schema drift checking, and Ruff lint/format checks passed after the merge.

### T-00.01.1 Backend project (#374)

- **What the AI produced:** the Django 6.1 backend using Python 3.13 and uv, environment-specific settings (`base`, `local`, `test`, `production`), configuration for Django REST Framework, django-allauth, drf-spectacular, Procrastinate, and PostgreSQL, along with automated tests and Ruff/mypy configuration.
- **How we verified it:** ran pytest, Ruff, mypy, and Django system checks. Verified PostgreSQL connectivity, successful database migrations, API documentation routing, and local Django startup.
- **Problems found and corrections:**
  - Django initially failed to load the secret key correctly. Fixed the environment configuration using `django-environ`.
  - PostgreSQL needed to be configured locally. Created a PostgreSQL 17 Docker container and successfully applied the database migrations.
  - The SQLite fallback was incompatible with Procrastinate's PostgreSQL-specific migrations. PostgreSQL is now required for all environments.
  - Fixed Ruff import-order warnings and reran the backend checks.

### T-00.01.2 Frontend project (#375)

- **What the AI produced:** the React 19 frontend with TypeScript, Vite, Mantine UI, React Router, TanStack Query, and French/English internationalization. Also generated the homepage, backend health-check integration, automated tests, and frontend quality tooling.
- **How we verified it:** four Vitest tests passed before hardening, covering French as the default language, English switching, successful backend communication, and unavailable backend handling. Production build, ESLint, and Prettier checks also passed before hardening.
- **Problems found and corrections:**
  - Mantine required `window.matchMedia`, which was unavailable in the test environment. Added a mock to the test setup.
  - Configured the Vite API proxy to allow React to communicate with Django.
  - Resolved ESLint/Prettier compatibility issues and corrected formatting.
  - Enabled strict TypeScript type-checking in both the application and Node configuration files.

### T-00.01.3 Docker Compose and README (#376)

- **What the AI produced:** the five-service Docker Compose environment (Django, React, PostgreSQL, Azurite, Mailpit), backend and frontend Dockerfiles, automatic migrations, development administrator creation, SMTP mailer adapter, integration tests, and updated README documentation.
- **How we verified it:** all five containers started; PostgreSQL, migrations, health endpoint, development admin authentication, and SMTP delivery were verified. Eight backend and four frontend tests passed before hardening, and 13 backend tests passed after adding observability tests. Additional formatting and typing verification remains in progress.
- **Problems found and corrections:**
  - pnpm attempted to reinstall dependencies without an interactive terminal. Moved dependency installation into image builds and reused the installed packages.
  - The frontend homepage timed out through host port `5173`. Changed the host port to `5174`.
  - Windows frontend bind mounts slowed page loading. Replaced them with Docker Compose Watch.
  - Fixed Ruff and mypy issues and excluded generated pnpm caches from formatting.
  - Azurite's SDK integration is deferred because the requested API version is unsupported by the emulator.
  - Updated the README with the Docker development workflow, credentials, ports, checks and current limitations.

### SET-01 Setup hardening (#373, #374–#376)

- **What the AI produced:** strict TypeScript configuration, PostgreSQL-only database settings, structured JSON logging with request IDs, an event-only frontend logger, a single allauth headless mount at `/api/auth/`, supporting tests, and documentation.
- **How we verified it:** after the first application, 13 backend pytest tests passed and Django reported no pending migrations. Additional Ruff, mypy, and Django routing issues were detected and corrected in a subsequent full-file replacement; the full suite must be rerun before committing.
- **Problems found and corrections:**
  - Mounting django-allauth headless under both `/api/auth/` and `/_allauth/` caused six URL namespace warnings. Removed the legacy mount.
  - Ruff required `datetime.UTC` instead of `timezone.utc`.
  - mypy could not infer the type of a test lambda. Replaced it with a typed callback.
  - Ruff's format report panicked on a file containing a UTF-8 byte-order mark. Replaced the affected production settings file without the marker and formatted relevant Django entry points.
  - The public authentication contract remains a SET-15 decision. Only routing changed; no custom authentication handlers were implemented.
  - Request logs exclude raw URL paths, query strings, request bodies, authorization tokens, and arbitrary message content to avoid exposing personal data.

### SET-32 SonarQube Cloud quality gate (#595)

- **What the AI produced:** SonarQube Cloud CI integration reusing coverage artifacts, repository-wide analysis configuration, setup documentation, and a commit-policy fix.
- **How we verified it:** Backend/frontend CI and the Sonar quality gate passed before the latest scope changes. Local workflow, scope, and commit-policy checks passed; latest integration still needs hosted validation.
- **Problems found and corrections:** Removed duplicate test runs, fixed coverage paths and lint exclusions, pinned Actions, updated certifi, expanded analysis to tools/workflows/configs, and corrected stale-base validation. Tools are excluded only from coverage. Existing quality gates remain unchanged; the policy fix activates after reaching main.

### SET-02 CI workflow and branch protection (#378, #379, #380, #381)

- **What the AI produced:** the `backend` and `frontend` jobs in `.github/workflows/ci.yml`, the coverage (70% minimum) and import-linter settings in `backend/pyproject.toml`, the Vitest coverage settings, the `typecheck` and `test:coverage` scripts, and the README CI section. The `main` ruleset (#381) is configured in the GitHub settings after this merges, not in code.
- **How we verified it:** ran every CI step locally against PostgreSQL 17 (Docker Compose) and Node 24 before opening the pull request; backend total coverage is 74%. Checked that each gate fails on bad input: a ruff error, a failing test, coverage below the minimum and a TypeScript error all exit non-zero. The pull request's own CI run is the final check.
- **Problems found and corrections:**
  - uv picked Python 3.14 for the backend on a Windows machine because the root `.python-version` is not seen from `backend/`. Added `backend/.python-version` (3.13) so local runs match CI and the Docker image; CI also pins 3.13.
  - Prettier reported every frontend file on Windows. The cause is `core.autocrlf` (CRLF in the working copy), not style: `prettier --check --end-of-line auto` passes, and the Linux runner checks out LF.
  - The first CI run failed: `backend/manage.py` has a shebang but was stored in git as not executable, which ruff (EXE001) only reports on Linux. Marked it executable in git (`git update-index --chmod=+x`).
  - SonarCloud failed the security rating on `ci.yml`: third-party actions not pinned to a commit and `uv run` calls that can re-resolve or build packages. Pinned every action to a full SHA, installed with `uv sync --locked --no-build` and called the tools straight from the synced environment.
  - `backend/modules/` does not exist yet, so the first import-linter contract only keeps `adapters/` independent of the Django project package. The module contracts are SET-14's job.

### SET-13 Glossary and French/English terminology (#404)

- **What the AI produced:** 50% or more AI-generated translation support for French/English terminology, wording consistency, shared translation content, and translation validation tests.
- **How we verified it:** compared terminology against the SET-13 acceptance criteria, checked that the glossary includes one French and one English wording per term, verified that shared translation keys match across languages, and ran the frontend tests, build, lint, and formatting checks.
- **Problems found and corrections:**
  - Kept legacy homepage/backend keys unchanged because they predate the `area.screen.element` convention.
  - Standardized new translation keys to `area.screen.element` with camelCase segments for multi-word names.
  - Reviewed French wording for project-specific terms such as B.A.D.R., notices of assessment, pickup, household files, and staff review.

### SET-09 Mock notices of assessment (#397, #398, #399, #400)

- **What the AI produced:** the generator (`generate.py`, `notices.py`, `tax.py`, `layout.py`), the phone-photo pipeline (`photos.py`), the tests, the tool README and the published spec, from the team draft and the owner's decisions (exact counts, a separate `applicants.csv`, a standalone uv project, committing the output).
- **How we verified it:** 26 pytest checks in `tools/mock_notices/tests/` (byte-identical output for seed 42; counts and cases; watermark and footer on both pages; `XXX XXX XXX` identification number; the cover page and line 199 `Montant établi` equal `truth.csv`; changed returns; calculation columns that add up; no negative declared amount with other seeds; edge cases; name and address rules on `applicants.csv`; committed output up to date, byte for byte; a failed run keeps the previous files). The layout was compared with a redacted sample notice and the line labels with the official 2025 TP-1. We changed a value in the committed `truth.csv`, a committed PDF and a committed photo on purpose and checked that the tests failed. We also looked at the PDFs and photos one by one.
- **Problems found and corrections:**
  - The team draft contradicted itself (50 PDFs + 15 photos in one table, 50 files in total in another). The final amount decided was 50 files (34 PDFs + 16 photos), and the spec now matches it.
  - The first lighting effect rotated a gradient and left dark triangles in the photo corners. Fixed by cropping the centre of a larger rotated gradient.
  - The first "unreadable" photo was so overexposed that the SPÉCIMEN watermark disappeared too. Replaced by an out-of-focus blur that loses the values but keeps the large watermark legible.
  - uv picked Python 3.14 for the tool because the root `.python-version` is not seen from a nested project. Pinned 3.13 in `tools/mock_notices/.python-version`.
  - A test expected the double space before the postal code, but PDF text extraction collapses it. The test now normalizes spaces.
  - The first layout (one page, four summary lines, ISO dates, `Last, First` name) was invented by the AI and never checked against a real notice. After it was asked, it was compared with a redacted sample notice (tax year 2018) and redesigned: two pages (cover page, then `Détail des calculs` with `Montant déclaré` / `Montant établi`), envelope-window address, notice number, French dates, footer box on every page, and some changed returns. Line labels now come from the 2025 TP-1. Photos show both pages side by side.
  - CodeRabbit found two bugs that only show with other seeds (the committed seed 42 output was not affected). The slip left out of a changed return could be larger than the employment income on line 101, giving a negative declared amount (seeds 50, 98, 213); it is now capped at that income. And `generate()` deleted the previous PDFs and photos before building the notices, so a seed that cannot give every case (533) left the old CSV files with no documents; the notices are now built first. Both have a test.

### SET-05 Database schema review and ERD (#384)

- **What the AI produced:** 50% or more AI-generated drafts of the
  Release 1 database schema, ERD, domain model and migration order.
- **How we verified it:** documents were read, reviewed and modified
  to reflect member discussions and the agreed Release 1 scope.
- **Problems found and corrections:**
  - Reviewed missing fields and omitted models in the migration order.
  - Clarified address storage, user names and Django password hashing.
  - Improved diagram readability and relationship explanations.
  - Requested consistency between Markdown fields and diagrams.
  - Left uncertain requirements open for agreement before implementation.

### SET-06 Architecture diagrams

- **What the AI produced:** 50% or more AI-generated architecture
  documentation, Mermaid diagrams and PNG exports for Release 1.
- **How we verified it:** documents were read, reviewed and modified
  following member discussions. Initial diagrams were rendered in
  Mermaid; final edited sources and exports require a consistency check.
- **Problems found and corrections:**
  - Connected the notice of assessment to Iris in the system context.
  - Clarified approval and rejection notifications to the proposed
    store manager.
  - Revised the dependency design so Eligibility receives decision
    inputs without calling back into Households.
  - Documented proposed failed-pickup and no-show handling, with final
    rules to be agreed before implementation.
  - Kept later features, including strikes and AI registration,
    outside the active Release 1 flows.

### SET-08.3 Git hooks and commit policy

- **What the AI produced:** tracked pre-commit and commit-msg hooks, a pull-request commit-policy check, Git line-ending attributes for the hooks, and setup instructions.
- **Leon's contribution:** Leon requested and approved the implementation plan, clarified that commit subjects may begin with `T` as well as `SET`, `US`, or `ES`, and activated the hooks in his clone. He brought CodeRabbit and SonarQube feedback back for review, including the untrusted-validator concern, and directed the follow-up changes before committing.
- **How we verified it:** enabled the tracked hooks in this checkout; used a temporary Git repository to confirm that ordinary invalid messages and staged whitespace fail, `T`, `SET`, `US`, and `ES` messages pass, and a real merge commit succeeds. A second temporary repository exercised the original pull-request check. The revised workflow passed YAML and shell syntax checks; an isolated local PR simulation rejected an invalid subject even when the PR replaced its hook with a script that always succeeds, and accepted a valid subject. Its GitHub-hosted behavior needs verification after it is merged into the base branch.
- **Problems found and corrections:** Atlassian's examples assume `issue-` branches and use older Python syntax, so the hooks were adapted to Iris's approved ID format. Local hooks cannot enforce policy across other clones by themselves; the pull-request check was added. CodeRabbit then found that the check executed the hook from the PR, allowing a contributor to replace it. The workflow was changed to run the base branch's hook and read PR commits only as data. SonarQube Cloud subsequently flagged the `actions/checkout` step under `pull_request_target`; the workflow now fetches Git objects without checking out PR files and executes only the hook extracted from the trusted base commit. The first PR needs human review because the trusted workflow is unavailable on the base branch until merge. A repository administrator must require the check, prevent direct pushes, and allow `pull_request_target` in the Actions event policy before GitHub's default block takes effect on November 2, 2026.
