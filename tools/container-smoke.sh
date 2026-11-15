#!/usr/bin/env bash
# AI contribution: 50% or more AI-generated
# Exercise real images in a disposable checkout; never touch an existing project.

initialize() {
  if [[ "$(id -u)" -eq 0 ]]; then
    echo "Run this smoke check as a non-root host user to verify bind-mount ownership." >&2
    return 1
  fi
  repo_dir=$(git rev-parse --show-toplevel)
  smoke_dir=$(mktemp -d "${TMPDIR:-/tmp}/iris-container-smoke.XXXXXXXX")
  : > "$smoke_dir/compose.env"
  project="iris-smoke-$(date +%s)-$$"
  watch_pid=""
  frontend_port=""
  export IRIS_UID="$(id -u)" IRIS_GID="$(id -g)"
  export IRIS_DB_PORT=0 IRIS_AZURITE_PORT=0 IRIS_MAILPIT_UI_PORT=0 IRIS_SMTP_PORT=0
  export IRIS_BACKEND_PORT=0 IRIS_FRONTEND_PORT=0
  export POSTGRES_DB=iris POSTGRES_USER=iris POSTGRES_PASSWORD=iris_container_smoke_password
  export DJANGO_SECRET_KEY=iris-container-smoke-only-not-a-secret
  export DJANGO_DEV_ADMIN_EMAIL=admin@iris.local DJANGO_DEV_ADMIN_PASSWORD=iris_smoke_admin_password
  export IRIS_TUNNEL_HOST="" IRIS_TUNNEL_HOSTS="" IRIS_TUNNEL_ORIGINS=""
}

compose() {
  docker compose --project-name "$project" --project-directory "$smoke_dir" \
    --env-file "$smoke_dir/compose.env" -f "$smoke_dir/docker-compose.yml" "$@"
}

cleanup() {
  local status=$?
  trap - EXIT
  set +e
  if [[ -n "$watch_pid" ]]; then
    kill "$watch_pid" 2>/dev/null
    wait "$watch_pid" 2>/dev/null
  fi
  if [[ "$status" -ne 0 ]]; then
    compose ps --all
    compose logs --no-color --tail 100
    if [[ -f "$smoke_dir/watch.log" ]]; then cat "$smoke_dir/watch.log"; fi
  fi
  compose down --volumes --remove-orphans
  docker image rm "$project-backend" "$project-worker" "$project-frontend" \
    "$project-runtime" 2>/dev/null
  rm -rf -- "$smoke_dir"
  exit "$status"
}

retry() {
  local attempt
  for attempt in {1..60}; do
    if "$@"; then return 0; fi
    sleep 2
  done
  echo "Timed out: $*" >&2
  return 1
}

prepare_contexts() {
  # Read tracked working-tree files, including uncommitted Dockerfile changes.
  # Untracked local .env files, node_modules and virtual environments stay outside.
  git -C "$repo_dir" ls-files -z -- backend frontend mock-data/validation docker-compose.yml |
    tar -C "$repo_dir" --null -T - -cf - | tar -C "$smoke_dir" -xf -
  [[ -s "$smoke_dir/mock-data/validation/contact-values.json" ]]
  local app
  for app in backend frontend; do
    mkdir -p "$smoke_dir/$app/.git" "$smoke_dir/$app/coverage"
    printf 'IRIS_SMOKE_CANARY=synthetic-only\n' > "$smoke_dir/$app/.env"
    printf 'synthetic-only\n' > "$smoke_dir/$app/.env.smoke"
    printf 'synthetic-only\n' > "$smoke_dir/$app/.git/iris-smoke-canary"
    printf 'synthetic-only\n' > "$smoke_dir/$app/coverage/iris-smoke-canary"
  done
  mkdir -p "$smoke_dir/backend/iris/__pycache__" "$smoke_dir/backend/tmp"
  printf 'synthetic-only\n' > "$smoke_dir/backend/iris/.env.smoke"
  printf 'synthetic-only\n' > "$smoke_dir/backend/iris/__pycache__/iris-smoke-canary.pyc"
  printf 'synthetic-only\n' > "$smoke_dir/backend/coverage.xml"
  printf 'synthetic-only\n' > "$smoke_dir/backend/iris/iris-smoke-canary.key"
  printf 'synthetic-only\n' > "$smoke_dir/backend/tmp/iris-smoke-canary"
  mkdir -p "$smoke_dir/frontend/node_modules" "$smoke_dir/frontend/dist"
  printf 'synthetic-only\n' > "$smoke_dir/frontend/src/.env.smoke"
  printf 'synthetic-only\n' > "$smoke_dir/frontend/src/iris-smoke-canary.key"
  printf 'synthetic-only\n' > "$smoke_dir/frontend/node_modules/iris-smoke-canary"
  printf 'synthetic-only\n' > "$smoke_dir/frontend/dist/iris-smoke-canary"
  prepare_package_resources
}

