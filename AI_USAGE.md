<!-- AI contribution: 50% or more AI-generated -->
# AI usage

How the Iris team uses generative AI, as required by the course rubric. This file stays up to date every iteration.

## Tools used

| Tool | Used for | By |
| --- | --- | --- |
| Claude (Anthropic) | Drafting the initial planning material: requirements, backlog structure, diagrams and documentation drafts. Every draft is reviewed, changed where needed and published by the team member who owns it. | Team leads (planning), owners of each document |
| Claude Code (Anthropic) | Writing code and documents for an assigned issue in the repository, under the owner's direction; the owner reviews, tests and commits | All team members |
| ChatGPT (OpenAI) | Generating and refining code, tests, configurations, and documentation for the backend, frontend, and Docker development environment. Also used for debugging, troubleshooting, and verification. | Owner of #374, #375, #376 |
| CodeRabbit | Automated review comments on pull requests (in addition to a teammate's review) | All pull requests |
| ChatGPT (OpenAI) | French/English terminology, wording consistency, shared translation content, translation validation tests, and PR-readiness review for SET-13. | Owner of #404 |
| ChatGPT (OpenAI) | Assisted with drafting and revising the SET-08.1 Statistics Canada source document under Leon's direction and review. | Leon Kojakian (#394) |
| ChatGPT (OpenAI) | Drafted T-02.11.1 tests for the future US-11 Store model, B.A.D.R. seed, and Django admin access under Leon's direction; documented the later Store REST API test plan. | Leon Kojakian (#439) |
| ChatGPT (OpenAI) | Implemented the US-11 Store model, migration, admin registration, service, and test factory from Leon's approved T-02.11.2 plan. | Leon Kojakian (#441) |
| ChatGPT (OpenAI) | Implemented the idempotent B.A.D.R. Store seed command and expanded its tests from Leon's approved T-02.11.3 plan. | Leon Kojakian (#442) |
| ChatGPT (OpenAI) | Implemented the T-01.01.3 sign-in screen, browser session handling, sign-out controls, translations, and frontend tests under Leon's approved plan. | Leon Kojakian (#425) |
| ChatGPT (OpenAI) | Drafted executable invitation service, API, RuleSet, and frontend tests from Leon's approved T-01.04.1 plan; Leon specified that invitations create new accounts only. | Leon Kojakian (#429) |
| ChatGPT (OpenAI) | Implemented the Invitation model, atomic creation/acceptance services, public acceptance API, RuleSet lifetime, translations, migration, and documentation from Leon's approved T-01.04.2 plan. | Leon Kojakian (#430) |
| ChatGPT (OpenAI) | Implemented the public invitation password page, typed API helper, French/English messages and frontend tests from Leon's approved T-01.04.3 plan; verified browser layouts and existing-session preservation. | Leon Kojakian (#431) |
| ChatGPT (OpenAI) | Implemented production configuration validation, secure entry-point defaults, admin-only API documentation, request throttling, tests and deployment guidance from Leon's approved FIX-04 plan. | Leon Kojakian (#630) |
| ChatGPT (OpenAI) | Implemented and reviewed the Categories reference module (#377), Django module scaffolding, import-boundary checks, documentation, and tests for SET-14 (#405). | Owner of #377 and #405 |
| ChatGPT (OpenAI) | The user provided architecture-aligned skeleton code and pseudocode as the foundation for US-17. ChatGPT assisted in generating approximately 50% of the remaining implementation, including walk-in registration models, normalization, services, staff API, tests, migrations, and documentation. ChatGPT also assisted with debugging Docker/PostgreSQL migrations, Ruff, mypy, import-linter, OpenAPI, and frontend API types. The user directed the implementation and performed local verification. | Owner of #463 and #464 (US-17) |
| ChatGPT (OpenAI) | Implemented the US-13 staff review screen, translations, tests, and local invitation URL configuration; independently audited story coverage. | Reuven Minciotti (#448, #451) |
| ChatGPT (OpenAI) | Implemented the partner application decision service, tests, configuration and documentation for T-02.13.2 under Reuven’s direction. | Reuven Minciotti (#449) |
| Claude Code (Anthropic) | Analyzed US-12 against the team pack, then implemented the PartnerApplication model, Store link, submission service, public API, Django admin, translations and tests from Ryan's approved T-02.12.2/T-02.12.1 plan. | Ryan Cheung (#444, #445) |

## How we declare AI-generated code

- **Source files:** the first lines of every file we write or change state one level: *No substantial AI-generated code*, *Below 50% AI-generated*, or *50% or more AI-generated*. Generated migrations, lock files and third-party code are excluded.
- **Pull requests:** the template's AI contribution section gives one level and lists the AI-assisted files. The PR policy check fails a pull request without them, and CodeRabbit's "AI declaration consistency" check compares them with the file headers.
- Code first generated by AI still counts as AI-generated after we edit it.

## AI-assisted features

One row per substantive feature where AI generated a meaningful part of the implementation.

| Feature (issue) | Files | Level | Pull request |
| --- | --- | --- | --- |
| SET-35 create-pr skill for opening pull requests (#692) | `.claude/skills/create-pr/{SKILL.md,scripts/check_pr.py}`, `docs/guides/create-pr.md`, `AI_USAGE.md` | 50% or more AI-generated | [#693](https://github.com/B-A-D-R-SL/iris/pull/693) |
| T-02.13.4 Partner review screens (#451) | `frontend/src/areas/staff/pages/PartnerApplications{,.test}.tsx`, `frontend/src/app/App{,.test}.tsx`, `frontend/src/shared/i18n/{en,fr}/store.json`, `frontend/src/shared/logger.ts`, `.env.example`, `docker-compose.yml`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.3 Partner applications staff API (#450) | `backend/modules/stores/{queries.py,README.md,api/serializers.py,api/staff_views.py,api/staff_urls.py,tests/test_staff_application_api.py,locale/fr/LC_MESSAGES/django.po}`, `backend/iris/urls.py`, `backend/pyproject.toml`, `docs/03-design/api.md`, `docs/04-architecture/architecture.md`, generated API types, `AI_USAGE.md` | 50% or more AI-generated; compiled catalog and generated API declarations exempt | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.1 Partner application review tests (#448) | `backend/modules/stores/tests/{conftest,test_application_decisions,test_application_recovery,test_staff_application_api}.py`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.2 Partner application decision service (#449) | `backend/modules/stores/{services.py,management/commands/resend_partner_invitation.py,tests/test_application_decisions.py,README.md}`, `backend/modules/accounts/services.py`, `backend/iris/{settings/base.py,observability.py}`, `backend/tests/test_observability.py`, `backend/.env.example`, `backend/pyproject.toml`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-05.36.3 Browse and detail screens (#507) and T-05.36.1 tests (#505) | `frontend/src/areas/household/` (`pages/{Listings,ListingDetail}.tsx` and their CSS and tests, `components/`, `browseFilters.ts`, `listingFormat.ts`, `useListingText.ts`, `household.module.css`, tests), `frontend/src/features/listings/browse.ts` and its tests, `frontend/src/app/App.tsx`, `frontend/src/shared/i18n/{fr,en}/household.json` | 50% or more AI-generated | Not yet opened (`US-36-browse-and-detail-screens` branch) |
| T-06.44.2 Confirm pickup service and API, with T-06.44.1 tests (#522, #521) | `backend/modules/reservations/{queries.py,services.py,permissions.py,domain/pickup.py,README.md}`, `backend/modules/reservations/api/{pickup_serializers,pickup_views,store_permissions,store_urls}.py`, `backend/modules/reservations/locale/fr/LC_MESSAGES/django.po`, `backend/modules/reservations/tests/{conftest,test_pickup_domain,test_pickup_service,test_pickup_api}.py`, `backend/modules/households/{queries.py,domain/names.py,tests/test_pickup_names.py,README.md}`, `backend/modules/listings/{queries.py,README.md}`, `backend/iris/{urls.py,settings/base.py}`, `backend/pyproject.toml`, `docs/02-requirements/business-rules.md`, `docs/03-design/api.md`, `frontend/src/shared/api/generated.d.ts`, `AI_USAGE.md` | 50% or more AI-generated (compiled catalog `django.mo` and generated API declarations exempt) | Not yet opened (`US-44-confirm-pickup` branch) |
| FIX-11 Shared role groups and authentication events (#637) | `backend/modules/accounts/{roles,queries,models,apps,signals}.py`, account role/event tests, accounts README, permission checks in listings/eligibility/audit/households, `backend/iris/{settings/base,observability}.py`, route/logging tests, `backend/pyproject.toml`, `docs/guides/observability.md`, `AI_USAGE.md` | 50% or more AI-generated | [#681](https://github.com/B-A-D-R-SL/iris/pull/681) |
| FIX-04 Production settings and entry points (#630) | `backend/iris/{settings/base.py,settings/production.py,wsgi.py,asgi.py,api.py,throttling.py}`, `backend/tests/{__init__,security_helpers,test_backend_config,test_production_settings,test_api,test_api_errors,test_endpoint_access}.py`, `backend/modules/accounts/tests/test_accounts.py`, `backend/modules/households/tests/{search_load_client,test_search_load,test_search_load_client}.py`, `backend/{.env.example,pyproject.toml}`, `frontend/src/shared/auth/api.test.ts`, `README.md`, `docs/03-design/api.md`, `docs/04-architecture/architecture.md`, `docs/guides/{production-settings,auth-routing,household-search}.md`, `AI_USAGE.md` | 50% or more AI-generated | [#683](https://github.com/B-A-D-R-SL/iris/pull/683) |
| FIX-23 Frontend development dependency security (#614) | `frontend/package.json`, `frontend/scripts/test-api-generation.mjs`, `sonar-project.properties`, `AI_USAGE.md`; `frontend/pnpm-lock.yaml` | 50% or more AI-generated; lockfile exempt | [#680](https://github.com/B-A-D-R-SL/iris/pull/680) |
| FIX-10 Translation files by area (#636) | `frontend/src/shared/i18n/{en,fr}/*.json`, `frontend/src/shared/i18n/{index,resources}.ts`, `frontend/src/test/i18n.test.ts`, `docs/01-project/glossary.md`, `docs/guides/design-system.md`, `AI_USAGE.md` | 50% or more AI-generated | [#679](https://github.com/B-A-D-R-SL/iris/pull/679) |
| FIX-07 Deny-by-default endpoint access test (#633) | `backend/tests/test_endpoint_access.py`, `docs/03-design/api.md`, `AI_USAGE.md` | 50% or more AI-generated | [#673](https://github.com/B-A-D-R-SL/iris/pull/673) |
| FIX-02 Private listing-photo processing and storage (#628) | `backend/adapters/{photos.py,blob_photos.py,photo_types.py}`, `backend/modules/listings/{contracts.py,photo_storage.py,services.py,queries.py,tests/,locale/,README.md}`, `backend/modules/reservations/{api/serializers.py,api/views.py,tests/test_api.py,locale/}`, `backend/{tools/,tests/test_photos.py,tests/test_photo_demo.py,tests/test_blob_photos.py,tests/test_blob_photos_azurite.py,photos.ini,iris/settings/base.py,pyproject.toml,.dockerignore,.env.example}`, `.env.example`, `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/guides/listing-photo-*.md`, `docs/guides/listing-posting.md`, `docs/03-design/api.md`, generated API types and `AI_USAGE.md` | 50% or more AI-generated; generated lock file, compiled catalogs and API declarations exempt | Not yet opened (`FIX-02-listing-photo-processing` branch) |
| FIX-09 Rule publishing audit and refactoring (#635) | `backend/modules/{rules,audit}/`, `backend/tests/{test_rule_publication.py,test_seed.py}`, `frontend/src/areas/staff/pages/{Audit*,auditHelpers.ts}`, audit and rule-seeding translations and generated API types | 50% or more AI-generated overall; `backend/modules/rules/tests/test_rule_set_versions.py` is below 50%; generated migration, compiled catalogs and API types exempt | [#658](https://github.com/B-A-D-R-SL/iris/pull/658) |
| US-25 duplicate check and tests (#479, #478) | `backend/modules/households/`, `backend/iris/settings/base.py`, `docs/02-requirements/business-rules.md`, `docs/03-design/api.md`, generated API types, `AI_USAGE.md` | 50% or more AI-generated | [#660](https://github.com/B-A-D-R-SL/iris/pull/660) |
| US-63 Household search (#553, #554; tests #552) | `backend/modules/households/`, `backend/modules/audit/{services.py,README.md,tests/test_household_views.py}`, `backend/iris/{asgi.py,settings/base.py,settings/local.py}`, `backend/{.env.example,tests/test_backend_config.py}`, `frontend/src/app/{App,RequireHouseholdSearch}.tsx`, `frontend/src/areas/staff/pages/Search*`, `frontend/src/features/households/{searchApi,useHouseholdSearch}*`, `frontend/src/test/{householdSearch.ts,render.tsx}`, routes, translations, generated API types and search documentation | 50% or more AI-generated; generated migration and API types exempt | [#662](https://github.com/B-A-D-R-SL/iris/pull/662) |
| SET-33 Colour prototypes and design docs (#651) | `docs/03-design/mockups/` (Release 1 coloured exports under the existing names, plus `Foundations.png` and the new-screen PNGs), `docs/guides/design-system.md` (Theme tokens and status map), `AI_USAGE.md` | 50% or more AI-generated for the Theme documentation; mockup PNGs are Figma exports | [#668](https://github.com/B-A-D-R-SL/iris/pull/668) |
| FIX-21 Split the mock notice page-drawing functions (#647) | `tools/mock_notices/layout.py`, `tools/mock_notices/tests/test_layout.py`, `AI_USAGE.md` | 50% or more AI-generated | [#667](https://github.com/B-A-D-R-SL/iris/pull/667) |
| FIX-15 Seed command boundary and household expiry (#641) | `backend/iris/management/commands/seed.py`, `backend/modules/households/domain/expiry.py`, `backend/modules/households/models.py`, `backend/modules/households/tests/test_expiry.py`, `backend/tests/test_seed.py`, `backend/pyproject.toml`, `docs/04-architecture/architecture.md`, `AI_USAGE.md` | 50% or more AI-generated | [#663](https://github.com/B-A-D-R-SL/iris/pull/663) |
| T-01.04.3 Invitation password page (#431) | `frontend/src/areas/public/pages/AcceptInvitation{,.test}.tsx`, `frontend/src/features/accounts/invitations{,.test}.ts`, `frontend/src/app/App.tsx`, `frontend/src/shared/i18n/{fr,en}.json`, `frontend/src/shared/logger.ts`, `.coderabbit.yaml`, `backend/modules/accounts/README.md`, `docs/03-design/api.md`, `AI_USAGE.md` | 50% or more AI-generated | [#657](https://github.com/B-A-D-R-SL/iris/pull/657) |
| T-01.04.2 Invitation model, services and acceptance API (#430) | `backend/modules/accounts/{models.py,services.py,api/,locale/fr/LC_MESSAGES/,README.md,migrations/0005_invitation.py}`, `backend/modules/accounts/tests/{conftest,test_invitations,test_invitation_logging,test_invitation_errors}.py`, `backend/modules/rules/{domain/schemas.py,tests/test_invitation_rules.py}`, `docs/02-requirements/business-rules.md`, `docs/03-design/{api,database-schema,domain-model}.md`, `docs/04-architecture/architecture.md`, `frontend/src/shared/api/generated.d.ts`, `AI_USAGE.md` | 50% or more AI-generated for source changes; Django migration, compiled catalog and generated API declarations exempt | [#657](https://github.com/B-A-D-R-SL/iris/pull/657) |
| T-01.04.1 Invitation acceptance tests (#429) | `backend/modules/accounts/tests/{factories,conftest,test_invitations,test_api}.py`, `backend/modules/rules/tests/test_invitation_rules.py`, `frontend/src/areas/public/pages/AcceptInvitation.test.tsx`, test-only import exceptions in `backend/pyproject.toml`, `AI_USAGE.md` | 50% or more AI-generated | [#657](https://github.com/B-A-D-R-SL/iris/pull/657); implementation supplied by #430 and #431 |
| T-09.62.1 Audit tests (#548) | `backend/modules/audit/tests/test_audit.py` | 50% or more AI-generated | [#619](https://github.com/B-A-D-R-SL/iris/pull/619) |
| T-09.62.2 Audit model and service (#549) | `backend/modules/audit/{models.py,services.py,README.md,migrations/}` | 50% or more AI-generated (migrations exempt) | [#619](https://github.com/B-A-D-R-SL/iris/pull/619) |
| T-01.01.1 Sign-in and sign-out tests (#423) | `backend/modules/accounts/tests/test_accounts.py`, `frontend/src/app/App.test.tsx`, `AI_USAGE.md` | 50% or more AI-generated | [#610](https://github.com/B-A-D-R-SL/iris/pull/610) |
| T-01.01.2 User model and sign-in API (#424) | `backend/modules/accounts/`, authentication settings/routes, development administrator command, affected regression tests, `backend/{pyproject.toml,uv.lock}`, generated API types, `docs/03-design/{api,database-schema}.md`, `docs/guides/auth-routing.md` | 50% or more AI-generated for the marked source files, including `backend/pyproject.toml`; Below 50% AI-generated for `backend/modules/rules/tests/test_rule_set_versions.py`; generated migrations, lockfile and API declarations exempt | [#610](https://github.com/B-A-D-R-SL/iris/pull/610) |
| T-01.01.3 Sign-in screen and session handling (#425) | `frontend/src/areas/public/pages/SignIn.tsx`, `frontend/src/shared/{auth,forms}/`, app providers and layouts, current-user query, French/English translations, frontend tests, `docs/guides/design-system.md`, `AI_USAGE.md` | 50% or more AI-generated | [#610](https://github.com/B-A-D-R-SL/iris/pull/610) |
| T-03.17.4 Walk-in form screens and T-03.17.1 tests (#465, #462) | `frontend/src/areas/staff/pages/WalkIn/`, `frontend/src/features/households/walkInApi.ts`, `frontend/src/app/App.tsx`, French/English translations, consent fields in `backend/modules/households/` (model, services, serializers, tests; migration exempt), `AI_USAGE.md` | 50% or more AI-generated | Not yet opened (`US-17` branch) |
| T-00.01.1 Backend project (#374) | `backend/iris/settings/`, `backend/manage.py`, `backend/pyproject.toml`, `backend/tests/test_backend_config.py`, `backend/.env.example` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| T-00.01.2 Frontend project (#375) | `frontend/src/`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `backend/iris/{views.py,urls.py}` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| T-00.01.3 Docker Compose and README (#376) | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/adapters/mailer/`, `backend/iris/management/commands/create_dev_admin.py`, `backend/tests/test_platform_setup.py`, `.env.example`, `README.md` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| SET-01 Setup hardening (#373, #374–#376) | `backend/iris/observability.py`, `backend/tests/test_observability.py`, `backend/iris/settings/base.py`, `frontend/src/shared/logger.ts`, `frontend/src/shared/logger.test.ts`, `backend/iris/urls.py` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| SET-32 SonarQube Cloud quality gate (#595) | `sonar-project.properties`, `.github/workflows/{ci,commit-policy}.yml`, `frontend/vite.config.ts`, `frontend/eslint.config.js`, `backend/uv.lock`, `README.md`, `docs/guides/sonarqube-cloud.md` | 50% or more AI-generated | [#605](https://github.com/B-A-D-R-SL/iris/pull/605) |
| SET-09 Mock notices of assessment (#397) | `tools/mock_notices/{generate.py,notices.py,tax.py,layout.py,photos.py,tests/test_generate.py,pyproject.toml,README.md}`, `docs/04-data/mock-notices-of-assessment.md` | 50% or more AI-generated | [#592](https://github.com/B-A-D-R-SL/iris/pull/592) |
| SET-13 Glossary and French/English terminology (#404) | `docs/01-project/glossary.md`, `frontend/src/shared/i18n/en.json`, `frontend/src/shared/i18n/fr.json`, `frontend/src/test/i18n.test.ts` | 50% or more AI-generated | [#594](https://github.com/B-A-D-R-SL/iris/pull/594) |
| SET-08.3 Git hooks and commit policy | `.githooks/pre-commit`, `.githooks/commit-msg`, `.gitattributes`, `.github/workflows/commit-policy.yml`, `README.md` | 50% or more AI-generated | Not yet opened |
| T-00.08.1 Official LICO table (#394) | `docs/04-data/lico-thresholds.md` | 50% or more AI-generated | Not yet opened (commit `5e3baad`) |
| T-00.08.2 LICO threshold seed | `backend/modules/eligibility/data/lico_2024.csv`, `backend/modules/rules/management/commands/seed_rules.py`, `backend/modules/rules/tests/test_seed_rules.py` | 50% or more AI-generated | Not yet opened |
| T-02.11.1 B.A.D.R. first store tests (#439) | `backend/modules/stores/tests/test_store.py`, `test_seed_badr_store.py`, `test_admin.py`, `test_api.py` (US-14 comment only) | 50% or more AI-generated | [#606](https://github.com/B-A-D-R-SL/iris/pull/606); model, seed, and admin tests pass |
| T-02.11.2 Store model and migration (#441) | `backend/modules/stores/{__init__.py,apps.py,fields.py,models.py,services.py,admin.py,migrations/0001_initial.py,locale/fr/LC_MESSAGES/,tests/factories.py}`, `backend/iris/settings/base.py`, `frontend/src/shared/api/generated.d.ts`, focused test additions | 50% or more AI-generated (generated migration and API declarations exempt; compiled catalog generated from the marked `.po` source) | [#606](https://github.com/B-A-D-R-SL/iris/pull/606) |
| T-02.11.3 B.A.D.R. seed (#442) | `backend/modules/stores/management/`, `backend/modules/stores/services.py`, `backend/modules/stores/tests/test_seed_badr_store.py`, `AI_USAGE.md` | 50% or more AI-generated | [#606](https://github.com/B-A-D-R-SL/iris/pull/606) |
| SET-12 Listing categories and safety lists (#403) | `docs/02-requirements/business-rules.md` (Listings section), `backend/modules/categories/data/categories.yaml` | 50% or more AI-generated | Not yet opened (`feature/SET-12` branch) |
| SET-02 CI workflow and branch protection (#378, #379, #380, #381) | `.github/workflows/ci.yml`, `backend/pyproject.toml` (coverage and import-linter settings), `frontend/vite.config.ts` (coverage settings), `frontend/package.json` (scripts), `README.md` (checks and CI section) | 50% or more AI-generated | Not yet opened |
| SET-15 OpenAPI and TypeScript generation (#406), partial implementation | `backend/iris/settings/base.py`, `backend/tests/test_api_schema.py`, `frontend/scripts/{gen-api,test-api-generation}.mjs`, `frontend/src/shared/api/generated.d.ts`, `frontend/src/test/api-types.typecheck.ts`, `frontend/package.json`, `frontend/pnpm-lock.yaml`, `.github/workflows/ci.yml`, `docs/guides/api-generation.md`, `docs/03-design/api.md`, `AI_USAGE.md`, `README.md` | 50% or more AI-generated | [#604](https://github.com/B-A-D-R-SL/iris/pull/604); categories compliance (#377) and documented team decisions remain pending |
| T-05.33.2 Listing model (#493) | `backend/modules/listings/{__init__.py,apps.py,models.py,migrations/0001_initial.py,tests/}`, `backend/modules/categories/tests/{factories.py,test_category_model.py}` (its minimal Category model and migration were replaced by #377's when `main` was merged into `US-33-post-a-listing`), `backend/iris/settings/base.py` | 50% or more AI-generated (generated migrations exempt) | Not yet opened (`US-33-post-a-listing` branch) |
| SET-16 Design system, translations and app shell (#407) | `frontend/src/app/` (theme, providers, routes, layouts, navigation, guards, error boundary), `frontend/src/areas/public/WelcomePage.tsx`, `frontend/src/features/accounts/currentUser.ts`, `frontend/src/shared/{forms,ui}/`, `frontend/src/shared/i18n/{fr,en}.json`, `frontend/src/test/`, `frontend/public/{manifest.webmanifest,favicon.svg,icons/}`, `frontend/index.html`, `frontend/package.json`, `docs/guides/design-system.md`; built from the Figma Components page (SET-11) | 50% or more AI-generated (lock file and generated icons exempt) | Not yet opened (`SET-16-design-system-translations-and-app-shell` branch) |
| T-00.01.4 Categories reference module (#377) | `backend/modules/categories/`, `frontend/src/features/categories/`, `backend/iris/urls.py`, `frontend/src/app/App.tsx`, translations, API types, and `docs/guides/reference-module.md` | 50% or more AI-generated | Pending PR (`feature/SET-14`) |
| SET-14 Module skeletons and boundary checks (#405) | `backend/modules/` (15 module structures and READMEs), `backend/iris/settings/base.py`, `backend/pyproject.toml`, and architecture-related Rules changes | 50% or more AI-generated | Pending PR (`feature/SET-14`) |
| T-09.62.3 Audit search (#550) | `backend/modules/audit/{api,queries.py,tests/test_search_api.py,README.md}`, `backend/iris/urls.py`, `frontend/src/areas/staff/pages/Audit*`, `frontend/src/app/App.tsx`, translations, generated API types, `docs/03-design/api.md`, `AI_USAGE.md` | 50% or more AI-generated | [#619](https://github.com/B-A-D-R-SL/iris/pull/619) |
| T-05.33.4 Posting form (#495) | `frontend/src/areas/store/{pages/NewListing.tsx,pages/newListingForm.ts,components/CategoryPicker.tsx}` and their CSS and tests, `frontend/src/features/listings/`, `frontend/src/shared/forms/IntegerField.tsx`, `frontend/src/shared/api/csrf.ts`, translations, `frontend/src/app/App.tsx`; the category-code change in `backend/modules/listings/` (serializers, service, domain input, tests) and `backend/modules/categories/queries.py`; regenerated API types; `docs/guides/{listing-posting,design-system}.md` | 50% or more AI-generated | Not yet opened (`US-33-post-a-listing` branch) |
| T-05.33.5 Time-to-post check (#496) | `docs/usability/time-to-post.md` (study plan and results template), `frontend/scripts/usability/` (preview API, timing rules, report, tests), `frontend/package.json` (scripts), `frontend/.gitignore` | 50% or more AI-generated; the times and observations come from the sessions | Not yet opened (`US-33-post-a-listing` branch) |
| T-03.17.2 Household/Member models and normalization (#463) | `backend/modules/households/{models.py,domain/address.py,domain/person.py,migrations/0001_initial.py,tests/factories.py,tests/test_address.py,README.md}`, `backend/pyproject.toml`, `AI_USAGE.md` | 50% or more AI-generated (including the AI-drafted migration; not an automatically generated migration) | Not yet opened (`US-17` branch; teammate review pending) |
| T-03.17.3 Staff walk-in registration services and API (#464) | `backend/modules/households/{services.py,queries.py,api/serializers.py,api/views.py,api/urls.py,tests/test_walk_in.py,README.md}`, `backend/iris/{urls.py,settings/base.py}`, `backend/pyproject.toml`, `frontend/src/shared/api/generated.d.ts`, `AI_USAGE.md` | 50% or more AI-generated for the Python source, tests and configuration edits; generated TypeScript declarations exempt | Not yet opened (`US-17` branch; teammate review pending) |
| SET-18 Seed data generator (#409) | `backend/iris/seedset.py`, `backend/iris/management/commands/seed.py`, `backend/modules/households/models.py`, `backend/modules/reservations/models.py`, their migrations, `backend/tests/test_seed.py`, `backend/tests/test_seed_plan.py`, `docs/04-data/seed-data.md` | 50% or more AI-generated | Not yet opened (`SET-18-data-generator` branch) |
| SET-19 AI reading spike (#410) | `tools/notice_reading_spike/{run.py,reader.py,fields.py,score.py,records.py,truth_reader.py,azure_layout_reader.py,layout_parser.py,vlm_reader.py,tests/,pyproject.toml,uv.lock,.python-version,.env.example,README.md}`, `docs/adr/0005-notice-reading.md`, the `document_reader` row in `docs/04-architecture/architecture.md`, `AI_USAGE.md`, and the wiki pages Notice Reading, Notice Reading – Results and Notice Reading – Law 25 Evidence | 50% or more AI-generated | [#612](https://github.com/B-A-D-R-SL/iris/pull/612) |
| T-02.12.2 PartnerApplication model and API (#445) | `backend/modules/stores/{models.py,services.py,admin.py,api/,locale/,README.md}`, `backend/iris/{urls.py,settings/base.py}` (route, throttle rate, `NUM_PROXIES`, `django.contrib.postgres`), `backend/pyproject.toml` (stores → categories boundary), regenerated API types, `docs/03-design/{api,database-schema}.md`, `docs/04-architecture/architecture.md` | 50% or more AI-generated (generated migration and API declarations exempt) | Not yet opened (`US-12-partner-application-api` branch) |
| T-02.12.1 Unit tests: Business applies to become a partner (#444) | `backend/modules/stores/tests/{factories.py,test_partner_application_model.py,test_partner_application_service.py,test_partner_application_api.py,test_admin.py}` | 50% or more AI-generated | Not yet opened (`US-12-partner-application-api` branch) |
| T-02.12.3 Become a partner page (#446) | `frontend/src/areas/public/pages/PartnerApply*`, `frontend/src/areas/public/pages/partnerApplication.ts`, `frontend/src/app/App.tsx`, French and English translations | 50% or more AI-generated | [#618](https://github.com/B-A-D-R-SL/iris/pull/618) |
| US-16 Eligibility engine (#457) | `backend/modules/eligibility/{domain/eligibility.py,models.py,services.py,tests/}`, migrations, documentation, settings | 50% or more AI-generated; migrations generated by Django | PR #621; 75 eligibility tests and 388 backend tests passed locally, domain coverage 100%; real household/notice integration pending |
| US-34 Listing safety checks (#497: #498, #499, #500) | `backend/modules/listings/{domain/safety.py,domain/posting.py,services.py,queries.py,api/,locale/fr/LC_MESSAGES/,README.md}`, `backend/modules/listings/tests/{test_safety.py,test_safety_service.py,test_safety_api.py}`, `frontend/src/areas/store/{components/ProhibitedItemsLink.tsx,components/CategoryPicker.tsx,pages/NewListing.tsx,pages/NewListing.module.css,pages/NewListing.test.tsx}`, `frontend/src/features/{listings/api.ts,listings/api.test.ts,categories/api.ts}`, translations, regenerated API types, `docs/guides/listing-posting.md`, `docs/03-design/api.md`, `docs/02-requirements/forms-and-fields.md` | 50% or more AI-generated (generated API declarations exempt; compiled catalog generated from the `.po` source) | Not yet opened (`feat/US-34-listing-safety` branch) |
| T-05.35.2 Category admin API and screen (#503) and T-05.35.1 tests (#502) | `backend/modules/listings/tests/test_category_admin.py`, `backend/modules/categories/` (`domain/rules.py`, `queries.py`, `services.py`, `api/serializers.py`, `api/staff_views.py`, `api/staff_urls.py`, `tests/test_staff_api.py`, French catalog, README), `backend/iris/urls.py`, `backend/pyproject.toml` (test-only import exceptions), `frontend/src/features/categories/` (`adminApi.ts`, `categoryForm.ts`, `CategoryDialog.tsx`, `CategoriesPage.tsx` and tests), translations, regenerated API types, `docs/02-requirements/forms-and-fields.md`, `docs/03-design/{api,database-schema}.md`, `AI_USAGE.md` | 50% or more AI-generated (generated API declarations and compiled catalog exempt) | Not yet opened (`user_story/US-35` branch) |

## Examples, verification and corrections

### SET-35 create-pr skill for opening pull requests (#692)

- **What the AI produced:** Claude Code generated the skill: `.claude/skills/create-pr/SKILL.md`, `scripts/check_pr.py` and the guide `docs/guides/create-pr.md`.
- **Owner's decisions:** Ryan decided what the skill had to do, its behaviour, and its restrictions and limitations, and tested the skill.
- **How we verified it:** PR #693 was opened with the skill itself. `check_pr.py` passed on its title and description before the push, and the PR got its assignee, milestone and Project Iris as the skill describes (checked with `gh pr view`).
- **Problems found and corrections:** the first `gh pr create` failed because the project was passed as "Iris" instead of its full title, "Project Iris"; the PR was opened on the retry. Checking the story against the skill showed two requirements were not implemented (repeating the command's answers back in one line, and checking for an already open PR before pushing); they were removed from #692 rather than claimed as done.

### T-02.13.1 Partner application review tests (#448)

- **What the AI produced:** Additional decision-service tests for each non-admin role, the rejection reason length boundary, audit failure rollback, and privacy-safe handling of email failure. PR review fixes add frontend-origin validation, invitation recovery and command tests, and structured logging privacy checks. Staff API and listing tests are included in `test_staff_application_api.py` (#450).
- **Verification:** On 2026-11-11, all 939 backend tests passed against an isolated native PostgreSQL 17 instance, including all 37 decision/configuration/recovery cases. Ruff and all four import-linter contracts passed. Coverage was not measured in this run. Changes are committed in [PR #665](https://github.com/B-A-D-R-SL/iris/pull/665).

### T-02.13.2 Partner application decision service (#449)

- **What the AI produced:** Under Reuven’s direction, ChatGPT implemented approval and rejection services with locked decisions, store and invitation creation, audit records, after-commit emails, frontend URL configuration, tests and module documentation. The free-text application hours are retained in the store’s `opening_hours.notes`. PR review fixes add explicit frontend-origin configuration errors before application locking and an operator recovery command that expires old invitation links and sends a fresh one after commit. Recovery does not repeat the application decision or expose contact details or tokens in logs.
- **Verification:** On 2026-11-11, all 939 backend tests passed on PostgreSQL 17, including 37 decision/configuration/recovery cases. Ruff, mypy for the four changed production Python files, Django system checks, and all four import-linter contracts passed. Coverage was not measured in this run. The implementation and review fixes are committed in [PR #665](https://github.com/B-A-D-R-SL/iris/pull/665).

### PR #665: review follow-up for the staff screen and API tests

- **What the AI produced:** An API test proving that unavailable invitation rules return 400 and roll back the store, invitation, decision and audit writes; French/English API tests for existing-account refusal; translated business-type/frequency lookups and value assertions; cookie cleanup; public API error-message rendering with generic server/network fallbacks and privacy-safe diagnostic events. Compose invitation URLs now default to the configured frontend port, while explicit URL overrides are preserved.
- **Owner's decisions:** Retain the rejection validation order. A later instruction authorizes server-owned `can_decide` availability in place of status-based button visibility. An early existing-account check on public application submission remains a product discussion; it is not part of these fixes.
- **Verification (2026-11-11):** All **942 backend tests** passed on native PostgreSQL 17 and all **413 frontend tests across 29 files** passed, including 14 partner-review screen cases. The frontend suite required localhost access for its preview-server tests. Ruff, mypy for the changed API test file, ESLint, TypeScript checks, the production frontend build, and formatting checks for the changed files passed. Compose YAML and the documented Bash-compatible nested-default expression were checked for the default port, a changed port, an explicit URL, and an empty URL; the Docker Compose executable was unavailable, so `docker compose config` was not run. Coverage was not measured.
Historical examples are preserved in the linked verification records.
The headings remain here so existing feature anchors continue to resolve.
### FIX-02 Private listing-photo processing and storage (#628)

- **What the AI produced:** under Mark’s (@markantoun0) direction, Codex implemented JPEG/PNG validation, Pillow resizing, EXIF orientation correction, metadata removal, private blob storage, five-minute read-only links, listing integration, failure cleanup, tests and documentation. Mark  requested sharing one storage loader between posting and browsing, moving shared result/error types out of the Azure adapter, and checking container privacy once per browse page instead of once per photo. He also provided SonarQube findings for correction, and directed that unrelated UI and backend issues remain outside the task’s scope.
- **Developer direction and learning:** Mark requested a step-by-step plan before coding and asked how image processing, storage adapters, Azure/Azurite, permissions and signed-link expiry fit together. He clarified the division of work with teammates, supplied SonarQube findings, reviewed the proposed simplifications and directed corrections. He kept the work focused on the photo task and explicitly excluded unrelated frontend placeholders. Local test accounts and setup data were kept in his local database; no credentials or account seed changes were committed.
- **Mark's manual verification:** Mark signed in as a store user, posted listings with different pictures and checked that the uploaded photos were saved and could be displayed through the returned signed URLs. He inspected Azurite blob storage in Docker and investigated why two photos appeared inside one internal storage file; listing the actual blobs confirmed two separate objects and references, rather than an overwrite. He verified that a working photo link allowed access during its five-minute lifetime and that requesting the same link after expiry returned `AuthorizationFailure`; an already downloaded image can remain visible in a browser tab. Using the test pictures, Mark also checked metadata removal and the change in pixel dimensions after processing.
- **Automated verification performed with AI assistance:** the latest full backend regression run passed 1,444 tests, covering the whole backend rather than only this feature; the real five-minute waiting test was excluded from that run. The standalone photo suite passed 79 tests, and Ruff, mypy and all four import-boundary checks passed. Real Azurite tests exercised uploads, private access, scoped links and deletion; the real five-minute expiry test had also passed in an earlier run. These checks complement Mark's manual tests; real Azure staging verification remains pending.

### US-25 Duplicate checking and tests (#479, #478)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-25-duplicate-checking-and-tests-479-478).

### US-63 Household search and tests (#552, #553, #554)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-63-household-search-and-tests-552-553-554).

### PR #665: server-owned availability and main conflict resolution

- **What changed:** Per the owner's follow-up, the staff API returns `can_decide` using the same active-admin/submitted-state predicate as write enforcement; the UI renders that flag. Main's split translation catalogs and structured logging helpers are preserved during conflict resolution, and the new endpoints are registered in its global access matrix. Remaining valid review checks add translated email/recovery text, HTTPS outside loopback, a finite SMTP timeout and after-commit decision logs. The duplicate beneficiary test was removed, recovery tests/fixtures were separated, and fixed rejection storage semantics are documented as BR-PARTNER-04.
- **Verification (2026-11-11):** 2030 backend tests passed on PostgreSQL 17 (5 optional integration skips, one CI-excluded slow-expiry case); 658 frontend tests passed. Combined backend coverage is 95.66%, added backend executable-line coverage is 98.17%, and domain line coverage is 99.35%. Full lint, formatting, type, import, schema/generator, migration, build and dependency-audit checks passed. See `docs/03-design/verification/US-13-review-checks.md` for scope, counts and reproduction. GitHub checks are verified after publishing.

### T-01.04.3 Invitation password page (#431)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01043-invitation-password-page-431).

### T-01.04.2 Invitation model, services and acceptance API (#430)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01042-invitation-model-services-and-acceptance-api-430).

### T-01.04.1 Invitation acceptance tests (#429)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01041-invitation-acceptance-tests-429).

### T-09.62.3 Audit search API and screen (#550)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-09623-audit-search-api-and-screen-550).

### FIX-11 Shared role groups and authentication events (#637)

- **What the AI produced:** shared store/staff role groups and an admin check, reused by model constraints and permissions; Django session signal handlers; UUID-only success log fields; browser-only headless authentication; tests and documentation.
- **Design:** `User.Role` aliases the enum in `accounts/roles.py` so the model can import public query groups without a circular import. Both user and invitation store constraints use the same group. Audit search remains admin-only. Household staff permissions also use the shared staff group.
- **Logging:** Django signals cover browser and admin sessions once per sign-in/out. Only `iris.auth` success events can serialize a UUID `user_id`; failed attempts, anonymous sign-out, credentials and other personal details are excluded.
- **Verification:** all 1,378 backend tests passed at 94.16% coverage. Ruff, mypy, all four import contracts, migration checks, all eight API-generator tests and TypeScript passed. API types were regenerated without changes; no migration was needed. Tests cover role separation, admin access, session events, log privacy, app-route 404 responses and the browser config endpoint.

### FIX-04 Production settings and entry points (#630)

- **What the AI produced:** under Leon Kojakian's approved plan, production secret/mailer validation, HTTPS/HSTS and proxy configuration, production defaults for WSGI/ASGI, an active-admin documentation permission, production anonymous/account request limits and translated 429 envelopes, regression tests, environment guidance and architecture/API updates.
- **Developer decisions:** retain local management/Compose settings, existing partner application and sign-in limits; use configurable general production limits of 60/minute for anonymous callers and 300/minute for authenticated accounts. Keep HSTS preload disabled pending domain-owner approval, explicitly acknowledge only Django's `security.W021`, and retain a strict deployment check for every other warning. Keep Azure resource changes and dedicated CI security jobs in SET-17 and FIX-17.
- **Initial verification:** all 65 new FIX-04 cases passed in the complete backend run: 36 fresh-process configuration/startup cases and 29 API/error cases. Production API requests use the real routed views, factories and pytest's isolated PostgreSQL database; they cover all roles, anonymous/inactive users, quota boundaries, French/English errors, proxy identities and `Retry-After`. The strict production deployment check passes with only the documented preload warning acknowledged. Ruff lint/format, mypy, all four import-boundary contracts, migration checks, OpenAPI validation and generated-type drift checks pass. Subprocess coverage measures production startup: all 52 added executable security lines are covered; overall coverage is 95.51%. The complete run reports 1,641 passed, one failed and one deselected (the separate five-minute photo-expiry test). The failure is the existing 100 requests/second household-search benchmark; it also fails on the unchanged committed baseline without coverage in this environment (p95 about 4.80 seconds against a 500 ms target). The local backend starts normally with current locked dependencies and its health/schema/docs URLs return 200. Azure deployment and deployed-proxy validation remain outstanding under SET-17.
- **Problems found and corrections:** the production email guard inspects Django 6.1's effective `MAILERS` configuration. Iris's application admin role differs from `is_staff`; tests also refuse a nonadmin with that flag. Existing connection-policy tests needed a valid production key and delivery backend. Production settings are copied so local/test dictionaries are unchanged. Coverage includes the fresh production subprocesses. Search-load investigation changes were reverted at Leon's request; the existing benchmark failure is deferred to a later task. An outdated local image lacked the Azure dependency already merged on main; rebuilding and recreating only the backend restored local startup without resetting the development database.

- **Final acceptance audit:** moved the API role cases to the required `backend/tests/test_api.py` name and updated references. All 29 API/error cases passed again after the rename; Ruff lint/format and mypy also passed.
- **CodeRabbit review follow-up:** refused Django's dummy and file-based production mailers alongside console/in-memory backends, restricted rate periods to explicit second/minute/hour/day aliases including plurals, and updated environment/deployment guidance. Removed the duplicate development-documentation test while retaining the stronger schema and Swagger tests. All 92 focused cases passed (60 configuration/startup, 28 API/error and four existing schema/documentation cases), including actual DRF quota/duration checks for all 18 accepted aliases and refusal of `month`/`hello` for both rate variables. Ruff lint/format, mypy, all four import contracts and migration checks passed again. [Published CI](https://github.com/B-A-D-R-SL/iris/actions/runs/42977759704) passed for review commit `ed442e0`. Search-load remediation remains deferred.
- **Dani's review follow-up:** rejected wildcard production hosts and added allauth's independent `ALLAUTH_TRUSTED_PROXY_COUNT`, defaulting to zero with negative values refused. Real request tests cover ignored spoofed headers, stable client addresses across changing ports and isolated login quotas behind zero/one/two trusted proxy hops. Added the protected-route permission-before-throttle regression and documented that boundary. Backend and frontend tests now distinguish allauth's native `{"status": 429}` response from DRF's envelope and failed-login HTTP 400 lockouts; no frontend behavior change was needed. All 145 focused backend cases passed (64 production configuration, 24 production API, eight error, four schema and 45 account cases), as did all six frontend authentication API tests. Ruff lint/format, mypy, four import contracts, migration checks, and the changed frontend test's ESLint/Prettier checks passed. These fixes are locally validated and require CI after commit/push. Azure's actual proxy chain remains SET-17 deployment verification; no trusted hop count was assumed and no Azure resources were changed.

- **Search benchmark follow-up:** fixed coverage instrumentation leaking into the load-driver subprocess; the real WSGI server and driver now share an environment filter that removes coverage hooks while retaining application settings. Added an environment regression and a real child-process coverage-startup regression. All 103 related search/access/audit/connection tests passed, and all 15 driver tests passed again with subprocess coverage hooks active. Ruff lint/format, mypy, all four import contracts and migration checks passed. Published CI for `99d5e30` is [green](https://github.com/B-A-D-R-SL/iris/actions/runs/42979854471); these additional benchmark changes need CI after commit/push. Leon confirmed that his two-CPU VM exists to host local Docker development, and capacity acceptance belongs in CI and staging. The local load failure is recorded as a resource-dependent result, not reported as a green full suite. No threshold, request count, dataset, audit requirement or CI test was relaxed. Query/index/serializer/worker experiments did not establish a reliable fix and were removed; application behavior, database schema and dependencies are unchanged. Actual staging capacity remains deployment verification.

- **Test-suite size review:** split `frontend/src/shared/auth/api.test.ts` into three top-level suites of 29, 43 and 31 lines, keeping all six test bodies, mocks and assertions unchanged. All six tests passed in Docker; the changed file also passed ESLint and Prettier. This regrouping needs CI after commit/push.

- **Localization documentation review:** corrected the API implementation status to reflect the configured `LocaleMiddleware`, supported French/English request-language selection and translated DRF throttling messages. Verified against base settings, the shared exception handler and the existing French/English request regression; this documentation-only change does not claim translation coverage for every endpoint.

### FIX-23 Frontend development dependency security (#614)

- **What the AI produced:** scoped pnpm overrides for jsdom's Undici 8.12.4 and openapi-typescript's Undici 6.29.1, the regenerated lockfile, an HTTP redirect regression test that uses Undici without Node's built-in fetch, and Sonar test classification for that standalone runner.
- **Why:** keep openapi-typescript 6.7.6 and TypeScript 6 compatible. Undici 6.29.1 removes the old busboy dependency. Undici 8.12.4 also covers the November 5 security fixes published after this issue.
- **Verification:** frozen install, dependency tree, ESLint, Prettier, TypeScript, build, unchanged generated API types, all 9 generator tests, and all 443 frontend tests passed (93.68% statement coverage). The coverage run used four workers after three tests timed out with the default 30 workers.
- **Audit:** no Undici or busboy findings remain. The full development audit still reports two existing findings: Zod 4.6.5 (high, GHSA-mrhx-c7xc-m3w5) and minimatch 10.2.6 (moderate, GHSA-g3hv-75wg-m249). GitHub alerts must be checked again after merging into main.

### FIX-10 Translation files by area (#636)

- **What the AI produced:** matching common, public, household, store and staff JSON files for English and French; a resource module that keeps the existing translation namespace; file-level parity, size, loading and empty-string tests; glossary and design-system updates.
- **Preserved:** every original key and value matches the files on `main`. No screen calls or translation wording changed. The largest file is now 182 lines instead of 686.
- **Verification:** all 458 frontend tests passed at 93.69% statement coverage, including 21 translation tests. ESLint, Prettier, TypeScript and the production build passed. Tests discover every area file, reject overlapping top-level prefixes, check that every file is loaded, and resolve every key in both languages. They also check French fallback when English entries are missing and key fallback when neither language has an entry.

### T-09.62.1–2 Audit tests and service (#548, #549)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-096212-audit-tests-and-service-548-549).

### T-02.12.3 Become a partner page (#446)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-02123-become-a-partner-page-446).

### US-16 Eligibility engine (#457)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-16-eligibility-engine-457).

### SET-18 Seed data generator (#409)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-18-seed-data-generator-409).

### T-06.44.2 Confirm pickup service and API, with T-06.44.1 tests (#522, #521)

- **Firas's direction:** implement #522 with its #521 tests in one pull request, following US-44's acceptance criteria, the "Confirm a pickup" wireframe, the architecture's pickup sequence and the review rules, and stay clear of the open pull requests (#659, #661, #662). The scan screen (#523) and late confirmation of a no-show (US-45) are later work.
- **What the AI produced:** `lookup_pickup` and `confirm_pickup`, scoped to the staff member's store, with a row lock so a pickup is recorded once; the two `/api/store/pickups/` endpoints with the shared error shape and fixed French/English messages; `pickup_listings` in listings and `pickup_names` (first name and last initial) in households; BR-RES-001 to BR-RES-005; tests for every role and every refusal, including six simultaneous confirmations; the API documentation and generated types.
- **How we verified it:** 963 backend tests passed with 93.6% coverage; ruff, mypy, lint-imports (4 contracts kept) and `makemigrations --check` were clean. The OpenAPI schema validated with `--fail-on-warn`. Trial merges against the open pull requests found only documentation, translation-catalog and append-only conflicts.
- **Problems found and corrections:**
  - Pickup codes are unique per listing, not per store, so one code can match two live reservations at the same store. The lookup refuses that case instead of picking one (BR-RES-004), as the architecture's sequence proposes.
  - Seeded codes such as `000001` use characters the wireframe's alphabet leaves out, so the lookup checks only the length and letters/digits, not that alphabet.
  - The docs leave stock on pickup open. Lowering `quantity_reserved` would offer handed-over units again, so confirming leaves stock unchanged (BR-RES-005, marked **Default**). The seed counts only `reserved` rows in `quantity_reserved`; that difference is left for the reservations owner.
  - `AuditEvent` has no pickup action, so no audit row is written; the reservation keeps who and when, and a `pickup_confirmed` log line has no names or codes.
  - The container has no gettext tools, so `django.mo` was compiled with a standard-library script and checked by a test that every refusal message has a French translation.

### US-44 local review follow-up (#522)

- **Tool:** OpenAI Codex.
- **Scope:** `backend/modules/reservations/services.py`, `backend/iris/settings/base.py`, `backend/modules/reservations/tests/test_pickup_service.py`, and this entry.
- **Contribution:** 50% or more AI-generated. Moved the confirmation clock read after acquiring the reservation lock, enabled the pickup success logger, and added regression coverage for a lock wait crossing the deadline and for the timestamp saved after a wait. The logging test now uses the project's configured log level.
- **Verification:** The three regression cases failed against the original implementation before the fixes were applied. Changes are local and uncommitted; no pull request or push was made.

### FIX-21 Split the mock notice page-drawing functions (#647)

- **What the AI produced:** the split of `_draw_cover_page` and `_draw_calculation_page` into one helper per block of the page; the four functions that choose the text and row order (`review_message`, `important_message`, `calculation_order`, `change_explanation`); and `tests/test_layout.py`, written before the code.
- **How we verified it:** `test_committed_output_is_up_to_date` regenerates the 50 notices and still matches the committed files byte for byte. Seven deliberate bugs were each caught: five by the new tests, and two drawing changes (row spacing and the gap above the explanation) by the committed-output test. 34 tests passed and ruff was clean; these were local runs, because CI does not run this tool's tests.
- **Problems found and corrections:** the first plan had a test that "377.1" sorts as a number rather than as text. Every real line number has three digits, so both orders agree and that test could never fail. It was replaced by a test that a line only declared is placed in number order.

### SET-33 Colour prototypes and design docs (#651)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-33-colour-prototypes-and-design-docs-651).

### FIX-15 Seed command boundary and household expiry (#641)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#fix-15-seed-command-boundary-and-household-expiry-641).

### T-01.01.1 Sign-in and sign-out tests (#423)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01011-sign-in-and-sign-out-tests-423).

### T-01.01.3 Sign-in screen and session handling (#425)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01013-sign-in-screen-and-session-handling-425).

### T-01.01.2 User model and authentication (#424)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01012-user-model-and-authentication-424).

### T-00.01.4 Categories reference module (#377) and SET-14 Module skeletons (#405)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-00014-categories-reference-module-377-and-set-14-module-skeletons-405).

### SET-15 OpenAPI and TypeScript generation (#406)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-15-openapi-and-typescript-generation-406).

### T-00.01.1 Backend project (#374)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-00011-backend-project-374).

### T-00.01.2 Frontend project (#375)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-00012-frontend-project-375).

### T-00.01.3 Docker Compose and README (#376)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-00013-docker-compose-and-readme-376).

### SET-01 Setup hardening (#373, #374–#376)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-01-setup-hardening-373-374376).

### SET-32 SonarQube Cloud quality gate (#595)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-32-sonarqube-cloud-quality-gate-595).

### SET-02 CI workflow and branch protection (#378, #379, #380, #381)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-02-ci-workflow-and-branch-protection-378-379-380-381).

### SET-13 Glossary and French/English terminology (#404)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-13-glossary-and-frenchenglish-terminology-404).

### SET-09 Mock notices of assessment (#397, #398, #399, #400)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-09-mock-notices-of-assessment-397-398-399-400).

### SET-05 Database schema review and ERD (#384)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-05-database-schema-review-and-erd-384).

### SET-06 Architecture diagrams

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-06-architecture-diagrams).

### SET-08.3 Git hooks and commit policy

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-083-git-hooks-and-commit-policy).

### T-00.08.1 Official LICO table (#394)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-00081-official-lico-table-394).

### T-00.08.2 LICO threshold seed

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-00082-lico-threshold-seed).

### T-02.11.1 B.A.D.R. first store tests (#439)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-02111-badr-first-store-tests-439).

### T-02.11.2 Store model and migration (#441)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-02112-store-model-and-migration-441).

### T-02.11.3 B.A.D.R. seed (#442)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-02113-badr-seed-442).

### SET-12 Listing categories and safety lists (#403)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#set-12-listing-categories-and-safety-lists-403).

### T-05.33.3 Posting service/API and T-05.33.1 tests (#494, #492)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-05333-posting-serviceapi-and-t-05331-tests-494-492).

### SET-16 Design system, translations and app shell (#407)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#set-16-design-system-translations-and-app-shell-407).

### T-05.33.4 Posting form (#495)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-05334-posting-form-495).

### T-05.33.5 Time-to-post check (#496)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-05335-time-to-post-check-496).

### T-03.17.2 and T-03.17.3 Walk-in household registration (#463, #464; US-17)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-03172-and-t-03173-walk-in-household-registration-463-464-us-17).

### T-03.17.4 Walk-in form screens and T-03.17.1 tests (#465, #462; US-17)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-03174-walk-in-form-screens-and-t-03171-tests-465-462-us-17).

### SET-19 AI reading spike (#410)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#set-19-ai-reading-spike-410).

### US-34 Listing safety checks (#497: #498, #499, #500)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#us-34-listing-safety-checks-497-498-499-500).

### T-05.35.2 Category admin API and screen and T-05.35.1 tests (#503, #502; US-35)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#t-05352-category-admin-api-and-screen-and-t-05351-tests-503-502-us-35).

### SET-34 Colour tokens and status badge (#652, #653, #654)

Detailed colour implementation, review history, changed-file declarations and
verification evidence are preserved in
[the historical verification ledger](docs/05-process/ai-usage-verification-2.md#set-34-colour-tokens-and-status-badge-652-653-654).

### FIX-07 Deny-by-default endpoint access test (#633)

- **Feature or task:** FIX-07 (#633), the automatic SEC-05 check: every API endpoint must refuse anonymous visitors and every role it does not allow, and a new endpoint without an entry in the access table fails the build.
- **What the AI produced:** with Claude Code, under Ammar Ranko's direction: `backend/tests/test_endpoint_access.py` (route discovery through Django's URL resolver, the `ACCESS`, `PUBLIC` and `NON_DRF` tables, a spy on DRF's permission check, and the anonymous and per-role tests), the Permissions row in `docs/03-design/api.md`, and this entry.
- **Developer direction and review:** Ammar chose the design: walk the resolver rather than list endpoints by hand, keep public endpoints and plain Django routes as explicit exceptions with a written reason, and judge each request by DRF's permission step rather than the status code alone. He reviewed the code line by line and checked the results locally before the pull request.
- **How we verified it:** the test file runs every DRF endpoint anonymously (unless public) and as each of the five roles against PostgreSQL, plus checks for missing or stale table entries, unlisted plain Django routes, and stand-in `path`, `re_path` and ViewSet routes. Ruff and mypy pass.
- **Problems found and corrections:**
  - Anonymous requests answered 401, not 403, because session authentication sends a `WWW-Authenticate` header; the anonymous test accepts both.
  - The peer review of #673 (MassPaol) and CodeRabbit found that only allowed roles were checked against the permission step: for anonymous visitors and refused roles, any 403 passed, including one raised later by a query or service (for example the household search query). A permission class raising by itself also skipped the first spy on `permission_denied`. The spy now wraps `check_permissions` and records whether the request passed or was refused there, and every case asserts it.
  - The review also found that the AI's discovery code missed ViewSet routes (their handlers are named `list` and `create`, so no methods were found and nothing was called) and `re_path` routes (their text starts with `^api/`). Both are now detected, with tests, and a DRF endpoint with no methods fails.
  - The AI's reason for the public schema ("for the generated TypeScript client") was wrong: `pnpm gen:api` builds the schema with `manage.py`, not the URL. The reason was corrected. FIX-04 (#630) now restricts production schema/docs access to active Iris admins; this table describes the local/test settings, with production access covered separately.
  - The AI's comments referred to a role matrix in `business-rules.md` that does not exist yet; they now point to US-07 (#434), and the `api.md` row states exactly what the test does and does not call.
  - The review also asked for the project's `UserFactory` instead of `create_user`, a skip instead of a `KeyError` for an endpoint missing from the table, and the reason check folded into the access-table test rather than kept as its own test. All done.
  - Two CodeRabbit pre-merge checks were answered without changes: the overlap with `test_signed_out_cannot_search` is intended, since this test covers every endpoint automatically; and splitting this shared file is a team decision.
- **Remaining:** after merge, the wiki Testing Plan and Security pages get SEC-05's status and a link to the test.

### T-04.32.2 Suspend service and buttons and T-04.32.1 tests (#489, #488; US-32)

- **What the AI produced:** Codex implemented the admin-only suspend/reactivate endpoints, atomic cancellation of reserved reservations with stock release, audit actions and reasons, localized post-commit holder email, the staff household actions screen, API types, tests and documentation.
- **Owner's decisions:** preserve the approval expiry; reactivate only before expiry; cancel only `reserved` reservations with `late_cancel=false`; allow counter-only files without email to change status; log email delivery failures without rolling back; keep the design within existing services and adapters.
- **Verification:** focused household and audit backend tests, frontend component tests, Ruff, mypy, import-linter, migration checks, TypeScript, ESLint and Prettier. Full frontend tests pass except the existing usability preview tests when sandbox networking forbids their local listener; they are rerun outside that restriction.

### T-05.36.3 Browse and detail screens and T-05.36.1 tests (#507, #505; US-36)

- **What the AI produced:** with Claude Code, under Anthony Monaco's direction: the household browse screen (`/listings`: today, category and store filter chips with bottom sheets, cards, 20 more on request, the not-approved and no-result states) and the listing detail screen (`/listings/:id`), built from the Figma H1 "Find and reserve" frames; the client for `GET /api/listings/`; Montreal-time formatting of pickup windows and dates; French and English texts; 33 tests.
- **Owner's decisions:** no backend change: the detail screen reuses the browse card (description, total quantity, maximum per household and pickup instructions wait for the planned `GET /api/listings/{id}/`), and a link opened directly finds its card in the browse pages; reserving is left to US-41; the store filter offers the stores of the listings loaded so far, as households have no store list; the H1 mockup colours apply to these two screens only, through scoped CSS variables, while the rest of the app keeps SET-16's grayscale theme.
- **How we verified it:** the 33 new tests pass with the rest of the frontend suite (502 tests) (about 97% line coverage of the new code), with axe checks on the list, the no-result, the not-approved and the detail states; TypeScript, ESLint and Prettier pass. The screens were screenshotted in Edge emulating a 360 x 800 phone: list, detail, category sheet, active filters and no results, none wider than 360 px. Anthony reviewed the code and checked the screens himself in the preview.
- **Problems found and corrections:**
  - The translation files are now merged with a shallow spread (FIX-10), so new `listing.*` keys in `household.json` would have replaced the store's `listing.*` keys; the new keys are under `household.browse` and `household.listingDetail` instead.
  - Server errors were first retried with back-off, which delayed the error screen by seconds; a server answer now shows at once with « Réessayer », and only a lost connection is retried.
  - Running Prettier on whole folders converted the line endings of teammates' files; those files were restored, leaving only the intended changes.

### FIX-03 Eligibility decision refactor and application logging (#629)

- **Tool and contribution level:** OpenAI Codex; 50% or more AI-generated. Extracted evidence validation and staff authorization, renamed the public exception to `EligibilityEvidenceUnavailableError`, and added post-commit `eligibility_decided` logging with an event-specific JSON allowlist. Income amounts, names and evidence stay out of the event.
- **AI-assisted files:** `backend/modules/eligibility/services.py`, `backend/modules/eligibility/tests/test_decision_service.py`, `backend/iris/observability.py`, `backend/tests/test_observability.py`, `backend/modules/eligibility/README.md`, `docs/guides/observability.md`, `AI_USAGE.md`.
- **Verification:** existing eligibility assertions retained with renamed exception references; new caplog/JSON tests cover staff/automatic decisions, both outcomes, per-decision snapshots, invalid evidence, rollback, failed inserts and privacy filtering. Full PostgreSQL run: 1,936 passed, 5 skipped, slow-expiry deselected, 95.54% coverage. Focused run: 114 passed, 91.72% coverage. Ruff, mypy (399 files), four import contracts, Django/migration checks, pip-audit and 36 PR-policy tests pass.
- **Corrections and review follow-up:** logging extras required a matching formatter allowlist. Windows-mounted startup/load timing failures cleared in a byte-verified native Linux copy, with thresholds unchanged. A full tracked-repository search for the retired exception name found no remaining references, including imports outside the eligibility module.
- **Owner review and pull request:** owner reviewed, committed and pushed [PR #687](https://github.com/B-A-D-R-SL/iris/pull/687); Codex did not commit or push. The review-status wording and typo were corrected, and this entry was condensed without removing verification history to respect the 500-line file limit.
