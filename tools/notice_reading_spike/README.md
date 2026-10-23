<!-- AI contribution: 50% or more AI-generated -->
# Notice reading spike

Spike SET-19 ([#410](https://github.com/B-A-D-R-SL/iris/issues/410)) compares two services that could read a Revenu Québec notice of assessment for Iris: Azure AI Document Intelligence and Gemini on Vertex AI in Montréal. This folder holds the benchmark harness; it runs each reader over the mock notices and scores it against `mock-data/notices/truth.csv`.

Read next: the [planning note](../../docs/06-planning/set-19-notice-reading-spike.md), the [draft ADR 0005](../../docs/adr/0005-notice-reading.md) (pass criteria and decision) and the [Law 25 evidence](../../docs/04-data/notice-reading-privacy-inputs.md). Only fictional notices are ever sent to a service, never a real one.

## Setup

You need an Azure subscription (a student one or B.A.D.R.'s), a Google Cloud account, the Google Cloud CLI (`gcloud`, [install](https://cloud.google.com/sdk/docs/install)) for the sign-in in step 3, and [uv](https://docs.astral.sh/uv/). Run every command below from this folder (`tools/notice_reading_spike`). uv installs Python 3.13 and the dependencies into `.venv` on the first run.

1. **Document Intelligence.** In the Azure portal, create a Document Intelligence resource on the free tier (F0). When Canada Central or Canada East is offered, pick one. Copy the endpoint and one key from "Keys and Endpoint".
2. **Vertex AI.** In Google Cloud, create a project, link a billing account and enable the Vertex AI API. In Model Garden, look at the models offered in Montréal (`northamerica-northeast1`) and pick the newest Gemini Flash.
3. **Sign in to Google.** Run `gcloud auth application-default login`. Vertex AI uses these Application Default Credentials; no Google key goes in `.env`.
4. **Fill `.env`.** Run `cp .env.example .env`, then fill every empty value. `.env` is ignored by git; never commit it.

| Variable | Value |
| --- | --- |
| `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY` | From the Document Intelligence resource |
| `AZURE_DI_PRICE_PER_PAGE_USD` | The layout price per page on Azure's pricing page |
| `GOOGLE_CLOUD_PROJECT` | The Google Cloud project ID |
| `VERTEX_MODEL` | The Gemini Flash model ID chosen in step 2 |
| `VERTEX_INPUT_PRICE_PER_MTOK_USD`, `VERTEX_OUTPUT_PRICE_PER_MTOK_USD` | That model's price per million input and output tokens |
| `VERTEX_LOCATION` | Keep `northamerica-northeast1`; the reader refuses any other value |

## Running

Commands read `.env` with `uv run --env-file .env`. Each run writes a CSV and a summary beside it (`--out results/x.csv` also writes `results/x.summary.md`).

**Tests and lint.** All offline, no account needed:

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

**Record fixtures.** `--record` saves the full raw service response, including every number printed on the notice. Use it only on the mock notices, never on a real document. Run the dev split, keep notices 003 and 031 and delete the other six files. The run overwrites the synthetic `tests/fixtures/layout-notice-003.json` with the real response. Commit the two kept files, then run `uv run pytest` again.

```sh
uv run --env-file .env run.py --reader azure-layout --split dev --record tests/fixtures/ --out results/azure-dev.csv
```

**Dev smoke run.** The dev split is 8 files (PDFs 001 to 005, photos 031 to 033). Run it first on each reader to catch setup errors cheaply:

```sh
uv run --env-file .env run.py --reader vlm --split dev --out results/vlm-dev.csv
```

**Full runs.** The pass criteria use the held-out notices; `--split all` reads all 50 files. Run it twice per reader to see whether the answers repeat:

```sh
uv run --env-file .env run.py --reader azure-layout --split all --out results/azure-1.csv
uv run --env-file .env run.py --reader azure-layout --split all --out results/azure-2.csv
uv run --env-file .env run.py --reader vlm --split all --out results/vlm-1.csv
uv run --env-file .env run.py --reader vlm --split all --out results/vlm-2.csv
```

Write `results/summary.md` by hand: repeatability between the two runs, and held-out against dev accuracy. Commit `results/` (mock data only).

**Real-notice conditions.** `--files` reads any PDF, PNG or JPEG. Download the public redacted sample notice published by Carte loisir ([PDF](https://www.carteloisir.ca/app/uploads/cal/exemples/avis-de-cotisation-pour-deficience-grave-et-prolongee-des-fonctions-mentales-ou-physiques-revenu-quebec.pdf)) to a folder outside the repository, never inside it, and never commit it. Use that path in the command below (`../../../notice-sample/redacted.pdf` is only an example). Also read two mockup screenshots that are not notices:

```sh
uv run --env-file .env run.py --reader vlm --files ../../../notice-sample/redacted.pdf "../../docs/03-design/mockups/Registration.png" "../../docs/03-design/mockups/Store - Post a listing.png" --out results/vlm-real.csv
```

Repeat with `--reader azure-layout`. Files outside the mock set have no truth row, so read their CSV rows by eye. The mockups should return no value at confidence 0.90 or more.

| Flag | Meaning |
| --- | --- |
| `--reader` | `truth` (replays `truth.csv`, checks the harness itself, no account), `azure-layout` or `vlm` |
| `--split` | `dev`, `heldout` or `all`: which mock notices to read |
| `--files PATH...` | Read these files instead of a split |
| `--record DIR` | Save each raw service response as `layout-<file>.json` (`azure-layout` only) |
| `--out CSV` | Where to write the results |

## After the first live Gemini call

The offline tests cannot check that Vertex AI accepts the JSON response schema (`response_json_schema` with nullable text). If the first call fails with a schema error, fix that before measuring.

The [Law 25 evidence](../../docs/04-data/notice-reading-privacy-inputs.md) has Gemini rows marked Unknown, because Google's documentation site could not be fetched when it was written. Read the pages it lists and update those rows before the decision.

## What this spike cannot test

- Notices over 2 pages: the F0 tier reads only the first 2 pages of a document.
- Other tax years: all mock notices are for one tax year.
- Federal (CRA) notices: only Revenu Québec notices are covered.
- Prompt injection: the mock notices contain no hostile text, so the Gemini reader's defences (strict validation, no tools) are checked only by unit tests.

## Finishing the spike

1. Provision both services and fill `.env` (Setup).
2. Record fixtures, commit the two kept files, rerun `uv run pytest`.
3. Dev smoke run, then two full runs per reader into `results/`; write `results/summary.md`.
4. Real-notice conditions with `--files`; add the findings to `results/summary.md`.
5. Fill the results table and the decision in [ADR 0005](../../docs/adr/0005-notice-reading.md).
6. Set the status in the [planning note](../../docs/06-planning/set-19-notice-reading-spike.md).
7. Add the `document_reader` row to [`architecture.md`](../../docs/04-architecture/architecture.md).
8. Update the Gemini rows of the [Law 25 evidence](../../docs/04-data/notice-reading-privacy-inputs.md).
9. Clean up (below), then open the pull request.

## Clean up after measuring

- Delete the Document Intelligence resource and the Google Cloud project. If you must keep them, revoke the Azure key and disable the Vertex AI API.
- Delete `.env`, and run `gcloud auth application-default revoke`.
- Delete the downloaded redacted sample.

## Files

| File | Role |
| --- | --- |
| `run.py` | Entry point: picks the reader and files, runs them, writes the CSV and summary |
| `reader.py` | The `DocumentReader` interface, `NoticeReading`, `ReadField` and `DocumentReadError`; see ADR 0005 |
| `azure_layout_reader.py` | Option A: Document Intelligence `prebuilt-layout` |
| `layout_parser.py` | Turns the layout result into the fields (our own parser for option A) |
| `vlm_reader.py` | Option B: Gemini on Vertex AI in Montréal, answering in JSON that is validated before use |
| `fields.py` | Parsing and normalizing amounts, dates and postal codes |
| `score.py` | Compares readings with `truth.csv`: accuracy, confident-and-wrong counts, summary tables |
| `records.py` | `RunRecord`, the per-file result |
| `truth_reader.py` | Test double that returns the truth; checks the harness without a service |
| `tests/` | Offline tests: the service readers run against fake clients; `tests/fixtures/` holds recorded responses |
| `.env.example` | The variables to fill in `.env` |
| `pyproject.toml`, `uv.lock`, `.python-version` | Dependencies, ruff and pytest settings, Python 3.13 |
| `results/` | CSVs and summaries of the live runs, committed (mock data only) |