prepare_package_resources() {
  local directory
  for directory in env build logs temp coverage tmp; do
    mkdir -p "$smoke_dir/backend/modules/common/$directory"
    printf 'synthetic-package-resource\n' \
      > "$smoke_dir/backend/modules/common/$directory/iris-smoke-preserved.txt"
  done
}

check_backend_resources() {
  docker run --rm --network none --entrypoint sh "$1" -ec '
    for directory in env build logs temp coverage tmp; do
      test "$(cat "/app/modules/common/$directory/iris-smoke-preserved.txt")" = synthetic-package-resource
    done
    for path in modules/categories/data/categories.yaml modules/eligibility/data/lico_2024.csv \
      modules/accounts/locale/fr/LC_MESSAGES/django.mo modules/accounts/migrations/0001_initial.py \
      modules/notifications/templates/notifications/message.html; do
      test -s "/app/$path"
    done
  '
}

check_images() {
  local service image
  for service in backend frontend; do
    image=$(compose images -q "$service")
    docker run --rm --entrypoint sh "$image" -ec '
      test "$(id -u)" -ne 0
      for path in .env .env.smoke .git/iris-smoke-canary coverage/iris-smoke-canary; do
        test ! -e "/app/$path"
      done
    '
  done
  docker run --rm --entrypoint sh "$(compose images -q backend)" -ec '
    test -f /app/manage.py && test -d /app/tests && test -d /app/modules
    touch "$HOME/iris-smoke-write" /tmp/iris-smoke-write
    test ! -w /opt/iris-venv
    for path in /app /app/manage.py /app/iris /app/iris/settings; do
      test "$(stat -c %u "$path")" -eq 0 && test ! -w "$path"
    done
    if (printf "# smoke mutation\n" >> /app/manage.py) 2>/dev/null; then exit 1; fi
    if chmod u+w /app/manage.py 2>/dev/null; then exit 1; fi
    if rm /app/manage.py 2>/dev/null; then exit 1; fi
    for path in iris/.env.smoke iris/__pycache__/iris-smoke-canary.pyc coverage.xml iris/iris-smoke-canary.key tmp/iris-smoke-canary; do
      test ! -e "/app/$path"
    done
    python -c "import django, PIL, psycopg; import pytest"
  '
  check_backend_resources "$(compose images -q backend)"
  docker run --rm --entrypoint sh "$(compose images -q frontend)" -ec '
    test -f /app/scripts/gen-api.mjs && test -f /app/vite.config.ts
    for path in src/.env.smoke src/iris-smoke-canary.key node_modules/iris-smoke-canary dist/iris-smoke-canary; do
      test ! -e "/app/$path"
    done
  '
}

build_runtime_image() {
  # No --target: this must exercise the Dockerfile default used by deployments.
  docker build "$@" --build-arg "APP_UID=$IRIS_UID" --build-arg "APP_GID=$IRIS_GID" \
    --tag "$project-runtime" "$smoke_dir/backend"
}

check_runtime_files() {
  docker run --rm --network none --entrypoint sh "$project-runtime" -ec '
    test "$(id -u)" -ne 0
    touch "$HOME/iris-smoke-write" /tmp/iris-smoke-write
    test ! -w /opt/iris-venv
    for path in /app /app/manage.py /app/iris /app/iris/settings; do
      test "$(stat -c %u "$path")" -eq 0 && test ! -w "$path"
    done
    if (printf "# smoke mutation\n" >> /app/manage.py) 2>/dev/null; then exit 1; fi
    if chmod u+w /app/manage.py 2>/dev/null; then exit 1; fi
    if rm /app/manage.py 2>/dev/null; then exit 1; fi
    for path in tests tools conftest.py photos.ini pyproject.toml uv.lock .python-version \
      .env .env.smoke .git/iris-smoke-canary coverage/iris-smoke-canary \
      iris/.env.smoke iris/iris-smoke-canary.key iris/__pycache__/iris-smoke-canary.pyc; do
      test ! -e "/app/$path"
    done
    test -z "$(find /app -type d -name tests -print -quit)"
    if command -v uv > /dev/null 2>&1; then exit 1; fi
  '
  check_backend_resources "$project-runtime"
}

