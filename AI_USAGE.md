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

## Examples, verification and corrections

### T-00.01.1 Backend project (#374)

- **What the AI produced:** the Django 6.1 backend using Python 3.13 and uv, environment-specific settings (`base`, `local`, `test`, `production`), configuration for Django REST Framework, django-allauth, drf-spectacular, Procrastinate, and PostgreSQL, along with automated tests and Ruff/mypy configuration.
- **How we verified it:** ran pytest, Ruff, mypy, and Django system checks. Verified PostgreSQL connectivity, successful database migrations, API documentation routing, and local Django startup.
- **Problems found and corrections:**
  - Django initially failed to load the secret key correctly. Fixed the environment configuration using `django-environ`.
  - PostgreSQL needed to be configured locally. Created a PostgreSQL 17 Docker container and successfully applied the database migrations.
  - The SQLite fallback was incompatible with Procrastinate's PostgreSQL-specific migrations. Development and integration testing were performed using PostgreSQL.
  - Fixed Ruff import-order warnings and reran the backend checks.

### T-00.01.2 Frontend project (#375)

- **What the AI produced:** the React 19 frontend with TypeScript, Vite, Mantine UI, React Router, TanStack Query, and French/English internationalization. Also generated the homepage, backend health-check integration, automated tests, and frontend quality tooling.
- **How we verified it:** four Vitest tests passed, covering French as the default language, English switching, successful backend communication, and unavailable backend handling. The production build, ESLint, and Prettier checks passed. Functionality was also verified manually in the browser.
- **Problems found and corrections:**
  - Mantine required `window.matchMedia`, which was unavailable in the test environment. Added a mock to the test setup.
  - Configured the Vite API proxy to allow React to communicate with Django.
  - Resolved ESLint/Prettier compatibility issues and corrected formatting.
  - Removed unused starter assets and documented the initial local setup in the README.

### T-00.01.3 Docker Compose and README (#376)

- **What the AI produced:** the five-service Docker Compose environment (Django, React, PostgreSQL, Azurite, Mailpit), backend and frontend Dockerfiles, automatic migrations, development administrator creation, SMTP mailer adapter, integration tests, and updated README documentation.
- **How we verified it:** successfully started all five containers. Verified PostgreSQL queries, database migrations, Django health endpoint, administrator authentication, and SMTP email delivery. Eight backend pytest tests and four frontend Vitest tests passed. Ruff, mypy, Django system checks, ESLint, Prettier, and the frontend production build also passed.
- **Problems found and corrections:**
  - pnpm repeatedly failed inside Docker because it attempted to reinstall dependencies without an interactive terminal. Changed the setup to install dependencies during image builds and reuse them.
  - The frontend homepage timed out through port `5173`. Switching the host port to `5174` resolved the issue.
  - Windows Docker bind mounts caused slow frontend loading. Replaced them with Docker Compose Watch, improving startup and page-loading performance while retaining automatic code synchronization.
  - Fixed Ruff warnings involving imports, Python syntax, and executable-file permissions.
  - Corrected a mypy typing error in the development administrator command.
  - Prettier scanned hundreds of generated pnpm cache files. Updated ignore configurations to exclude dependency caches.
  - An Azurite Blob Storage test failed because the Azure SDK requested an unsupported API version. This remains deferred.
  - Updated the README to document the optimized one-command Docker workflow, service configuration, credentials, and testing commands.