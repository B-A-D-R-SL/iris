# AI contribution: 50% or more AI-generated
FROM python:3.13-slim

ARG APP_UID=1000
ARG APP_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/iris-venv \
    UV_LINK_MODE=copy \
    PATH="/opt/iris-venv/bin:$PATH"

WORKDIR /app
# Linux host primary groups may share a GID with an existing base-image group.
RUN test "$APP_UID" -gt 0 && test "$APP_GID" -gt 0 \
    && groupadd --non-unique --gid "$APP_GID" iris \
    && useradd --uid "$APP_UID" --gid iris --create-home \
        --home-dir /home/iris --shell /usr/sbin/nologin iris
RUN python -m pip install --no-cache-dir --only-binary=:all: uv==0.12.23
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --no-build

# Keep development/test tools and package resources root-owned.
COPY manage.py conftest.py photos.ini ./
COPY adapters/ ./adapters/
COPY iris/ ./iris/
COPY modules/ ./modules/
COPY tests/ ./tests/
COPY tools/ ./tools/
# Protect parent directories too, so the runtime user cannot replace source files.
RUN chmod -R a=rX /app

ENV HOME=/home/iris
USER iris

EXPOSE 8000