runtime_python() {
  local network=$1 database=$2
  shift 2
  docker run --rm --network "$network" --entrypoint python \
    -e DJANGO_SETTINGS_MODULE=iris.settings.production \
    -e DJANGO_SECRET_KEY=container-smoke-production-only-key-0123456789-ABCDEF \
    -e DJANGO_ALLOWED_HOSTS=iris.example \
    -e "DATABASE_URL=$database" \
    -e MAILER_ADAPTER=smtp -e EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
    -e DEFAULT_FROM_EMAIL=noreply@iris.example -e PUBLIC_APP_ORIGIN=https://iris.example \
    "$project-runtime" "$@"
}

check_runtime_libraries() {
  runtime_python none postgresql://iris:iris_smoke_only@127.0.0.1:1/iris -c '
import importlib.util
from pathlib import Path
import django, PIL, psycopg

for module in ("pytest", "ruff", "mypy", "factory", "faker", "pip_audit", "uv"):
    assert importlib.util.find_spec(module) is None, module
for path in (Path("/app"), *Path("/app").rglob("*")):
    assert path.stat().st_uid == 0 and path.stat().st_mode & 0o222 == 0, path
django.setup()
from django.db import connections
assert all(connection.connection is None for connection in connections.all())
'
}

check_runtime_services() {
  local database="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@db:5432/$POSTGRES_DB"
  runtime_python "${project}_default" "$database" manage.py check --deploy --fail-level WARNING
  runtime_python "${project}_default" "$database" manage.py seed_rules
  runtime_python "${project}_default" "$database" manage.py seed_categories
}

set_frontend_port() {
  local published parsed
  frontend_port=""
  published=$(compose port frontend 5173) || return
  if [[ ! "$published" =~ ^127\.0\.0\.1:([0-9]{1,5})$ ]]; then
    echo 'Frontend must be published on exactly 127.0.0.1 with a numeric port.' >&2
    return 1
  fi
  parsed=$((10#${BASH_REMATCH[1]}))
  if [[ "$parsed" -lt 1 || "$parsed" -gt 65535 ]]; then
    echo 'Frontend published port must be between 1 and 65535.' >&2
    return 1
  fi
  frontend_port=$parsed
}

frontend_get() {
  if [[ "$#" -ne 1 || ! "${frontend_port:-}" =~ ^[1-9][0-9]{0,4}$ || "$frontend_port" -gt 65535 ]]; then
    echo 'Validate the frontend loopback port before probing it.' >&2
    return 1
  fi
  case "$1" in
    /|/api/health/|/src/main.tsx) ;;
    *) echo 'Unexpected frontend smoke probe path.' >&2; return 1 ;;
  esac
  # Local development HTTP only: fixed loopback host, fixed paths, no redirects,
  # no curlrc configuration, and no proxy even when proxy variables are exported.
  curl --disable --noproxy '*' --proto '=http' --fail --silent --show-error \
    --connect-timeout 1 --max-time 10 "http://127.0.0.1:${frontend_port}${1}"
}

health_ready() {
  frontend_get /api/health/ | grep -q '"status": "ok"'
}

all_services_running() {
  [[ "$(compose ps --status running --services | wc -l)" -eq 6 ]]
}

check_services() {
  set_frontend_port
  retry health_ready
  frontend_get / | grep -q '<div id="root">'
  frontend_get /src/main.tsx > /dev/null
  retry all_services_running
  local service
  for service in backend worker frontend; do
    [[ "$(compose exec -T "$service" id -u)" -ne 0 ]]
  done
  compose exec -T worker python -c '
from pathlib import Path
assert b"procrastinate" in Path("/proc/1/cmdline").read_bytes()
'
  compose exec -T backend python manage.py shell -c \
    'from modules.accounts.models import User; assert User.objects.filter(email="admin@iris.local", is_superuser=True).exists()'
}

