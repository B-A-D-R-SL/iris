# AI contribution: 50% or more AI-generated
FROM python:3.13-slim AS base

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

ENV HOME=/home/iris
EXPOSE 8000

# Installation tools and dependency metadata stay outside the final runtime image.
FROM base AS installer
RUN python -m pip install --no-cache-dir --only-binary=:all: uv==0.12.23
COPY pyproject.toml uv.lock .python-version ./

# Compose selects this target for its bind-mounted development checks.
FROM installer AS development
RUN uv sync --frozen --no-install-project --no-build

COPY manage.py conftest.py photos.ini ./
COPY adapters/ ./adapters/
COPY iris/ ./iris/
COPY modules/ ./modules/
COPY tests/ ./tests/
COPY tools/ ./tools/
# Protect parent directories too, so the runtime user cannot replace source files.
RUN chmod -R a=rX /app
USER iris

# Remove test sources before copying files into the runtime image's layers.
FROM installer AS runtime-build
RUN uv sync --frozen --no-install-project --no-dev --no-build

COPY manage.py ./
COPY adapters/ ./adapters/
COPY iris/ ./iris/
COPY modules/ ./modules/
RUN find /app/adapters /app/iris /app/modules -type d -name tests -prune -exec rm -rf {} + \
    && find /app/adapters /app/iris /app/modules -type f -name conftest.py -delete \
    && chmod -R a=rX /app

# The default build contains only locked runtime dependencies and application files.
FROM base AS runtime
COPY --from=runtime-build /opt/iris-venv/ /opt/iris-venv/
COPY --from=runtime-build /app/manage.py ./
COPY --from=runtime-build /app/adapters/ ./adapters/
COPY --from=runtime-build /app/iris/ ./iris/
COPY --from=runtime-build /app/modules/ ./modules/
RUN chmod -R a=rX /app
USER iris
