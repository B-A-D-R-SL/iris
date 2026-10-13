# Iterations 1 and 2 in detail

Iteration 1 (Oct 5–6): setup and planning by Ammar and Danial. Iteration 2 (Oct 7–20): foundations and design, so everyone learns the project before building features. Everything is merged by **Sunday Oct 18 at 11:59 pm**, reviewed Monday Oct 19 and submitted Tuesday Oct 20.

## Hand-offs inside Iteration 2

| Date | Who | Hands over | Needed by |
| --- | --- | --- | --- |
| Thu Oct 8 | Ammar | Minimal skeleton running with one command (SET-01) | Everyone who writes code |
| Fri Oct 9 | Ryan | Final category list (SET-12) | Ammar's reference module (SET-01 task 4) |
| Fri Oct 9 | Reuven | RuleSetVersion model (SET-07 task 1) | Leon's threshold seed (SET-08 task 2) |
| Mon Oct 12 | Leon | Thresholds fetched (SET-08 task 1) | Reuven's default seed (SET-07 task 3) |
| Wed Oct 14 | Massimo | First 20 mock notices (SET-09) | The AI spike and seed data in Iteration 3 |
| Thu Oct 15 | Each pair | Schema review done (SET-05) | Iteration 3 migrations |

## Iteration 1 (Release 1)

### [SET-03] Project board and repository settings

Suggested owner: **Danial Kouba** · 2 points · Oct 5–Oct 6 · depends on — · blocks —

Done when:

- Project Iris board with Board, By iteration, Roadmap and My work views
- Labels epic, user-story and task; one milestone per iteration
- Everyone has write access to the repository and the board
- Actions allowed to create issues; CodeRabbit installed


### [SET-04] Planning documents and Iteration 1 submission

Suggested owner: **Ammar Ranko** · 2 points · Oct 5–Oct 6 · depends on — · blocks —

Done when:

- Push-now documents committed: README, CONTRIBUTING, AI_USAGE.md, project overview, how we work, testing strategy, release plan, Iteration 2 plan, decision records 0001 to 0004
- Tag Iteration1 created on the submitted version
- Kickoff meeting notes saved in docs/meetings/2026-10-05.md
- Iteration 1 submitted with links to the documents, repository and board


## Iteration 2 (Release 1)

### [SET-01] Repo skeleton and reference module

Suggested owner: **Ammar Ranko** · 5 points · Oct 7–Oct 18 · depends on — · blocks SET-02, SET-07, SET-14, SET-15, SET-16, US-01, US-11, US-33, US-35, US-57

Done when:

- Minimal skeleton (Django + React + PostgreSQL start with one command) pushed to main by Thu Oct 8
- docker compose up starts backend, frontend, PostgreSQL 17, Azurite (file storage) and Mailpit (email)
- GET /api/health/ returns 200 with {"status": "ok"}
- README setup takes 10 steps or fewer on Windows and macOS
- Reference module 'categories' implemented through every layer and documented as the pattern to copy
- Dockerfile for the application image and a .dockerignore
- Logging configured: Python logging with JSON output, one request id per request, INFO/WARNING/ERROR levels, never personal data; one front-end logger module

- [T-00.01.1] **Back-end project** (Oct 7–Oct 9; depends on —): Django 6.1 project 'iris' on Python 3.13 managed with uv. DRF, django-allauth (headless), drf-spectacular, procrastinate, django-environ. Settings read DATABASE_URL, AZURE_STORAGE_*, EMAIL_* from the environment. pytest-django, factory_boy, ruff and mypy configured in pyproject.toml. Files: `backend/iris/settings/{base,local,test,production}.py, backend/pyproject.toml, backend/manage.py`.
- [T-00.01.2] **Front-end project** (Oct 10–Oct 12; depends on T-00.01.1): Vite + React 19 + TypeScript (strict). Mantine UI, React Router, TanStack Query, react-i18next (French default, English switch). ESLint + Prettier + Vitest + Testing Library. One home page that calls GET /api/health/ and shows the result. Files: `frontend/package.json, frontend/src/app/, frontend/src/shared/i18n/{fr,en}.json, frontend/vite.config.ts`.
- [T-00.01.3] **Docker Compose and README** (Oct 13–Oct 15; depends on T-00.01.2): Services: backend (port 8000), frontend (5173), db (postgres:17, port 5432, volume), azurite (10000), mailpit (8025 UI, 1025 SMTP). Backend runs migrations on start. A manage.py command creates admin@iris.local with a local password for development sign-in. Minimal mailer adapter (backend/adapters/mailer/{base.py,smtp.py}) sending through Mailpit, so other pairs can send plain emails before the full email system exists. Files: `docker-compose.yml, .env.example, README.md`.
- [T-00.01.4] **Reference module: categories** (Oct 16–Oct 18; depends on T-00.01.3, SET-12): Implement listing categories end to end as the example every pair copies: Category model, a pure rule in domain/ (food categories need a best-before date), services.py, queries.py, GET /api/categories/ (public), a React page listing categories in the current language, and tests at each layer. Write docs/guides/reference-module.md walking through the files. Files: `backend/modules/categories/{models.py,domain/rules.py,services.py,queries.py,api/,tests/}, frontend/src/features/categories/, docs/guides/reference-module.md`.

