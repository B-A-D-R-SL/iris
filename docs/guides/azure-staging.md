# AI contribution: 50% or more AI-generated

# Azure staging setup (SET-17)

This page records what exists in Azure for the Iris staging environment, who
can reach it, how it was created, and what is left to finish
[SET-17](https://github.com/B-A-D-R-SL/iris/issues/408). It is the handover
for whoever continues SET-17.

**Status on 13 November 2026:** the resource group, Key Vault, email service
and original budget alert are recorded as provisioned by Ammar. The SET-17 branch
now implements the release image, supervised worker, migration/seed startup, CI
image smoke and deployment workflow. Hosting resources and live Azure checks
remain to be activated by the owner using the [operations guide](azure-staging-operations.md).
No paid resources were created during repository implementation.

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

Keep email credentials in Key Vault references for App Service. For optional
local provider testing, use your own git-ignored `backend/.env`; do not print
connection strings into the terminal/chat. Normal local tests use Mailpit/fakes.

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

## Completing SET-17

Follow [Connect GitHub and activate staging](azure-staging-operations.md) in order:
verify the cost/free-allowance gate; merge reviewed code; publish the first
public GHCR image; create the database, private storage and one-instance B1 app;
resolve Key Vault references; configure scoped OIDC; then enable deployment and
record live application/worker/email/photo/proxy checks.

| Item | Status |
| --- | --- |
| Resource group, Key Vault and ACS email | Existing resources recorded above |
| Original USD 60/month budget | Existing; add early USD 15 budget before hosting |
| Azure mailer and queued email system (US-57) | Merged on main; included in this branch |
| Production settings (FIX-04) | Merged; staging inherits their security guards |
| Release image and React/static serving | Implemented in this branch |
| Worker supervision, serialized migrations and fictional seed | Implemented in this branch |
| CI release-image boot and smoke | Implemented; local validation recorded in AI_USAGE |
| Deploy workflow after successful main push CI | Implemented; disabled until owner opt-in |
| Database, private Blob storage and App Service | Owner activation still required |
| GitHub environment, public image package and OIDC roles | Owner configuration still required |
| Canadian region exception | [Proposed ADR](../04-architecture/adr-set17-student-staging.md) |
| Live Azure smoke and cost/free-meter evidence | Required before closing #408 |

## Cost correction for six months

The original handover estimated USD 30–35/month with a paid PostgreSQL server,
which would exhaust USD 100 in about three months. The six-month plan therefore
requires **confirmed student PostgreSQL free allowances for all six months**
and an actual total quote within USD 15/month, reserving USD 10 of the credit.
If that cannot be confirmed, leave hosting/deployment disabled and revise the
architecture with the team. Published allowances do not prove eligibility.

Use one Linux B1 plan, existing vault/email, public GHCR and Standard LRS storage;
no ACR, paid deployment slots, scale-out or telemetry workspace. Retain the USD
60 alert for the issue and add early USD 15 notifications. Alerts do not cap
spend. Stopping the app does not stop B1 plan charges; stopped PostgreSQL still
bills storage and automatically restarts after seven days. See the
[operations cost check](azure-staging-operations.md#1-cost-check-before-creating-anything)
for verification, pricing sources and shutdown limits.

## Related

- [SET-17 (#408)](https://github.com/B-A-D-R-SL/iris/issues/408)
- [SET-24 production (#415)](https://github.com/B-A-D-R-SL/iris/issues/415)
- [Production settings](production-settings.md)
- [Architecture, section 5](../04-architecture/architecture.md)
- [Student staging ADR](../04-architecture/adr-set17-student-staging.md)
