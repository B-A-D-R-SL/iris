
# Equity and diversity statement

**Status:** Draft for teammate review · **Updated:** October 30, 2026 ·
**Tracking:** [SET-31 #590](https://github.com/B-A-D-R-SL/iris/issues/590)

Iris should support the dignity and practical needs of the households B.A.D.R.
serves. Age, disability, language confidence, family structure, cultural
background, work schedules and access to technology can affect how a person
uses the service. Equal access requires assisted routes and understandable,
reviewable decisions as well as a usable interface.

This statement proposes how the team applies that commitment. B.A.D.R. retains
authority over eligibility and distribution policy; the development team must
make the agreed policy visible, testable and open to correction.

## Design commitments and checks

| Commitment | How it applies to Iris | Evidence needed |
| --- | --- | --- |
| Access without a smartphone or personal email | Preserve walk-in registration and staff assistance. Do not make a personal online account a new requirement for an assisted workflow without an approved decision. | Demonstrate the walk-in path and staff-assisted reservation with the registration owners. |
| French and English access | Use the shared translation system for labels, messages and emails; use respectful, plain wording. These two languages are the committed scope, not a claim that every language need is covered. | Check both languages with realistic tasks; translation-key parity alone does not establish understandable wording. Agree other assistance needs with B.A.D.R. |
| Access for people with disabilities | Apply the project's WCAG 2.1 AA target: labelled inputs, visible focus, keyboard navigation, readable contrast and status messages that do not depend only on colour. | Automated checks plus manual keyboard, zoom and assistive-technology checks; record findings in the accessibility audit. |
| Usability on limited devices | Use phone-first layouts from 360 px and clear loading, empty and failure states. Avoid making successful recovery depend on repeated document uploads. | Inspect narrow layouts and interrupted or failed requests; test on the supported device/browser range. |
| Dignity and privacy | Ask only for necessary information, avoid stigmatizing labels, keep documents and decision details restricted to authorized roles. Do not expose priority scores to other households or store staff. | Compare forms with approved requirements; test role and ownership restrictions and review visible text. |
| Explainable eligibility and priority | Implement B.A.D.R.-approved, versioned rules; make reasons and a human-review route available. Deterministic rules still require fairness review. | Test threshold boundaries, varied household sizes, uncertain evidence and policy changes; review disputed outcomes with B.A.D.R. |
| Fair handling of practical constraints | Review pickup windows, no-show rules and assisted options against transport, disability, work and caregiving constraints. | Obtain stakeholder decisions for exceptions and support procedures; do not invent a new exemption or penalty in the UI. |

These checks are delivery targets, not a statement that Iris has passed a full
accessibility audit or that its policies have been proven equitable.

## Participation and team practice

The team should seek voluntary feedback through B.A.D.R. from people with
different access needs and from the staff who support them. Participation in
testing must not affect access to assistance. Use synthetic scenarios until the
project's real-data conditions are met, and keep identifying feedback out of
public issues and screenshots.

Within the student team, document decisions and share domain knowledge so that
work is not dependent on one person's availability. Review terminology and
examples for stereotypes. Treat a reported barrier as a concrete design or
policy question, with an owner and follow-up, rather than assuming that one
successful user test represents all households.

## Scope and team confirmations

- Confirm assisted support for households who are not comfortable in either
  committed language; no additional language service is promised by this draft.
- Confirm the accessibility/usability review participants and support needs with
  B.A.D.R., without creating an unnecessary demographic dataset.
- Confirm how people raise an accessibility concern or request a human decision
  review, including during an outage.

## Sources and related pages

- [Project overview and users](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/overview.md)
- [Personas](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/personas.md)
- [Shared design system and translated form fields](https://github.com/B-A-D-R-SL/iris/blob/main/docs/guides/design-system.md)
- [Wiki accessibility requirements](https://github.com/B-A-D-R-SL/iris/wiki/Accessibility)
  and [non-functional requirements](https://github.com/B-A-D-R-SL/iris/wiki/Non-Functional-Requirements)
- [Accessibility/security audit #418](https://github.com/B-A-D-R-SL/iris/issues/418)
- [Societal impact](https://github.com/B-A-D-R-SL/iris/wiki/Societal-Impact),
  [Risk register](https://github.com/B-A-D-R-SL/iris/wiki/Risks)

## Review record

Teammate reviewer: **Pending** · Review date: **Pending** · Review evidence: **Pending**
