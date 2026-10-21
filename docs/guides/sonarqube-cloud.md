# SonarQube Cloud setup

The CI workflow contains one SonarQube Cloud scanner job that reuses the existing test jobs' coverage reports. It does not configure a self-hosted SonarQube server or require `SONAR_HOST_URL`.

Automatic analysis is currently enabled for the project. This implementation does not change that setting. An administrator-approved switch to CI-based analysis is required before the scanner can run successfully; automatic and CI-based analysis must not run together.

## Required SonarQube Cloud project values

Create or import the Iris project in SonarQube Cloud, then add these GitHub repository settings:

| GitHub setting       | Type                | Value                            |
| -------------------- | ------------------- | -------------------------------- |
| `SONAR_ORGANIZATION` | Repository variable | SonarQube Cloud organization key |
| `SONAR_PROJECT_KEY`  | Repository variable | SonarQube Cloud project key      |
| `SONAR_TOKEN`        | Repository secret   | SonarQube Cloud analysis token   |

Only `SONAR_TOKEN` is a secret. The project and organization identifiers remain configurable through non-secret repository variables. Do not commit tokens or generated credentials.

## Analysis workflow

Analysis runs in the `sonar` job of `.github/workflows/ci.yml`. There is no separately triggered Sonar workflow.

It runs on:

- Pull requests opened, synchronized, or reopened.
- Pushes to `main`.
- Manual `workflow_dispatch` runs.

The existing `backend` and `frontend` jobs run their tests once and upload coverage artifacts after their existing quality checks pass. The `sonar` job declares `needs: [backend, frontend]`, downloads both artifacts from the same workflow run, checks that the reports are nonempty, and runs `SonarSource/sonarqube-scan-action`.

The scanner job has no PostgreSQL service, backend/frontend dependency installation, or test execution. Missing reports fail artifact upload or the scanner job rather than silently omitting coverage.

The backend coverage command runs from `backend/`, using the existing test discovery, exclusions, and 70% minimum in `backend/pyproject.toml`. It includes both `tests/` and module tests:

```bash
pytest --cov --cov-report=term --cov-report=xml:coverage.xml
```

## Coverage reports

SonarQube Cloud imports these generated reports:

| Area           | Tool                                 | Artifact            | Report path after download    |
| -------------- | ------------------------------------ | ------------------- | ----------------------------- |
| Backend Django | `pytest` with `pytest-cov`           | `backend-coverage`  | `backend/coverage.xml`        |
| Frontend React | `vitest --coverage` with V8 coverage | `frontend-coverage` | `frontend/coverage/lcov.info` |

The import paths are configured in `sonar-project.properties`:

- `sonar.python.coverage.reportPaths=backend/coverage.xml`
- `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info`

The artifacts contain only the report files. The scanner restores them under `backend/` and `frontend/coverage/` in its checkout. All three jobs use `ubuntu-latest` and the same event checkout, so backend Cobertura source directories resolve against the same repository workspace path. Frontend LCOV filenames are prefixed with `frontend/` using the reporter's `projectRoot`. Source and test scope includes `backend/modules/`.

The test jobs keep main's Node 24, pnpm 10.34.6, Python 3.13, pinned Actions, and locked dependency installation. Their names, tests, audits, and 70% backend coverage minimum are preserved; the only test-command addition exports backend XML. Artifact Actions are pinned to immutable commits too.

## Analysis scope

`sonar.sources=.` includes analyzable files throughout the repository, including
`tools/mock_notices`, `.github` workflows, and frontend configuration files such
as `vite.config.ts` and `eslint.config.js`. Dependencies, generated coverage,
build output, and Python caches remain excluded through the existing exclusion
patterns and Git ignore rules.

`sonar.tests=.` uses test inclusion patterns to classify backend tests, frontend
tests and setup files, and `tools/**/tests/**/*.py` as tests rather than production
sources. Test directories are excluded from the source scope to avoid indexing
the same file in both categories.

`sonar.coverage.exclusions` includes `tools/**` because this CI workflow does not
produce coverage for the standalone tools project. Tools and their tests remain
in static analysis; this exclusion affects only coverage calculations. Backend
and frontend coverage report paths and the quality gate remain unchanged.

## Quality gate setup

Configure the quality gate in SonarQube Cloud and assign it to the Iris project. The scanner waits for the quality gate result with `sonar.qualitygate.wait=true`, so the GitHub Actions job fails when the gate fails.

If the team decides that this gate must block merges, an administrator can require its status check after the first successful scan. This change does not modify repository rules or existing required checks.

## Notes

- Keep the existing SonarQube Cloud GitHub App integration for PR decoration. Changing the analysis method does not require removing the App.
- Switching automatic analysis off is a separate administrator action requiring team approval, not something this workflow performs.
- Do not add `SONAR_HOST_URL`; SonarQube Cloud uses the hosted service endpoint by default.
- Pull requests from forks may not receive `SONAR_TOKEN` from GitHub Actions secrets. Use repository-internal branches for SonarQube Cloud PR analysis unless administrators intentionally support a fork-safe setup.
