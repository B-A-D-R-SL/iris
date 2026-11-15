<!-- AI contribution: 50% or more AI-generated -->
# Container hardening (FIX-24)

[FIX-24 #615](https://github.com/B-A-D-R-SL/iris/issues/615) hardens the existing
development frontend image and the backend image shared by web and worker
processes. The startup commands, ports and Compose Watch workflow are configured
in [docker-compose.yml](../../docker-compose.yml).

## Users and permissions

The backend uses an `iris` account with a writable home and temporary space.
Its packaged application tree at `/app`, including executable scripts and their
parent directories, is root-owned and read-only. The runtime user cannot change
permissions or replace those files. Its dependency environment stays outside the
development source mount at `/opt/iris-venv`, also owned by root and readable by
`iris`. Normal startup does not install dependencies or change file ownership.

Backend and worker bind-mount the host source at `/app`. Image ownership cannot
change permissions on that mount. On Linux, use `id -u` and `id -g` to find your
host IDs. If either differs from `1000`, set both `IRIS_UID` and `IRIS_GID` in the
root `.env` to the matching positive IDs, then rebuild. The UID must be unused
in the base image; normal Linux development accounts use IDs of `1000` or higher.
An existing non-root group ID can be shared through the image's `iris` group.

```bash
docker compose up --build --watch
```

This keeps coverage, linter caches and the photo demo's host-visible output
writable. The defaults work with the normal Docker Desktop workflow; these
overrides are for Linux source-mount ownership. Do not run the application as
root to work around a permission error.

The frontend uses the base image's `node` account. Application files, dependencies
and the home directory are writable by that account so Vite, TypeScript caches,
coverage, API generation and Compose Watch can update their outputs.

Compose mounts the small shared `mock-data/validation` fixture directory read-only
for backend and frontend tests. The backend also reads the generated frontend
Unicode reference table through a read-only file mount. These test inputs remain
outside the application images; frontend source and dependencies continue to use
image files and Watch synchronization.

## Dependency installation and image contents

The backend Dockerfile provides two runnable targets. Compose explicitly builds
`development`, which includes the locked development dependencies, test sources
and repository tools needed by the [README checks](../../README.md).

The last/default target is `runtime`, intended for staging web and worker
processes. Build it with the usual command:

```bash
docker build --tag iris-backend:runtime backend
```

Dependency installation bootstraps pinned uv from wheels with
`--only-binary=:all:`. The development target syncs with
`--frozen --no-install-project --no-build`; the runtime build also uses `--no-dev`.
The final runtime image copies the installed environment and application packages
from intermediate stages. Application test directories, pytest configuration,
repository tools, uv and dependency manifests stay outside its layers. Migrations,
management commands, translations, notification templates and seed data remain available.
Both targets keep packaged sources root-owned and read-only.

The frontend bootstraps pinned pnpm with npm's `--ignore-scripts`, then installs
the frozen project lock with pnpm's `--ignore-scripts`. The locked Vite/Rolldown
and Lightning CSS dependencies supply platform binaries through optional
packages. A dependency update must pass the image build, development-server,
production-build and test checks with scripts disabled. Investigate any failure
before allowing a package's build script, and document a necessary exception
beside the installation command.

Both Dockerfiles copy named source/configuration paths. Their `.dockerignore`
files exclude nested environment files, private keys and credential files.
Backend virtual environments and generated build, log, coverage and temporary
outputs are excluded only at the context root; similarly named directories
inside application packages remain available as resources. Python bytecode and
tool caches remain excluded recursively. Real credentials must be supplied at
runtime.

## Verification

Run the isolated smoke checks from the repository root with Bash and Docker
Compose available:

```bash
python3 -m unittest discover -s tools/tests -p "test_container_smoke.py"
bash tools/container-smoke.sh
```

Use `IRIS_SMOKE_NO_CACHE=1 bash tools/container-smoke.sh` to repeat dependency
installation without cached build layers. Run the checks as your normal host
user so they can verify bind-mount ownership.

The smoke runner copies tracked working-tree files into a disposable directory
and uses a unique Compose project so it can exercise file writes and Watch
without changing the working checkout or
the usual development project's data. It verifies the application images as
their configured users, service startup, health/proxy responses, developer write
paths and exclusion of synthetic credential canaries. It also builds the default
runtime target separately, checks production startup without development tools,
executes the production deployment check and seed commands against the disposable
database, and verifies that nested application resource directories survive the
build. Watch checks cover file addition, modification and deletion, plus frontend
replacement after a dependency manifest changes. CI runs the same check in addition to the existing backend and
frontend quality jobs. Local results and review corrections are recorded in
[the verification history](../05-process/ai-usage-verification-3.md#fix-24-dockerfile-hardening-615).

HTTP probes are restricted to the disposable frontend's published
`127.0.0.1` port and three fixed health/asset paths. The runner rejects non-loopback
endpoints and invalid ports, ignores curl configuration and inherited proxies,
and does not follow redirects. These local development requests contain no real
credentials or user data. The offline tests verify rejected endpoints and paths,
curl options and failure propagation before the image/Compose checks run.

## Staging and SonarQube Cloud

[SET-17](https://github.com/B-A-D-R-SL/iris/issues/408) owns the live Azure
deployment. Verify the rebuilt backend image with the deployment's explicit web
and worker commands, migrations, writable temporary paths and injected production
configuration. Follow [production settings](production-settings.md) for startup
checks. Local Compose verification does not establish successful Azure rollout.

Review all seven Docker findings in the PR analysis and confirm zero
vulnerabilities on `main` after merge. Follow the [SonarQube Cloud
guide](sonarqube-cloud.md) to check the project's active analysis mode. Any
remaining finding considered safe needs an administrator's documented rationale.
