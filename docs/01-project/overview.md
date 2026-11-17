<!-- AI contribution: 50% or more AI-generated -->

# Project overview

This page describes the whole-project target across releases. **Release 1 uses
staff-led walk-in registration:** staff upload notices and enter their values.
Online household uploads, AI reading/automatic approval and priority tiers are
future work, not active Release 1 features. See the
[Release 1 architecture scope](../04-architecture/architecture.md#scope).

**Iris** is a web app for **B.A.D.R.**, a Montréal nonprofit. It does two things:

1. **Verifies that a household is low-income**, online or at B.A.D.R.'s office, using each adult's Revenu Québec notice of assessment and the official low-income cut-offs with the help of AI 
2. **Gets surplus food and goods to those households**: partner stores (and B.A.D.R. itself, as a store) post their surplus, verified households reserve it, and pick it up at the store with a code. Households most in need see new listings first.

It works on a phone first, in French and English, and keeps personal data in Canada under Quebec's privacy law (Law 25).

## Users

The middle column is what `main` does at Release 1 (`c13fc04`, November 17, 2026).
The last column is planned and not built yet. Stories without a milestone are
not yet scheduled to a release.

| User | In Release 1 | Planned |
| --- | --- | --- |
| Household (account holder) | Registers in person at B.A.D.R. (staff enter the file). Browse (US-36) and reserve (US-41) are built and tested at API level, but no household account is linked to a file yet, so no household can sign in and use them in a running instance. | Account linking ([US-93 #704](https://github.com/B-A-D-R-SL/iris/issues/704), Release 2); online application and notice upload ([US-21 #473](https://github.com/B-A-D-R-SL/iris/issues/473), Release 2); cancel a reservation ([US-43 #519](https://github.com/B-A-D-R-SL/iris/issues/519)) |
| Partner store staff and managers | Post surplus; confirm pickups by scanning or typing the code | Today's expected pickups ([US-38 #509](https://github.com/B-A-D-R-SL/iris/issues/509)); managers invite their staff ([US-06 #433](https://github.com/B-A-D-R-SL/iris/issues/433)) |
| Business applying to be a partner | Fills the public "Become a partner" form | |
| B.A.D.R. intake worker | Registers walk-in households, uploads their notices, submits and approves files, searches files | Reserve on someone's behalf ([US-47 #526](https://github.com/B-A-D-R-SL/iris/issues/526)) |
| B.A.D.R. admin | Everything an intake worker does; approves partners; edits, deactivates and reactivates stores; manages categories; suspends and reactivates households; searches the audit log | Invite staff ([US-05 #432](https://github.com/B-A-D-R-SL/iris/issues/432)); decide review cases ([US-68 #559](https://github.com/B-A-D-R-SL/iris/issues/559)); rule settings screens ([US-69 #560](https://github.com/B-A-D-R-SL/iris/issues/560)); reports |

Who may do what, checked against the code: the
[permission matrix](../02-requirements/business-rules.md#permission-matrix).

Personas: [personas.md](personas.md).

## What we commit to

| Level | Scope |
| --- | --- |
| **Committed (Must)** | Accounts and roles; partner applications and stores (B.A.D.R. included); walk-in and online registration with the notice of assessment; eligibility with the low-income cut-offs; AI reading and automatic approval; duplicates; file expiry and renewal; listings with safety checks; reservations, pickup codes, no-shows; priority tiers and strikes; email notifications; staff console, review queue, audit log; reporting; Law 25 privacy rights |
| **If time allows (Should)** | Needs matching, community resource assistant, conveniences (repost, digest, store self-service, alternate for pickups) |
| **Stretch (Could)** | Furniture through B.A.D.R. |


Two promises shape everything: no real personal data goes into Iris before B.A.D.R. signs the privacy impact assessment (we use generated test data until then), and nothing beyond what eligibility needs is collected.

## Releases

| Release | Due | Planned delivery |
| --- | --- | --- |
| Release 1 | Tue Nov 17, 2026 | Delivered on `main`: partners apply and are approved; staff register, search and approve walk-in households; admins manage stores, categories, suspensions and the audit log; stores post goods and confirm pickups with a code. Browse and reserve are built at API level, but households cannot use them until account linking (US-93, Release 2). Staging is the deployment target but has not been deployed. |
| Release 2 (tentative) | Fri Feb 5, 2027 | Online registration with AI reading and automatic approval; priority tiers and strikes; review queue; privacy rights; production. Pilot with real households once the privacy assessment is signed. |
| Release 3 (tentative) | Tue Apr 13, 2027 | Reporting, needs, assistant and furniture if time allows; accessibility and security audit; user acceptance testing; French admin guide and handover. |

**Staging status — November 17, 2026:** the release image and deployment
workflow are implemented and SET-17 (#408) is closed, but staging has never been
deployed: `STAGING_DEPLOY_ENABLED` is unset, every `deploy-staging` run was
skipped and GitHub records no deployment. The owner's
[SET-17 activation status](https://github.com/B-A-D-R-SL/iris/pull/700#issuecomment-6887009431)
explains why: the student subscription's region policies and PostgreSQL capacity
blocked the database. The database, storage and App Service still need
activation after the hosting region/subscription decision. See the [deployment status](../04-architecture/architecture.md#5-release-1-deployment).

## People

| Role | Person |
| --- | --- |
| Client | B.A.D.R. |
| Product Owner | Nadia Misraoui, General Coordinator of B.A.D.R. (see the wiki [Stakeholder](https://github.com/B-A-D-R-SL/iris/wiki/Stakeholder) page) |
| B.A.D.R. privacy officer | Nadia Misraoui |
| Team | Ten students in five pairs: Platform (Ammar Ranko, Danial Kouba), Fairness & partners (Reuven Minciotti, Leon Kojakian), Registration (Massimo Paolini, Vladimir Shterenkiker), Goods (Anthony Monaco, Ryan Cheung), Staff & insight (Mark Antoun, Firas Al Haddad). Contributions are on the wiki [Contributions](https://github.com/B-A-D-R-SL/iris/wiki/Contributions) page. |
