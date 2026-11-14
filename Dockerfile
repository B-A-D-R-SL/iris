# AI contribution: 50% or more AI-generated
FROM node:24-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5 AS frontend
WORKDIR /build
RUN npm install --global pnpm@10.34.6
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS dependencies
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.12.23
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-build --no-install-project

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS release
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" DJANGO_SETTINGS_MODULE=iris.settings.staging
WORKDIR /app
RUN groupadd --gid 10001 iris && useradd --uid 10001 --gid iris --no-create-home iris
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/ ./
COPY --from=frontend /build/dist /app/frontend_dist
# Synthetic build-only settings: collectstatic neither connects to a DB nor sends mail.
RUN DJANGO_SECRET_KEY=build-only-key-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ-abcdef \
    DJANGO_ALLOWED_HOSTS=build.example.org \
    DATABASE_URL=postgresql://build:build@localhost/build \
    DEFAULT_FROM_EMAIL=noreply@build.example.org \
    PUBLIC_APP_ORIGIN=https://build.example.org \
    python manage.py collectstatic --noinput
ARG IRIS_RELEASE_SHA=local
ENV IRIS_RELEASE_SHA=${IRIS_RELEASE_SHA}
USER iris
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["python", "-m", "iris.release"]
