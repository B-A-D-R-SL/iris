
# Societal impact

**Status:** Draft for teammate review · **Updated:** October 30, 2026 ·
**Tracking:** [SET-31 #590](https://github.com/B-A-D-R-SL/iris/issues/590)

Iris is intended to help B.A.D.R. verify eligibility and connect households to
surplus food and essential goods. The intended benefits are simpler intake,
more reliable pickups and a traceable distribution process. These are goals
to evaluate with B.A.D.R.; the project has not established a measured reduction
in poverty, food insecurity, waste or staff workload.

## Effects on the people who use Iris

| Group | Intended benefit | Potential harm | How the design reduces it |
| --- | --- | --- | --- |
| Households seeking assistance | Clear application status and access to available goods. | An incorrect eligibility result can deny help; collecting financial documents can expose or stigmatize a household. | Minimize collected data, keep documents private, preserve explainable decisions and make a staff review route available. |
| People with limited device access, literacy or language confidence | A short mobile flow can reduce travel and repeated form filling. | Digital-only intake or confusing instructions can exclude people who already face barriers. | Maintain assisted walk-in registration and staff reservations; provide French/English plain language, accessible forms and clear recovery from errors. |
| Households competing for scarce goods | Approved priority rules can give households most in need earlier access. | Connectivity, pickup distance, work and caregiving schedules can still shape who benefits. No-show penalties can amplify those barriers. | B.A.D.R. approves priority and strike policies; keep rule versions and human review. Test realistic scheduling and assisted-access scenarios before treating a rule as fair. |
| Partner businesses | A simple posting and pickup process can make donating surplus easier. | Inaccurate availability or unsafe listings can waste trips or put recipients at risk. | Validate quantities and pickup windows, require the safe-and-allowed confirmation, apply category safety rules and confirm pickups consistently. |
| B.A.D.R. staff and volunteers | A shared file and audit trail can reduce duplicate work and support accountability. | Automation can hide mistakes; review queues or an outage can add work and delay service. | Show decision reasons, preserve staff responsibility, provide audit records, and agree an operational fallback and handover guide. |

These are design responses and requirements. End-to-end delivery and operational
effectiveness must be demonstrated with the corresponding stories and acceptance
checks; this page does not certify them as implemented.

## Environment and sustainability

Redistribution may put available food and goods to use. Pickup records and
estimated goods values can describe activity, but they do not prove avoided
landfill, avoided emissions or increased household nutrition. Such claims need
an agreed baseline and measurement method. Extra pickup travel and cloud
processing also consume resources; the design should avoid unnecessary uploads,
repeat document processing and excessive data retention.

The modular monolith and operating guide aim to make Iris maintainable for a
nonprofit without an internal development team. Continued staff time, service
costs and maintenance ownership remain part of its societal cost.

## Proposed evaluation with B.A.D.R.

| Question | Evidence to collect during an approved pilot |
| --- | --- |
| Can people complete intake and recover from mistakes? | Observed task completion and support needs for self-service and assisted flows; record accessibility blockers without publishing case details. |
| Does distribution work reliably? | Completed pickups, cancellations, no-shows and stock-conflict failures for an agreed period; review the reasons with staff. |
| Can people challenge an error? | Whether test participants find the human-review route; aggregate review turnaround and corrections after deployment. |
| Is staff work manageable? | Staff feedback, observed intake time and review-queue age compared with a baseline agreed before the pilot. |
| What value was redistributed? | Picked-up units and their documented estimated value; label estimates and avoid equating listed or reserved goods with completed pickups. |

B.A.D.R. should agree targets and collection methods before the pilot. Prefer
aggregate operational evidence and voluntary feedback. Do not collect new
sensitive demographic attributes merely to populate a report; small-group
results and free-text feedback can identify households and need privacy review.

## Sources and related pages

- [Project overview and committed scope](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/overview.md)
- [Personas and design needs](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/personas.md)
- [Goods categories and safety rules](https://github.com/B-A-D-R-SL/iris/blob/main/docs/02-requirements/business-rules.md)
- [Walk-in registration #461](https://github.com/B-A-D-R-SL/iris/issues/461),
  [Human review request #570](https://github.com/B-A-D-R-SL/iris/issues/570),
  [Redistributed value #564](https://github.com/B-A-D-R-SL/iris/issues/564)
- [Risk register](https://github.com/B-A-D-R-SL/iris/wiki/Risks),
  [Equity and diversity](https://github.com/B-A-D-R-SL/iris/wiki/Diversity-Statement),
  [Economics](https://github.com/B-A-D-R-SL/iris/wiki/Economic-Impact)

## Team confirmations

- Agree pilot participants, baseline measures and feedback methods with B.A.D.R.
- Confirm the assisted-service and outage procedures and the owner of each.
- Confirm how staff will review priority, pickup and no-show policy concerns.

## Review record

Teammate reviewer: **Pending** · Review date: **Pending** · Review evidence: **Pending**