check_tools() {
  compose exec -T backend python -m pytest -c photos.ini tests/test_photos.py -q \
    --cov=adapters.photos --cov-report=xml:container-smoke-coverage.xml --cov-fail-under=90
  [[ -s "$smoke_dir/backend/container-smoke-coverage.xml" ]]
  [[ -d "$smoke_dir/backend/.pytest_cache" ]]
  compose exec -T backend ruff check adapters/photos.py
  [[ -d "$smoke_dir/backend/.ruff_cache" ]]
  compose exec -T backend python -B manage.py spectacular \
    --format openapi-json --validate --fail-on-warn > "$smoke_dir/schema.json"
  compose exec -T frontend pnpm gen:api --schema-stdin < "$smoke_dir/schema.json"
  compose exec -T frontend pnpm gen:api --schema-stdin --check < "$smoke_dir/schema.json"
  compose exec -T frontend pnpm test:api --schema-stdin < "$smoke_dir/schema.json"
  compose exec -T frontend pnpm build
  compose exec -T frontend sh -ec 'test -s dist/index.html; test -d node_modules/.tmp; test -d node_modules/.vite'
}

check_frontend_coverage() {
  compose exec -T frontend pnpm exec vitest run src/shared/forms/formats.test.ts \
    src/shared/forms/contact.test.ts --coverage --reporter=dot
  compose exec -T frontend test -s coverage/lcov.info
}

watch_contents_match() {
  compose exec -T frontend sh -ec 'test "$(cat "$1")" = "$2"' sh "$1" "$2"
}

watch_file_absent() {
  compose exec -T frontend test ! -e "$1"
}

wait_for_watch() {
  local attempt
  for attempt in {1..60}; do
    if ! kill -0 "$watch_pid" 2>/dev/null; then
      echo 'Compose Watch exited before becoming ready.' >&2
      return 1
    fi
    if grep -q 'Watch enabled' "$smoke_dir/watch.log"; then return 0; fi
    sleep 2
  done
  echo 'Compose Watch did not become ready within 120 seconds.' >&2
  return 1
}

frontend_recreated() {
  local current
  current=$(compose ps -q frontend)
  [[ -n "$current" && "$current" != "$1" ]]
}

check_watch_rebuild() {
  local previous
  previous=$(compose ps -q frontend)
  printf '\n' >> "$smoke_dir/frontend/package.json"
  retry frontend_recreated "$previous"
  set_frontend_port
  retry health_ready
  [[ "$(compose exec -T frontend id -u)" -ne 0 ]]
}

check_watch() {
  # Replace the background shell so cleanup owns the external Watch process PID.
  (exec docker compose --project-name "$project" --project-directory "$smoke_dir" \
    --env-file "$smoke_dir/compose.env" -f "$smoke_dir/docker-compose.yml" watch --no-up frontend) \
    > "$smoke_dir/watch.log" 2>&1 &
  watch_pid=$!
  wait_for_watch
  local directory relative
  for directory in src public; do
    relative="frontend/$directory/iris-smoke-watch.txt"
    printf 'added\n' > "$smoke_dir/$relative"
    retry watch_contents_match "/app/$directory/iris-smoke-watch.txt" added
    printf 'changed\n' > "$smoke_dir/$relative"
    retry watch_contents_match "/app/$directory/iris-smoke-watch.txt" changed
    rm -- "$smoke_dir/$relative"
    retry watch_file_absent "/app/$directory/iris-smoke-watch.txt"
  done
  printf '\n<!-- iris-smoke-watch -->\n' >> "$smoke_dir/frontend/index.html"
  retry compose exec -T frontend grep -q 'iris-smoke-watch' /app/index.html
  retry health_ready
  check_watch_rebuild
}

main() {
  set -Eeuo pipefail
  initialize
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  prepare_contexts
  local build_args=()
  if [[ "${IRIS_SMOKE_NO_CACHE:-0}" = 1 ]]; then build_args+=(--no-cache); fi
  echo 'Building disposable application images and checking excluded canaries.'
  compose build "${build_args[@]}" backend frontend worker
  compose create --no-build
  check_images
  echo 'Checking the default backend runtime image without development dependencies.'
  build_runtime_image "${build_args[@]}"
  check_runtime_files
  check_runtime_libraries
  echo 'Starting all six services and checking non-root tools and proxy traffic.'
  compose up -d
  check_services
  check_runtime_services
  check_tools
  check_frontend_coverage
  echo 'Checking frontend Watch synchronization of added, changed and removed files.'
  check_watch
  echo 'Container smoke checks passed.'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
