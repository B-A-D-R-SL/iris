# AI contribution: 50% or more AI-generated

# SET-17: temporary student staging and cost boundary

Status: **Accepted** for the staging design (one release image, opt-in
deployment, fictional data only, temporary environment); **hosting region and
subscription still open.**

- Proposed in the SET-17 branch for team review, 13 November 2026.
- Updated 14 November 2026: the hosting region is pending (see below).
- Accepted 15 November 2026: the team merged the implementation in
  [PR #700](https://github.com/B-A-D-R-SL/iris/pull/700) and closed
  [SET-17 #408](https://github.com/B-A-D-R-SL/iris/issues/408) as completed. The
  merge did not choose a region or deploy Azure.
- Checked November 17, 2026 against `main` at `c13fc04`: no region decision has
  been recorded, `STAGING_DEPLOY_ENABLED` is unset, every `deploy-staging` run was
  skipped and staging has not been deployed. The region decision will be added
  here when it is made.

## Context

The architecture and SET-17 target Canada East, B1 App Service, PostgreSQL
Flexible Server B1ms, private Blob Storage, ACS email and Key Vault. The current
student subscription's allowed-region policy excludes Canadian compute regions.
Ammar has provisioned `iris-staging`, the vault and ACS resources; hosting is
not yet activated. Daniel requires the remaining USD 100 to last six months.
The original USD 30–35/month paid database estimate cannot meet that constraint.

## Decision proposed for this staging environment

Use the existing ACS services with Canadian data geography. Staging contains
fictional data only. This is a temporary environment; recreate on B.A.D.R.'s
Canadian subscription under SET-24 rather than treating the student deployment
as production.

**The region for the database, storage and App Service is pending.** This ADR
originally proposed West US 2. On 14 November 2026 the subscription and
Concordia region policies together allowed only West US 2 and West US, and
PostgreSQL `Standard_B1ms` could not be created in either (West US 2 is
restricted for this subscription; West US returned `SkuNotAvailable`). The team
has escalated to Microsoft for access to B.A.D.R.'s USD 2,000 per year
nonprofit Azure credit and is in parallel pursuing student-subscription
capacity. The region will be decided from those answers and recorded here,
with the database, storage and App Service kept together in that one region.
The deployment workflow is region-independent, so this decision changes only
documentation and Azure setup.

Keep the issue's one-instance Linux B1 App Service and PostgreSQL 17 B1ms only
if the owner confirms six months of the student free PostgreSQL allowance,
including storage and backup, and a subscription-specific total estimate no
greater than USD 15/month (or the lower remaining-credit allocation). Otherwise
leave deployment disabled and bring the hosting decision back to the team.
The implementation does not silently substitute SQLite, a free unverified
third-party database, another Azure compute architecture, or a paid upgrade.

Build one non-root image containing React, Django/Gunicorn and the existing
Procrastinate worker. WhiteNoise serves only public build/static output; private
listing photos retain the Blob adapter. One container supervisor couples web
and worker lifetime and forwards shutdown to both process groups. A PostgreSQL
advisory lock serializes startup migrations and optional idempotent fictional
seeding. Database setup failure prevents serving requests.

Successful push CI on current `main` authorizes deployment. CI includes a real
release-image boot/migrate/seed/static smoke check against isolated PostgreSQL.
The deploy job rechecks current main and its latest successful CI, builds from
locked dependencies/pinned base images, pushes to public GHCR, signs in through
environment-scoped Azure OIDC, and sets the existing web app's image by digest.
Runtime managed identity resolves secrets from Key Vault; the deploy identity
has Website Contributor on that web app only. Deployment defaults to disabled.

## Consequences and limits

- One App Service plan, no ACR, paid slot, telemetry workspace or scale-out.
  Local structured logs remain available; Application Insights remains a later
  observability decision rather than a resource created by this task.
- Initial migration/seeding and every restart can cause brief unavailability.
  B1 has no swap slot here; keep migrations compatible with the prior image.
  This is neither HA nor a zero-downtime production deployment.
- The readiness endpoint verifies DB connectivity, worker process existence
  and revision; it cannot prove the queue is progressing or ACS delivered mail.
  Live proxy, blob privacy and email smoke tests remain activation requirements.
- PostgreSQL public ingress is restricted to the app's possible outbound IPs
  and requires authenticated TLS. Blob containers prohibit anonymous reads.
  Private networking and production keyless provider access remain separate work.
- Monthly budget alerts are notifications, not caps. Preserve the original USD
  60 alert and add an early USD 15 budget; monitor actual/free-meter usage and
  remaining credit. The student spending limit stays enabled. Stopping a web
  app does not stop plan billing. No six-month cost guarantee is made without
  checking this subscription's quote, entitlement and usage.

Activation, owner responsibilities and rollback are documented in the
[operations guide](../guides/azure-staging-operations.md). No Azure resources
were created by the repository implementation, and the Canadian production
target remains unchanged.
