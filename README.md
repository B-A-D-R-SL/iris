# Iris

Iris is a solidarity redistribution platform for sharing food and goods across communities, developed for **Concordia University's SOEN 490 capstone**.

## Project Overview

- **Frontend:** React 19, TypeScript, Vite, Mantine UI, French/English support.
- **Backend:** Django 6.1 (Python 3.13), REST API, authentication, background jobs.
- **Local services:** PostgreSQL 17, Azurite (Azure Blob Storage emulator), Mailpit (email testing).

**Development runs with one command.** Docker Compose starts all five services, automatically applies database migrations, and creates a local administrator.

The development environment uses **Docker Compose Watch** to synchronize frontend code changes automatically. Dependencies are installed during image builds and reused between runs, avoiding unnecessary installations and improving startup performance.

## Getting Started (Windows/macOS/Linux)

### 1. Prerequisites

Install [Git](https://git-scm.com/) and [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with a recent Docker Compose version).

Ensure Docker is running and Docker Compose supports Watch (v2.22+).

### 2. Clone the Repository

```bash
git clone https://github.com/B-A-D-R-SL/iris.git
cd iris
git switch setup
```

### 3. Start Iris

**First launch:**

```bash
docker compose up --build --watch
```

This builds the application images, installs dependencies, starts all five services, initializes PostgreSQL, and launches the application.

**Subsequent launches:**

```bash
docker compose up --watch
```

This reuses existing images and dependencies for faster startup. Frontend code changes are automatically synchronized from your editor into the running container.

Rebuild when dependencies, Dockerfiles, or other image requirements change.

### 4. Access the Application

| Service | Address |
| --- | --- |
| Iris frontend | http://localhost:5174 |
| Django admin | http://localhost:8000/admin/ |
| Backend health endpoint | http://localhost:8000/api/health/ |
| API documentation | http://localhost:8000/api/docs/ |
| Mailpit inbox | http://localhost:8025 |

**Local administrator credentials:**

- Username: `admin@iris.local`
- Password: `iris_local_admin_password`

These credentials are for **local development only** and must never be used in production.

### 5. Stop the Application

Press `Ctrl+C` in the terminal running Docker Compose.

To stop and remove the containers while preserving database data:

```bash
docker compose down
```

**Important:** Avoid `docker compose down -v` unless you intentionally want to delete persistent development data.

## Configuration

The development environment works with default local settings. No manual environment configuration is required for the Docker setup.

Optionally, copy `.env.example` to `.env` at the repository root to customize local ports and credentials. Never commit `.env`.

| Service | Internal Port | Host Port |
| --- | --- | --- |
| Frontend | 5173 | 5174 |
| Backend | 8000 | 8000 |
| PostgreSQL | 5432 | 55433 |
| Azurite Blob | 10000 | 10000 |
| Mailpit UI | 8025 | 8025 |
| Mailpit SMTP | 1025 | 1025 |

PostgreSQL uses port `55433` on the host to avoid conflicts with existing local databases. Containers communicate through Docker's internal network.

## Development and Testing

### Live Development

With `docker compose up --watch`, frontend changes made in PyCharm or another editor are synchronized into Docker automatically, enabling Vite's hot reload.

Backend source code is mounted directly into its container, allowing Django to reload when Python files change.

### Backend Checks

```bash
docker compose exec backend python -m pytest
docker compose exec backend ruff check .
docker compose exec backend mypy .
docker compose exec backend python manage.py check
```

### Frontend Checks

```bash
docker compose exec frontend pnpm test
docker compose exec frontend pnpm build
docker compose exec frontend pnpm lint
docker compose exec frontend pnpm format:check
```

### Email Testing

Mailpit captures outgoing development emails without delivering them to real recipients.

Send a test email:

```bash
docker compose exec backend python manage.py shell -c "from adapters.mailer.smtp import SmtpMailer; print(SmtpMailer().send(['test@iris.local'], 'Iris test', text='Hello from Iris'))"
```

View the message at http://localhost:8025.

### Manual Development (Optional)

The frontend and backend can also run outside Docker using `uv` and `pnpm`, with PostgreSQL available separately.

Start Django from `backend/`:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Start React from `frontend/` in another terminal:

```bash
pnpm install --frozen-lockfile
pnpm dev
```

For manual execution, configure `backend/.env` with a valid `DJANGO_SECRET_KEY` and a `DATABASE_URL` pointing to the PostgreSQL host port (`55433` for the Compose database). When running outside Docker, Vite normally uses `http://localhost:5173`.

**Docker Compose is the recommended development workflow.**

## Current Development Status

The initial frontend and backend foundations, Docker Compose environment, database integration, development administrator, and email testing infrastructure are implemented.

Backend and frontend automated tests and quality checks are passing. PostgreSQL connectivity, migrations, administrator authentication, and SMTP email delivery have been verified.

**Known limitation:** Azurite starts successfully, but Blob Storage operations have not yet passed integration testing due to an API-version incompatibility with the newer Azure SDK. This remains to be addressed.
