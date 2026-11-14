# AI contribution: 50% or more AI-generated

# SET-17: connect GitHub and activate staging

Repository implementation is ready for owner review; **Azure activation and live
verification remain manual**. These steps create billable resources. Do not run
them before completing the cost check. Never use the Concordia IT subscription.
Use fictional data only. The deployment workflow itself creates no infrastructure.

## 1. Cost check before creating anything

**Update, 13 November 2026:** Daniel confirmed that the PostgreSQL allowance is
available for all six months. This records his confirmation, not an independent
portal inspection. Confirm remaining credit and the actual total quote below
before creating paid resources; deployment remains disabled.

Ask Ammar, the subscription owner, to check **Azure for Students → Free services**
and **Cost Management → Cost analysis** together:

- Remaining credit must cover six months, including already-created resources.
  Keep the student spending limit enabled; do not upgrade to pay-as-you-go.
- PostgreSQL must show the unused **750 B1ms hours/month, 32 GB storage and 32 GB
  backup** allowance, valid for the whole six months. Published student offers
  are not proof that this particular subscription is eligible.
- Price **one Linux B1 instance in West US 2** using this subscription's currency
  and offer. Microsoft's public page advertises about USD 13.14/month; that is
  an estimate, not a quote for this subscription.
- Plan for **at most USD 15/month total**, or less if remaining credit requires
  it: `(remaining credit - USD 10 reserve) / months remaining`. Six months at
  USD 15 uses USD 90. Only proceed if the actual quote and free allowance fit.
- Keep PostgreSQL at B1ms, 32 GB, seven-day local backups, no HA, no replicas,
  no geo-redundancy, and **storage auto-grow disabled**. The free allocation is
  shared with other servers on the subscription. Monitor backup usage too.
- Use existing email/Key Vault, one Standard LRS storage account, GHCR public
  image storage, and the App Service's included HTTPS hostname. No ACR, second
  App Service plan, paid deployment slot, Insights/Log Analytics workspace,
  Front Door, custom domain, or automatic scale-out for this task.

**If the free database allowance is absent or expires early, stop.** The paid
B1/B1ms design in #408 is not a six-month USD 100 solution. Keep deployment
disabled and agree a changed hosting design with the team rather than silently
substituting a database or using the credit in three months.

The existing USD 60/month budget satisfies the original issue but is inadequate
for this credit. The subscription owner should retain it for traceability and
add a **USD 15/month** budget with actual alerts at 30/60/80/100% and a forecast
alert at 100%, sent to both owners. Use the equivalent amount if billing is not
USD. Review actual cost after day one and weekly; budget notifications are
delayed and **do not stop resources**. Check remaining student credit as well.

Stopping a web app does **not** stop B1 plan charges. To remove those charges,
export the deployment configuration, delete the staging app and its now-empty
plan, then recreate them from this guide when needed. Never delete the DB to
save a small compute charge. Stopped PostgreSQL still bills storage and restarts
automatically after seven days; stopping is not a six-month cost guarantee.

