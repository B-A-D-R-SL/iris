## Tools used

| Tool | Used for | By |
| --- | --- | --- |
| ChatGPT (OpenAI) | Generating and refining code, tests, configurations, and documentation for the backend, frontend, and Docker development environment. Also used for debugging, troubleshooting, and verification. | Owner of #374, #375, #376 |

## AI-assisted features

| Feature (issue) | Files | Level | Pull request |
| --- | --- | --- | --- |
| T-00.01.1 Backend project (#374) | `backend/iris/settings/`, `backend/manage.py`, `backend/pyproject.toml`, `backend/tests/test_backend_config.py`, `backend/.env.example` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| T-00.01.2 Frontend project (#375) | `frontend/src/`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `backend/iris/{views.py,urls.py}` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| T-00.01.3 Docker Compose and README (#376) | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `backend/adapters/mailer/`, `backend/iris/management/commands/create_dev_admin.py`, `backend/tests/test_platform_setup.py`, `.env.example`, `README.md` | 50% or more AI-generated | Not yet opened (`setup` branch) |
| SET-01 Setup hardening (#373, #374–#376) | `backend/iris/observability.py`, `backend/tests/test_observability.py`, `backend/iris/settings/base.py`, `frontend/src/shared/logger.ts`, `frontend/src/shared/logger.test.ts`, `backend/iris/urls.py` | 50% or more AI-generated | Not yet opened (`setup` branch) |

## Examples, verification and corrections

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
