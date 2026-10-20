# SonarQube Cloud setup

This workflow configures SonarQube Cloud CI-based analysis. It does not configure a self-hosted SonarQube server or require `SONAR_HOST_URL`.

## Required SonarQube Cloud project values

Create or import the Iris project in SonarQube Cloud, then add these GitHub repository settings:

| GitHub setting | Type | Value |
| --- | --- | --- |
| `SONAR_ORGANIZATION` | Repository variable | SonarQube Cloud organization key |
| `SONAR_PROJECT_KEY` | Repository variable | SonarQube Cloud project key |
| `SONAR_TOKEN` | Repository secret | SonarQube Cloud analysis token |

Project keys and organization keys are not secrets, but they are environment-specific and must be copied from SonarQube Cloud by an administrator. Do not commit tokens or generated credentials.

## Analysis workflow

The dedicated workflow is `.github/workflows/sonarqube-cloud.yml`.

It runs on:

- Pull requests opened, synchronized, or reopened.
- Pushes to `main`.
- Manual `workflow_dispatch` runs.

The workflow starts a PostgreSQL 17 service, runs backend pytest coverage, runs frontend Vitest coverage, validates the required SonarQube Cloud settings, then runs `SonarSource/sonarqube-scan-action`.

The backend coverage command runs from `backend/`, using the existing test discovery, exclusions, and 70% minimum in `backend/pyproject.toml`. It includes both `tests/` and module tests:

```bash
.venv/bin/python -m pytest --cov --cov-report=xml:coverage.xml --cov-report=term
```

## Coverage reports

SonarQube Cloud imports these generated reports:

| Area | Tool | Report path |
| --- | --- | --- |
| Backend Django | `pytest` with `pytest-cov` | `backend/coverage.xml` |
| Frontend React | `vitest --coverage` with V8 coverage | `frontend/coverage/lcov.info` |

The import paths are configured in `sonar-project.properties`:

- `sonar.python.coverage.reportPaths=backend/coverage.xml`
- `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info`

The reports are generated and scanned in the same job. Backend Cobertura source directories resolve to that job's backend checkout; frontend LCOV filenames are prefixed with `frontend/` using the reporter's `projectRoot`. Source and test scope includes `backend/modules/`.

The workflow uses main's Node 24, pnpm 10.34.6, Python 3.13, pinned Actions, and locked dependency installation. Existing `backend` and `frontend` CI jobs remain unchanged.

## Quality gate setup

Configure the quality gate in SonarQube Cloud and assign it to the Iris project. The scanner waits for the quality gate result with `sonar.qualitygate.wait=true`, so the GitHub Actions job fails when the gate fails.

If the team decides that this gate must block merges, an administrator can require its status check after the first successful scan. This change does not modify repository rules or existing required checks.

## Notes

- Disable SonarQube Cloud automatic analysis for this project; coverage import requires CI-based analysis.
- Do not add `SONAR_HOST_URL`; SonarQube Cloud uses the hosted service endpoint by default.
- Pull requests from forks may not receive `SONAR_TOKEN` from GitHub Actions secrets. Use repository-internal branches for SonarQube Cloud PR analysis unless administrators intentionally support a fork-safe setup.