Sources: [student allowances](https://azure.microsoft.com/en-us/free/students),
[Linux App Service pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/linux/),
[App Service billing](https://learn.microsoft.com/en-us/azure/app-service/overview-manage-costs),
[budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets),
[spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).

## 2. Merge the reviewed repository changes and publish the first image

Do this before creating B1 resources so they do not sit idle during code review.

1. Commit/push `setup/SET-17`, open its PR to `main`, review and merge it. The
   workflow runs only after the entire **CI** workflow succeeds for a push to
   the current `main`; PR CI alone cannot authorize deployment.
2. GitHub → repository **Settings → Environments** → create **`staging`**.
   Restrict deployment branches to **`main`**. Add required reviewers where the
   repository plan supports them. This also scopes the OIDC subject below.
3. Leave repository variable **`STAGING_DEPLOY_ENABLED` unset**. Default is off.
4. After main CI passes, **Actions → Deploy staging → Run workflow**, branch
   `main`, check **publish_only**. This builds/pushes the image using the scoped
   `GITHUB_TOKEN`, without signing in to Azure or needing Azure credentials.
5. GitHub organisation **Packages → iris → Package settings → Change visibility
   → Public**. This repo is public and the image contains public code only.
   Grant this repository Actions access to the package if it already exists.
   Azure must be able to pull the image anonymously. No PAT or registry password
   belongs in App Service. GHCR packages are initially private by default.
6. Record the published `sha256` digest and main commit. Use the image's full
   `ghcr.io/b-a-d-r-sl/iris@sha256:...` reference for initial creation. Digests,
   rather than `latest`, are used for subsequent deployments too.

The workflow must exist on `main` before GitHub exposes workflow_run/manual
dispatch. A manual deployment also checks the current revision's latest main
push CI result. A newer main commit or failing/in-progress rerun refuses an old
deployment. This is not a command to bypass failed CI.

## 3. Database, private storage and secrets

Use the **Azure portal** or Azure Cloud Shell (PowerShell). Local Azure CLI is
optional. Choose the **Azure for Students** subscription explicitly on every
creation screen. Reuse resource group **`iris-staging`**, region **West US 2**;
Canadian compute regions are currently prohibited by the subscription policy.

1. Create PostgreSQL Flexible Server **`iris-stg-db-ar1`**, PostgreSQL **17**,
   Burstable **Standard_B1ms**, **32 GB**, seven-day locally redundant backups,
   no HA/geo-redundancy/replica, auto-grow off. Verify the cost/free meter once
   more on the final screen. Database name **`iris`**; admin **`irisadmin`**.
   Generate a strong password and store it only in the vault/your password
   manager. Enable public networking with **no public firewall rules yet**.
   Leave **Allow Azure services** off; app-specific IP rules are added below.
   Creating the server supplies `postgres`, not the application's `iris` DB.
   Create **`iris`** before adding its URL to Key Vault. In Azure Cloud Shell
   (PowerShell), explicitly target the student subscription and staging server:

   ```powershell
   az postgres flexible-server db create --subscription "Azure for Students" --resource-group iris-staging --server-name iris-stg-db-ar1 --database-name iris --output none
   ```

2. Vault **`iris-stg-kv-ar1` → Secrets**: add **`database-url`** with a URL-encoded
   password, for example the structure below (replace all angle brackets):

   ```text
   postgresql://irisadmin:<URL-encoded-password>@iris-stg-db-ar1.postgres.database.azure.com:5432/iris?sslmode=verify-full&sslrootcert=/etc/ssl/certs/ca-certificates.crt
   ```

3. Add **`django-secret-key`**, a cryptographically generated value of at least
   50 characters, and **`seed-password`**, a strong random password. Do not paste
   either into chat or source code. Existing `acs-connection-string` stays put.
   The handover lists Dani as **Secrets User**, which cannot create secrets:
   Ammar must create these or temporarily grant **Key Vault Secrets Officer**
   at this vault only, then remove that extra permission.
4. Create StorageV2 account **`irisstgfilesar1`** (choose a unique suffix if taken),
   **Standard LRS**, West US 2, HTTPS only, minimum TLS 1.2, anonymous blob access
   disabled. Create container **`listing-photos`**, access level **Private**.
   Store its connection string as **`storage-connection-string`** in the vault.
   Keep staging photos small; this task does not provision a private endpoint
   or a paid storage tier. Private here means no anonymous object access.

## 4. Create and configure the one-instance app

Create the app **last**. These are the only always-on compute resources, besides
the database covered by the confirmed allowance.

1. Create **`iris-stg-plan`**, Linux **B1**, **one instance**, West US 2.
2. Create **`iris-staging-ar1`**, publish **Container**, Linux, existing plan,
   public external registry **`https://ghcr.io`**, initial image digest from
   step 2, port **8000**. No registry credentials. Use the legacy single-container
   deployment mode (`linuxFxVersion=DOCKER|...`); this workflow does not target
   the newer sidecar/sitecontainers model. If names are unavailable, use a
   unique suffix and use that same name in every later command/variable.
3. Copy the app's **actual default hostname** from Overview. New apps can have
   an extra regional/hash suffix; do not infer it from the app name.
4. Turn on **system-assigned managed identity**. Ammar/Access Administrator must
   assign it **Key Vault Secrets User** scoped to **`iris-stg-kv-ar1` only**.
   Contributor alone cannot grant role assignments. Allow RBAC time to propagate.
5. **Configuration / General settings**: HTTPS only, minimum TLS 1.2, Always On,
   health check **`/api/ready/`**. Disable FTP and SCM basic publishing credentials;
   the deployment uses OIDC, not a publish profile. Set startup timeout to 600
   seconds to allow initial migrations/seeding. Do not override the image CMD.
6. PostgreSQL **Networking**: add each IPv4 address from the app's **outbound IP
   addresses and possible/additional outbound addresses** as an individual
   start=end firewall rule. No `0.0.0.0`/all-Azure rule or `0.0.0.0–255.255.255.255`
   rule. Refresh these rules after a plan/network change. SQL authentication
   remains required. This is staging public networking with restricted sources;
   production private networking remains SET-24.

Set these app environment variables (substitute the actual hostname):

| Name | Value |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `iris.settings.staging` |
| `WEBSITES_PORT` | `8000` |
| `WEBSITES_CONTAINER_START_TIME_LIMIT` | `600` |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `false` |
| `DJANGO_ALLOWED_HOSTS` | actual default hostname, without scheme |
| `PUBLIC_APP_ORIGIN` | `https://` plus that hostname |
| `IRIS_SEED_ON_START` | `1` (fictional staging only; seed is idempotent) |
| `MAILER_ADAPTER` | `azure` |
| `DEFAULT_FROM_EMAIL` | `DoNotReply@e05b7d2a-a167-48c1-ab47-0ba4b41d3386.azurecomm.net` — confirm against domain MailFrom |
| `AZURE_STORAGE_CONTAINER_NAME` | `listing-photos` |
| `LISTING_PHOTO_STORE_BACKEND` | `modules.listings.photo_storage.configured_store` |

For secrets use **Key Vault references**, not literal values:

| Setting | Vault secret name |
| --- | --- |
| `DATABASE_URL` | `database-url` |
| `DJANGO_SECRET_KEY` | `django-secret-key` |
| `SEED_PASSWORD` | `seed-password` |
| `AZURE_STORAGE_CONNECTION_STRING` | `storage-connection-string` |
| `AZURE_COMMUNICATION_CONNECTION_STRING` | existing `acs-connection-string` |

Each reference has this structure, replacing `SECRET-NAME`:

```text
@Microsoft.KeyVault(SecretUri=https://iris-stg-kv-ar1.vault.azure.net/secrets/SECRET-NAME/)
```

Confirm every reference's status is **Resolved**. Save settings and restart the
app. An unresolved reference, failed migration or missing seed password must
prevent startup. Secrets never pass through the GitHub build/deploy job.

`DRF_NUM_PROXIES` and `ALLAUTH_TRUSTED_PROXY_COUNT` remain at their safe default
zero until the trusted Azure forwarding chain is verified. Verify that the
front end overwrites spoofed forwarding headers before setting both to the
observed count (typically one, but do not infer it from a local test). See
[production proxy requirements](production-settings.md#https-and-trusted-proxies).
Also verify that App Service health probes reach `/api/ready/` without an HTTP
redirect; the local release smoke only simulates the forwarding header.

## 5. Give GitHub a staging-only deployment identity

Prefer a **user-assigned managed identity** so Concordia need not allow Entra
app registrations. No client secret is necessary. Run in Cloud Shell; these
commands create the identity/federation and RBAC only, not paid compute.

```powershell
az account set --subscription "Azure for Students"
$stagingSubscription = az account show --query id -o tsv
az identity create --subscription $stagingSubscription -g iris-staging -n iris-stg-deploy-ar1 -l westus2 --output none
az identity federated-credential create --subscription $stagingSubscription -g iris-staging --identity-name iris-stg-deploy-ar1 -n github-staging --issuer https://token.actions.githubusercontent.com --subject repo:B-A-D-R-SL/iris:environment:staging --audiences api://AzureADTokenExchange --output none
$deployPrincipal = az identity show --subscription $stagingSubscription -g iris-staging -n iris-stg-deploy-ar1 --query principalId -o tsv
$stagingApp = az webapp show --subscription $stagingSubscription -g iris-staging -n iris-staging-ar1 --query id -o tsv
az role assignment create --subscription $stagingSubscription --assignee-object-id $deployPrincipal --assignee-principal-type ServicePrincipal --role "Website Contributor" --scope $stagingApp --output none
```

The last assignment needs Ammar/Access Administrator. **Do not** give the GitHub
identity Owner, subscription Contributor, or Key Vault Secrets User. It only
updates/restarts this existing web app. The separate app runtime identity reads
the vault. **This is still a privileged deployment identity:** changing the
container image lets deployed code read all secrets available to that runtime
identity, including resolved vault references. Lack of a direct Key Vault role
does not prevent this indirect access.

Protect `main` with required review and passing checks; limit repository write,
workflow-edit and environment-administration access to trusted maintainers.
Restrict the `staging` environment to `main`, require deployment reviewers where
supported, prevent self-approval/admin bypass where supported, and review any
change to its branch policies, OIDC subject or variables. Do not allow untrusted
PR code or fork runs to receive the deployment identity. Keep its OIDC subject
scoped to this repository's `staging` environment; never broaden it to another
repository or grant subscription Contributor/Owner or direct Key Vault access.
 If identity creation or federation is blocked by university policy,
ask the directory administrator for this exact federation; do not weaken the
workflow by committing a publish profile/client secret.

GitHub **Settings → Environments → staging → Environment variables**:

| Variable | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | deployment identity's **Client ID** (not Principal ID) |
| `AZURE_TENANT_ID` | Concordia Directory/Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure for Students subscription ID |
| `AZURE_STAGING_APP_NAME` | actual app name, e.g. `iris-staging-ar1` |
| `AZURE_STAGING_HOSTNAME` | actual default hostname from Overview |
| `STAGING_COST_CONFIRMED` | `true`, **only after** step 1's owner check |

These identifiers are configuration, not passwords. Finally set **repository**
variable **`STAGING_DEPLOY_ENABLED=true`**. It must be repository-scoped because
GitHub evaluates job conditions before loading environment-scoped variables.
Run **Deploy staging** on `main` with **publish_only unchecked**. Future successful
main push CI runs deploy automatically. CI failure leaves the existing app alone.

## 6. Live verification before closing #408

- Deployment job succeeds and `/api/ready/` returns the new main commit as
  `revision`, after migrations and seeding. Check both web and worker startup.
- `/` and a React deep link load with JS/CSS/fonts; `/admin/login/` has styling;
  missing `/api/...` and `/assets/...` are real 404s, not SPA HTML.
- Sign in using the fictional seed admin `coordonnateur@example.test` and the
  vault's seed password. Rotate shared demo credentials
  if their audience changes. The seed command does not reset edited passwords.
- Check secure cookies, HTTPS redirect/HSTS and real trusted-proxy behavior.
- Post a fictional listing/photo; anonymous blob URL fails, signed photo URL
  works and expires. No local filesystem photo storage or public container.
- Trigger one email through Iris to your **controlled real test recipient** and
  inspect EmailLog plus inbox/spam. Portal Try Email is not app/worker evidence.
  Do not send the fictional seed inboxes to ACS. Provider acceptance is not proof
  of inbox delivery. This step also completes US-57's SET-17 integration handoff.
- Confirm actual costs/free meters after day one and record the URL, revision,
  date, screenshots/results and remaining credit in the issue/SET-21 evidence.

The pipeline smoke proves the new revision, DB connectivity, a live supervised
worker process, and public static assets. It does not prove a non-stalled queue,
provider mail delivery, photo permissions or Azure's proxy topology. Those are
the manual checks above; do not mark them passed from local tests.

## Rollback and failure handling

The new image runs a strict deployment check, takes a PostgreSQL advisory lock,
runs migrations, optionally seeds, then supervises Gunicorn and Procrastinate.
Either child exiting stops both and fails the container. Shutdown handling is
installed before setup; TERM/INT reaches the setup process group and waits for
its transaction/connection cleanup. Cancellation never starts web/worker children.
A failed setup starts neither. Setup emits fixed `iris.deployment` events for
start, migrations, seed, completion and failure without passwords, DB error text
or user identifiers. `IRIS_OPERATOR_LANGUAGE=en` (default) or `fr` selects
translated setup/configuration diagnostics; these use registry-safe lazy gettext
so an unresolved vault reference can be reported before Django initializes.
GitHub deployment-gate annotations are intentional CI diagnostics, not app logs.

The registered `iris.recover_stalled_jobs` maintenance task runs every ten
minutes, using Procrastinate's default heartbeat-based detection (not job age).
If a dead worker left a templated email in `SENDING`, the notification service
marks it `FAILED` with `delivery_outcome_unknown` **before** retrying the native
job. Existing `SENT`/`FAILED` logs are not changed and their tasks do not resend;
`PENDING`/`RETRYING` deliveries can retry normally. Legacy email jobs without an
EmailLog are failed rather than blindly resent. Other stalled jobs retry normally.
A recovery failure logs only a fixed event and preserves the job for another
recovery pass. This is a conservative unknown-outcome policy: an accepted email
may have been sent, and an unsent one may require operator investigation/reissue;
recovery does not claim exactly-once provider delivery. Keep the worker running
for scheduled recovery and cleanup. See [Procrastinate's recovery guidance](https://procrastinate.readthedocs.io/en/stable/howto/production/retry_stalled_jobs.html).
 Repeated seed runs preserve edits. B1 has **no paid swap slot** here;
expect a short restart, and keep schema migrations compatible with the old app
while Azure replaces containers. One instance is intentional; this is not HA.

Record the previous digest before deployment. On a bad application release,
disable `STAGING_DEPLOY_ENABLED`, restore that known compatible digest in the
app's container configuration, restart and verify readiness/assets. The normal
workflow deliberately refuses older main commits; rollback is an owner operation.
Do not automatically reverse migrations or reset/flush the database. Review
schema compatibility and use Azure's retained backup/point-in-time restore if
necessary. A failed smoke check does not itself roll back migrated schema.

References: [GitHub OIDC with Azure](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect),
[Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references),
[container deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-container-github-action),
[custom container settings](https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container).
