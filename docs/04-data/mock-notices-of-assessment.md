# Mock notices of assessment

Iris is built and tested with **generated** notices of assessment, never real ones. They feed the AI reading spike (SET-19), automated tests, demos, the seed data (SET-18) and the staging environment. Owner of the generator: SET-09 (Massimo).

## Rules

- Every page carries the watermark **SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER** diagonally and in the footer. Phone photos are made from the watermarked pages, so they carry it too.
- Names come from Faker (`fr_CA`); addresses use real Montréal street names with fictional civic numbers and postal codes. Random seed **42**, so the same command always gives the same files.
- The identification number is always printed as `XXX XXX XXX`; no social insurance number appears anywhere.
- The layout follows the **structure** of a real notice (see [Compared with a real notice](#compared-with-a-real-notice)), not its graphic design: no logo, and the form code reads `TPF-99 (SPÉCIMEN)`.

## Layout

Each notice is a two-page PDF (US Letter).

**Page 1, cover page**

| Where | What is printed | Read by Iris |
| --- | --- | --- |
| Top left | `Revenu Québec` (plain text, no logo) and an 11-digit document control number | Never |
| Under it, envelope window (Courier) | `First Last`, then `civic number, street, app. unit` (unit on about 40%), then `Montréal (Québec)  H1A 1A1` | Name and address: yes |
| Top right | `Numéro d'identification : XXX XXX XXX`, `Numéro de l'avis :` (11 characters, starts with Q or M), `Date de l'avis :` | Date: yes. Numbers: never |
| Result box | `Par dépôt direct` or `Par chèque` › `Remboursement` and the amount; or `Solde à payer`; or `Solde nul` | No |
| Title | `Avis de cotisation` and `Année d'imposition 2025` | Tax year: yes |
| Messages | Thanks; "accepted as submitted" or "we changed your return (see page 2)"; refund or payment instructions | No |

**Page 2, `Détail des calculs`**: one row per TP-1 line with the columns `Ligne`, label, `+ − =`, **`Montant déclaré`** (what the person filed) and **`Montant établi`** (what Revenu Québec assessed). Income lines (101, 111, 114, 119, 122, 130, 147, 154 as they apply), **199 Revenu total**, deductions (201, 214, 250), 275 Revenu net, 295/297, 299 Revenu imposable, credits (350, 377, 377.1, 399), tax (401, 406, 432, 450), payments (451, 456, 462, 465) and 478 Remboursement or 479 Solde à payer. Labels come from the 2025 TP-1. When the return was changed, an `Explication des changements` paragraph follows the table.

**Every page**: a footer box with `Prénom et nom de famille`, `Date de l'avis` and `Année d'imposition`, then the watermark line; `TPF-99 (SPÉCIMEN)` and `Page n de 2` at the top right.

## Values

| Value | How it is generated | Read by Iris |
| --- | --- | --- |
| Tax year | 2025; 2023 for the `old_tax_year` case | Yes |
| Notice date | Between March 1 and June 30 of the year after the tax year, printed `28 mars 2026` (`1er` for the first of the month) | Yes |
| Total income, line 199 **Montant établi** | 4,000 to 85,000 $ (80% below 38,000 $); 0 $ for `zero_income`. Split over income lines by profile: employment, employment and EI, retirement (OAS, QPP, pension), social assistance, or employment and social assistance; sometimes interest | Yes |
| Changed returns | Files 003, 011, 017, 024, 029 (clean) and 034, 041 (photos): the person left out a slip (employment income or interest, 150 to 2,500 $), so line 199 `Montant déclaré` is lower than `Montant établi` | Must read **établi** |
| Other lines | Plausible but simplified: worker deduction 6% (max 1,421 $), social assistance deducted at line 295, 14 % basic credit on 18,571 $, 14/19/24 % brackets, tax withheld, work premium. Not an exact tax calculation | No |

Amounts in the table are printed `23 456,78` (with ` $` on the cover page) and stored in cents in the CSV files.

## Output

50 files: every notice is a different (fictional) person and is delivered as either a PDF or a phone photo.

| Folder or file | Content |
| --- | --- |
| `mock-data/notices/pdf/` | 34 PDF notices (two pages, text layer included) |
| `mock-data/notices/photos/` | 16 phone photos (PNG, about 2100 × 1400 px): both pages side by side on a table, each rotated −7° to +7°, uneven lighting, shadow, blur, JPEG quality 60 |
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
| `unreadable` | 1 | `photos/notice-050.png` | Out-of-focus photo: the values cannot be read, the large watermark still can | Reading fails; manual entry |

`truth.csv` always holds what is **printed**, even for the unreadable photo, so a reader's output can be scored against it. `total_income_cents` is line 199 in the **Montant établi** column.

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

## Compared with a real notice

The layout was checked against a redacted sample notice of assessment (tax year 2018, form TPF-99 (2019-02), pages 1 and 2 of 4, personal data masked and stamped EXEMPLE) published as an example by [Carte loisir](https://www.carteloisir.ca/app/uploads/cal/exemples/avis-de-cotisation-pour-deficience-grave-et-prolongee-des-fonctions-mentales-ou-physiques-revenu-quebec.pdf). The sample is not stored in the repository. Line numbers and labels were checked against the official [2025 TP-1](https://www.revenuquebec.ca/fr/services-en-ligne/formulaires-et-publications/details-courant/tp-1/).

| Same as the sample | Known differences |
| --- | --- |
| Cover page, then `Détail des calculs` | 2 pages instead of 4 (pages 3 and 4 of the sample were not available) |
| Envelope-window name and address, first name first | No logo and no Mon dossier pictogram; form code `TPF-99 (SPÉCIMEN)` |
| Identification number, notice number and date at the top right | Watermark on every page |
| `Avis de cotisation` / `Année d'imposition` title, French long date | Some wording (payment message, explanation of changes) is ours |
| `Montant déclaré` and `Montant établi` columns, line numbers, `+ − =` signs, totals in bold | The sample is from 2018; a current notice may differ. Compare with a recent notice from Mon dossier when one is available, without saving it |
| Footer box on every page | |

What this means for the AI reading spike (SET-19): the reader must find line 199 among about 20 rows, take the **Montant établi** column, parse French dates, and ignore the notice, identification and document numbers (business rules: never stored).

## How to run

```sh
cd tools/mock_notices
uv run generate.py                 # writes to mock-data/notices/
uv run pytest                      # checks the generator and the committed output
```

Details and options: [tools/mock_notices/README.md](../../tools/mock_notices/README.md). The generated files are committed, so most people never need to run it.
