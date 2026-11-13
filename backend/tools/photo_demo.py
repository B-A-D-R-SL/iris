# AI contribution: 50% or more AI-generated
"""Generate synthetic before/after examples using the actual photo processor."""

import argparse
import re
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from adapters.photos import PhotoValidationError, process_photo

OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "tmp"


def _output_directory(name: str) -> Path:
    """Create one new child of backend/tmp; reject paths and redirected roots."""
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name) is None:
        raise ValueError(
            "Output directory must be a simple name, without path separators."
        )
    if OUTPUT_ROOT.is_symlink() or OUTPUT_ROOT.is_junction():
        raise ValueError(
            "The demo output root must not be a symbolic link or junction."
        )
    OUTPUT_ROOT.mkdir(exist_ok=True)
    folder = OUTPUT_ROOT / name
    folder.mkdir(exist_ok=False)
    return folder


def _pattern(size: tuple[int, int], *, transparent: bool = False) -> Image.Image:
    """Draw synthetic orientation and proportion markers for visual comparison."""
    image = Image.new("RGBA" if transparent else "RGB", size, "white")
    draw = ImageDraw.Draw(image)
    width, height = size
    draw.rectangle((0, 0, width // 2, height // 2), fill="tomato")
    draw.rectangle((width // 2, 0, width, height // 2), fill="gold")
    draw.rectangle((0, height // 2, width // 2, height), fill="skyblue")
    draw.rectangle((width // 2, height // 2, width, height), fill="lightgreen")
    font = ImageFont.load_default(size=max(16, min(size) // 12))
    draw.text((width // 2, height // 10), "TOP", fill="black", font=font, anchor="mt")
    draw.polygon(
        (
            (width // 2, height // 4),
            (width * 3 // 8, height // 2),
            (width * 5 // 8, height // 2),
        ),
        fill="black",
    )
    draw.ellipse(
        (width // 4, height // 2, width * 3 // 4, height * 7 // 8),
        outline="black",
        width=max(2, width // 100),
    )
    if transparent:
        draw.rectangle((0, 0, width // 4, height // 4), fill=(0, 0, 0, 0))
    return image


def _sample(
    size: tuple[int, int],
    image_format: str,
    *,
    rotated: bool = False,
    transparent: bool = False,
) -> bytes:
    """Encode a synthetic fixture with known metadata and optional EXIF rotation."""
    exif = Image.Exif()
    exif[271] = "IRIS SYNTHETIC CAMERA"
    exif[34853] = {1: "N", 2: (45, 0, 0), 3: "W", 4: (73, 0, 0)}
    options: dict[str, object] = {"exif": exif}
    if image_format == "PNG":
        text = PngImagePlugin.PngInfo()
        text.add_text("Description", "IRIS SYNTHETIC PRIVATE TEXT")
        options["pnginfo"] = text
    output = BytesIO()
    with _pattern(size, transparent=transparent) as image:
        if rotated:
            exif[274] = 6
            with image.transpose(Image.Transpose.ROTATE_90) as sideways:
                sideways.save(output, format=image_format, **options)
        else:
            image.save(output, format=image_format, **options)
    return output.getvalue()


def _describe(content: bytes) -> str:
    """Report decoded dimensions and metadata presence for before/after checks."""
    with Image.open(BytesIO(content)) as image:
        image.load()
        exif = image.getexif()
        return (
            f"{image.width} x {image.height}; {len(content)} bytes; "
            f"EXIF={'present' if exif else 'absent'}; "
            f"GPS={'present' if exif.get_ifd(34853) else 'absent'}; "
            f"orientation={exif.get(274, 'absent')}; "
            f"PNG text={'present' if getattr(image, 'text', {}) else 'absent'}"
        )


def _write_sample(folder: Path, name: str, content: bytes) -> list[str]:
    """Write a fixture pair and an untagged raw-pixel preview for orientation cases."""
    sample = Path(name)
    (folder / f"{sample.stem}-original{sample.suffix}").write_bytes(content)
    result = process_photo(content, max_dimension=1280)
    (folder / f"{sample.stem}-processed{sample.suffix}").write_bytes(result.content)
    # Explicit raw-pixel preview avoids image viewers auto-rotating the original.
    if "orientation" in name:
        with (
            Image.open(BytesIO(content)) as image,
            Image.new("RGB", image.size) as raw,
        ):
            raw.paste(image)
            raw.save(folder / "orientation-raw-pixels.png")
    return [
        name,
        f"  Before: {_describe(content)}",
        f"  After:  {_describe(result.content)}",
    ]


def run_demo(folder_name: str) -> Path:
    """Write synthetic examples into a new named directory beneath backend/tmp."""
    folder = _output_directory(folder_name)
    cases = [
        ("landscape.jpg", (4000, 3000), "JPEG", {}),
        ("portrait.png", (3000, 4000), "PNG", {}),
        ("small.jpg", (640, 480), "JPEG", {}),
        ("orientation.jpg", (800, 1200), "JPEG", {"rotated": True}),
        ("transparency.png", (640, 480), "PNG", {"transparent": True}),
    ]
    lines = [
        "Iris photo processing: SYNTHETIC DATA ONLY",
        "",
        "Open original/processed pairs. TOP must be upright, shapes retain",
        "their proportions. Check orientation-raw-pixels.png for sideways",
        "pixels; image viewers may auto-rotate the original JPEG.",
        "",
    ]
    for name, size, image_format, options in cases:
        content = _sample(size, image_format, **options)
        lines.extend(_write_sample(folder, name, content))
    for name, content, max_pixels in (
        ("corrupted JPEG", b"\xff\xd8\xfffake", 20_000_000),
        ("pixel limit", _sample((100, 50), "PNG"), 4999),
    ):
        try:
            process_photo(content, max_dimension=1280, max_pixels=max_pixels)
        except PhotoValidationError as exc:
            lines.append(f"{name}: rejected ({exc.code}); no output image")
        else:
            raise RuntimeError(f"Expected rejection: {name}")
    report = folder / "results.txt"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    """Run the explicit demo command, refusing to overwrite an existing directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        help="New directory name under backend/tmp, such as photo-demo; no paths",
    )
    args = parser.parse_args()
    try:
        report = run_demo(args.output_dir)
    except FileExistsError:
        parser.error("Output directory already exists. Choose a new directory.")
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Synthetic before/after images and report: {report.resolve()}")


if __name__ == "__main__":
    main()