### [SET-02] CI workflow and branch protection

Suggested owner: **Danial Kouba** · 3 points · Oct 7–Oct 18 · depends on SET-01 · blocks SET-14, SET-17

Done when:

- ci.yml runs on every pull request: lint, type checks, module boundary checks, tests with coverage, dependency audits, front-end build
- main requires a pull request, green CI and 1 approval; force pushes blocked
- CodeRabbit reviews every pull request using .coderabbit.yaml

- [T-00.02.1] **Back-end CI job** (Oct 7–Oct 10; depends on —): Job 'backend': uv sync, ruff check, ruff format --check, mypy, lint-imports (import-linter), pytest --cov with a minimum of 70% total, pip-audit. Service container postgres:17. Files: `.github/workflows/ci.yml`.
- [T-00.02.2] **Front-end CI job** (Oct 11–Oct 14; depends on T-00.02.1): Job 'frontend': pnpm install --frozen-lockfile, eslint, tsc --noEmit, vitest run --coverage, pnpm build, pnpm audit --prod (high and critical fail). Files: `.github/workflows/ci.yml`.
- [T-00.02.3] **Branch protection and review setup** (Oct 15–Oct 18; depends on T-00.02.2): Ruleset on main: pull request required, 1 approval, dismiss stale approvals, status checks 'backend' and 'frontend' required, block force pushes. Confirm CodeRabbit posts a review on a test pull request. Files: `GitHub settings`.

### [SET-05] Database schema review and ERD

Suggested owner: **Mark Antoun** · 2 points · Oct 7–Oct 18 · depends on — · blocks SET-21

Done when:

- Publish docs/03-design/database-schema.md for the Release 1 tables, starting from the team draft; each pair reviews the tables of its modules and approves the pull request
- ERD and domain model diagrams published in the wiki and matching the table list
- Migration order (which module first) written down

- [T-00.05.1] **Schema review with each pair** (Oct 7–Oct 12; depends on —): 15-minute review per pair: column names, types, nullability, constraints, indexes, which module owns the table. Record every change in the document. Files: `docs/03-design/database-schema.md`.
- [T-00.05.2] **ERD and migration order** (Oct 13–Oct 18; depends on T-00.05.1): Update the Mermaid ERD to match. Add the migration order: rules, accounts, categories, stores, households, documents, eligibility, listings, reservations, priority, review, audit, notifications, privacy, then stretch modules. Files: `docs/03-design/database-schema.md`.

### [SET-06] Architecture diagrams

Suggested owner: **Mark Antoun** · 3 points · Oct 7–Oct 18 · depends on — · blocks SET-21, SET-23

Done when:

- Publish in the wiki and docs/03-design/architecture.md, starting from the team draft diagrams: system context, high-level architecture (containers), layers inside a module, module dependencies, deployment
- Sequence diagrams for walk-in registration, partner onboarding and reserve-and-pickup; state diagrams for the household file and the reservation
- PNG exports in docs/03-design/img/ for slides

- [T-00.06.1] **Structure diagrams** (Oct 7–Oct 12; depends on —): C4 context (users, Iris, Azure services), container (browser app, Django API, worker, PostgreSQL, Blob, email, Document Intelligence), module dependencies (allowed arrows only), deployment (Azure Canada East resources). Files: `docs/03-design/architecture.md, docs/03-design/img/`.
- [T-00.06.2] **Sequence diagrams** (Oct 13–Oct 18; depends on T-00.06.1): Walk-in registration (intake worker -> households service -> eligibility -> audit -> email job) and reserve-and-pickup (household -> reservations service atomic update -> code -> store confirms -> audit). Files: `docs/03-design/architecture.md`.

