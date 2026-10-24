# AI contribution: 50% or more AI-generated
"""Checks the run loop, the CLI outputs and the truth reader."""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import subprocess
from pathlib import Path

import pytest
from conftest import make_reading, make_row

from azure_layout_reader import AzureLayoutReader
from reader import DocumentReadError, NoticeReading
from run import (
    READERS,
    SERVICE_LOGGERS,
    content_type_for,
    git_commit,
    main,
    run_files,
    run_settings,
    select_files,
)
from score import DEV_FILES, summarize
from truth_reader import TruthReader

HOST = "example.cognitiveservices.azure.com"


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


class SometimesBrokenReader:
    """Raises an unexpected error whose message holds notice text, then reads normally."""

    def __init__(self) -> None:
        self.calls = 0

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        self.calls += 1
        if self.calls == 1:
            raise ValueError("raw response: Lefebvre 31 651,04")
        return make_reading(make_row())


class CountingFactory:
    """A READERS entry that counts how often a reader was built and called."""

    def __init__(self) -> None:
        self.built = 0
        self.reader = FlakyReader()

    def __call__(self) -> FlakyReader:
        self.built += 1
        return self.reader


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
    summary = summarize(records, truth, {"reader": "truth"})
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


def test_run_records_an_unexpected_exception_and_continues(tmp_path, caplog):
    names = ["pdf/notice-001.pdf", "pdf/notice-002.pdf"]
    files = _write_files(tmp_path, names)
    with caplog.at_level(logging.INFO):
        records = run_files(SometimesBrokenReader(), files, tmp_path)
    assert [record.file for record in records] == names
    assert records[0].reading is None
    assert records[0].error == "ValueError"
    assert records[1].reading is not None
    assert records[1].error is None
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert errors == ["pdf/notice-001.pdf unexpected ValueError"]
    assert "Lefebvre" not in caplog.text
    assert "31 651,04" not in caplog.text


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
    summary = out.with_suffix(".summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# Notice reading run\n\n## Settings\n\n- commit: ")
    assert "- reader: truth\n" in summary
    assert f"- date: {dt.date.today().isoformat()}\n" in summary
    assert "- notice-050 outcome: n/a" in summary  # the dev split has no unreadable photo


def test_main_keeps_service_sdk_loggers_at_warning(tmp_path):
    main(["--reader", "truth", "--split", "dev", "--out", str(tmp_path / "x.csv")])
    assert {logging.getLogger(name).level for name in SERVICE_LOGGERS} == {logging.WARNING}
    assert set(SERVICE_LOGGERS) >= {"azure", "google", "google_genai", "httpx"}


@pytest.mark.parametrize(
    ("bad_name", "message"),
    [("missing.pdf", "not a file: .*missing.pdf"), ("scan.gif", "unsupported file type: .gif")],
)
def test_main_rejects_an_invalid_files_path_before_any_reader_call(
    tmp_path, monkeypatch, bad_name, message
):
    factory = CountingFactory()
    monkeypatch.setitem(READERS, "truth", factory)
    good = _write_files(tmp_path, ["sample.pdf", "scan.gif"])[0]
    argv = ["--reader", "truth", "--files", str(good), str(tmp_path / bad_name)]
    with pytest.raises(SystemExit, match=message):
        main(argv + ["--out", str(tmp_path / "x.csv")])
    assert factory.built == 0
    assert factory.reader.calls == 0


def test_main_refuses_record_with_files(tmp_path, monkeypatch):
    factory = CountingFactory()
    monkeypatch.setitem(READERS, "truth", factory)
    sample = _write_files(tmp_path, ["sample.pdf"])[0]
    argv = ["--reader", "truth", "--files", str(sample), "--record", str(tmp_path / "rec")]
    with pytest.raises(SystemExit, match="--record cannot be used with --files"):
        main(argv + ["--out", str(tmp_path / "x.csv")])
    assert factory.built == 0
    assert not (tmp_path / "rec").exists()


def test_git_commit_runs_fixed_arguments_and_returns_the_short_hash(monkeypatch):
    seen: dict = {}

    def fake_run(args, **kwargs):
        seen.update(args=args, kwargs=kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="abc1234\n", stderr="")

    monkeypatch.setattr("run.subprocess.run", fake_run)
    assert git_commit() == "abc1234"
    assert seen["args"] == ["git", "rev-parse", "--short", "HEAD"]
    assert seen["kwargs"]["check"] is True
    assert not seen["kwargs"].get("shell")


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("git"),
        subprocess.CalledProcessError(128, ["git"]),
        subprocess.TimeoutExpired(["git"], 10),
    ],
)
def test_git_commit_is_unknown_and_warns_when_git_fails(monkeypatch, caplog, error):
    def fake_run(*args, **kwargs):
        raise error

    monkeypatch.setattr("run.subprocess.run", fake_run)
    with caplog.at_level(logging.WARNING):
        assert git_commit() == "unknown"
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.WARNING, f"git_commit_unknown {type(error).__name__}")
    ]


def test_run_settings_log_the_endpoint_host_once_and_never_the_key(monkeypatch, caplog):
    monkeypatch.setenv("AZURE_DI_ENDPOINT", f"https://{HOST}/")
    monkeypatch.setenv("AZURE_DI_KEY", "secret-key-value")
    monkeypatch.setenv("AZURE_DI_PRICE_PER_PAGE_USD", "0.01")
    monkeypatch.setattr("run.git_commit", lambda: "abc1234")
    with caplog.at_level(logging.INFO):
        settings = run_settings("azure-layout", AzureLayoutReader.from_env())
    assert settings == {
        "commit": "abc1234",
        "reader": "azure-layout",
        "model": "prebuilt-layout",
        "endpoint host": HOST,
        "date": dt.date.today().isoformat(),
    }
    run_logs = [r.getMessage() for r in caplog.records if r.name == "run"]
    assert sum(HOST in message for message in run_logs) == 1
    assert "secret-key-value" not in caplog.text


def test_run_settings_for_a_reader_without_settings_has_commit_reader_and_date(
    truth, notices_dir, monkeypatch
):
    monkeypatch.setattr("run.git_commit", lambda: "abc1234")
    settings = run_settings("truth", TruthReader(truth, notices_dir))
    assert list(settings) == ["commit", "reader", "date"]


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


class ParseFailingRecordingReader:
    """Keeps the raw answer, then fails to parse it, like AzureLayoutReader on a bad shape."""

    def __init__(self) -> None:
        self.last_result: dict | None = None

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        self.last_result = {"unexpected": "shape"}
        raise DocumentReadError("unexpected AnalyzeResult shape")


def test_run_files_records_a_raw_result_the_parser_rejected(tmp_path):
    record_dir = tmp_path / "recorded"
    files = _write_files(tmp_path, ["pdf/notice-004.pdf"])
    records = run_files(ParseFailingRecordingReader(), files, tmp_path, record_dir)
    assert records[0].error == "DocumentReadError"
    saved = json.loads((record_dir / "layout-notice-004.json").read_text("utf-8"))
    assert saved == {"unexpected": "shape"}


def test_main_record_fails_clearly_for_a_reader_without_raw_results(tmp_path):
    with pytest.raises(SystemExit, match="--record"):
        main(
            ["--reader", "truth", "--split", "dev", "--out", str(tmp_path / "x.csv")]
            + ["--record", str(tmp_path / "rec")]
        )
