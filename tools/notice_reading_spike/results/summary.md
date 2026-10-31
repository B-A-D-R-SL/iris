<!-- AI contribution: 50% or more AI-generated -->
# SET-19 results: reading the 50 mock notices

Runs of 2026-10-30, mock notices only. Code, prompt and settings frozen at commit `f6c30d2` before the held-out runs. Each reader read all 50 files twice (`azure-1`, `azure-2`, `vlm-1`, `vlm-2`); the per-run tables are in the `*.summary.md` files beside this one, and every value read is in the CSV files.

| Reader | Setup |
| --- | --- |
| A. Document Intelligence | `prebuilt-layout`, free tier (F0), Canada Central (Toronto); our label-keyed parser |
| B. Gemini | `gemini-3.5-flash` on Vertex AI, Montréal (`northamerica-northeast1`); no temperature, top_p, top_k or thinking setting sent, per Google's Gemini 3.x guidance; Vertex reported serving `gemini-3.5-flash` itself |

## Against the pass criteria (41 readable held-out notices: 29 PDFs, 12 photos)

| Criterion | Pass | A. Document Intelligence (both runs) | B. Gemini run 1 | B. Gemini run 2 |
| --- | --- | --- | --- | --- |
| Total income, PDFs | ≥ 95% | **100%** (29/29) | **96.6%** (28/29) | **100%** (29/29) |
| Total income, photos | ≥ 85% | **100%** (12/12) | **100%** (12/12) | **100%** (12/12) |
| Income wrong at confidence ≥ 0.90 | 0 | **0** | **0** | **0** |
| Name | ≥ 90% | **90.2%** (37/41); PDFs alone 86.2% | **97.6%** (40/41) | **100%** |
| Address | ≥ 90% | **80.5%** (33/41) ✗ | **97.6%** (40/41) | **100%** |
| Tax year | ≥ 90% | **100%** | **97.6%** (40/41) | **100%** |
| Notice date | ≥ 90% | **100%** | **97.6%** (40/41) | **100%** |
| Unreadable photo (notice 050) | no value at ≥ 0.90 | **0** | **0** | **0** |
| Wrong documents (2 app screenshots; one separate run per reader) | no value at ≥ 0.90 | **0** (nothing returned) | **0** (nothing returned) | (same run) |
| Document numbers returned | 0 | **0** | **0** | **0** |
| Time p95 | ≤ 60 s | **38.2 s** (median 5.6 s) | **9.5 s** (median 4.1 s) | **5.1 s** (median 3.6 s) |
| Cost per notice | ≤ 0.05 USD | **0.017 USD** at the paid rate (F0 is free) | **0.014 USD** | **0.014 USD** |

Every miss by either reader was a field left unread; no field of any notice came back with a wrong value, at any confidence. Gemini's run-1 misses are all one notice (022), whose call failed.

**Result:** Gemini passes every measured criterion. Document Intelligence fails the address criterion (80.5%), passes the name criterion only on PDFs and photos combined, and passes the rest.

## What went wrong, and why

**Document Intelligence**

1. **Envelope line split (4 of 29 held-out PDFs: 009, 024, 027, 030).** Name and the whole address came back unread. In the recorded response for 009, the OCR put `Montréal (Québec)` and `H9A 8M1` on two lines; the parser expects them on one, so it never found the envelope block. The other three show the same symptom but were not inspected. The fix is small (accept the postal code on the next line), but this was found on held-out files after the freeze, so it was not applied: validating it needs notices the parser was not tuned on. US-22 should include it.
2. **Postal codes on photos (6 of 15 readable photos, 4 held-out).** The OCR read letters in the postal code as digits (Z as 2, S as 8). Every misread code contains a Z, S or T. The parser leaves an invalid code unread rather than guessing, so these cost accuracy but never produced a wrong value.
3. **Confidence below 0.90 on correct values.** 15 correct fields per run (7 incomes, 6 names, 2 dates) came back below 0.90, some from watermark text that the OCR put in the same cell. Under US-24's rule (name, tax year and income read at 0.90 or more), 28 of the 41 held-out notices would qualify for automatic approval; the other 13 would go to staff review although most were read correctly.
4. **Free-tier waits.** One call a minute waited about 30 s: the slow calls start almost exactly 60 s apart (19:55:14, 19:56:15, 19:57:15 and so on), whatever the file. This is consistent with the F0 tier's per-minute limit, not with the files. The service itself took 4.5 to 10.6 s per notice; the paid tier has a higher limit.

