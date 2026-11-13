# AI contribution: 50% or more AI-generated

# Azure staging setup (SET-17)

This page records what exists in Azure for the Iris staging environment, who
can reach it, how it was created, and what is left to finish
[SET-17](https://github.com/B-A-D-R-SL/iris/issues/408). It is the handover
for whoever continues SET-17.

**Status on 12 November 2026:** the resource group, Key Vault, email service
and budget alert exist and work. The database, photo storage, App Service and
deploy workflow are not created yet.

## Subscription and region

| Item | Value |
| --- | --- |
| Subscription | Azure for Students, owned by @ammarranko |
| Directory | Concordia University (members sign in with their Concordia account) |
| Credit | 100 USD, renewable each school year; no credit card, so Azure stops services instead of charging when the credit runs out |
| Allowed regions | West US 2, West US, South Central US, Mexico Central, Norway East |

The subscription has a Microsoft policy, **Allowed resource deployment
regions**, that excludes every Canadian region. The architecture places
staging in Canada East, so the staging setup differs for now:

- Services with a separate **data location** (Communication Services) store
  their data in **Canada**.
- Region-bound services go to **West US 2**. The Key Vault holds keys only,
  and staging holds fictional data only.
- When B.A.D.R. activates its Microsoft nonprofit Azure grant, staging and
  production are rebuilt on B.A.D.R.'s subscription in Canada East
  (SET-24, #415). Nothing here is moved; it is recreated with the same steps.

The Concordia directory also gives a few university IT administrators
inherited access to every student subscription. That is normal for school
accounts and is one more reason real household data must never go into this
environment.

## What exists now

All resources are in the resource group **`iris-staging`** (tags
`project=iris`, `env=staging`).

| Resource | Name | Location | Purpose |
| --- | --- | --- | --- |
| Resource group | `iris-staging` | West US 2 | Holds every staging resource |
| Key Vault | `iris-stg-kv-ar1` | West US 2 | Stores staging secrets. RBAC permission model, 7-day soft-delete retention |
| Email Communication Service | `iris-stg-email-ar1` | Global, data in Canada | Owns the sending domain |
| Email domain | `AzureManagedDomain` | Global | Free Azure-managed domain; Domain, SPF, DKIM, DKIM2 and DMARC verified |
| Communication Service | `iris-stg-acs-ar1` | Global, data in Canada | The service the app calls to send email; linked to the domain above |
| Budget | `iris-staging-budget` | Subscription | 60 USD per month, alerts at 50, 80 and 100 % of actual cost |

**Sender address:** `DoNotReply@e05b7d2a-a167-48c1-ab47-0ba4b41d3386.azurecomm.net`

The Azure-managed domain is for testing: it allows only a few emails per hour
and may land in spam. Production will use B.A.D.R.'s own domain.

### Secrets in the Key Vault

| Secret | Contents |
| --- | --- |
| `acs-connection-string` | Connection string for `iris-stg-acs-ar1` |

The value was copied from Communication Services straight into the vault and
was never displayed, written to a file or pasted in chat. Secrets live **only**
in the vault. Never commit them, paste them in chat, or put them anywhere other
than your own git-ignored `backend/.env`.

## Who has access

| Person | Role | Scope | Allows |
| --- | --- | --- | --- |
| @ammarranko | Owner | Subscription | Everything, including billing and access control |
| @ammarranko | Key Vault Secrets Officer | `iris-stg-kv-ar1` | Create, read and change secrets |
| @DaniK1001 | Contributor | `iris-staging` | Create, change and delete staging resources |
| @DaniK1001 | Key Vault Secrets User | `iris-stg-kv-ar1` | Read secrets only |
| @leonlolleonlol | Contributor | `iris-staging` | Create, change and delete staging resources |
| @leonlolleonlol | Key Vault Secrets User | `iris-stg-kv-ar1` | Read secrets only |

Notes:

- Contributor does not allow reading Key Vault secrets or changing access.
  Only the Owner can give or remove access, so a teammate cannot lock anyone
  out or grant themselves more.
- Leon's Contributor role was first created as an *eligible* Privileged
  Identity Management assignment, which must be activated for up to 8 hours
  at a time. It was replaced by a permanent *active* assignment, like
  Danial's. The eligible assignment was removed.
- Every change is recorded under the person's name in `iris-staging` →
  **Activity log**.

### Adding someone

1. Portal → **Resource groups** → `iris-staging` → **Access control (IAM)**
   → **+ Add** → **Add role assignment**.
2. **Privileged administrator roles** tab → **Contributor** → **Next** →
   **+ Select members** → their Concordia account → **Review + assign**.
3. If they need to read secrets: Key Vault `iris-stg-kv-ar1` → **Access
   control (IAM)** → add **Key Vault Secrets User** (never Officer or
   Administrator).
4. On the **Assignment type** tab, choose **Active** and **Permanent**, or
   they will have to activate the role every 8 hours.

## Using it

Sign in at <https://portal.azure.com> with your Concordia account and choose
the **Azure for Students** subscription.

Read the email connection string into your local, git-ignored `backend/.env`:

```bash
az login
az account set --subscription "Azure for Students"
az keyvault secret show --vault-name iris-stg-kv-ar1 -n acs-connection-string --query value -o tsv
```

Send a test email from the portal: `iris-stg-acs-ar1` → **Email** → **Try
Email**. Send real test emails to your own address only. Unit tests and CI use
the fake mailer, with no network and no key.

## How it was created

Commands run with the Azure CLI 2.92 (PowerShell). Always pass
`--subscription "Azure for Students"`; the same sign-in can also see a
Concordia IT subscription that must not be touched.

1. **Sign in and select the subscription.**

   ```powershell
   az login --use-device-code
   az account set --subscription "Azure for Students"
   ```

2. **Check the region policy.** This found the five allowed regions.

   ```powershell
   az policy assignment list --query "[].{name:displayName, params:parameters}" -o json
   ```

3. **Register the resource providers** (new student subscriptions start with
   them off).

   ```powershell
   "Microsoft.Communication","Microsoft.KeyVault","Microsoft.Web","Microsoft.DBforPostgreSQL","Microsoft.Storage" | ForEach-Object { az provider register --namespace $_ }
   ```

4. **Resource group.**

   ```powershell
   az group create -n iris-staging -l westus2 --tags project=iris env=staging
   ```

5. **Key Vault, and permission to manage its secrets.**

   ```powershell
   az keyvault create -g iris-staging -n iris-stg-kv-ar1 -l westus2 --enable-rbac-authorization true --retention-days 7 --tags project=iris env=staging
   $me   = az ad signed-in-user show --query id -o tsv
   $kvId = az keyvault show -n iris-stg-kv-ar1 --query id -o tsv
   az role assignment create --assignee-object-id $me --assignee-principal-type User --role "Key Vault Secrets Officer" --scope $kvId
   ```

6. **Email service, domain and Communication Services**, with data stored in
   Canada.

   ```powershell
   az extension add -n communication
   az communication email create -n iris-stg-email-ar1 -g iris-staging --location global --data-location canada
   az communication email domain create --domain-name AzureManagedDomain --email-service-name iris-stg-email-ar1 -g iris-staging --location global --domain-management AzureManaged
   $domId = az communication email domain show --domain-name AzureManagedDomain --email-service-name iris-stg-email-ar1 -g iris-staging --query id -o tsv
   az communication create -n iris-stg-acs-ar1 -g iris-staging --location global --data-location canada --linked-domains $domId
   ```

7. **Store the connection string** without displaying it.

   ```powershell
   $acs = az communication list-key -n iris-stg-acs-ar1 -g iris-staging --query primaryConnectionString -o tsv
   az keyvault secret set --vault-name iris-stg-kv-ar1 -n acs-connection-string --value $acs --output none
   Remove-Variable acs
   ```

8. **Test email.** `az communication email send` to the subscription owner
   returned `Succeeded`.

9. **Budget.** Created through the Cost Management API
   (`Microsoft.Consumption/budgets`, API version `2023-05-01`): monthly,
   60 USD, alerts at 50, 80 and 100 %.

10. **Team access.** Contributor on `iris-staging` and Key Vault Secrets User
    on the vault for Danial and Leon, through the portal (see
    [Adding someone](#adding-someone)).

## What is left for SET-17

SET-17's done-when list: resource group with App Service (Linux container, B1),
PostgreSQL Flexible Server B1ms, private Blob container, Communication Services
email and Key Vault; `deploy-staging.yml` that deploys `main` after CI passes,
runs migrations and seeds staging; budget alert at 60 USD.

| Item | Status |
| --- | --- |
| Resource group | Done |
| Communication Services email | Done |
| Key Vault | Done |
| Budget alert at 60 USD | Done |
| Production settings (FIX-04, #630) | Merged in #683 |
| Azure mailer adapter (T-08.57.2, #540) | Not started; production refuses console email, so staging needs it |
| PostgreSQL Flexible Server B1ms | To do |
| Private Blob container for listing photos | To do |
| Release image (web server, built React app, worker) | To do |
| App Service (Linux container, B1) | To do, create last because it bills from creation |
| `deploy-staging.yml` | To do |
| Architecture section 5 and an ADR for the region | To do once the region is final |

### Remaining steps

Create the database, storage and App Service in **West US 2**, in
`iris-staging`, and put each secret straight into `iris-stg-kv-ar1`.

1. **Database.**

   ```powershell
   $hex    = -join ([Security.Cryptography.RandomNumberGenerator]::GetBytes(20) | ForEach-Object { $_.ToString("x2") })
   $dbPass = "Iris-$hex"
   az postgres flexible-server create -g iris-staging -n iris-stg-db-ar1 -l westus2 --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 17 --admin-user irisadmin --admin-password $dbPass --public-access 0.0.0.0 --backup-retention 7 --yes
   az postgres flexible-server db create -g iris-staging -s iris-stg-db-ar1 -d iris
   az keyvault secret set --vault-name iris-stg-kv-ar1 -n database-url --value "postgresql://irisadmin:$dbPass@iris-stg-db-ar1.postgres.database.azure.com:5432/iris?sslmode=require" --output none
   ```

   `--public-access 0.0.0.0` admits Azure services only. That is acceptable
   for fictional staging data; production uses private networking.

2. **Django secret key and seed password** (FIX-04 requires at least 50
   characters).

   ```powershell
   $djKey = -join ([Security.Cryptography.RandomNumberGenerator]::GetBytes(40) | ForEach-Object { $_.ToString("x2") })
   az keyvault secret set --vault-name iris-stg-kv-ar1 -n django-secret-key --value $djKey --output none
   $seed = "Seed-" + (-join ([Security.Cryptography.RandomNumberGenerator]::GetBytes(12) | ForEach-Object { $_.ToString("x2") }))
   az keyvault secret set --vault-name iris-stg-kv-ar1 -n seed-password --value $seed --output none
   ```

3. **Private photo storage.**

   ```powershell
   az storage account create -g iris-staging -n irisstgfilesar1 -l westus2 --sku Standard_LRS --kind StorageV2 --allow-blob-public-access false --min-tls-version TLS1_2
   $stConn = az storage account show-connection-string -g iris-staging -n irisstgfilesar1 --query connectionString -o tsv
   az storage container create --name listing-photos --connection-string $stConn --public-access off
   az keyvault secret set --vault-name iris-stg-kv-ar1 -n storage-connection-string --value $stConn --output none
   ```

4. **Release image** (code, in this branch):
   - Add `gunicorn` and `whitenoise` with `uv add`.
   - Multi-stage Dockerfile at the repository root: build the frontend with
     `pnpm build`, copy `dist` into the backend image, run `collectstatic`,
     run as a non-root user (keep FIX-24's rules).
   - Settings: WhiteNoise middleware, `STATIC_ROOT`, the built React app
     served by Django with a fallback to `index.html` outside `api/`,
     `admin/`, `accounts/` and `static/`.
   - `backend/scripts/start.sh`: `migrate --noinput`; seed when
     `IRIS_SEED_ON_START=1`; start `procrastinate worker` in the background;
     `exec gunicorn` on port 8000. Running the worker in the web container is
     a Release 1 limitation to record in the architecture document.

5. **App Service** with a system-assigned identity that can read the vault.

   ```powershell
   az appservice plan create -g iris-staging -n iris-stg-plan --is-linux --sku B1 -l westus2
   az webapp create -g iris-staging -p iris-stg-plan -n iris-staging-ar1 --container-image-name ghcr.io/b-a-d-r-sl/iris:latest
   $principal = az webapp identity assign -g iris-staging -n iris-staging-ar1 --query principalId -o tsv
   az role assignment create --assignee-object-id $principal --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" --scope $kvId
   az webapp config set -g iris-staging -n iris-staging-ar1 --always-on true
   ```

   App settings: `DJANGO_SETTINGS_MODULE=iris.settings.production`,
   `WEBSITES_PORT=8000`, `DJANGO_ALLOWED_HOSTS=iris-staging-ar1.azurewebsites.net`,
   `ALLAUTH_TRUSTED_PROXY_COUNT=1`, and each secret as a Key Vault reference,
   for example
   `DJANGO_SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://iris-stg-kv-ar1.vault.azure.net/secrets/django-secret-key/)`.
   Set the health check path to `/api/health/`. See
   [production settings](production-settings.md) for every required variable.

6. **`deploy-staging.yml`:** runs when the CI workflow succeeds on `main`;
   builds and pushes the image to `ghcr.io` with `GITHUB_TOKEN`; signs in to
   Azure (OIDC with `azure/login`, or a publish profile if app registration is
   blocked in the Concordia directory); deploys with `azure/webapps-deploy`;
   then calls `/api/health/` until it answers.

7. **Check:** sign in with a seeded account, post a listing with a photo,
   trigger an email, and record the URL and date for SET-21 (#412).

## Cost

| Resource | About per month (USD) |
| --- | --- |
| Key Vault, email service, budget | Under 1 |
| PostgreSQL Flexible Server B1ms, 32 GB | 15 to 18 |
| App Service plan B1 | 13 to 15 |
| Storage account | Under 1 |
| **Total once complete** | **About 30 to 35** |

The 100 USD credit lasts about three months once everything runs. Stop the
database when it is not used:

```powershell
az postgres flexible-server stop -g iris-staging -n iris-stg-db-ar1
```

## Related

- [SET-17 Azure staging environment and deploy workflow (#408)](https://github.com/B-A-D-R-SL/iris/issues/408)
- [T-08.57.2 Azure and fake mailers (#540)](https://github.com/B-A-D-R-SL/iris/issues/540)
- [SET-24 Production environment and release workflow (#415)](https://github.com/B-A-D-R-SL/iris/issues/415)
- [LLL spike: keyless secret access (#682)](https://github.com/B-A-D-R-SL/iris/issues/682)
- [Production settings](production-settings.md)
- [Architecture, section 5](../04-architecture/architecture.md)
