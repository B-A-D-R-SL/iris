# AI contribution: 50% or more AI-generated
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/iris-venv \
    UV_LINK_MODE=copy \
    PATH="/opt/iris-venv/bin:$PATH"

WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .

EXPOSE 8000
