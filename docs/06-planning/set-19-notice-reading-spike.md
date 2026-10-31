<!-- AI contribution: 50% or more AI-generated -->
# SET-19: How should Iris read notices of assessment?

Iris must read the household income from a Revenu Québec notice of assessment (US-22, issue #410). This spike compares two ways to do it, and the pass criteria below were fixed before any measurement.

## Options

- **Azure AI Document Intelligence:** layout model plus our own parser for the notice's labels.
- **Gemini on Vertex AI, Montréal region:** a vision model asked for the fields as JSON.

## How we compare them

- 50 mock notices: 8 for tuning and 42 held out. Each option runs on all of them twice.
- Real-notice conditions: PDFs, readable photos, an unreadable photo and wrong documents.
- Law 25 evidence: every statement about a provider quotes its documentation or contract. Anything the sources do not answer is `Unknown`. B.A.D.R.'s privacy officer decides.

## Pass criteria

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

## Outputs

- Decision record: [ADR 0005](../adr/0005-notice-reading.md)
- Law 25 inputs for the privacy officer: [notice-reading-privacy-inputs.md](../04-data/notice-reading-privacy-inputs.md)
- Test harness: [tools/notice_reading_spike](../../tools/notice_reading_spike/README.md)

## Status

Measured on 2026-10-30 ([results](../../tools/notice_reading_spike/results/summary.md)). Gemini passed every criterion measured; Document Intelligence failed the address criterion (80.5%). Recommendation in ADR 0005: Gemini, still Proposed. Still to do: real-notice conditions, B.A.D.R.'s choice of Google agreement (abuse-monitoring exemption), and B.A.D.R.'s decision.
