# AI contribution: 50% or more AI-generated
"""Exercise the demo's CLI and real processor within the coverage process."""

import sys
from pathlib import Path

import pytest
from PIL import Image

from tools import photo_demo


@pytest.fixture
def output_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep demo output in an isolated test folder, without a production override."""
    root = tmp_path / "demo-root"
    monkeypatch.setattr(photo_demo, "OUTPUT_ROOT", root)
    return root


def test_demo_command_exports_readable_images_and_metadata_evidence(
    output_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run the CLI parser and real processing, checking metadata and pixel dimensions."""
    monkeypatch.setattr(sys, "argv", ["photo_demo", "--output-dir", "examples"])
    photo_demo.main()
    assert "Synthetic before/after" in capsys.readouterr().out
    folder = output_root / "examples"
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


def test_demo_refuses_to_overwrite_an_existing_directory(
    output_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Existing outputs remain untouched when the CLI refuses a repeated name."""
    folder = output_root / "existing"
    folder.mkdir(parents=True)
    marker = folder / "keep.txt"
    marker.write_text("do not overwrite", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["photo_demo", "--output-dir", "existing"])
    with pytest.raises(SystemExit) as refused:
        photo_demo.main()
    assert refused.value.code == 2
    assert "already exists" in capsys.readouterr().err
    assert marker.read_text(encoding="utf-8") == "do not overwrite"
    assert set(folder.iterdir()) == {marker}


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "a/../../escape",
        "a/b",
        r"a\b",
        "/tmp/escape",
        r"C:\escape",
        ".",
        "..",
        "",
        "x" * 65,
    ],
)
def test_demo_rejects_unsafe_output_names_before_writing(
    name: str,
    output_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI-supplied paths cannot create files outside the fixed demo root."""
    monkeypatch.setattr(sys, "argv", ["photo_demo", "--output-dir", name])
    with pytest.raises(SystemExit) as refused:
        photo_demo.main()
    assert refused.value.code == 2
    assert "simple name" in capsys.readouterr().err
    assert not output_root.exists()
    assert not (output_root.parent / "escape").exists()


@pytest.mark.parametrize("link_check", ["is_symlink", "is_junction"])
def test_demo_refuses_a_redirected_output_root(
    link_check: str, output_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filesystem redirection cannot turn an allowed name into an outside write."""
    monkeypatch.setattr(Path, link_check, lambda path: path == output_root)
    with pytest.raises(ValueError, match="symbolic link or junction"):
        photo_demo.run_demo("examples")
    assert not output_root.exists()
