#!/usr/bin/env bash
# AI contribution: 50% or more AI-generated
# Exercise real images in a disposable checkout; never touch an existing project.
set -Eeuo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this smoke check as a non-root host user to verify bind-mount ownership." >&2
  exit 1
fi

repo_dir=$(git rev-parse --show-toplevel)
smoke_dir=$(mktemp -d "${TMPDIR:-/tmp}/iris-container-smoke.XXXXXXXX")
: > "$smoke_dir/compose.env"
project="iris-smoke-$(date +%s)-$$"
watch_pid=""
export IRIS_UID="$(id -u)" IRIS_GID="$(id -g)"
export IRIS_DB_PORT=0 IRIS_AZURITE_PORT=0 IRIS_MAILPIT_UI_PORT=0 IRIS_SMTP_PORT=0
export IRIS_BACKEND_PORT=0 IRIS_FRONTEND_PORT=0
export POSTGRES_DB=iris POSTGRES_USER=iris POSTGRES_PASSWORD=iris_container_smoke_password
export DJANGO_SECRET_KEY=iris-container-smoke-only-not-a-secret
export DJANGO_DEV_ADMIN_EMAIL=admin@iris.local DJANGO_DEV_ADMIN_PASSWORD=iris_smoke_admin_password
export IRIS_TUNNEL_HOST="" IRIS_TUNNEL_HOSTS="" IRIS_TUNNEL_ORIGINS=""

compose() {
  docker compose --project-name "$project" --project-directory "$smoke_dir" \
    --env-file "$smoke_dir/compose.env" -f "$smoke_dir/docker-compose.yml" "$@"
}

cleanup() {
  local status=$?
  trap - EXIT
  set +e
  if [ -n "$watch_pid" ]; then
    kill "$watch_pid" 2>/dev/null
    wait "$watch_pid" 2>/dev/null
  fi
  if [ "$status" -ne 0 ]; then
    compose ps --all
    compose logs --no-color --tail 100
    if [ -f "$smoke_dir/watch.log" ]; then cat "$smoke_dir/watch.log"; fi
  fi
  compose down --volumes --remove-orphans
  docker image rm "$project-backend" "$project-worker" "$project-frontend" 2>/dev/null
  rm -rf -- "$smoke_dir"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

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
  test -s "$smoke_dir/mock-data/validation/contact-values.json"
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
    for path in iris/.env.smoke iris/__pycache__/iris-smoke-canary.pyc coverage.xml iris/iris-smoke-canary.key tmp/iris-smoke-canary; do
      test ! -e "/app/$path"
    done
    python -c "import django, PIL, psycopg; import pytest"
  '
  docker run --rm --entrypoint sh "$(compose images -q frontend)" -ec '
    test -f /app/scripts/gen-api.mjs && test -f /app/vite.config.ts
    for path in src/.env.smoke src/iris-smoke-canary.key node_modules/iris-smoke-canary dist/iris-smoke-canary; do
      test ! -e "/app/$path"
    done
  '
}

health_ready() {
  curl --fail --silent --show-error --connect-timeout 1 --max-time 3 \
    "$frontend_url/api/health/" | grep -q '"status": "ok"'
}

all_services_running() {
  test "$(compose ps --status running --services | wc -l)" -eq 6
}

check_services() {
  frontend_url="http://$(compose port frontend 5173)"
  retry health_ready
  curl --fail --silent --show-error --max-time 10 "$frontend_url/" | grep -q '<div id="root">'
  curl --fail --silent --show-error --max-time 10 "$frontend_url/src/main.tsx" > /dev/null
  retry all_services_running
  local service
  for service in backend worker frontend; do
    test "$(compose exec -T "$service" id -u)" -ne 0
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
  test -s "$smoke_dir/backend/container-smoke-coverage.xml"
  test -d "$smoke_dir/backend/.pytest_cache"
  compose exec -T backend ruff check adapters/photos.py
  test -d "$smoke_dir/backend/.ruff_cache"
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
  test -n "$current" && test "$current" != "$1"
}

check_watch_rebuild() {
  local previous
  previous=$(compose ps -q frontend)
  printf '\n' >> "$smoke_dir/frontend/package.json"
  retry frontend_recreated "$previous"
  frontend_url="http://$(compose port frontend 5173)"
  retry health_ready
  test "$(compose exec -T frontend id -u)" -ne 0
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

prepare_contexts
build_args=()
if [ "${IRIS_SMOKE_NO_CACHE:-0}" = 1 ]; then build_args+=(--no-cache); fi
echo 'Building disposable application images and checking excluded canaries.'
compose build "${build_args[@]}" backend frontend worker
compose create --no-build
check_images
echo 'Starting all six services and checking non-root tools and proxy traffic.'
compose up -d
check_services
check_tools
check_frontend_coverage
echo 'Checking frontend Watch synchronization of added, changed and removed files.'
check_watch
echo 'Container smoke checks passed.'
