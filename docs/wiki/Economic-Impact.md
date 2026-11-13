
# Economics and economic impact

**Status:** Draft for teammate review · **Updated:** October 30, 2026 ·
**Tracking:** [SET-31 #590](https://github.com/B-A-D-R-SL/iris/issues/590)

Iris has three distinct economic dimensions: the value of goods actually
redistributed, the labour needed to build and maintain the system, and its
recurring service costs. The estimates below are planning scenarios, not
supplier quotations, observed savings or approved spending commitments.

## Value of goods redistributed

The planned reporting workflow sums the estimated value of **picked-up units**
over a selected period. Stores may enter an estimated value; otherwise the
category default applies. Category values are documented in the
[business rules](https://github.com/B-A-D-R-SL/iris/blob/main/docs/02-requirements/business-rules.md).
Reporting is tracked by [US-72 #564](https://github.com/B-A-D-R-SL/iris/issues/564),
with the dashboard in [#562](https://github.com/B-A-D-R-SL/iris/issues/562) and CSV
export in [#563](https://github.com/B-A-D-R-SL/iris/issues/563).

Do not count an uncollected reservation as redistributed goods. State the value
method and period alongside totals. These estimated values are not cash
revenue, tax receipts, measured household savings or proof of avoided waste.
Keep public reports aggregate and review small totals for identification risk.

## Cost if built by consultants

The example below illustrates a **lean Release 1 build from scratch**, using existing open-source frameworks
and a single blended rate. Its 500 hours and CAD 65/hour rate are planning
assumptions, not a quote or a commitment that every requirement can be
completed within that time.

| Work package | Assumed hours | At CAD 65/hour |
| --- | ---: | ---: |
| Requirements and interface design | 50 | CAD 3,250 |
| Platform, accounts and deployment | 80 | CAD 5,200 |
| Partner applications, stores, listings and reservations | 110 | CAD 7,150 |
| Walk-in intake and eligibility | 100 | CAD 6,500 |
| Audit and notifications | 60 | CAD 3,900 |
| Integration, testing, documentation and handover | 100 | CAD 6,500 |
| **Illustrative total** | **500** | **CAD 32,500** |

For context, Canada's Job Bank reports a median **employee wage** of
[CAD 45.67/hour for software programmers in Montréal](https://www.on.jobbank.gc.ca/marketreport/wages-occupation/22532/22446)
(2023–2024 data). An employee wage is not a consultant quote: contractor rates
can include overhead and vary with experience and scope. The CAD 65/hour rate
above is an assumption, not a Job Bank consultant rate.

This example covers the Release 1 workflow described in the
[project overview](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/overview.md).
It excludes later online registration and AI reading, priority tiers, the full
review queue, privacy-rights features and later reporting. It also excludes
taxes, cloud bills, formal legal services, B.A.D.R.'s staff time, ongoing
maintenance and any allowance for overruns. **A price for the full project is
not yet estimated.** Student contributions are in-kind effort, not money paid.

Before relying on the example, have the team validate its hours and scope or
obtain a consultant quote. Every additional 100 hours at CAD 65/hour adds
CAD 6,500. Keep CAD labour figures and USD cloud figures separate unless an
explicit dated exchange rate is supplied.

## Infrastructure costs

[ADR 0001](https://github.com/B-A-D-R-SL/iris/blob/main/docs/adr/0001-tech-stack.md)
records an early estimate of **USD 35–50/month for production**. The wiki's
[NFR-07](https://github.com/B-A-D-R-SL/iris/wiki/Non-Functional-Requirements)
sets a target of **under USD 60/month per environment**. Neither figure is a
current Azure quote or a measured bill; the original estimate must be checked
against the selected configuration and usage.

| Planned component | Inputs required for a current estimate |
| --- | --- |
| Azure App Service and release image | Linux/container plan, instance count, runtime hours and image registry. Include the background worker's capacity. |
| PostgreSQL Flexible Server | Compute, database storage, backup retention and redundancy. |
| Private Blob Storage | Document/photo volume, retention, read/write operations and transfer. |
| Communication Services email | Message volume, applicable service charges and domain configuration. |
| Key Vault and Application Insights | Secret operations, telemetry ingestion and retention. |
| AI Document Intelligence for the later online flow | Pages processed, selected model, regional availability and retries; do not treat it as free or as an active Release 1 workflow. |
| Other operating items | Staging, domain renewal, support, backup/restore testing and maintenance labour. |

Use the [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
with a saved date, region, SKU and usage assumptions. A Canada East deployment
is the architectural target; verify every selected service's processing and
storage location rather than substituting a cheaper region.

For scale only, the old USD 35–50/month assumption annualizes to **USD 420–600**
for one environment, or **USD 840–1,200** for two equally sized environments.
The USD 60/month target annualizes to USD 720 per environment; these arithmetic
scenarios do not establish that the target is achievable.

Budget alerts require an accountable responder. They do **not** automatically
cap usage or stop charges; see
[Microsoft's budget documentation](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
Compare actual gross charges and credits separately after staging runs, then
revise this estimate before production.

## Funding and sustainability

The closed [kickoff record #591](https://github.com/B-A-D-R-SL/iris/issues/591)
records funding for AI usage and Azure hosting. ADR 0001 and the existing
[Budget wiki page](https://github.com/B-A-D-R-SL/iris/wiki/Budget) identify
B.A.D.R.'s Microsoft nonprofit grant as the hosting funding source.

[Microsoft currently advertises USD 2,000/year in Azure credits for eligible
nonprofits](https://www.microsoft.com/en-us/nonprofits/azure) (checked October
30, 2026). This is public offer information, not proof of B.A.D.R.'s current
balance, renewal or coverage of every selected service. Confirm those details
in the organization's grant/subscription records without publishing account
identifiers or billing documents.

The proposed operating model is B.A.D.R.-owned service accounts, grant credits
where applicable, and an agreed organizational budget for uncovered costs.
Confirm the billing owner, renewal date, paid maintenance arrangement and
fallback if credits expire. Do not assume the grant funds maintenance labour.
No household fee, sale of personal information or unapproved donor commitment
is introduced by this model.

## Team confirmations

- Validate the consultant work packages, hours, rates and exclusions.
- Save an itemized regional Azure estimate and compare it with the cost target.
- Confirm funding coverage, payer, grant renewal and a post-handover maintainer.
- Agree report wording so estimated goods value is not presented as measured
  economic savings.

## Review record

Teammate reviewer: **Pending** · Review date: **Pending** · Review evidence: **Pending**
