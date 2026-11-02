<!-- AI contribution: 50% or more AI-generated -->
# Notice reading spike

Spike SET-19 ([#410](https://github.com/B-A-D-R-SL/iris/issues/410)) compares two services that could read a Revenu Québec notice of assessment for Iris: Azure AI Document Intelligence and Gemini on Vertex AI in Montréal. This folder holds the benchmark harness; it runs each reader over the mock notices and scores it against `mock-data/notices/truth.csv`.

The two options get different PDF input: Document Intelligence receives the original PDF, with its text layer; Gemini receives 150-dpi PNG renders of each page, so it sees only the visible text.

Read next: [Notice Reading](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading) on the wiki (overview, with the [results](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Results) and the [Law 25 evidence](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence)) and the [draft ADR 0005](../../docs/adr/0005-notice-reading.md) (pass criteria and decision). The spike sends the mock notices and the public redacted sample (no personal data) to the services, and never a real notice.

## Setup

You need an Azure subscription (a student one or B.A.D.R.'s), a Google Cloud account, the Google Cloud CLI (`gcloud`, [install](https://cloud.google.com/sdk/docs/install)) for the sign-in in step 3, and [uv](https://docs.astral.sh/uv/). Run every command below from this folder (`tools/notice_reading_spike`). uv installs Python 3.13 and the dependencies into `.venv` on the first run.

1. **Document Intelligence.** In the Azure portal, create a Document Intelligence resource on the free tier (F0) in Canada Central, the only Canadian region that offered it on 2026-10-30. Copy the endpoint and one key from "Keys and Endpoint".
2. **Vertex AI.** In Google Cloud, create a project, link a billing account and enable the Vertex AI API. In Model Garden, check that Gemini 3.5 Flash is offered in Montréal (`northamerica-northeast1`).
3. **Sign in to Google.** Run `gcloud auth application-default login`. Vertex AI uses these Application Default Credentials; no Google key goes in `.env`.
4. **Fill `.env`.** Run `cp .env.example .env`, then fill every empty value. `.env` is ignored by git; never commit it.

| Variable | Value |
| --- | --- |
| `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY` | From the Document Intelligence resource |
| `AZURE_DI_PRICE_PER_PAGE_USD` | The layout price per page on Azure's pricing page |
| `GOOGLE_CLOUD_PROJECT` | The Google Cloud project ID |
| `VERTEX_MODEL` | `gemini-3.5-flash`, the only Gemini Flash model whose processing Google commits to Canada; the reader refuses any other |
| `VERTEX_INPUT_PRICE_PER_MTOK_USD`, `VERTEX_OUTPUT_PRICE_PER_MTOK_USD` | That model's price per million input and output tokens |
| `VERTEX_LOCATION` | Keep `northamerica-northeast1`; the reader refuses any other value |

## Running

Commands read `.env` with `uv run --env-file .env`. Each run writes a CSV and a summary beside it (`--out results/x.csv` also writes `results/x.summary.md`). The summary starts with the run's settings: commit, reader, model, endpoint host or region, temperature and thinking setting where they apply, and date. Its accuracy table has a column each for held-out PDFs and held-out photos, which the pass criteria use, and one for the dev files.

**Tests and lint.** All offline, no account needed:

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

**Record fixtures.** `--record` saves the full raw service response, including every number printed on the notice. Use it only on the mock notices, never on a real document; `run.py` refuses it together with `--files`. Run the dev split, keep notices 003 and 031 and delete the other six files. Recorded files are named `layout-notice-NNN.json` and sit beside the synthetic `tests/fixtures/synthetic-layout-notice-003.json`, which stays. Commit the two kept files, then run `uv run pytest` again: the truth test checks every fixture. If a recording does not parse to its truth, fix the parser using dev files only, or remove that recording and note why on the wiki's results page.

```sh
uv run --env-file .env run.py --reader azure-layout --split dev --record tests/fixtures/ --out results/azure-dev.csv
```

**Dev smoke run.** The dev split is 8 files (PDFs 001 to 005, photos 031 to 033). Run it first on each reader to catch setup errors cheaply:

```sh
uv run --env-file .env run.py --reader vlm --split dev --out results/vlm-dev.csv
```

**Freeze before the held-out runs.** The dev split is for tuning the parser and the prompt. Before the held-out runs, freeze the code, the prompt and the model settings, and note the commit (each summary's settings block records it). If anything changes afterwards, rerun both full passes. The Gemini reader sends no temperature, top_p, top_k or thinking setting, so the model's defaults apply: Google's Gemini 3.x guidance says these parameters "are no longer recommended" and to remove them from requests. If you switch to a model whose guidance differs, set them in `vlm_reader.py` before the held-out runs and note it on the wiki's results page.

**Full runs.** The pass criteria use the held-out notices; `--split all` reads all 50 files. Run it twice per reader to see whether the answers repeat:

```sh
uv run --env-file .env run.py --reader azure-layout --split all --out results/azure-1.csv
uv run --env-file .env run.py --reader azure-layout --split all --out results/azure-2.csv
uv run --env-file .env run.py --reader vlm --split all --out results/vlm-1.csv
uv run --env-file .env run.py --reader vlm --split all --out results/vlm-2.csv
```

Write the analysis by hand on the wiki's [Notice Reading – Results](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Results) page: repeatability between the two runs, and held-out against dev accuracy. Commit `results/` (mock data only).

**Real-notice conditions.** `--files` reads any PDF, PNG or JPEG; every path is checked before the first call. Download the public redacted sample notice published by Carte loisir ([PDF](https://www.carteloisir.ca/app/uploads/cal/exemples/avis-de-cotisation-pour-deficience-grave-et-prolongee-des-fonctions-mentales-ou-physiques-revenu-quebec.pdf)) into `private/redacted.pdf` in this folder. This folder's `.gitignore` keeps `private/` out of git: never put the sample anywhere else in the repository, and never commit it. Also read two mockup screenshots that are not notices. Write the `--files` outputs to `private/` too (`run.py` refuses any other folder):

```sh
uv run --env-file .env run.py --reader vlm --files private/redacted.pdf "../../docs/03-design/mockups/Registration.png" "../../docs/03-design/mockups/Store - Post a listing.png" --out private/vlm-real.csv
```

Repeat with `--reader azure-layout`. Files outside the mock set have no truth row, so read their CSV rows by eye. The mockups should return no value at confidence 0.90 or more. Copy only the per-file lists of confident fields from these summaries into the wiki's results page, never the CSVs.

| Flag | Meaning |
| --- | --- |
| `--reader` | `truth` (replays `truth.csv`, checks the harness itself, no account), `azure-layout` or `vlm` |
| `--split` | `dev`, `heldout` or `all`: which mock notices to read |
| `--files PATH...` | Read these files instead of a split; each must be inside the repository, and `--out` must be inside `private/` |
| `--record DIR` | Save each raw service response as `layout-<file>.json` (`azure-layout` with `--split` only); must be inside this folder |
| `--out CSV` | Where to write the results; must be a `.csv` file inside this folder |

## After the first live Gemini call

The offline tests cannot check that Vertex AI accepts the JSON response schema (`response_json_schema` with nullable text). If the first call fails with a schema error, fix that before measuring.

If you change the model, recheck its rows on the wiki's [Law 25 evidence](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence) page: the Canadian processing commitment and the security controls are listed per model.

## What this spike cannot test

- Notices over 2 pages: the F0 tier reads only the first 2 pages of a document.
- Other tax years' layouts: 49 mock notices are for tax year 2025 and one (notice 046) for 2023, all in the same generated layout.
- Federal (CRA) notices: only Revenu Québec notices are covered.
- Prompt injection: the mock notices contain no hostile text, so the Gemini reader's defences (strict validation, no tools) are checked only by unit tests.

## Finishing the spike

1. Provision both services and fill `.env` (Setup).
2. Record fixtures, commit the two kept files, rerun `uv run pytest`.
3. Dev smoke run, then two full runs per reader into `results/`; write the analysis on the wiki's results page.
4. Real-notice conditions with `--files`; add the findings to the wiki's results page.
5. Fill the results table and the decision in [ADR 0005](../../docs/adr/0005-notice-reading.md).
6. Set the status on the wiki's [Notice Reading](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading) page.
7. Add the `document_reader` row to [`architecture.md`](../../docs/04-architecture/architecture.md).
8. Check the provider rows of the wiki's [Law 25 evidence](https://github.com/B-A-D-R-SL/iris/wiki/Notice-Reading-%E2%80%93-Law-25-Evidence) page.
9. Clean up (below), then open the pull request.

## Clean up after measuring

- Delete the Document Intelligence resource and the Google Cloud project. If you must keep them, revoke the Azure key and disable the Vertex AI API.
- Delete `.env`, and run `gcloud auth application-default revoke`.
- Delete the `private/` folder (the redacted sample and its outputs).

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
