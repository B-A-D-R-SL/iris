# AI contribution: 50% or more AI-generated
"""Exercise the documented developer command and its generated evidence."""

import subprocess
import sys
from pathlib import Path

from PIL import Image


def test_demo_command_exports_readable_images_and_metadata_evidence(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "examples"
    result = subprocess.run(
        [sys.executable, "-m", "tools.photo_demo", "--output-dir", str(folder)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert "Synthetic before/after" in result.stdout
    for name, expected in (
        ("landscape", (1280, 960)),
        ("portrait", (960, 1280)),
        ("small", (640, 480)),
        ("orientation", (800, 1200)),
        ("transparency", (640, 480)),
    ):
        suffix = "png" if name in {"portrait", "transparency"} else "jpg"
        with Image.open(folder / f"{name}-original.{suffix}") as original:
            original.load()
            assert original.getexif().get_ifd(34853)
        with Image.open(folder / f"{name}-processed.{suffix}") as processed:
            processed.load()
            assert processed.size == expected
            assert not processed.getexif()
    report = (folder / "results.txt").read_text(encoding="utf-8")
    assert report.count("EXIF=present; GPS=present") == 5
    assert report.count("EXIF=absent; GPS=absent") == 5
    assert "corrupted JPEG: rejected (invalid_image)" in report
    assert "pixel limit: rejected (too_many_pixels)" in report
    with Image.open(folder / "orientation-raw-pixels.png") as raw:
        assert raw.size == (1200, 800)


def test_demo_refuses_to_overwrite_an_existing_directory(tmp_path: Path) -> None:
    marker = tmp_path / "keep.txt"
    marker.write_text("do not overwrite", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "tools.photo_demo", "--output-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert marker.read_text(encoding="utf-8") == "do not overwrite"
    assert set(tmp_path.iterdir()) == {marker}