### [SET-07] Rule settings module

Suggested owner: **Reuven Minciotti** · 3 points · Oct 7–Oct 18 · depends on SET-01 · blocks SET-18, US-16, US-34, US-50, US-69

Done when:

- Rule values are stored as versions; publishing a change creates a new version and never edits an old one
- Business-rule functions receive rule values as arguments; nothing is hard-coded
- Default values for every rule type are seeded

- [T-00.07.1] **RuleSetVersion model and service** (Oct 7–Oct 10; depends on —): Model RuleSetVersion(rule_type, version, values JSONB, effective_from, created_by, created_at), unique (rule_type, version). services.publish(rule_type, values, user) validates and creates version n+1. queries.active(rule_type, at=now) returns the version in effect. Files: `backend/modules/rules/{models.py,services.py,queries.py}`.
- [T-00.07.2] **Validation per rule type** (Oct 11–Oct 14; depends on T-00.07.1): A JSON schema per rule type: lico_thresholds, auto_approval, priority, tiers, strikes, reservations, listing_safety, file_validity, retention. Values and defaults as published in business-rules.md. Files: `backend/modules/rules/domain/schemas.py`.
- [T-00.07.3] **Default rule seed** (Oct 15–Oct 18; depends on T-00.07.2, T-00.08.1): Command seed_rules creates version 1 of every rule type with the default values published in business-rules.md (lico_thresholds comes from SET-08). Files: `backend/modules/rules/management/commands/seed_rules.py`.

### [SET-08] Low-income thresholds from Statistics Canada

Suggested owner: **Leon Kojakian** · 2 points · Oct 7–Oct 18 · depends on — · blocks US-16

Done when:

- Thresholds taken from Statistics Canada table 11-10-0241-01: before tax, community size 500,000 and over, family sizes 1 to 7 or more, latest reference year
- Values saved in backend/modules/eligibility/data/lico_<year>.csv with the source link and retrieval date
- Publish docs/04-data/lico-thresholds.md with the source links and the seven values, and seed them as rule type lico_thresholds

