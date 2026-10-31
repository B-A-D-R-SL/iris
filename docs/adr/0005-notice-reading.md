<!-- AI contribution: 50% or more AI-generated -->
# ADR 0005: How Iris reads notices of assessment

Status: Proposed · Date: 2026-10-23 · Results: 2026-10-30

## Context

Iris reads the household income from a Revenu Québec notice of assessment (US-22), so that staff do not retype it and automatic approval can rely on it. Four constraints shape the choice:

- **Law 25:** the notice is personal and financial information. The [evidence document](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence) lists what ss. 17 and 18.3 ask for, including written terms with the provider; B.A.D.R.'s privacy officer decides how they apply.
- **Canadian processing:** the team requires AI reading to run in a Canadian region.
- **Budget:** the team caps an environment at 60 USD per month and plans 35 to 50 USD for hosting ([architecture draft](../04-architecture/architecture-initial-draft.md)), and a result must arrive within 60 seconds per notice.
- **Wrong values are costly:** a wrong income at high confidence could auto-approve a household, so the confidence threshold (0.90) is a rule setting.

Spike SET-19 ([#410](https://github.com/B-A-D-R-SL/iris/issues/410)) measures two options on 50 fictional notices. Overview: [Notice Reading](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading) on the wiki; runbook: [harness README](../../tools/notice_reading_spike/README.md).

## Options compared

| Option | How it reads |
| --- | --- |
| A. Azure AI Document Intelligence | `prebuilt-layout` returns the page text and lines; our own parser finds the labelled values |
| B. Gemini on Vertex AI (Montréal, `northamerica-northeast1`) | A vision model gets the page images and answers in JSON, which is validated key by key before use |

The PDF input differs: Document Intelligence receives the original PDF, with its text layer; Gemini receives 150-dpi PNG renders of each page, so it sees only the visible text (no native-PDF Gemini variant is measured in this spike).

## Interface

Both options sit behind one port, so the choice stays a configuration detail. Copied from `tools/notice_reading_spike/reader.py`:

```python
@dataclass(frozen=True)
class ReadField[T]:
    """One value read from a notice, with the reader's confidence in it."""

    value: T | None  # None: could not be read
    confidence: float  # 0.0 to 1.0


@dataclass(frozen=True)
class NoticeReading:
    """The fields Iris needs from a notice of assessment."""

    full_name: ReadField[str]  # as printed, e.g. "Zoé Jessica Lapointe"
    street_number: ReadField[str]
    street_name: ReadField[str]
    unit: ReadField[str]  # "" when the notice prints no unit
    postal_code: ReadField[str]  # "H2X 4N1"
    tax_year: ReadField[int]
    total_income_cents: ReadField[int]  # line 199, Montant établi
    notice_date: ReadField[dt.date]


class DocumentReadError(Exception):
    """The service failed or its answer is unusable: the household enters the values by hand."""


class DocumentReader(Protocol):
    """Reads a notice of assessment. `content_type` is a PDF, PNG or JPEG media type."""

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading: ...
```

The name is returned as printed because the notice prints one string and compound names make a first and last name split guesswork; the name check allows extra middle names. A reader must not return the identification number, the notice number or the document control number: the spike measures this (`document_number_leaks`), and US-22 must enforce it in application code. The mock notices print the identification number (SIN) masked as `XXX XXX XXX`, so a check for SIN patterns is for US-22 to add.

## Pass criteria (set before any measurement)

| Measure (held-out mock notices) | Pass |
| --- | --- |
| Total income, PDFs | ≥ 95% correct |
| Total income, readable photos | ≥ 85% correct |
| Total income wrong at confidence ≥ 0.90 | 0 (such a value could auto-approve a household) |
| Name, address, tax year, notice date | ≥ 90% correct each |
| Unreadable photo and wrong documents | No value at confidence ≥ 0.90 |
| Document numbers returned | 0 |
| Time per notice | p95 ≤ 60 s |
| Cost per notice | ≤ 0.05 USD (about 15 USD a month at 300 notices; the team caps an environment at 60 USD a month and plans 35–50 USD for hosting) |
| Law 25 | Processing in Canada; deletion control or short retention; no training on our data; written terms covering s. 18.3; no blocking `Unknown`. Final say: B.A.D.R.'s privacy officer |

## Results

| Option | Total income, PDFs | Total income, photos | Confident and wrong | Name, address, tax year, notice date | Unreadable and wrong documents | Document numbers | Time p95 | Cost per notice | Data location (spike / production) | Law 25 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. Document Intelligence | 100% (29/29) | 100% (12/12) | 0 | 90.2%, **80.5% (fails)**, 100%, 100% | Unreadable photo and 2 wrong documents: 0 values at ≥ 0.90 | 0 | 38.2 s (free-tier waits; median 5.6 s) | 0.017 USD at the paid rate | Canada Central (Toronto) / Canada Central, the only Canadian region offering it: outside Québec | Deletes each result after reading (tested); a Core Online Service, so the contract keeps data at rest in the Canada Geo; training on our data unknown; covered by the Microsoft credits; terms for legal review |
| B. Gemini on Vertex AI | 100% (29/29); run 1: 96.6%, one failed call | 100% (12/12) | 0 | 100% each; run 1: 97.6% each, same failed call | Unreadable photo and 2 wrong documents: 0 values at ≥ 0.90 | 0 | 5.1 s (run 1: 9.5 s) | 0.014 USD | Montréal endpoint / Montréal endpoint; Google commits processing to Canada, not Québec | No training on our data; caching can be turned off; prompts flagged for abuse may be kept 90 days and read by Google staff unless B.A.D.R. has a Google Cloud Master Agreement; contracting company in Toronto; second vendor outside the credits; terms for legal review |

Held-out mock notices (29 PDFs, 12 readable photos), two full runs per option on 2026-10-30 at frozen commit `f6c30d2`; A's two runs were identical, so one figure is shown, and B's figures are run 2 with run 1 noted where it differs. The wrong documents (two app screenshots) were read in a separate run with the same reader code. Neither option returned a wrong value for any field. The data location column gives the region the spike used and the region production would use. The Law 25 column summarizes the [evidence document](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence), which holds the quoted sources and is not repeated here.

Analysis, failure causes and limits: [results analysis](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Results). In short:

- **A** misses names and addresses when the OCR splits the envelope's last line (4 of 29 PDFs), and misreads letters in photo postal codes (4 of 12 held-out photos). Both leave fields unread, never wrong. It also gives confidence below 0.90 to correct values, so 13 of 41 notices would go to staff review under US-24's rule.
- **B** read every field of every readable notice it received. It had one transient call failure in 100 calls and reports confidence 0.99 or 1.0 on everything, so its confidence cannot tell a good reading from a bad one. On the public redacted sample, whose name is replaced by the printed placeholder `Nom Prénom`, it returned that placeholder as the name at confidence 0.90.
- **Both** read the tax year and notice date of the public redacted sample, an older real layout neither was tuned on, and invented no income where the sample's amounts are blanked out.

## Decision

**Recommended by the spike: option B, Gemini on Vertex AI in Montréal**, behind the `DocumentReader` port. This is a recommendation; the status stays Proposed until the steps below are done and B.A.D.R. accepts it.

- **For:** it passed every measured criterion, including on photos and on the layout variations that cost option A a fifth of its addresses. It is also faster and cheaper per notice, and Google states in its terms that it does not train on customer data.
- **Even:** neither option keeps notices in Québec. Document Intelligence runs in Toronto; Google commits the Montréal endpoint's processing only to Canada.
- **Against:** B.A.D.R. would hold a second vendor account, outside the Microsoft nonprofit credits. Prompts that Google's classifiers flag may be kept up to 90 days and read by Google staff, unless B.A.D.R. signs a Google Cloud Master Agreement. Gemini's confidence is not informative. And Gemini 3.5 Flash is the only Gemini Flash model with processing committed to Canada (3.6 to 3.8 Flash are committed to the US and EU only), while Google already routes it to a newer model on its Gemini API: if it is retired before a successor is committed to Canada, option B has no model to run on.
- **Before it is accepted:** B.A.D.R. chooses a Google Cloud Master Agreement, which exempts it from that logging, or accepts the logging (evidence document, question 5); B.A.D.R. agrees to a second vendor; then the conditions below.
- **Fallback:** option A, if B is ruled out on Law 25 or vendor grounds. A deletes each notice right after reading, says nothing about prompt logging, and stays within the Microsoft credits. It needs the envelope line-split fix, measured on notices the parser was not tuned on.

## Conditions before real notices

Whichever option is chosen, no real notice goes to a service until all of these are met:

- A privacy impact assessment signed by B.A.D.R.
- An account held by B.A.D.R. in a Canadian region.
- Written terms between B.A.D.R. and the provider that cover s. 17 and s. 18.3.
- Updated consent text that tells households a service reads their notice.
- Handling that meets s. 12.1 (a decision made only by automated processing), so a person can have a result reviewed.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| Azure-hosted vision language model | Not confirmed that one is offered with processing in Canada (evidence document, [still unknown](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence#still-unknown-and-what-badr-should-read)). Before deciding, check the Azure AI Foundry model catalog filtered on Canada East and Canada Central with deployment type Standard |
| Document Intelligence custom neural model | Needs labelled real notices to train, and we may use only fictional ones |
| Self-hosted open-weights vision model | A GPU server costs more than the whole budget, and B.A.D.R. cannot run it |
| US-hosted models | Break the Canadian processing requirement |
| Manual entry only | Safe but slow: staff retype every income, which US-22 aims to avoid |

## Consequences

- The 0.90 threshold should become a versioned rule setting when US-22 and US-24 are built, like the other settings in the business rules; it is not a constant in the reader.
- `TruthReader` becomes the fake reader for the application's tests, so no test calls a service.
- If Gemini is chosen, the LLM security checks apply: the model has no tools, its output is validated before use, untrusted text in a notice is never treated as instructions, and no secret goes in a prompt.
- If Gemini is chosen, B.A.D.R. holds a second vendor account, contract and bill, outside the Microsoft nonprofit credits.
- If Gemini is chosen, US-22 retries a failed call with backoff before falling back to manual entry, and US-24 does not rely on Gemini's confidence alone for the income: it reported 0.99 or 1.0 on every value in the spike.
- If Gemini is chosen, B.A.D.R.'s project turns off Google's prompt caching (a per-project `cacheConfig` setting), the counterpart of Document Intelligence's delete call.
- If Document Intelligence is chosen, it runs in Canada Central (Toronto), the only Canadian region that offered it on 2026-10-30, while the rest of Iris runs in Canada East ([evidence document](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence), note 1). Notices then leave Québec on their way to the reader, and [ADR 0001](0001-tech-stack.md), which lists Document Intelligence among the Canada East services, needs correcting.
