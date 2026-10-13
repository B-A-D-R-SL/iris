# SonarQube Cloud setup

Iris uses SonarQube Cloud CI-based analysis only. Do not configure a self-hosted SonarQube server or `SONAR_HOST_URL` for this project.

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

The backend coverage command runs from the repository root so Cobertura filenames match the root SonarQube Cloud scan:

```bash
PYTHONPATH=backend uv run --project backend --python 3.13 pytest backend/tests --cov=backend/iris --cov=backend/adapters --cov-config=.coveragerc --cov-report=xml:backend/coverage.xml --cov-report=term-missing
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

## Quality gate setup

Configure the quality gate in SonarQube Cloud and assign it to the Iris project. The scanner waits for the quality gate result with `sonar.qualitygate.wait=true`, so the GitHub Actions job fails when the gate fails.

After the first successful scan, enable the corresponding required status check in GitHub branch protection for `main`.

## Notes

- Disable SonarQube Cloud automatic analysis for this project; coverage import requires CI-based analysis.
- Do not add `SONAR_HOST_URL`; SonarQube Cloud uses the hosted service endpoint by default.
- Pull requests from forks may not receive `SONAR_TOKEN` from GitHub Actions secrets. Use repository-internal branches for SonarQube Cloud PR analysis unless administrators intentionally support a fork-safe setup.
