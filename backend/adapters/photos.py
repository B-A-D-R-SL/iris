# AI contribution: 50% or more AI-generated
"""Prepare listing photos before storage, without Django or provider dependencies."""

from dataclasses import dataclass
from io import BytesIO
from struct import error as StructError

from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_PIXELS = 20_000_000
JPEG_QUALITY = 85
CONTENT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png"}
MAX_16_BIT = 65535
MAX_8_BIT = 255


class PhotoValidationError(ValueError):
    """A stable reason code; callers translate it without exposing decoder errors."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ProcessedPhoto:
    content: bytes
    content_type: str
    width: int
    height: int


def _check_image(image: Image.Image, max_pixels: int) -> str:
    if image.format not in CONTENT_TYPES:
        raise PhotoValidationError("unsupported_format")
    if image.width * image.height > max_pixels:
        raise PhotoValidationError("too_many_pixels")
    # A listing photo is a single still image; do not silently discard animation.
    if getattr(image, "n_frames", 1) != 1:
        raise PhotoValidationError("animated_image")
    return image.format


def _normalize(image: Image.Image) -> Image.Image:
    """Resolve transparency and bit depth before resampling colors."""
    mode = "RGBA" if image.has_transparency_data else "RGB"
    if image.mode == "I" or image.mode.startswith("I;16"):
        with (
            image.convert("I") as integers,
            integers.point(lambda value: value * MAX_8_BIT / MAX_16_BIT) as scaled,
            scaled.convert("L") as luminance,
        ):
            transparent = image.info.get("transparency")
            if transparent is not None:
                # Compare the original 16-bit samples before quantization: two
                # distinct shades may collapse to the same 8-bit value.
                mask = [
                    0 if value == transparent else MAX_8_BIT
                    for value in range(MAX_16_BIT + 1)
                ]
                with integers.point(mask, "L") as alpha:
                    luminance.putalpha(alpha)
            return luminance.convert(mode)
    return image.convert(mode)


def _encode(image: Image.Image, image_format: str) -> ProcessedPhoto:
    # Conversion/copy alone may retain info/EXIF. Transfer only pixels to a fresh
    # image so EXIF, GPS, XMP, comments and PNG text cannot be copied to storage.
    with Image.new(image.mode, image.size) as clean:
        clean.paste(image)
        output = BytesIO()
        options = {"quality": JPEG_QUALITY} if image_format == "JPEG" else {}
        clean.save(output, format=image_format, **options)
        return ProcessedPhoto(
            output.getvalue(), CONTENT_TYPES[image_format], clean.width, clean.height
        )


def _process(content: bytes, max_dimension: int, max_pixels: int) -> ProcessedPhoto:
    with Image.open(BytesIO(content), formats=list(CONTENT_TYPES)) as candidate:
        image_format = _check_image(candidate, max_pixels)
        candidate.verify()
    # verify() does not decode pixels and requires reopening before load().
    with Image.open(BytesIO(content), formats=list(CONTENT_TYPES)) as image:
        image.load()
        with (
            ImageOps.exif_transpose(image) as upright,
            _normalize(upright) as normalized,
        ):
            normalized.thumbnail(
                (max_dimension, max_dimension), Image.Resampling.LANCZOS
            )
            return _encode(normalized, image_format)


def process_photo(
    content: bytes,
    *,
    max_dimension: int,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> ProcessedPhoto:
    """Decode a bounded JPEG/PNG and return fresh, oriented, resized image bytes.

    Limits must be positive integers supplied by trusted callers. Pixel limits
    apply before full decoding. Pillow's own bomb protections remain enabled;
    no process-global image or warning settings are changed. No I/O or logging.
    """
    if any(
        type(limit) is not int or limit <= 0
        for limit in (max_dimension, max_bytes, max_pixels)
    ):
        raise ValueError("Photo limits must be positive integers.")
    if len(content) > max_bytes:
        raise PhotoValidationError("too_many_bytes")
    try:
        return _process(content, max_dimension, max_pixels)
    except PhotoValidationError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise PhotoValidationError("too_many_pixels") from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, StructError):
        raise PhotoValidationError("invalid_image") from None
