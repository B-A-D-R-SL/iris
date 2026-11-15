<!-- AI contribution: 50% or more AI-generated -->

<!-- FIX-08 synchronization with main, 14 November 2026: resolved five conflicts
against 27946c1, retained US-18 approvals/FIX-14 contact tests and unified the
workflow/API docs. Approval assertions now distinguish submission, eligibility
and outcome audits, including rollback and concurrency. The actor constraint is
added NOT VALID and validated after committing its brief lock; fixtures use
factories. Validation: 546 selected backend cases passed (545 in the suite and
the corrected import case on retry), 62 frontend cases passed; Ruff, mypy,
four import contracts, Django/migration checks, API drift and frontend build
passed. The resolved merge is left for the owner's commit/push and remote CI. -->

<!-- FIX-08 review verification, 14 November 2026: 288 targeted PostgreSQL tests
and 973 related household/store/rule/access tests passed; 55 frontend tests passed.
Audit/eligibility branch coverage: 94.90%. Ruff, mypy (434 sources), all four
import contracts, Django/schema checks, frontend types/lint/format/build and
offline PR policy passed. All 55 original split-file tests were retained once.
The unchanged HTTP load benchmark and optional slow-expiry case were excluded.
PR metadata and issue links were updated; commit/push, remote CI and post-merge
signed-off remain owner actions. No review replies were posted by Codex. -->
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
| FIX-24 Dockerfile hardening (#615) | Backend/frontend Dockerfiles and ignore files, Compose and sample environment, CI container smoke runner and HTTP boundary tests, frontend API-generation tests, README and container/production guides, this record. | 50% or more AI-generated (OpenAI Codex) | [#711](https://github.com/B-A-D-R-SL/iris/pull/711) |
| SET-17 Azure staging and deploy workflow (#408) | Root release `Dockerfile`/`.dockerignore`, staging settings/routes/views/setup/supervision and tests, backend server dependencies, CI/deploy workflows and helper tests, staging guides and region/cost ADR, architecture, `AI_USAGE.md` | 50% or more AI-generated; lockfile generated | Owner review pending (`setup/SET-17`) |
| FIX-08 Household access and eligibility audit (#634) | `backend/modules/audit/{models.py,services.py,api/serializers.py,migrations/0006_household_events_and_system_actor.py,migrations/0007_enforce_system_actor.py,tests/,locale/fr/LC_MESSAGES/,README.md}`, `backend/modules/households/{services.py,api/views.py,tests/factories.py,tests/test_walk_in_audit.py,tests/approval/{helpers,test_outcomes,test_side_effects}.py,README.md}`, `backend/modules/eligibility/{queries.py,services.py,tests/,README.md}`, `backend/pyproject.toml`, `frontend/src/areas/staff/pages/{Audit.test.tsx,AuditComponents.tsx,auditHelpers.ts,WalkIn/WalkIn.tsx,WalkIn/WalkIn.test.tsx}`, `frontend/src/shared/i18n/{en,fr}/staff.json`, `docs/02-requirements/business-rules.md`, `docs/03-design/{api,household-api}.md`, `docs/04-architecture/{architecture,architecture-workflows,workflow-diagrams}.md`, `AI_USAGE.md`; generated API types | 50% or more AI-generated (OpenAI Codex; audit migrations explicitly declared; compiled catalog and generated API types exempt) | [#701](https://github.com/B-A-D-R-SL/iris/pull/701); review fixes validate saved automatic decisions, enforce database actor consistency, prevent background detail refetches, translate errors and split oversized tests/docs |
| FIX-29 Audit the walk-in notice and decision summary screens (#713) | `backend/modules/households/{notice_services.py,api/views.py,api/notice_views.py,api/approval_views.py,README.md}`, `backend/modules/households/tests/{test_walk_in_audit,test_walk_in_approve_api}.py`, `docs/02-requirements/business-rules.md`, `docs/03-design/household-api.md`, `AI_USAGE.md` | 50% or more AI-generated (Claude Code) | The pull request that closes #713. Verified by the audit tests written first and watched failing: each read and notice recording records one event, while refused requests, HEAD probes and a failed audit write record and disclose nothing |
| FIX-14 Shared contact rules and auth/store cleanup (#640) | `backend/modules/common/`, `backend/iris/observability.py`, household/store models, serializers, admin and contact tests; shared JSON contact fixtures; frontend form normalizers/fields/tests, auth API/context/provider, sign-in/sign-out, translations and ESLint exemption; contact/auth/architecture/observability documentation and implementation draft. Review fixes add private rejection diagnostics and exact paste-retention assertions. New migrations update validator state without rewriting data. | 50% or more AI-generated (OpenAI Codex; generated migrations exempt) | [#702](https://github.com/B-A-D-R-SL/iris/pull/702) |
| US-18 review fixes by Massimo on PR #698 (#466, #468) | `backend/modules/households/{services,notice_services,_approval}.py`, `backend/modules/households/README.md`, `backend/modules/households/tests/test_walk_in_notice_safety.py`, `backend/modules/documents/{services,messages}.py`, `backend/modules/documents/domain/notice.py`, `backend/modules/documents/README.md`, `backend/modules/documents/locale/fr/LC_MESSAGES/django.po`, `backend/modules/documents/tests/{test_notice_rules,test_notice_rule_limits}.py`, `backend/modules/rules/{domain/schemas.py,tests/test_schemas.py}`, `backend/modules/accounts/queries.py`, `backend/tests/test_file_store.py`, `frontend/src/areas/staff/pages/WalkIn/NoticesDecision.test.tsx`, `frontend/src/shared/i18n/{en,fr}/staff.json`, `docs/02-requirements/business-rules.md`, `AI_USAGE.md` | 50% or more AI-generated; compiled catalog exempt | The US-18 pull request into `main` (#698) |
| US-18 CodeRabbit fixes on PR #698 (#466, #470) | `backend/.env.example`, `backend/adapters/file_store/azure_blob.py`, `backend/tests/test_file_store.py`, `backend/modules/documents/tests/{test_notice_rules,test_income_notice_model,test_record_notice,test_file_link_api}.py`, `backend/modules/rules/tests/test_schemas.py`, `frontend/src/areas/staff/pages/WalkIn/{Notices,Notices.test}.tsx`, `backend/modules/households/{queries,services}.py`, `backend/modules/households/README.md`, `backend/modules/households/tests/{conftest,test_submission,test_submission_api,test_submission_concurrency,test_household_size}.py`, `docs/02-requirements/business-rules.md`, `docs/04-architecture/architecture.md`, `AI_USAGE.md` | 50% or more AI-generated | The US-18 pull request into `main` (#698) |
| US-18 merge of `main` after US-57 email system (#466, #698) | `backend/modules/notifications/{services.py,README.md,tests/test_set_password_email.py}`, `backend/modules/households/{README.md,tests/test_walk_in_approval.py}`, `backend/iris/settings/{base,local,test}.py`, `backend/{.env.example,conftest.py,pyproject.toml,uv.lock}`, `backend/modules/accounts/queries.py`, `AI_USAGE.md` | 50% or more AI-generated; `uv.lock` generated | The US-18 pull request into `main` (#698) |
| US-18 into main: merge of `main` and submit before approval (#466, #470) | `backend/modules/households/{services,queries,policies,_approval,approval_services,notice_services}.py`, `backend/modules/households/api/{urls,approval_views,notice_views}.py`, `backend/modules/households/{README.md,locale/fr/LC_MESSAGES/django.po}`, `backend/modules/households/tests/test_walk_in_approve_api.py`, `backend/modules/households/tests/approval/{conftest,helpers,test_outcomes,test_side_effects}.py` and `backend/modules/households/tests/notices/{conftest,helpers,test_record_notice,test_member_edits_and_list}.py` (split from `test_walk_in_approval.py` and `test_walk_in_notices.py`), `backend/iris/observability.py`, `backend/tests/test_observability.py`, `backend/modules/eligibility/services.py`, `backend/modules/accounts/queries.py`, `backend/modules/audit/services.py`, `backend/modules/notifications/{services.py,README.md}`, `backend/modules/rules/{domain/schemas.py,tests/test_schemas.py}`, `backend/iris/settings/{base,production}.py`, `backend/{.env.example,pyproject.toml}`, `backend/tests/test_endpoint_access.py`, `frontend/src/areas/staff/pages/WalkIn/{Notices,NoticeCard,NoticeFields,NoticeSummary,DecisionSummary,DecisionOutcome}.tsx`, `frontend/src/areas/staff/pages/WalkIn/{Notices.test,NoticesDecision.test,DraftSaved}.tsx`, `frontend/src/test/walkInNotices.tsx`, `frontend/src/areas/staff/pages/WalkIn/{noticeForm,noticeForm.test,shownDecision,useDecision,useLanguage,useNoticeCard,useNoticeEditing}.ts`, `frontend/src/areas/staff/pages/WalkIn/WalkIn.module.css`, `frontend/eslint.config.js`, `frontend/src/features/households/noticeApi.ts`, `frontend/src/shared/i18n/{en,fr}/staff.json`, `frontend/src/app/routes/staffRoutes.tsx`, `frontend/src/shared/api/generated.d.ts`, `docs/02-requirements/{business-rules,forms-and-fields}.md`, `docs/03-design/api.md`, `docs/04-architecture/architecture.md`, `docs/guides/observability.md`, `AI_USAGE.md` | 50% or more AI-generated; generated API declarations and compiled catalogs exempt | The US-18 pull request into `main` |
| US-18 Walk-in approve endpoint (#466) | `backend/modules/households/api/{approval_views,urls}.py`, `backend/modules/households/tests/test_walk_in_approve_api.py`, `backend/modules/households/README.md`, `docs/03-design/api.md`, generated API types, `AI_USAGE.md` | 50% or more AI-generated; generated API declarations exempt | [#675](https://github.com/B-A-D-R-SL/iris/pull/675) into US-18, then the US-18 pull request into `main` |
| T-03.18.4 Walk-in notices and decision summary screen (#470) | `frontend/src/areas/staff/pages/WalkIn/{Notices,Notices.test,noticeForm,noticeForm.test}.ts(x)`, `frontend/src/features/households/noticeApi.ts`, `frontend/src/areas/staff/pages/WalkIn/{DraftSaved,WalkIn}.tsx`, `frontend/src/app/App.tsx`, `frontend/src/shared/i18n/{fr,en}/staff.json`, `docs/02-requirements/forms-and-fields.md`, `docs/04-architecture/architecture.md`, `AI_USAGE.md` | 50% or more AI-generated | [#675](https://github.com/B-A-D-R-SL/iris/pull/675) into US-18, then the US-18 pull request into `main` |
| US-57 Email system and core emails (#538; tests #539, adapters #540, templates/jobs #541) | `backend/adapters/mailer/`, `backend/modules/notifications/`, account/store integrations including merged main/US-13 approval, rejection and reissue, affected household tests, rules/audit policy registration, settings/configuration/tests, environment examples, Compose, documentation and `AI_USAGE.md`. The owner chose to preserve US-13's bounded stored rejection reason in its dedicated email. PR #697 review fixes contain known-template email validation failures, preserve the producer-validated US-32 suspension/reactivation reason with a 2,000-character queued capture ceiling, and skip unsupported allauth prefixes with static logging. The CodeRabbit follow-up adds central-reference size justifications, safe invalid Azure Retry-After diagnostics, and existing BR-ID traceability in tests (BR-PARTNER-05 for recovery/invitation preflight). The later FIX-17 merge adds CI compatibility through synthetic SMTP/public sender/HTTPS origin configuration and invalid ZAP-report rejection, preserving runtime guards and upstream verification history. Merging FIX-12 also requires conditional forwarding of supplied blur/focus handlers in `frontend/src/shared/forms/fieldProps.ts`, preserving invitation password validation; `frontend/src/areas/public/pages/AcceptInvitation.test.tsx` adds the blur regression. [Verification and corrections](backend/modules/notifications/README.md#pr-verification-and-set-17-handoff) distinguish historical results, passing targeted checks and the successful native worker/Mailpit rerun from deployed Azure verification owned by SET-17. | 50% or more AI-generated (OpenAI Codex; generated migration and lockfile exempt) | [#697](https://github.com/B-A-D-R-SL/iris/pull/697) |
| FIX-13 App shell: routes per area, layer rule, no placeholder routes (#639) | `frontend/eslint.config.js`, `frontend/src/app/{App,App.test,navigation,navigation.test,PlaceholderScreen,RequireRole,RequireHouseholdSearch}.ts(x)`, `frontend/src/app/routes/*.tsx`, `frontend/src/app/layouts/{StaffLayout,MobileAreaLayout}.tsx`, `frontend/src/shared/auth/{roles,roles.test,currentUser,currentUser.test,authContext,AuthProvider}.ts(x)`, `frontend/src/shared/ui/{AppBar.tsx,AppBar.module.css,index.ts}`, `frontend/src/shared/forms/{validators.ts,validators.test.tsx}`, `frontend/src/test/{lintRules.test.ts,render.tsx}`, `docs/guides/design-system.md` | 50% or more AI-generated | [#695](https://github.com/B-A-D-R-SL/iris/pull/695) |
| FIX-12 Split the listing posting screen and log posting failures (#638) | `frontend/src/areas/store/pages/{NewListing.tsx,useNewListingMutation.ts,NewListing.test.tsx}`, `frontend/src/areas/store/components/{NewListingSections.tsx,CategoryPicker.tsx}`, `frontend/src/shared/forms/{fieldProps.ts,TextField.tsx,IntegerField.tsx,FileUpload.tsx}`, `frontend/src/shared/{logger.ts,logger.test.ts}`, `frontend/src/features/listings/{api.ts,api.test.ts}` | 50% or more AI-generated | [#689](https://github.com/B-A-D-R-SL/iris/pull/689) |
| FIX-17 CI security gates: gitleaks and ZAP baseline (#643) | `.github/workflows/ci.yml`, `.github/scripts/{zap_gate,test_zap_gate}.py`, `.gitleaks.toml`, `.zap/rules.tsv`, `backend/iris/settings/ci_scan.py`, `backend/tests/test_ci_scan_settings.py`, `README.md`, `AI_USAGE.md` | 50% or more AI-generated | [#676](https://github.com/B-A-D-R-SL/iris/pull/676) |
| SET-35 create-pr skill for opening pull requests (#692) | `.claude/skills/create-pr/{SKILL.md,scripts/check_pr.py}`, `docs/guides/create-pr.md`, `AI_USAGE.md` | 50% or more AI-generated | [#693](https://github.com/B-A-D-R-SL/iris/pull/693) |
| T-02.13.4 Partner review screens (#451) | `frontend/src/areas/staff/pages/PartnerApplications{,.test}.tsx`, `frontend/src/app/App{,.test}.tsx`, `frontend/src/shared/i18n/{en,fr}/store.json`, `frontend/src/shared/logger.ts`, `.env.example`, `docker-compose.yml`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.3 Partner applications staff API (#450) | `backend/modules/stores/{queries.py,README.md,api/serializers.py,api/staff_views.py,api/staff_urls.py,tests/test_staff_application_api.py,locale/fr/LC_MESSAGES/django.po}`, `backend/iris/urls.py`, `backend/pyproject.toml`, `docs/03-design/api.md`, `docs/04-architecture/architecture.md`, generated API types, `AI_USAGE.md` | 50% or more AI-generated; compiled catalog and generated API declarations exempt | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.1 Partner application review tests (#448) | `backend/modules/stores/tests/{conftest,test_application_decisions,test_application_recovery,test_staff_application_api}.py`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-02.13.2 Partner application decision service (#449) | `backend/modules/stores/{services.py,management/commands/resend_partner_invitation.py,tests/test_application_decisions.py,README.md}`, `backend/modules/accounts/services.py`, `backend/iris/{settings/base.py,observability.py}`, `backend/tests/test_observability.py`, `backend/.env.example`, `backend/pyproject.toml`, `AI_USAGE.md` | 50% or more AI-generated | [#665](https://github.com/B-A-D-R-SL/iris/pull/665) |
| T-05.36.3 Browse and detail screens (#507) and T-05.36.1 tests (#505) | `frontend/src/areas/household/` (`pages/{Listings,ListingDetail}.tsx` and their CSS and tests, `components/`, `browseFilters.ts`, `listingFormat.ts`, `useListingText.ts`, `household.module.css`, tests), `frontend/src/features/listings/browse.ts` and its tests, `frontend/src/app/App.tsx`, `frontend/src/shared/i18n/{fr,en}/household.json` | 50% or more AI-generated | Not yet opened (`US-36-browse-and-detail-screens` branch) |
| T-06.44.3 Scan screen (#523), part of US-44 (#520) | `frontend/src/areas/store/pages/{Confirm,ConfirmSteps,useConfirmPickup,usePickupClock,confirmCode,confirmFormat,confirmFacts,confirmMessages}.*`, `frontend/src/areas/store/components/PickupScanner.*`, `frontend/src/features/reservations/pickupApi.ts` and tests, `frontend/src/app/App.tsx`, `frontend/src/shared/{i18n/{en,fr}/household.json,logger.ts}`, `frontend/{package.json,vite.config.ts}`, `frontend/pnpm-lock.yaml`, `backend/iris/settings/local.py`, `docker-compose.yml`, `.env.example`, `AI_USAGE.md` | 50% or more AI-generated; lockfile exempt | [#686](https://github.com/B-A-D-R-SL/iris/pull/686) |
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
| T-03.18.2 IncomeNotice model and upload (#468) and its T-03.18.1 tests (#467) | `backend/adapters/file_store/`, `backend/modules/documents/` (domain, messages, model, services, queries, API, French catalogue, tests, README), `backend/modules/households/{services.py,domain/person.py,api/notice_serializers.py,api/notice_views.py,api/urls.py,tests/test_walk_in_notices.py,tests/test_walk_in_holder_edits.py,tests/test_person.py,README.md}`, `backend/modules/accounts/{queries.py,tests/test_intake_staff.py}`, `backend/modules/rules/domain/schemas.py`, `backend/iris/{urls.py,settings/}`, `backend/conftest.py`, `backend/tests/test_file_store.py`, `docker-compose.yml`, docs (`business-rules.md`, `api.md`, `database-schema.md`, `architecture.md`) | 50% or more AI-generated; Below 50% AI-generated for `backend/modules/rules/tests/test_schemas.py`, `backend/.env.example` and `docs/02-requirements/business-rules.md`; generated migration, `uv.lock`, `.mo` files and API declarations exempt | [#661](https://github.com/B-A-D-R-SL/iris/pull/661) |
| US-41 Reserve a unit (#513: #514, #515, #516, #517) | `backend/modules/reservations/{models.py,migrations/0002_reservation_timestamps_and_indexes.py,domain/codes.py,domain/limits.py,services.py,api/reserve_views.py,api/reserve_serializers.py,api/urls.py,locale/fr/LC_MESSAGES/,README.md}`, `backend/modules/reservations/tests/{factories.py,test_reserve_domain.py,test_reservation_model.py,test_reserve_service.py,test_reserve_api.py,test_concurrency.py}`, `backend/modules/listings/{services.py,queries.py,README.md,tests/test_take_units.py}`, `backend/modules/households/{services.py,README.md,tests/test_lock_household.py}`, `frontend/src/features/reservations/` (`api.ts`, `ReserveButton.tsx`, `QuantityPicker.tsx` and its CSS, `quantity.ts`, `RefusalNotice.tsx` and its CSS, `refusalMessage.ts`, `ReservationConfirmation.tsx` and its CSS, and tests), `frontend/src/areas/household/household.module.css`, `frontend/src/areas/household/pages/{ListingDetail.tsx,ListingDetail.module.css,ListingDetail.test.tsx,ListingDetailReserve.test.tsx,testListings.ts}`, `backend/modules/rules/{domain/schemas.py,tests/test_schemas.py}`, `backend/modules/reservations/api/serializers.py`, `backend/tests/test_endpoint_access.py`, translations, regenerated API types, `docs/02-requirements/business-rules.md`, `docs/03-design/api.md`, `AI_USAGE.md`, `docs/05-process/ai-usage-verification-2.md` | 50% or more AI-generated (generated API declarations and compiled catalog exempt) | Not yet opened (`feat/US-41-reserve-a-unit` branch) |

## Examples, verification and corrections

Historical examples are preserved in the linked verification records. The headings remain here so existing feature anchors continue to resolve.

The US-13 records below describe PR #665's original implementation and verification. Later US-57 queue/template integration is recorded in the [notification runbook](backend/modules/notifications/README.md); earlier test counts are historical, not results for the merged integration.

### US-18 review fixes by Massimo on PR #698 (#466, #468)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#us-18-review-fixes-by-massimo-on-pr-698-466-468).

### US-18 CodeRabbit fixes on PR #698 (#466, #470)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#us-18-coderabbit-fixes-on-pr-698-466-470).

### US-18 merge of `main` after US-57 email system (#466, #698)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#us-18-merge-of-main-after-us-57-email-system-466-698).

### US-18 into main: merge, conflict resolution and submit before approval (#466, #470)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#us-18-into-main-merge-conflict-resolution-and-submit-before-approval-466-470).

### SET-35 create-pr skill for opening pull requests (#692)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#set-35-create-pr-skill-for-opening-pull-requests-692).

### T-02.13.1 Partner application review tests (#448)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-02131-partner-application-review-tests-448).

### T-02.13.2 Partner application decision service (#449)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-02132-partner-application-decision-service-449).

### PR #665: review follow-up for the staff screen and API tests

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#pr-665-review-follow-up-for-the-staff-screen-and-api-tests).

### FIX-02 Private listing-photo processing and storage (#628)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-02-private-listing-photo-processing-and-storage-628).

### US-25 Duplicate checking and tests (#479, #478)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-25-duplicate-checking-and-tests-479-478).

### US-63 Household search and tests (#552, #553, #554)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-63-household-search-and-tests-552-553-554).

### PR #665: server-owned availability and main conflict resolution

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#pr-665-server-owned-availability-and-main-conflict-resolution).

### T-01.04.3 Invitation password page (#431)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01043-invitation-password-page-431).

### T-01.04.2 Invitation model, services and acceptance API (#430)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01042-invitation-model-services-and-acceptance-api-430).

### T-01.04.1 Invitation acceptance tests (#429)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-01041-invitation-acceptance-tests-429).

### T-09.62.3 Audit search API and screen (#550)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-09623-audit-search-api-and-screen-550).

### FIX-11 Shared role groups and authentication events (#637)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-11-shared-role-groups-and-authentication-events-637).

### FIX-04 Production settings and entry points (#630)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-04-production-settings-and-entry-points-630).

### FIX-23 Frontend development dependency security (#614)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-23-frontend-development-dependency-security-614).

### FIX-10 Translation files by area (#636)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-10-translation-files-by-area-636).

### T-09.62.1–2 Audit tests and service (#548, #549)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-096212-audit-tests-and-service-548-549).

### T-02.12.3 Become a partner page (#446)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#t-02123-become-a-partner-page-446).

### US-16 Eligibility engine (#457)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#us-16-eligibility-engine-457).

### SET-18 Seed data generator (#409)

[Verification and corrections](docs/05-process/ai-usage-verification-1.md#set-18-seed-data-generator-409).

### T-06.44.3 Scan screen (#523)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-06443-scan-screen-523).

### T-06.44.2 Confirm pickup service and API, with T-06.44.1 tests (#522, #521)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-06442-confirm-pickup-service-and-api-with-t-06441-tests-522-521).

### US-44 local review follow-up (#522)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#us-44-local-review-follow-up-522).

### FIX-21 Split the mock notice page-drawing functions (#647)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-21-split-the-mock-notice-page-drawing-functions-647).

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

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#set-34-colour-tokens-and-status-badge-652-653-654).

### FIX-07 Deny-by-default endpoint access test (#633)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-07-deny-by-default-endpoint-access-test-633).

### T-03.18.2 IncomeNotice model and upload and T-03.18.1 tests (#468, #467; US-18)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-03182-incomenotice-model-and-upload-and-t-03181-tests-468-467-us-18).

### T-03.18.3 Walk-in approval (#469), local work on 2026-11-08

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-03183-walk-in-approval-469-local-work-on-2026-11-08).

### T-04.32.2 Suspend service and buttons and T-04.32.1 tests (#489, #488; US-32)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-04322-suspend-service-and-buttons-and-t-04321-tests-489-488-us-32).

### T-05.36.3 Browse and detail screens and T-05.36.1 tests (#507, #505; US-36)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#t-05363-browse-and-detail-screens-and-t-05361-tests-507-505-us-36).

### FIX-05 Request and email failure diagnostics (#631)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-05-request-and-email-failure-diagnostics-631).

### FIX-12 Split the listing posting screen and log posting failures (#638)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-12-split-the-listing-posting-screen-and-log-posting-failures-638).

### FIX-03 Eligibility decision refactor and application logging (#629)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-03-eligibility-decision-refactor-and-application-logging-629).

### FIX-13 App shell: routes per area, frontend layer rule, no placeholder routes (#639)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-13-app-shell-routes-per-area-frontend-layer-rule-no-placeholder-routes-639).

### FIX-14 Shared phone/postal rules and auth/store cleanup (#640)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-14-shared-phonepostal-rules-and-authstore-cleanup-640).

### FIX-01 Listing posting refactor and failure logging (#627)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-01-listing-posting-refactor-and-failure-logging-627).

### US-41 Reserve a unit (#513: #514, #515, #516, #517)

[Verification and corrections](docs/05-process/ai-usage-verification-2.md#us-41-reserve-a-unit-513-514-515-516-517).

### FIX-24 Dockerfile hardening (#615)

[Verification and corrections](docs/05-process/ai-usage-verification-3.md#fix-24-dockerfile-hardening-615).

### SET-17 Azure staging and PR #700 review follow-up

[Verification and corrections](docs/05-process/ai-usage-set17.md).
