# AI contribution: 50% or more AI-generated
"""Runs a document reader over mock notices, scores it and writes the CSV and summary.

Usage: uv run run.py --reader truth|azure-layout (--split dev|heldout|all | --files PATH...)
       --out results/x.csv [--record DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

from azure_layout_reader import AzureLayoutReader
from reader import (
    DocumentReader,
    DocumentReadError,
    MeteredReader,
    NoticeReading,
    RecordingReader,
)
from records import RunRecord
from score import DEV_FILES, FIELD_NAMES, TruthRow, load_truth, score_reading, summarize
from truth_reader import TruthReader

__all__ = ["READERS", "RunRecord", "main", "run_files"]

logger = logging.getLogger(__name__)

NOTICES_DIR = Path(__file__).resolve().parents[2] / "mock-data" / "notices"
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _truth_reader() -> DocumentReader:
    return TruthReader(load_truth(NOTICES_DIR / "truth.csv"), NOTICES_DIR)


READERS: dict[str, Callable[[], DocumentReader]] = {
    "truth": _truth_reader,
    "azure-layout": AzureLayoutReader.from_env,
}


def content_type_for(path: Path) -> str:
    """The media type to send for a file, from its extension."""
    try:
        return CONTENT_TYPES[path.suffix.lower()]
    except KeyError:
        raise ValueError(f"unsupported file type: {path.suffix or path.name}") from None


def _record_name(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _cost(reader: DocumentReader) -> float:
    return reader.last_cost_usd if isinstance(reader, MeteredReader) else 0.0


def _read_one(reader: DocumentReader, path: Path, root: Path) -> RunRecord:
    content = path.read_bytes()
    content_type = content_type_for(path)
    reading: NoticeReading | None = None
    error: str | None = None
    started = time.perf_counter()
    try:
        reading = reader.read_notice(content, content_type)
    except DocumentReadError as exc:
        error = type(exc).__name__
    seconds = time.perf_counter() - started
    record = RunRecord(_record_name(path, root), reading, seconds, error, _cost(reader))
    logger.info("%s %.2fs %s", record.file, seconds, error or "ok")
    return record


def _record_raw_result(reader: RecordingReader, path: Path, record_dir: Path) -> None:
    if reader.last_result is not None:
        record_dir.mkdir(parents=True, exist_ok=True)
        target = record_dir / f"layout-{path.stem}.json"
        target.write_text(json.dumps(reader.last_result, ensure_ascii=False), encoding="utf-8")


def run_files(
    reader: DocumentReader, files: list[Path], root: Path, record_dir: Path | None = None
) -> list[RunRecord]:
    """Read each file; a DocumentReadError becomes a failed record, anything else propagates.

    With `record_dir`, each successful raw service result is saved as `layout-<file stem>.json`.
    """
    records = []
    for path in files:
        records.append(_read_one(reader, path, root))
        if record_dir is not None and isinstance(reader, RecordingReader):
            _record_raw_result(reader, path, record_dir)
    return records


def select_files(split: str, truth: dict[str, TruthRow], root: Path) -> list[Path]:
    """The files of a split: `dev` (DEV_FILES), `heldout` (the rest) or `all`."""
    names = [name for name in truth if split == "all" or (name in DEV_FILES) == (split == "dev")]
    return [root / name for name in names]


def _cell(value: object) -> str:
    return "" if value is None else str(value)


def write_csv(records: list[RunRecord], truth: dict[str, TruthRow], path: Path) -> None:
    """One row per file: each field's value, confidence and outcome, then seconds, error, cost."""
    header = ["file"]
    for name in FIELD_NAMES:
        header += [name, f"{name}_confidence", f"{name}_outcome"]
    header += ["seconds", "error", "cost_usd"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for record in records:
            row_truth = truth.get(record.file)
            outcomes = score_reading(row_truth, record.reading).outcomes if row_truth else {}
            row = [record.file]
            for name in FIELD_NAMES:
                field = getattr(record.reading, name) if record.reading else None
                row += [
                    _cell(field.value if field else None),
                    _cell(field.confidence if field else None),
                    outcomes.get(name, ""),
                ]
            row += [f"{record.seconds:.3f}", record.error or "", f"{record.cost_usd:.6f}"]
            writer.writerow(row)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader", required=True, choices=sorted(READERS))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--split", choices=["dev", "heldout", "all"])
    source.add_argument("--files", nargs="+", type=Path)
    parser.add_argument(
        "--record", type=Path, metavar="DIR", help="save each raw service result under DIR"
    )
    parser.add_argument("--out", required=True, type=Path, help="CSV path; summary goes beside it")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)
    truth = load_truth(NOTICES_DIR / "truth.csv")
    files = args.files or select_files(args.split, truth, NOTICES_DIR)
    try:
        reader = READERS[args.reader]()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    if args.record and not isinstance(reader, RecordingReader):
        raise SystemExit(
            f"error: --record needs a reader that keeps raw results, not {args.reader}"
        )
    records = run_files(reader, files, NOTICES_DIR, args.record)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_csv(records, truth, args.out)
    summary_path = args.out.with_suffix(".summary.md")
    summary_path.write_text(summarize(records, truth), encoding="utf-8")
    logger.info("wrote %s and %s", args.out, summary_path)


if __name__ == "__main__":
    main()
