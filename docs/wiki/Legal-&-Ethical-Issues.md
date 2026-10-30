
# Licence and legal aspects

**Status:** Draft for teammate review · **Updated:** October 30, 2026 ·
**Tracking:** [SET-31 #590](https://github.com/B-A-D-R-SL/iris/issues/590)

This page records Iris's licence, privacy requirements and unresolved evidence
for the pilot. It does not establish that all required controls are implemented
or that B.A.D.R. has completed a compliance assessment.

## MIT licence and third-party material

The repository's [LICENSE](https://github.com/B-A-D-R-SL/iris/blob/main/LICENSE)
uses MIT and names **Copyright (c) 2026 B.A.D.R-SL**. It permits commercial and
other reuse, modification and redistribution subject to preserving its notice
and permission terms. It includes a warranty disclaimer. The
[OSI MIT text](https://opensource.org/license/mit) is the external licence reference.

The software licence does not authorize publication of household records,
uploaded documents, signatures, credentials or confidential agreements. B.A.D.R.
branding and third-party images and packages need their own permissions or
licence review. Dependency manifests identify packages; they are not a complete
third-party licence inventory. Keep required notices when distributing Iris and
verify the dependency inventory before handover.

## Quebec privacy framework

The project is designed around Quebec's **Act respecting the protection of
personal information in the private sector**, as amended by Law 25. B.A.D.R.
should confirm its applicable obligations and operational procedures. The
[Act](https://www.legisquebec.gouv.qc.ca/en/document/cs/p-39.1) and the
[CAI responsibilities guide](https://www.cai.gouv.qc.ca/uploads/pdfs/CAI_GU_Responsabilites_Entreprises.pdf)
are the primary legal and regulator references; the table distinguishes them
from implementation evidence still required in Iris.

| Area | Legal reference | Project response and evidence to confirm |
| --- | --- | --- |
| Accountable privacy governance | Act, s. 3.1; CAI guide | Confirm the responsible officer and public professional contact; publish clear governance information. The project overview names an intended officer but is not evidence of formal designation. |
| Privacy impact assessment (EFVP/PIA) | Act, s. 3.3 | Document the assessment for the information-system project. Iris additionally requires B.A.D.R.'s signed assessment before real personal data enters the system. |
| Necessary collection and transparency | Act, ss. 5, 8; CAI collection guidance | Explain purposes and collect necessary fields only; establish retention and access rules. Consent does not make unnecessary collection acceptable. |
| Consent and privacy defaults | Act, ss. 9.1, 14; CAI guide | Use distinct, understandable purposes, recorded consent versions and optional communications off by default. Test the actual flow. |
| Exclusively automated decisions | Act, s. 12.1 | Inform the person; support the statutory explanation and observation rights. The planned human-review route is US-77. Deterministic automation still requires this analysis. |
| Service providers and location | Act, ss. 17, 18.3 | Review processor agreements, access, protection and cross-border data flows. Keep a service inventory and documented regional configuration. |
| End of purpose and individual rights | Act, ss. 23, 27, 32; CAI guide | Review retention/deletion rules and access, correction and portability processes; confirm applicable response deadlines and exceptions. |
| Confidentiality incidents | Act, ss. 3.5–3.8; CAI guide | Maintain an incident register and response procedure; assess serious-injury risk and required notifications. An unfinished application screen cannot replace that operating process. |

Collection guidance:
[CAI — Collecte de renseignements personnels](https://www.cai.gouv.qc.ca/protection-renseignements-personnels/information-entreprises-privees/collecte-renseignements-personnels_entreprises).
The existing [Privacy & Data Protection](https://github.com/B-A-D-R-SL/iris/wiki/Privacy-%26-Data-Protection)
page lists proposed retention periods and stories. Those are project defaults
to approve and implement, not statutory durations supplied by Law 25. File
deletion also needs an agreed treatment of backups and audit retention.

## Data stored and processed in Canada

The [project overview](https://github.com/B-A-D-R-SL/iris/blob/main/docs/01-project/overview.md)
commits to keeping personal data in Canada. The
[architecture](https://github.com/B-A-D-R-SL/iris/blob/main/docs/04-architecture/architecture.md)
targets Azure Canada East. This is a project constraint, not a blanket statement
that Law 25 requires all personal information to stay in Canada.

Section 17 addresses communication or entrusted processing **outside Quebec**
and requires an assessment and appropriate agreement under its conditions.
Another Canadian province is still outside Quebec. A Canadian database region
alone does not demonstrate that every data flow satisfies the law or the
project's Canada-only commitment.

Before the real-data pilot, document the chosen location, processor and access
path for the database and backups, document/photo storage, document reading,
email, logs, telemetry, support access and subprocessors. Check any replication,
fallback or remote access. Record the decisions in the assessment and service
agreements; do not infer region availability from an architecture diagram.

Use generated data in development, tests, demonstrations and public evidence.
Keep income values, document contents and identifiers out of logs, issues and
screenshots, following the
[review rules](https://github.com/B-A-D-R-SL/iris/blob/main/docs/05-process/review-rules.md).
Human approval of this page does not authorize uploading household data to an
unverified cloud or AI service.

## Ethical responsibilities and agreements

B.A.D.R. defines organizational policy; the team implements and tests it.
Eligibility and priority must be explainable and reviewable. AI document
extraction must not silently turn an uncertain value into a definitive decision.
Assess barriers and impacts through the societal impact and diversity pages,
and record AI assistance in the repository's
[AI_USAGE.md](https://github.com/B-A-D-R-SL/iris/blob/main/AI_USAGE.md).

The existing [Stakeholder](https://github.com/B-A-D-R-SL/iris/wiki/Stakeholder)
page records privately submitted sponsorship and responsibility agreements.
Do not attach signatures or infer additional contractual terms from this
summary. Confirm food-safety responsibilities and partner terms with B.A.D.R.;
the application's listing confirmation is not evidence of regulatory approval.

## Team confirmations

- Confirm the privacy officer's formal designation, correct name and public
  contact; the overview and wiki currently spell the surname differently.
- Link the approved privacy assessment and service/region inventory without
  publishing confidential contracts or personal data.
- Confirm retention, rights handling, incident response and partner terms with
  B.A.D.R.; link implementation and operating evidence before real-data use.
- Complete third-party licence/asset review before distribution and handover.

## Review record

Teammate reviewer: **Pending** · Review date: **Pending** · Review evidence: **Pending**
