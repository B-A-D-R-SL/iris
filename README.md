# Iris

Iris is a solidarity redistribution platform that helps communities share and redistribute resources. Developed for **SOEN 490 — Software Engineering Capstone** at Concordia University.

## Project overview

- **Frontend:** React 19, TypeScript, Vite, and Mantine UI, with French and English support.
- **Backend:** Django 6.1 (Python 3.13), REST API, authentication infrastructure, and background-job support.
- **Database:** PostgreSQL 17, currently running in Docker.

**Current setup:** PostgreSQL runs in Docker; developers start Django and React in **two separate terminals**.

**Planned setup:** Docker Compose will start the frontend, backend, PostgreSQL, Azurite, and Mailpit together with **one command**:

```bash
docker compose up --build
```

> Docker Compose is not implemented yet. Use the steps below for now.

## Run locally

### 1. Prerequisites

Install **Git**, **Docker Desktop**, **[uv](https://docs.astral.sh/uv/)**, **Node.js 24**, and **[pnpm 10](https://pnpm.io/)**. Start Docker Desktop before proceeding.

### 2. Clone the repository

```bash
git clone https://github.com/B-A-D-R-SL/iris.git
cd iris
git switch setup
```

The latest setup is currently on the `setup` branch.

### 3. Start PostgreSQL

On first setup, create the database container:

```bash
docker run --name iris-postgres-dev -e POSTGRES_USER=iris -e POSTGRES_PASSWORD=iris_local_dev_password -e POSTGRES_DB=iris -p 127.0.0.1:55432:5432 -v iris-postgres-dev-data:/var/lib/postgresql/data -d postgres:17
```

On later sessions, start the existing container instead:

```bash
docker start iris-postgres-dev
```

The database credentials above are **for local development only**.

### 4. Backend — Terminal 1

```powershell
cd backend
uv sync
Copy-Item .env.example .env
```

> On macOS/Linux, use `cp .env.example .env` instead of `Copy-Item`.

In `backend/.env`, set:

```dotenv
DATABASE_URL=postgresql://iris:iris_local_dev_password@127.0.0.1:55432/iris
DJANGO_SECRET_KEY=REPLACE_WITH_A_GENERATED_SECRET
```

Generate a secret using:

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy its output into `DJANGO_SECRET_KEY` in `.env`. **Never commit `.env`.** Then run:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

- Health endpoint: http://127.0.0.1:8000/api/health/
- API documentation: http://127.0.0.1:8000/api/docs/

### 5. Frontend — Terminal 2

Open a second terminal **at the repository root**, leaving Django running in the first:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open **http://localhost:5173/**. The homepage defaults to French, supports English switching, and displays **Connecté** when Django is reachable.

## Checks

From `backend/`:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
uv run python manage.py check
```

From `frontend/`:

```bash
pnpm test
pnpm build
pnpm lint
pnpm format:check
```

## What's next

Docker Compose integration, the categories reference module, and Iris's redistribution features. Track progress in [GitHub Issues](https://github.com/B-A-D-R-SL/iris/issues).
