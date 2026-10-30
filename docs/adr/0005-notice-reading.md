<!-- AI contribution: 50% or more AI-generated -->
# ADR 0005: How Iris reads notices of assessment

Status: Proposed · Date: 2026-10-23

## Context

Iris reads the household income from a Revenu Québec notice of assessment (US-22), so that staff do not retype it and automatic approval can rely on it. Four constraints shape the choice:

- **Law 25:** the notice is personal and financial information. The [evidence document](../04-data/notice-reading-privacy-inputs.md) lists what ss. 17 and 18.3 ask for, including written terms with the provider; B.A.D.R.'s privacy officer decides how they apply.
- **Canadian processing:** the team requires AI reading to run in a Canadian region.
- **Budget:** the team caps an environment at 60 USD per month and plans 35 to 50 USD for hosting ([architecture draft](../04-architecture/architecture-initial-draft.md)), and a result must arrive within 60 seconds per notice.
- **Wrong values are costly:** a wrong income at high confidence could auto-approve a household, so the confidence threshold (0.90) is a rule setting.

Spike SET-19 ([#410](https://github.com/B-A-D-R-SL/iris/issues/410)) measures two options on 50 fictional notices. Method and runbook: [planning note](../06-planning/set-19-notice-reading-spike.md), [harness README](../../tools/notice_reading_spike/README.md).

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
| A. Document Intelligence | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run |
| B. Gemini on Vertex AI | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run | pending live run |

The data location column gives the region each run used (each run logs the Document Intelligence endpoint host or the Gemini region, and its summary records it) and the region production would use. The Law 25 column summarizes the [evidence document](../04-data/notice-reading-privacy-inputs.md), which holds the quoted sources and is not repeated here.

## Decision

Recorded after the live runs, against the pass criteria above.

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
| Azure-hosted vision language model | Not confirmed that one is offered with processing in Canada (evidence document, [still unknown](../04-data/notice-reading-privacy-inputs.md#still-unknown-and-what-badr-should-read)). Before deciding, check the Azure AI Foundry model catalog filtered on Canada East and Canada Central with deployment type Standard |
| Document Intelligence custom neural model | Needs labelled real notices to train, and we may use only fictional ones |
| Self-hosted open-weights vision model | A GPU server costs more than the whole budget, and B.A.D.R. cannot run it |
| US-hosted models | Break the Canadian processing requirement |
| Manual entry only | Safe but slow: staff retype every income, which US-22 aims to avoid |

## Consequences

- The 0.90 threshold should become a versioned rule setting when US-22 and US-24 are built, like the other settings in the business rules; it is not a constant in the reader.
- `TruthReader` becomes the fake reader for the application's tests, so no test calls a service.
- If Gemini is chosen, the LLM security checks apply: the model has no tools, its output is validated before use, untrusted text in a notice is never treated as instructions, and no secret goes in a prompt.
- If Gemini is chosen, B.A.D.R. holds a second vendor account, contract and bill, outside the Microsoft nonprofit credits.
- If Document Intelligence is chosen, it runs in Canada Central (Toronto), the only Canadian region that offered it on 2026-10-30, while the rest of Iris runs in Canada East ([evidence document](../04-data/notice-reading-privacy-inputs.md), note 1). Notices then leave Québec on their way to the reader, and [ADR 0001](0001-tech-stack.md), which lists Document Intelligence among the Canada East services, needs correcting.
