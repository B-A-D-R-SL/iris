<!-- AI contribution: 50% or more AI-generated -->
# US-13 review verification

Verified on November 11, 2026 after merging main (`2b389ed`) into PR #665.

| Local check | Result |
| --- | --- |
| Backend suite, native PostgreSQL 17 | 2030 passed, 5 skipped, 1 slow-expiry case deselected (same exclusion as CI) |
| Backend combined line/branch coverage | 95.66% (required minimum: 70%) |
| Added backend executable-line coverage against main | 268 / 273 lines, 98.17% |
| Domain line coverage (whole backend) | 305 / 307 lines, 99.35%; this PR changes no domain files |
| Frontend suite | 658 passed across 40 files |
| Frontend line coverage | 95.46% |
| Ruff lint and format; full Python type check | Passed (407 Python files type-checked) |
| Import-linter; migration drift | Four contracts kept; no missing migrations |
| ESLint, TypeScript, Prettier, production build | Passed |
| Generated API schema/types; generator regression tests | Current types; 9 regression cases passed |
| Backend / frontend production dependency audits | No known vulnerabilities |
| PR policy checker regression tests | 36 passed |

The five local skips are optional integration cases requiring external emulators;
CI enables its Azurite service. No test was disabled to obtain these results.
The slow-expiry exclusion matches the committed CI command.

Added-line coverage was computed from executable lines in the coverage XML,
intersected with added lines in `git diff --unified=0 origin/main -- backend`,
excluding tests and migrations. Coverage thresholds were not reduced.

## Reproduction

Use the environment and locked dependencies described in the root README, then:

```sh
cd backend
pytest -m "not slow_expiry" --cov --cov-report=term --cov-report=xml:coverage.xml
ruff check .
ruff format --check .
mypy .
lint-imports
python manage.py makemigrations --check --dry-run
pip-audit --strict
cd ../frontend
pnpm test:coverage
pnpm lint
pnpm format:check
pnpm typecheck
pnpm build
pnpm gen:api --check
pnpm test:api
pnpm audit --prod --audit-level high
```

Django commands require `DJANGO_SECRET_KEY`, `DATABASE_URL` pointing to PostgreSQL
17, and `DJANGO_SETTINGS_MODULE=iris.settings.test` for tests. CI also sets the
public Azurite emulator configuration and `IRIS_TEST_AZURITE=1`.

## Behavioral evidence

- API availability and write services share the active-admin/submitted-state rule.
  Responses include `can_decide`; UI tests verify a submitted application's actions
  stay hidden when that API flag is false. Services still recheck under a row lock.
- The global access matrix covers all three review endpoints for every role, plus
  anonymous access; API-to-database approval/rejection tests verify persisted state,
  invitations, audit records and after-commit emails.
- Approval and rejection logs are emitted only after commit. Email failure retains
  the decision and exposes only a restricted application UUID for operator recovery.
- Recovery expires prior links, refuses accepted invitations/existing accounts, and
  rolls back expiry changes on issuance failure. SMTP callbacks have a finite timeout.
- Invitation origins require HTTPS outside localhost/loopback development; email
  subjects and bodies resolve through the applicant's translation catalog.
- Rejection validation precedence is retained. The trimmed 500-character reason
  contract derives from the existing model field (BR-PARTNER-04); no extra raw-input
  serializer bound was introduced.
- Submission-time existing-account checks remain a follow-up discussion (item 13).

These are local verification results. GitHub CI is checked separately on the
published commit before requesting Ryan's review.
