# Mock notices of assessment generator

Generates fake Revenu Québec notices of assessment (*avis de cotisation*) for Iris. Every page is watermarked **SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER**. What is generated and why: [docs/04-data/mock-notices-of-assessment.md](../../docs/04-data/mock-notices-of-assessment.md).

The output is committed in [`mock-data/notices/`](../../mock-data/notices/), so you only need this tool to change or regenerate it.

## Run

Needs [uv](https://docs.astral.sh/uv/). From this folder:

```sh
uv run generate.py                  # writes to <repo>/mock-data/notices/
uv run generate.py --out /tmp/notices
uv run generate.py --seed 7         # different people, same structure (do not commit)
uv run pytest                       # 17 checks, about 15 seconds
```

From the repository root: `uv run --project tools/mock_notices tools/mock_notices/generate.py`.

uv installs Python 3.13 and the dependencies (reportlab, Faker, Pillow, pypdfium2) into `tools/mock_notices/.venv` on the first run. This project is separate from `backend/` so the Django app does not depend on PDF and image libraries.

The seed is fixed at 42 and the PDFs are written with reportlab's `invariant` mode, so running the generator twice gives byte-identical files. If you change the generator, regenerate and commit `mock-data/notices/` in the same pull request: `test_committed_output_is_up_to_date` fails otherwise.

## Output

| Path in `mock-data/notices/` | Content |
| --- | --- |
| `pdf/notice-NNN.pdf` | 34 one-page PDF notices with a text layer |
| `photos/notice-NNN.png` | 16 phone photos (15 readable, 1 unreadable) |
| `truth.csv` | What is printed on each file, one row per file |
| `applicants.csv` | What the household declared at registration, to test the name and address checks |

Read the files with the `csv` module (UTF-8, no BOM). Amounts are integer cents; dates are ISO `YYYY-MM-DD`; `unit` is empty when there is none.

## Files

| File | Role |
| --- | --- |
| `generate.py` | Entry point: builds the notice data (Faker, seed 42), the edge cases and the declared values, lays out the PDF (reportlab) and writes the CSV files |
| `photos.py` | Turns a notice PDF into a phone photo (Pillow): rendered at 110 dpi with pypdfium2, uneven light, rotated −7° to +7°, shadow, table background, blur, JPEG quality 60, saved as PNG. The unreadable photo is out of focus instead (blur radius 6, JPEG quality 20): the values are lost but the large watermark stays legible |
| `tests/test_generate.py` | Reproducibility, counts and cases, watermark and masked SIN on every PDF page, PDF text equals `truth.csv`, edge cases, name and address matching rules on `applicants.csv`, committed output up to date |

## Changing the cases

The file number → case table is `CASES` in `generate.py`; the name controls are `MIDDLE_NAME_NUMBERS`, `UPPERCASE_NUMBERS` and `ACCENT_CONTROLS`. Update the counts in the spec document and in `EXPECTED_CASES` / `EXPECTED_VARIATIONS` in the tests at the same time.
