# ADR 0001: Tech stack and modular monolith

Status: Accepted · Date: 2026-10-05

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
