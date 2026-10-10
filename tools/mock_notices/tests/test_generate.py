# AI contribution: 50% or more AI-generated
"""Checks the mock notice generator against docs/04-data/mock-notices-of-assessment.md."""

from __future__ import annotations

import csv
import datetime as dt
import re
from collections import Counter
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image, ImageFilter, ImageStat

from generate import (
    APPLICANT_COLUMNS,
    CURRENT_TAX_YEAR,
    DEFAULT_OUT,
    MASKED_SIN,
    TRUTH_COLUMNS,
    WATERMARK,
    format_amount,
    generate,
    strip_accents,
)

EXPECTED_CASES = {
    "clean": 30,
    "photo": 15,
    "old_tax_year": 1,
    "name_mismatch": 1,
    "address_mismatch": 1,
    "zero_income": 1,
    "unreadable": 1,
}
EXPECTED_VARIATIONS = {
    "none": 42,
    "accents_stripped": 2,
    "uppercase": 2,
    "middle_name_omitted": 2,
    "different_last_name": 1,
    "moved": 1,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def pdf_pages_text(path: Path) -> list[str]:
    document = pdfium.PdfDocument(path)
    try:
        # Extraction collapses runs of spaces, so the expected strings use single spaces.
        texts = [page.get_textpage().get_text_range() for page in document]
        return [re.sub(r" +", " ", text.replace("\r\n", "\n")) for text in texts]
    finally:
        document.close()


def edge_strength(path: Path) -> float:
    """Mean edge intensity: high for sharp text, low for a blurred photo."""
    image = Image.open(path).convert("L").filter(ImageFilter.FIND_EDGES)
    return ImageStat.Stat(image).mean[0]


def name_key(text: str) -> list[str]:
    return strip_accents(text).casefold().split()


def name_matches(declared: dict[str, str], printed: dict[str, str]) -> bool:
    # rule: name check (case and accents ignored, extra middle names allowed)
    same_last = name_key(declared["last_name"]) == name_key(printed["last_name"])
    first_included = set(name_key(declared["first_name"])) <= set(name_key(printed["first_name"]))
    return same_last and first_included


def address_matches(declared: dict[str, str], printed: dict[str, str]) -> bool:
    # rule: address check (postal code and civic number)
    def postal(code: str) -> str:
        return code.replace(" ", "").upper()

    return declared["street_number"] == printed["street_number"] and postal(
        declared["postal_code"]
    ) == postal(printed["postal_code"])


@pytest.fixture(scope="session")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("notices")
    generate(path)
    return path


@pytest.fixture(scope="session")
def truth(out: Path) -> list[dict[str, str]]:
    return read_csv(out / "truth.csv")


@pytest.fixture(scope="session")
def applicants(out: Path) -> list[dict[str, str]]:
    return read_csv(out / "applicants.csv")


def output_files(folder: Path) -> list[str]:
    return sorted(
        path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()
    )


# --- Reproducibility --------------------------------------------------------


def test_same_seed_gives_byte_identical_files(out: Path, tmp_path: Path) -> None:
    generate(tmp_path)
    assert output_files(tmp_path) == output_files(out)
    for name in output_files(out):
        assert (tmp_path / name).read_bytes() == (out / name).read_bytes(), name


def test_committed_output_is_up_to_date(out: Path) -> None:
    # The files in mock-data/notices/ must be what the generator produces today.
    assert output_files(DEFAULT_OUT) == output_files(out)
    for name in ("truth.csv", "applicants.csv"):
        assert read_csv(DEFAULT_OUT / name) == read_csv(out / name), name


# --- Files and cases ----------------------------------------------------------


def test_csv_columns_follow_spec(out: Path) -> None:
    assert tuple(read_csv(out / "truth.csv")[0]) == TRUTH_COLUMNS
    assert tuple(read_csv(out / "applicants.csv")[0]) == APPLICANT_COLUMNS


def test_fifty_files_34_pdfs_and_16_photos(out: Path, truth: list[dict[str, str]]) -> None:
    assert len(truth) == 50
    assert len(list((out / "pdf").glob("*.pdf"))) == 34
    assert len(list((out / "photos").glob("*.png"))) == 16


def test_case_counts_follow_spec(truth: list[dict[str, str]]) -> None:
    assert Counter(row["case"] for row in truth) == EXPECTED_CASES


def test_every_truth_row_has_a_file_and_every_file_has_a_row(
    out: Path, truth: list[dict[str, str]], applicants: list[dict[str, str]]
) -> None:
    files = [name for name in output_files(out) if not name.endswith(".csv")]
    assert sorted(row["file"] for row in truth) == files
    assert [row["file"] for row in applicants] == [row["file"] for row in truth]


def test_photos_are_png_and_pdfs_are_pdf(truth: list[dict[str, str]]) -> None:
    for row in truth:
        is_photo = row["case"] in {"photo", "unreadable"}
        folder, extension = ("photos/", ".png") if is_photo else ("pdf/", ".pdf")
        assert row["file"].startswith(folder), row["file"]
        assert row["file"].endswith(extension), row["file"]


# --- What is printed ----------------------------------------------------------


def test_every_pdf_page_is_watermarked_and_sin_masked(
    out: Path, truth: list[dict[str, str]]
) -> None:
    sin_pattern = re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{3}\b")
    for row in truth:
        if not row["file"].endswith(".pdf"):
            continue
        for text in pdf_pages_text(out / row["file"]):
            assert WATERMARK in text, row["file"]
            assert MASKED_SIN in text, row["file"]
            assert not sin_pattern.search(text), row["file"]


def test_pdf_text_shows_truth_values(out: Path, truth: list[dict[str, str]]) -> None:
    for row in truth:
        if not row["file"].endswith(".pdf"):
            continue
        text = pdf_pages_text(out / row["file"])[0]
        address = f"{row['street_number']}, {row['street_name']}"
        if row["unit"]:
            address += f", app. {row['unit']}"
        total = format_amount(int(row["total_income_cents"]))

        assert f"{row['last_name']}, {row['first_name']}" in text, row["file"]
        assert address in text, row["file"]
        assert f"Montréal (Québec) {row['postal_code']}" in text, row["file"]
        assert f"Année d'imposition\n{row['tax_year']}" in text, row["file"]
        assert f"Date de l'avis\n{row['notice_date']}" in text, row["file"]
        assert f"Revenu total (ligne 199) {total}" in text, row["file"]


def test_values_stay_in_spec_ranges(truth: list[dict[str, str]]) -> None:
    for row in truth:
        tax_year = int(row["tax_year"])
        notice_date = dt.date.fromisoformat(row["notice_date"])
        assert dt.date(tax_year + 1, 3, 1) <= notice_date <= dt.date(tax_year + 1, 6, 30)
        assert 0 <= int(row["total_income_cents"]) <= 85_000_00
        assert row["postal_code"].startswith("H")
        if row["case"] != "old_tax_year":
            assert tax_year == CURRENT_TAX_YEAR


def test_format_amount_uses_french_canadian_style() -> None:
    assert format_amount(0) == "0,00 $"
    assert format_amount(2_345_678) == "23 456,78 $"
    assert format_amount(-12_305) == "123,05 $"


# --- Edge cases ---------------------------------------------------------------


def test_edge_cases_are_what_their_name_says(
    truth: list[dict[str, str]], applicants: list[dict[str, str]]
) -> None:
    by_case = {
        row["case"]: (row, applicant) for row, applicant in zip(truth, applicants, strict=True)
    }

    old, _ = by_case["old_tax_year"]
    assert int(old["tax_year"]) < CURRENT_TAX_YEAR - 1  # refused even from January to June

    zero, _ = by_case["zero_income"]
    assert zero["total_income_cents"] == "0"

    printed, declared = by_case["name_mismatch"]
    assert not name_matches(declared, printed)
    assert address_matches(declared, printed)

    printed, declared = by_case["address_mismatch"]
    assert name_matches(declared, printed)
    assert declared["street_number"] != printed["street_number"]
    assert declared["postal_code"] != printed["postal_code"]

    unreadable, _ = by_case["unreadable"]
    assert unreadable["file"].endswith(".png")


def test_unreadable_photo_is_much_blurrier_than_every_other_photo(
    out: Path, truth: list[dict[str, str]]
) -> None:
    photos = [row for row in truth if row["file"].endswith(".png")]
    strength = {row["file"]: edge_strength(out / row["file"]) for row in photos}
    unreadable = next(strength[row["file"]] for row in photos if row["case"] == "unreadable")
    least_sharp_photo = min(strength[row["file"]] for row in photos if row["case"] == "photo")
    assert unreadable < 0.6 * least_sharp_photo


def test_photos_are_rgb_and_large_enough_to_read(out: Path, truth: list[dict[str, str]]) -> None:
    for row in truth:
        if row["file"].endswith(".png"):
            with Image.open(out / row["file"]) as image:
                assert image.mode == "RGB"
                assert image.width >= 1000
                assert image.height >= 1300


# --- Declared values (applicants.csv) -----------------------------------------


def test_declared_values_follow_the_matching_rules(
    truth: list[dict[str, str]], applicants: list[dict[str, str]]
) -> None:
    for printed, declared in zip(truth, applicants, strict=True):
        expected_name = declared["name_should_match"] == "true"
        expected_address = declared["address_should_match"] == "true"
        assert name_matches(declared, printed) is expected_name, declared["file"]
        assert address_matches(declared, printed) is expected_address, declared["file"]


def test_variation_counts_follow_spec(applicants: list[dict[str, str]]) -> None:
    assert Counter(row["variation"] for row in applicants) == EXPECTED_VARIATIONS


def test_name_controls_really_differ_from_the_notice(
    truth: list[dict[str, str]], applicants: list[dict[str, str]]
) -> None:
    for printed, declared in zip(truth, applicants, strict=True):
        if declared["variation"] in {"accents_stripped", "uppercase", "middle_name_omitted"}:
            assert printed["case"] == "clean"
            declared_name = (declared["first_name"], declared["last_name"])
            assert declared_name != (printed["first_name"], printed["last_name"])
