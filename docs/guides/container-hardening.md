<!-- AI contribution: 50% or more AI-generated -->
# Container hardening (FIX-24)

[FIX-24 #615](https://github.com/B-A-D-R-SL/iris/issues/615) hardens the existing
development frontend image and the backend image shared by web and worker
processes. The startup commands, ports and Compose Watch workflow are configured
in [docker-compose.yml](../../docker-compose.yml).

## Users and permissions

The backend uses an `iris` account with a writable home and temporary space.
Its dependency environment stays outside the development source mount at
`/opt/iris-venv`, owned by root and readable by `iris`. Normal startup does not
install dependencies or change file ownership.

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

The backend bootstraps pinned uv from wheels with pip's `--only-binary=:all:` and
syncs the existing lock with `--frozen --no-install-project --no-build`. Source
build scripts are disabled. Development dependencies remain available for the
container-based checks documented in the [README](../../README.md).

The frontend bootstraps pinned pnpm with npm's `--ignore-scripts`, then installs
the frozen project lock with pnpm's `--ignore-scripts`. The locked Vite/Rolldown
and Lightning CSS dependencies supply platform binaries through optional
packages. A dependency update must pass the image build, development-server,
production-build and test checks with scripts disabled. Investigate any failure
before allowing a package's build script, and document a necessary exception
beside the installation command.

Both Dockerfiles copy named source/configuration paths. Their `.dockerignore`
files also exclude nested environment files, private keys, credential files,
local dependencies, caches and generated output. Backend package resources,
migrations, translations, templates and seed data remain included, along with
the tools needed by the documented development commands. Real credentials must
be supplied at runtime.

## Verification

Run the isolated smoke checks from the repository root with Bash and Docker
Compose available:

```bash
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
paths and exclusion of synthetic credential canaries. Watch checks cover file
addition, modification and deletion, plus frontend replacement after a dependency
manifest changes. CI runs the same check in addition to the existing backend and
frontend quality jobs. Local results and review corrections are recorded in
[AI usage](../../AI_USAGE.md#fix-24-dockerfile-hardening-615).

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
