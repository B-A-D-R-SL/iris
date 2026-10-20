<!-- AI contribution: 50% or more AI-generated -->

# OpenAPI and TypeScript generation (SET-15)

## Current coverage

- `/api/schema/` serves the drf-spectacular schema.
- `/api/docs/` serves Swagger UI using that schema.
- `GET /api/health/` is described as a public JSON endpoint returning
  `{"status": "ok"}`. It checks the backend process, not database or other service
  connectivity. Its existing Django implementation is unchanged.
- Authentication remains mounted under `/api/auth/` using django-allauth's own
  routes. This work does not add authentication operations to the generated
  schema or change authentication behavior. See [authentication routing](auth-routing.md).

The [API conventions](../03-design/api.md) publish the team draft, distinguish
implemented and planned endpoints, and record implementation gaps and pending
team decisions. This guide describes generation tooling; it does not establish
additional API requirements or imply that every documented convention is
already implemented.

Categories compliance remains dependent on [reference module #377](https://github.com/B-A-D-R-SL/iris/issues/377).
There is no categories endpoint in this checkout; the unmerged SET-12 seed data
does not implement one. Categories must be checked against the adopted
conventions and added to the schema when its module is implemented.

## Generator compatibility

The generator is pinned to openapi-typescript 6.7.6. Version 7.13.0 requires a
TypeScript 5 peer, so it is not used with this frontend's TypeScript 6 toolchain.
Version 6.7.6 has no TypeScript peer restriction and was verified in isolation
with Node 24, pnpm 10.34.6, and TypeScript 6.0.3, with strict peer checks enabled.
The generated health response types accept valid responses and reject an
incorrect or missing status. No existing dependency version was changed.

## Generate and check types

Use the project's Python 3.13, Node 24, uv, and pnpm setup. Install the locked
backend and frontend dependencies as described in the README, and provide the
backend's existing required configuration (`DJANGO_SECRET_KEY` and a PostgreSQL
`DATABASE_URL`). Generation does not start services or run migrations.

From `frontend/`:

```sh
pnpm gen:api
pnpm gen:api --check
pnpm test:api
```

The generator script calls drf-spectacular in the already-installed backend
environment, validates the exported OpenAPI document, and passes it in memory to
[openapi-typescript 6.7.6](https://registry.npmjs.org/openapi-typescript/6.7.6). It does not resolve backend
dependencies or download Python. A running HTTP server is unnecessary.

The output is `frontend/src/shared/api/generated.d.ts`. Keep that file under
version control, regenerate it after schema changes, and include it in the same
review as the backend change. Existing frontend API consumers and their runtime
response validation are preserved.

Generation uses stable ordering, the existing Prettier configuration, and LF
line endings. `--check` compares against the generated content without writing
the output; missing or outdated types cause a nonzero exit. The existing
`backend` CI job runs this check, retaining the existing required check names
and all current checks.

`test:api` verifies deterministic generation and successful and failing checks
using a temporary output file. It also verifies that check mode does not rewrite
stale output or create missing output. Tracked generated files are never altered
to simulate failures. The Node regression test is named
`scripts/test-api-generation.mjs` so Vitest does not collect it as a browser test.