- [T-00.08.1] **Fetch the official table** (Oct 7–Oct 12; depends on —): Open https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110024101 (French: https://www150.statcan.gc.ca/t1/tbl1/fr/tv.action?pid=1110024101). Set 'Low income cut-off type' to Before tax, keep the latest reference year (2024 at the Apr 29, 2026 release), and read the row 'Population of 500,000 and over' for family sizes 1 person to 7 or more persons. Or download the full CSV https://www150.statcan.gc.ca/n1/tbl/csv/11100241-eng.zip and filter the same values. Files: `docs/04-data/lico-thresholds.md`.
- [T-00.08.2] **Data file and seed** (Oct 13–Oct 18; depends on T-00.08.1, T-00.07.1): CSV columns: family_size (1..7, 7 = 7 or more), threshold_cents. Load it as version 1 of rule type lico_thresholds with {year, source_url, retrieved_on, thresholds}. Files: `backend/modules/eligibility/data/lico_2024.csv, backend/modules/rules/management/commands/seed_rules.py`.

### [SET-09] Mock notices of assessment

Suggested owner: **Massimo Paolini** · 3 points · Oct 7–Oct 18 · depends on — · blocks SET-18, SET-19

Done when:

- tools/mock_notices/generate.py creates at least 50 fake notices of assessment (PDF and phone-photo PNG) marked SPECIMEN - DOCUMENT FICTIF
- truth.csv lists the correct values of every file
- Edge cases included: old tax year, name mismatch, address mismatch, unreadable photo, zero income

- [T-00.09.1] **Notice layout generator** (Oct 7–Oct 10; depends on —): Python + reportlab + Faker('fr_CA'). Publish docs/04-data/mock-notices-of-assessment.md (fields and cases) from the team draft and follow it. Fixed random seed 42 so output is reproducible. Watermark on every page. SIN always shown as XXX XXX XXX. Files: `tools/mock_notices/generate.py, tools/mock_notices/README.md`.
- [T-00.09.2] **Phone-photo variants** (Oct 11–Oct 14; depends on T-00.09.1): Pillow: render 15 notices to PNG, rotate -7 to +7 degrees, add shadow and blur, JPEG quality 60, place on a table-like background. Files: `tools/mock_notices/photos.py`.
- [T-00.09.3] **Truth file and edge cases** (Oct 15–Oct 18; depends on T-00.09.2): Columns: file, first_name, last_name, street_number, street_name, unit, postal_code, tax_year, total_income_cents, notice_date, case. Include 5 edge-case files listed in the acceptance criteria. Files: `mock-data/notices/truth.csv`.

### [SET-10] Wireframes: registration and staff screens

Suggested owner: **Vladimir Shterenkiker** · 3 points · Oct 7–Oct 18 · depends on — · blocks SET-16

Done when:

- Low-fidelity wireframes (Figma or Excalidraw) for: online registration steps, walk-in registration, household home, staff search, household page, review queue, partner applications
- Publish the registration, walk-in and staff forms in docs/02-requirements/forms-and-fields.md (field names, French and English labels, validation) from the team draft; every field appears in a wireframe
- PNG exports in the wiki and docs/03-design/wireframes/, reviewed by the Registration and Staff pairs


### [SET-11] Wireframes: store, listing, reservation and partner screens

Suggested owner: **Anthony Monaco** · 3 points · Oct 7–Oct 18 · depends on — · blocks SET-16

Done when:

- Publish the partner, store and listing forms in docs/02-requirements/forms-and-fields.md from the team draft
- Low-fidelity wireframes for: partner application, store home (today's pickups), post a listing, my listings, confirm a pickup, browse listings, listing detail, my reservations
- Phone-first (360 px wide)
- PNG exports in the wiki and docs/03-design/wireframes/, reviewed by the Goods and Fairness pairs


### [SET-12] Listing categories and safety lists

Suggested owner: **Ryan Cheung** · 2 points · Oct 7–Oct 18 · depends on — · blocks US-12, US-34

Done when:

- Category list (code, French, English, food or not, default value) and prohibited items list agreed with the team and added to business-rules.md
- Seed file backend/modules/categories/data/categories.yaml matches the document


### [SET-13] Glossary and French/English terminology

Suggested owner: **Firas Al Haddad** · 2 points · Oct 7–Oct 18 · depends on — · blocks SET-16

Done when:

- Every term used on screens has one French and one English wording in docs/01-project/glossary.md
- Translation key naming convention written (area.screen.element)
- Shared keys added to frontend/src/shared/i18n/fr.json and en.json


### [SET-15] API conventions, OpenAPI and TypeScript client

Suggested owner: **Danial Kouba** · 3 points · Oct 7–Oct 18 · depends on SET-01 · blocks US-07, US-12, US-17

Done when:

- drf-spectacular serves /api/schema/ and /api/docs/
- pnpm gen:api generates TypeScript types from the schema
- CI fails when the committed types differ from the schema
- Publish docs/03-design/api.md (paths, errors, paging, dates, money) from the team draft; the categories module follows it


### [US-11] B.A.D.R. set up as the first store

Suggested owner: **Leon Kojakian** · 2 points · Oct 7–Oct 18 · depends on SET-01 · blocks SET-18, US-12, US-14, US-33

*As B.A.D.R., I want to exist as a store in Iris so that I can post my own surplus like any partner.*

Done when:

- Store model with name, address (street number, street, unit, city, postal code), phone, email, opening hours, pickup instructions, is_badr and is_active
- B.A.D.R. store created by the seed with is_badr = true
- Admin can see and edit it in the Django admin site

- [T-02.11.1] Unit tests (Oct 7–Oct 18)
- [T-02.11.2] **Store model and migration** (Oct 7–Oct 12; depends on —): Store(name, street_number, street_name, unit, city, postal_code, phone, email, opening_hours JSONB, pickup_instructions, is_badr, is_active, created_at). Unique partial index: only one store with is_badr = true. Files: `backend/modules/stores/{models.py,admin.py}`.
- [T-02.11.3] **B.A.D.R. seed** (Oct 13–Oct 18; depends on T-02.11.2): Creates the B.A.D.R. store with placeholder address 0000 rue Exemple, Montreal, H0H 0H0 until B.A.D.R. confirms. Files: `backend/modules/stores/management/commands/seed_badr_store.py`.

