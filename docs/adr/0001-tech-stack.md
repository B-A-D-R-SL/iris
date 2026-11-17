# ADR 0001: Tech stack and modular monolith

Status: Accepted · Date: 2026-10-05 · Amended: 2026-11-17 (see below)

> **Amendment, November 17, 2026 (FIX-32, [#739](https://github.com/B-A-D-R-SL/iris/issues/739)).**
> The decision below is kept as written in October. Where Release 1 differs:
>
> - **Two-factor for staff** is not installed yet: `allauth.mfa` is not in
>   `INSTALLED_APPS`. It is planned for Release 2 ([US-09 #436](https://github.com/B-A-D-R-SL/iris/issues/436), SEC-03).
> - **AI Document Intelligence** is no longer the chosen notice reader.
>   [ADR 0005](0005-notice-reading.md) (Proposed) compares it with Gemini on Vertex AI
>   (Montréal) and proposes Gemini, with Document Intelligence as fallback, pending
>   B.A.D.R.'s decision. No AI service is used by Release 1 code.
> - **Hosting region:** Canada East remains the production target (SET-24). The
>   temporary staging environment cannot use Canadian regions on the student
>   subscription; see the [SET-17 ADR](../04-architecture/adr-set17-student-staging.md).
>   Staging has not been deployed.
> - **"Thresholds and weights in admin settings":** settings are versioned in the
>   `rules` module, but there is no admin screen or API to change them yet ([US-69 #560](https://github.com/B-A-D-R-SL/iris/issues/560));
>   they are loaded with `seed_rules`.

## Context

Ten part-time students build Iris in one year for B.A.D.R., a nonprofit with no developers that must run it cheaply afterwards. Iris handles low-income households' income documents under Quebec's Law 25. The main risks are wrong eligibility or priority decisions, privacy, cost and handover, not scale.

## Decision

- **Modular monolith:** one Django application and one React application, deployed as one container; one module per business area with its own tables; modules call each other only through `services.py` and `queries.py`; boundaries checked by import-linter in CI. Details: the architecture document and diagrams (published in Iteration 2, SET-06).
- **Back end:** Python 3.13, Django 6.1, Django REST Framework, django-allauth (headless, two-factor for staff), drf-spectacular, Procrastinate (job queue in PostgreSQL).
- **Front end:** React 19, TypeScript, Vite, Mantine, TanStack Query, React Router, react-i18next; installable on a phone.
- **Data:** PostgreSQL 17.
- **Hosting:** Azure, Canada East: App Service (container), PostgreSQL Flexible Server, private Blob Storage, Communication Services (email), Key Vault, AI Document Intelligence. About 35 to 50 USD per month for production, covered by B.A.D.R.'s Microsoft nonprofit grant.
- **Outside services behind adapters** (file storage, email, document reading) with fakes for tests.

## Why it is the best fit

| Need | How the decision answers it |
| --- | --- |
| Ten people in parallel without breaking each other | One module per pair, walls checked in CI |
| Never two households for the last unit | One database, one atomic update |
| Fair, explainable decisions | Rules in plain Python, tested exhaustively, with versioned settings |
| B.A.D.R. changes its policy | Thresholds and weights in admin settings |
| Data in Quebec, low cost | Azure Canada East, one container |
| Simple handover | One application to run |

## Consequences

- One deployment unit: a bad release affects everything; mitigated by CI, staging and release approval.
- Shared server and database: heavy work runs in background jobs; timeouts on outside calls.
- Walls need discipline: CI catches imports, reviews catch the rest.
- Scaling: several copies behind a load balancer handle tens of thousands of households; a module can be extracted later if one part ever needs it.

## Alternatives considered

| Alternative | Better at | Why not |
| --- | --- | --- |
| Microservices | Isolation, scaling one part | Cost, complexity, harder reservations, hard handover |
| Serverless functions | Pay per use | Cold starts, hard local testing, transactions |
| Supabase (backend-as-a-service) | Less back-end code | Rules in SQL, hard to test and version; vendor dependence |
| Power Apps (low-code) | Maintenance by B.A.D.R. | Licences for households, cannot express our rules, little software engineering |
| Spring Boot, ASP.NET, NestJS | Teams stronger in Java, C# or TypeScript | Django gives admin, security and migrations built in; Python suits the AI work |
