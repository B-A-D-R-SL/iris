
# Risk register

**Status:** Draft for teammate review · **Updated:** October 30, 2026 ·
**Tracking:** [SET-31 #590](https://github.com/B-A-D-R-SL/iris/issues/590)

Iris handles income evidence and controls access to scarce goods. This register
prioritizes failures that could harm households, prevent a safe pilot, or stop
the team from delivering the committed workflow. It extends the existing wiki
risk list with actions and evidence needed to reassess each risk.

Likelihood and impact are qualitative estimates, not measured probabilities.
**Critical** means potential serious privacy harm or wrongful exclusion from
assistance; **High** means a material delivery or operational failure. Owners
below are proposed coordination roles, to confirm at planning; this page does
not assign new GitHub work. A mitigation remains planned until its evidence is
linked and reviewed.

## Top risks and response

| ID / priority | Risk and consequence | Likelihood / impact | Mitigation and next evidence | Proposed follow-up owner |
| --- | --- | --- | --- | --- |
| R-01 / Critical | Income documents or household records leak through public storage, logs, screenshots or unauthorized access. A real-data pilot could harm households and have to stop. | Medium / Critical | Use generated development data; review necessary fields; require server-side role/ownership checks, private files and privacy-safe logs. Before real data, collect the signed privacy impact assessment and end-to-end permission/storage evidence. | Privacy lead with module owners and B.A.D.R. |
| R-02 / Critical | Incorrect eligibility or priority rules exclude a household or give scarce goods to the wrong group. | Medium / Critical | B.A.D.R. approves policy; preserve rule versions, thresholds, inputs and outcomes; test cutoff boundaries and policy changes; provide human review. Link approved examples and reproducible decision tests. | Eligibility and priority owners with B.A.D.R. |
| R-03 / High | AI reads an amount, tax year or identity field incorrectly and online approval trusts it. | Medium / High | Keep extraction separate from deterministic decisions; show values for confirmation; route uncertain, inconsistent or edited results for staff review under approved rules. Validate the document-reading spike on synthetic notices before adopting the online workflow. | Document-reading and review owners |
| R-04 / High | Unclear policy or an unfinished shared service blocks several modules or causes incompatible implementations. | High / High | Agree API contracts and policy examples early; sequence Must workflows first; integrate small changes and demonstrate a complete path each iteration. Audit recording is an immediate shared dependency; verify #549 and the #547 service contract rather than assuming they are delivered. | Iteration coordinator with module owners |
| R-05 / High | Concurrent reservations or repeated pickup requests oversell stock or count a pickup twice. | Medium / High | Use database transactions, constraints and atomic updates; test concurrent requests, retries and cancellation/pickup conflicts against PostgreSQL. Agree no-show and stock-release timing before implementation. | Listings and reservations owners |
| R-06 / High | A phone-only, inaccessible or unclear flow excludes people without devices, reliable connectivity or fluency in French/English. | High / High | Keep assisted walk-in registration and staff reservations; use bilingual plain language, 360 px layouts, labelled fields and keyboard access. Demonstrate assisted workflows and record accessibility/usability findings, not just translation-key parity. | Registration and frontend owners with B.A.D.R. |
| R-07 / High | Cloud costs, grant expiry or an unsupported service region make the pilot unaffordable or violate the agreed data-location policy. | Medium / High | Reprice every service and environment; confirm credits and payer; review storage, document processing, backups and telemetry locations. Establish budget alerts and a response owner, then compare actual usage with the estimate. | Platform owner with B.A.D.R. |
| R-08 / High | A failed release, lost database or unavailable maintainer interrupts assistance after student handover. | Medium / High | Keep the modular monolith, staging checks and rollback procedure; demonstrate a backup restore and provide an operating guide, account ownership and a maintenance contact. Confirm a manual service fallback with B.A.D.R. | Platform and handover owners with B.A.D.R. |

## Immediate review actions

1. Check R-04 with the audit owners: [Audit model/service #549](https://github.com/B-A-D-R-SL/iris/issues/549)
   and [Audit log #547](https://github.com/B-A-D-R-SL/iris/issues/547). Link the
   shared service's implementation and tests when available.
2. For R-01, confirm the privacy assessment owner, approval evidence and the
   service-by-service data-location inventory before any real household data.
3. For R-02 and R-05, resolve the policy and reservation questions listed in the
   architecture document; preserve those answers in the relevant requirements.
4. Confirm the proposed owners and review all eight risks at iteration planning
   and before a release. Raise priority when evidence reveals greater exposure;
   reduce it only with linked tests, an approved decision or an operational check.

## Sources and related pages

- [Project commitments and synthetic-data gate](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/overview.md)
- [Architecture, module boundaries, reservation questions and deployment](https://github.com/B-A-D-R-SL/iris/blob/main/docs/04-architecture/architecture.md)
- [Review rules for permissions, sensitive data and atomic updates](https://github.com/B-A-D-R-SL/iris/blob/main/docs/05-process/review-rules.md)
- [AI reading spike #410](https://github.com/B-A-D-R-SL/iris/issues/410),
  [Eligibility engine #457](https://github.com/B-A-D-R-SL/iris/issues/457),
  [Accessibility/security audit #418](https://github.com/B-A-D-R-SL/iris/issues/418)
- [Societal impact](https://github.com/B-A-D-R-SL/iris/wiki/Societal-Impact),
  [Equity and diversity](https://github.com/B-A-D-R-SL/iris/wiki/Diversity-Statement),
  [Economics](https://github.com/B-A-D-R-SL/iris/wiki/Economic-Impact),
  [Licence and legal aspects](https://github.com/B-A-D-R-SL/iris/wiki/Legal-%26-Ethical-Issues)

## Review record

Teammate reviewer: **Pending** · Review date: **Pending** · Review evidence: **Pending**
