# Mock notices of assessment

Iris is built and tested with **generated** notices of assessment, never real ones. They feed the AI reading spike (SET-19), automated tests, demos, the seed data (SET-18) and the staging environment. Owner of the generator: SET-09 (Massimo).

## Rules

- Every page carries the watermark **SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER** diagonally and in the footer. Phone photos are made from the watermarked page, so they carry it too.
- Names come from Faker (`fr_CA`); addresses use real Montréal street names with fictional civic numbers and postal codes. Random seed **42**, so the same command always gives the same files.
- The social insurance number is always printed as `XXX XXX XXX`.
- The layout imitates the structure of a notice (header, taxpayer block, summary lines), not its graphic design or logo.

## Fields printed on each notice

| Printed label | Value | Read by Iris |
| --- | --- | --- |
| Avis de cotisation – Impôt sur le revenu | Title | |
| Année d'imposition | 2025; 2023 for the `old_tax_year` case | Yes |
| Date de l'avis | `YYYY-MM-DD`, between March 1 and June 30 of the year after the tax year | Yes |
| Nom, prénom | Faker name, printed `Last name, First name` | Yes |
| Adresse | Civic number, street, `app.` unit (about 40%), `Montréal (Québec)`, postal code starting with H | Yes |
| Numéro d'assurance sociale | `XXX XXX XXX` | Never |
| Revenu total (ligne 199) | 4,000 to 85,000 $ (80% below 38,000 $); 0 $ for the `zero_income` case | Yes |
| Revenu net (ligne 275) | Total income minus 0 to 15% | No |
| Revenu imposable (ligne 299) | Net income minus 0 to 5% | No |
| Impôt du Québec à payer / Remboursement | Random: 70% a refund up to 2,000 $, otherwise up to 1,500 $ to pay; `Solde 0,00 $` when zero | No |

Amounts are printed in the French Canadian style (`23 456,78 $`) and stored in cents in the CSV files.

## Output

50 files: every notice is a different (fictional) person and is delivered as either a PDF or a phone photo.

| Folder or file | Content |
| --- | --- |
| `mock-data/notices/pdf/` | 34 PDF notices (one page, text layer included) |
| `mock-data/notices/photos/` | 16 phone photos (PNG): the page rendered to an image, rotated −7° to +7°, uneven lighting, shadow, blur, JPEG quality 60, on a table background |
| `mock-data/notices/truth.csv` | What is printed on each file: `file, first_name, last_name, street_number, street_name, unit, postal_code, tax_year, total_income_cents, notice_date, case` |
| `mock-data/notices/applicants.csv` | What the household **declared** at registration for each file, to test the name and address checks (below) |

`file` is the path relative to `mock-data/notices/`, for example `pdf/notice-001.pdf`. `unit` is empty when there is none.

## Cases covered (`case` column)

| Case | Count | Files | What is special | Expected Iris behaviour |
| --- | --- | --- | --- | --- |
| `clean` | 30 | `pdf/notice-001.pdf` to `pdf/notice-030.pdf` | Nothing | Read with high confidence; auto-approval possible |
| `photo` | 15 | `photos/notice-031.png` to `photos/notice-045.png` | Phone photo | Read; some low confidence |
| `old_tax_year` | 1 | `pdf/notice-046.pdf` | Tax year 2023 (notice dated 2024) | `OLD_TAX_YEAR` |
| `name_mismatch` | 1 | `pdf/notice-047.pdf` | Declared last name differs from the notice | `NAME_MISMATCH` |
| `address_mismatch` | 1 | `pdf/notice-048.pdf` | Declared civic number and postal code differ (the person moved) | `ADDRESS_MISMATCH` |
| `zero_income` | 1 | `pdf/notice-049.pdf` | All amounts 0 $ | Read 0 $; eligible |
| `unreadable` | 1 | `photos/notice-050.png` | Photo so blurred and overexposed that the values cannot be read | Reading fails; manual entry |

`truth.csv` always holds what is **printed**, even for the unreadable photo, so a reader's output can be scored against it.

## Declared values (`applicants.csv`)

Columns: `file, first_name, last_name, street_number, street_name, unit, postal_code, name_should_match, address_should_match, variation`.

For most files the declared values equal the printed ones (`variation` = `none`). The business rules say the name check ignores case and accents and allows extra middle names, and the address check compares the postal code and civic number. So some clean files are **controls** that must still match:

| `variation` | Count | Declared value | `name_should_match` | `address_should_match` |
| --- | --- | --- | --- | --- |
| `none` | 42 | Same as the notice | true | true |
| `accents_stripped` | 2 | Name without accents (`Hélène` → `Helene`) | true | true |
| `uppercase` | 2 | Name in capitals | true | true |
| `middle_name_omitted` | 2 | The notice shows two first names, the household declared only the first | true | true |
| `different_last_name` | 1 | Another last name (`name_mismatch` case) | false | true |
| `moved` | 1 | Another civic number, street, unit and postal code (`address_mismatch` case) | true | false |

## How to run

```sh
cd tools/mock_notices
uv run generate.py                 # writes to mock-data/notices/
uv run pytest                      # checks the generator and the committed output
```

Details and options: [tools/mock_notices/README.md](../../tools/mock_notices/README.md). The generated files are committed, so most people never need to run it.
