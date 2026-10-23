# AI contribution: 50% or more AI-generated
"""Checks the run loop, the CLI outputs and the truth reader."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import pytest
from conftest import make_reading, make_row

from reader import DocumentReadError, NoticeReading
from run import content_type_for, main, run_files, select_files
from score import DEV_FILES, summarize
from truth_reader import TruthReader


class FlakyReader:
    """Fails on the second call, like a service outage; reports a cost per call."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_cost_usd = 0.0

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        self.calls += 1
        self.last_cost_usd = 0.02
        if self.calls == 2:
            raise DocumentReadError("service failed")
        return make_reading(make_row())


class BrokenReader:
    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        raise KeyError("a bug, not a read failure")


def _write_files(folder: Path, names: list[str]) -> list[Path]:
    paths = []
    for name in names:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        paths.append(path)
    return paths


def _table_row(summary: str, label: str) -> str:
    return next(line for line in summary.splitlines() if line.startswith(f"| {label} |"))


def test_truth_reader_scores_100_percent_on_all_50_files(truth, notices_dir):
    reader = TruthReader(truth, notices_dir)
    files = [notices_dir / name for name in truth]
    records = run_files(reader, files, notices_dir)
    assert [record.file for record in records] == list(truth)
    summary = summarize(records, truth)
    assert "Failures: 0" in summary
    for label in ("name", "address", "tax year", "total income", "notice date"):
        row = _table_row(summary, label)
        assert row.count("100.0%") == 3
        assert row.endswith("| 0 |")


def test_truth_reader_returns_confidence_one_and_the_truth(truth, notices_dir):
    reader = TruthReader(truth, notices_dir)
    content = (notices_dir / "pdf/notice-003.pdf").read_bytes()
    reading = reader.read_notice(content, "application/pdf")
    row = truth["pdf/notice-003.pdf"]
    assert reading.total_income_cents.value == row.total_income_cents
    assert reading.full_name.value == f"{row.first_name} {row.last_name}"
    assert reading.notice_date.confidence == 1.0
    assert reader.last_cost_usd == 0.0


def test_truth_reader_rejects_unknown_document(truth, notices_dir):
    reader = TruthReader(truth, notices_dir)
    with pytest.raises(DocumentReadError):
        reader.read_notice(b"not a mock notice", "application/pdf")


def test_run_records_failure_and_continues(tmp_path):
    names = ["pdf/notice-001.pdf", "pdf/notice-002.pdf", "pdf/notice-003.pdf"]
    records = run_files(FlakyReader(), _write_files(tmp_path, names), tmp_path)
    assert [record.file for record in records] == names
    assert records[1].reading is None
    assert records[1].error == "DocumentReadError"
    assert records[0].reading is not None and records[0].error is None
    assert records[2].reading is not None
    assert records[0].cost_usd == 0.02
    assert all(record.seconds >= 0 for record in records)


def test_run_lets_unexpected_exceptions_propagate(tmp_path):
    files = _write_files(tmp_path, ["pdf/notice-001.pdf"])
    with pytest.raises(KeyError):
        run_files(BrokenReader(), files, tmp_path)


def test_run_uses_given_path_for_files_outside_the_notices_folder(tmp_path):
    notices = tmp_path / "notices"
    notices.mkdir()
    outside = _write_files(tmp_path / "elsewhere", ["sample.pdf"])
    records = run_files(FlakyReader(), outside, notices)
    assert records[0].file == outside[0].as_posix()


@pytest.mark.parametrize(
    ("name", "content_type"),
    [
        ("a.pdf", "application/pdf"),
        ("a.PNG", "image/png"),
        ("a.jpg", "image/jpeg"),
        ("a.jpeg", "image/jpeg"),
    ],
)
def test_content_type_from_extension(name, content_type):
    assert content_type_for(Path(name)) == content_type


def test_content_type_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="gif"):
        content_type_for(Path("scan.gif"))


def test_select_files_splits_dev_and_heldout(truth, notices_dir):
    dev = select_files("dev", truth, notices_dir)
    heldout = select_files("heldout", truth, notices_dir)
    everything = select_files("all", truth, notices_dir)
    assert {p.relative_to(notices_dir).as_posix() for p in dev} == set(DEV_FILES)
    assert len(heldout) == 42
    assert len(everything) == 50
    assert not set(dev) & set(heldout)


def test_main_writes_csv_and_summary_without_logging_values(tmp_path, caplog):
    out = tmp_path / "truth.csv"
    with caplog.at_level(logging.INFO):
        main(["--reader", "truth", "--split", "dev", "--out", str(out)])
    assert out.with_suffix(".summary.md").exists()
    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8
    first = rows[0]
    assert first["file"] == "pdf/notice-001.pdf"
    assert first["total_income_cents"] == "3165104"
    assert first["total_income_cents_outcome"] == "correct"
    assert first["error"] == ""
    assert "pdf/notice-001.pdf" in caplog.text and "ok" in caplog.text
    assert "3165104" not in caplog.text and "Lefebvre" not in caplog.text


def test_main_with_files_outside_the_notices_folder_runs_unscored(tmp_path, notices_dir):
    out = tmp_path / "files.csv"
    copy = tmp_path / "sample.pdf"  # same bytes as a mock notice, so the truth reader answers
    copy.write_bytes((notices_dir / "pdf" / "notice-001.pdf").read_bytes())
    main(["--reader", "truth", "--files", str(copy), "--out", str(out)])
    summary = out.with_suffix(".summary.md").read_text(encoding="utf-8")
    assert f"- {copy.as_posix()}: full_name, street_number" in summary
    assert "| name |" not in summary


class RecordingFakeReader:
    """Exposes the raw result of its last call, like AzureLayoutReader."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_result: dict | None = None

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        self.calls += 1
        self.last_result = None
        if self.calls == 2:
            raise DocumentReadError("service failed")
        self.last_result = {"call": self.calls}
        return make_reading(make_row())


def test_run_files_records_each_raw_result_by_notice_number(tmp_path):
    names = ["pdf/notice-001.pdf", "pdf/notice-002.pdf", "pdf/notice-003.pdf"]
    record_dir = tmp_path / "recorded"
    run_files(RecordingFakeReader(), _write_files(tmp_path, names), tmp_path, record_dir)
    assert sorted(p.name for p in record_dir.iterdir()) == [
        "layout-notice-001.json",
        "layout-notice-003.json",  # the failed read of 002 leaves nothing to record
    ]
    assert json.loads((record_dir / "layout-notice-003.json").read_text("utf-8")) == {"call": 3}


def test_main_record_fails_clearly_for_a_reader_without_raw_results(tmp_path):
    with pytest.raises(SystemExit, match="--record"):
        main(
            ["--reader", "truth", "--split", "dev", "--out", str(tmp_path / "x.csv")]
            + ["--record", str(tmp_path / "rec")]
        )
