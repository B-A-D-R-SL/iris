# Project overview

**Iris** is a web app for **B.A.D.R.**, a Montréal nonprofit. It does two things:

1. **Verifies that a household is low-income**, online or at B.A.D.R.'s office, using each adult's Revenu Québec notice of assessment and the official low-income cut-offs with the help of AI 
2. **Gets surplus food and goods to those households**: partner stores (and B.A.D.R. itself, as a store) post their surplus, verified households reserve it, and pick it up at the store with a code. Households most in need see new listings first.

It works on a phone first, in French and English, and keeps personal data in Canada under Quebec's privacy law (Law 25).

## Users

| User | What they do in Iris |
| --- | --- |
| Household (account holder) | Applies, uploads notices of assessment, browses and reserves surplus, picks it up |
| Partner store staff and managers | Post surplus, see today's pickups, confirm pickups; managers invite their staff |
| Business applying to be a partner | Fills the public "Become a partner" form |
| B.A.D.R. intake worker | Registers walk-in households, searches files, reserves for people who need help |
| B.A.D.R. admin | Approves partners, decides review cases, sets the rules, sees reports and the audit log |

Personas: [personas.md](personas.md).

## What we commit to

| Level | Scope |
| --- | --- |
| **Committed (Must)** | Accounts and roles; partner applications and stores (B.A.D.R. included); walk-in and online registration with the notice of assessment; eligibility with the low-income cut-offs; AI reading and automatic approval; duplicates; file expiry and renewal; listings with safety checks; reservations, pickup codes, no-shows; priority tiers and strikes; email notifications; staff console, review queue, audit log; reporting; Law 25 privacy rights |
| **If time allows (Should)** | Needs matching, community resource assistant, conveniences (repost, digest, store self-service, alternate for pickups) |
| **Stretch (Could)** | Furniture through B.A.D.R. |


Two promises shape everything: no real personal data goes into Iris before B.A.D.R. signs the privacy impact assessment (we use generated test data until then), and nothing beyond what eligibility needs is collected.

## Releases

| Release | Due | What B.A.D.R. gets |
| --- | --- | --- |
| Release 1 | Tue Nov 17, 2026 | Partners apply and are approved; staff register and approve walk-in households; stores post; households browse, reserve and pick up with a code. Staging online. |

TENTATIVES

| Release 2 | Fri Feb 5, 2027 | Online registration with AI reading and automatic approval; priority tiers and strikes; review queue; privacy rights; production. Pilot with real households once the privacy assessment is signed. |

TENTATIVES


| Release 3 | Tue Apr 13, 2027 | Reporting, needs, assistant and furniture if time allows; accessibility and security audit; user acceptance testing; French admin guide and handover. |


## People

| Role | Person |
| --- | --- |
| Client | B.A.D.R. |
| B.A.D.R. privacy officer | Nadia Mirsraoui |
| Team | Ten students in five pairs, see 
