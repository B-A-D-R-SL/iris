# Notice reading run

## Settings

- commit: f6c30d2
- reader: azure-layout
- model: prebuilt-layout
- endpoint host: iris-spike-di-massimo.cognitiveservices.azure.com
- date: 2026-10-30

## Results

| Field | Held-out PDFs | Held-out photos | Dev (all) | Confident-and-wrong |
| --- | --- | --- | --- | --- |
| name | 86.2% (25/29) | 100.0% (12/12) | 100.0% (8/8) | 0 |
| address | 86.2% (25/29) | 66.7% (8/12) | 75.0% (6/8) | 0 |
| tax year | 100.0% (29/29) | 100.0% (12/12) | 100.0% (8/8) | 0 |
| total income | 100.0% (29/29) | 100.0% (12/12) | 100.0% (8/8) | 0 |
| notice date | 100.0% (29/29) | 100.0% (12/12) | 100.0% (8/8) | 0 |

- Changed returns, income accuracy (7 files): 100.0% (7/7)
- notice-050 outcome: 0 field(s) at confidence >= 0.90 (pass: 0)
- Failures: 0
- document_number_leaks: 0
- Median seconds: 5.6
- p95 seconds: 38.2
- Mean cost per notice (USD): 0.0168