**Gemini**

1. **One transient failure (notice 022, run 1).** Google refused the call with a 4xx error after 1.1 s; replayed alone, it succeeded, and run 2 read it correctly. US-22 needs a retry with backoff.
2. **Confidence carries no information.** Every value it returned had confidence 0.99 or 1.0, apart from an empty unit at confidence 0 on the unreadable notice 050 in run 1. It made no reading errors here, so these runs cannot show whether it would also say 1.0 when wrong; US-24 should not rely on its confidence alone for the income.
3. **Model lifetime.** Google's Gemini API page now routes `gemini-3.5-flash` to `gemini-3.6-flash`, and Google's data residency table commits processing to Canada for 3.5 Flash only (3.6 to 3.8 Flash: US and EU). If Google retires it in Montréal before a successor arrives there, option B has no model to run on.

## Repeatability and tuning

- **Run 1 against run 2.** Document Intelligence returned the same value and confidence for all 400 fields. Gemini differed only on notice 022 (failed in run 1) and on the unit of the unreadable notice 050 (empty at confidence 0 in run 1, not returned in run 2).
- **Dev against held-out.** Document Intelligence did better on the 8 dev files it was tuned on (name 100%) than on the held-out files (name 90.2%): the line-split failure did not occur in the 5 dev PDFs. Gemini scored the same on both. This is the overfitting risk of a label-keyed parser, and the reason the held-out split exists.

## Real-notice conditions

Run on 2026-10-30 with `--files`, reader code unchanged since the freeze. Outputs were kept outside the repository; only the fields returned at confidence 0.90 or more are copied here.

| File | Document Intelligence | Gemini |
| --- | --- | --- |
| Public redacted sample (Carte loisir, tax year 2018, two pages) | tax year, notice date | name, unit, tax year, notice date |
| `Registration.png` (app screenshot, not a notice) | nothing returned | nothing returned |
| `Store - Post a listing.png` (app screenshot, not a notice) | nothing returned | nothing returned |

- **An older real layout.** Both read the tax year (2018) and the notice date (2019-03-28) as printed, on a layout neither was tuned on. The sample's income amounts and address are blanked out; neither reader returned an income or an address.
- **A placeholder read as a name.** The publisher replaced the name with the printed text `Nom Prénom`. Gemini returned it as the name at confidence 0.90, the US-24 threshold. That is what is printed, but it shows that Gemini's confidence cannot tell a placeholder from a person's name: US-24's check of the notice name against the declared name is what catches it. Gemini also returned "no unit" at confidence 1.0 for an address it could not see.
- **Wrong documents.** Neither reader returned any field for the two app screenshots.

## Limits of this evidence

- All 50 notices come from our own generator, so they share one layout and one font. Real notices will vary more, which matters most for option A's parser.
- With 41 held-out notices, one notice moves a score by about 2.4 points; option A's name score (90.2%) is one notice above the line.
- A perfect score on 41 notices still allows an error rate of up to about 7% (rule of three, 95% confidence).
- Only one real notice was read, and its personal fields are blanked out, so these runs say nothing about accuracy on real names, addresses or incomes.
- The Law 25 comparison is separate: [evidence document](../../../docs/04-data/notice-reading-privacy-inputs.md). Google commits the Montréal endpoint's processing to Canada, not Québec, and prompts its classifiers flag may be kept up to 90 days and read by Google staff unless B.A.D.R. has a Google Cloud Master Agreement.
