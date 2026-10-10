# Mock notices of assessment generator

Generates fake Revenu Québec notices of assessment (*avis de cotisation*) for Iris. Every page is watermarked **SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER**. What is generated and why: [docs/04-data/mock-notices-of-assessment.md](../../docs/04-data/mock-notices-of-assessment.md).

## Run

Needs [uv](https://docs.astral.sh/uv/). From this folder:

```sh
uv run generate.py                  # writes to <repo>/mock-data/notices/
uv run generate.py --out /tmp/notices
uv run generate.py --seed 7         # different people, same structure (do not commit)
```

uv installs Python 3.13 and the dependencies (reportlab, Faker, Pillow, pypdfium2) into `tools/mock_notices/.venv` on the first run. This project is separate from `backend/` so the Django app does not depend on PDF and image libraries.

The seed is fixed at 42 and the PDFs are written with reportlab's `invariant` mode, so running the generator twice gives byte-identical files.

## Files

| File | Role |
| --- | --- |
| `generate.py` | Entry point: builds the notice data (Faker, seed 42) and lays out the PDF (reportlab) |
| `photos.py` | Turns a notice PDF into a phone photo (Pillow): rendered at 110 dpi with pypdfium2, uneven light, rotated −7° to +7°, shadow, table background, blur, JPEG quality 60, saved as PNG |
