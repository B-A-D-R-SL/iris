# AI contribution: 50% or more AI-generated
"""Photo privacy and decoding tests; synthetic inputs, no database or cloud."""

from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin

from adapters.photos import PhotoValidationError, process_photo


def image_bytes(
    size: tuple[int, int] = (100, 50),
    image_format: str = "JPEG",
    /,
    **options: object,
) -> bytes:
    with Image.new("RGB", size, "red") as image:
        output = BytesIO()
        image.save(output, format=image_format, **options)
        return output.getvalue()


@pytest.mark.parametrize(
    ("image_format", "size", "expected"),
    [
        ("JPEG", (4000, 3000), (1280, 960)),
        ("PNG", (3000, 4000), (960, 1280)),
        ("PNG", (2000, 2000), (1280, 1280)),
        ("JPEG", (640, 480), (640, 480)),
        ("PNG", (333, 100), (333, 100)),
    ],
)
def test_resize_preserves_dimensions_and_actual_format(
    image_format: str, size: tuple[int, int], expected: tuple[int, int]
) -> None:
    result = process_photo(image_bytes(size, image_format), max_dimension=1280)
    with Image.open(BytesIO(result.content)) as output:
        output.load()
        assert output.format == image_format
        assert output.size == expected == (result.width, result.height)
    assert (
        result.content_type == {"JPEG": "image/jpeg", "PNG": "image/png"}[image_format]
    )


@pytest.mark.parametrize("image_format", ["JPEG", "PNG"])
def test_output_drops_exif_gps_and_other_private_metadata(image_format: str) -> None:
    exif = Image.Exif()
    exif[271] = "IRIS SYNTHETIC CAMERA"
    exif[270] = "IRIS SYNTHETIC DESCRIPTION"
    exif[34853] = {1: "N", 2: (45, 0, 0), 3: "W", 4: (73, 0, 0)}
    options: dict[str, object] = {"exif": exif}
    if image_format == "PNG":
        text = PngImagePlugin.PngInfo()
        text.add_text("Description", "IRIS SYNTHETIC PNG TEXT")
        text.add_itxt("XML:com.adobe.xmp", "IRIS SYNTHETIC XMP")
        options["pnginfo"] = text
    else:
        options["comment"] = b"IRIS SYNTHETIC COMMENT"
        options["xmp"] = (
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">IRIS SYNTHETIC XMP</x:xmpmeta>'
        )
    content = image_bytes((100, 50), image_format, **options)
    with Image.open(BytesIO(content)) as original:
        original.load()
        assert original.getexif().get_ifd(34853)
        assert original.getexif()[271] == "IRIS SYNTHETIC CAMERA"
    result = process_photo(content, max_dimension=1280)
    with Image.open(BytesIO(result.content)) as output:
        output.load()
        assert not output.getexif()
        assert not output.getexif().get_ifd(34853)
        assert not set(output.info) & {"exif", "xmp", "comment", "Description"}
        assert not getattr(output, "text", {})
    assert b"IRIS SYNTHETIC" not in result.content


@pytest.mark.parametrize(
    ("orientation", "order"),
    [
        (1, (0, 1, 2, 3)),
        (2, (1, 0, 3, 2)),
        (3, (3, 2, 1, 0)),
        (4, (2, 3, 0, 1)),
        (5, (0, 2, 1, 3)),
        (6, (2, 0, 3, 1)),
        (7, (3, 1, 2, 0)),
        (8, (1, 3, 0, 2)),
    ],
)
def test_all_exif_orientations_are_applied_to_pixels(
    orientation: int, order: tuple[int, ...]
) -> None:
    colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
    exif = Image.Exif()
    exif[274] = orientation
    with Image.new("RGB", (6, 4)) as image:
        for box, color in zip(
            ((0, 0, 3, 2), (3, 0, 6, 2), (0, 2, 3, 4), (3, 2, 6, 4)),
            colors,
            strict=True,
        ):
            image.paste(color, box)
        content = BytesIO()
        image.save(content, format="PNG", exif=exif)
    result = process_photo(content.getvalue(), max_dimension=1280)
    with Image.open(BytesIO(result.content)) as output:
        assert output.size == ((4, 6) if orientation >= 5 else (6, 4))
        corners = (
            (0, 0),
            (output.width - 1, 0),
            (0, output.height - 1),
            (output.width - 1, output.height - 1),
        )
        assert tuple(output.getpixel(point) for point in corners) == tuple(
            colors[index] for index in order
        )
        assert not output.getexif()


@pytest.mark.parametrize("palette", [False, True])
def test_png_transparency_survives_reencoding(palette: bool) -> None:
    with Image.new("RGBA", (20, 10), (255, 0, 0, 0)) as image:
        image.putpixel((10, 5), (0, 255, 0, 128))
        output = BytesIO()
        if palette:
            with image.convert("P") as indexed:
                indexed.save(output, format="PNG")
        else:
            image.save(output, format="PNG")
    result = process_photo(output.getvalue(), max_dimension=1280)
    with Image.open(BytesIO(result.content)) as processed:
        assert processed.mode == "RGBA"
        assert processed.getpixel((0, 0)) == (255, 0, 0, 0)
        assert processed.getpixel((10, 5)) == (0, 255, 0, 128)


@pytest.mark.parametrize("mode", ["RGB", "L", "P"])
def test_shrinking_color_key_png_preserves_soft_transparent_edges(mode: str) -> None:
    # A narrow white stripe on a transparent background must stay translucent
    # when reduced, rather than acquire opaque red/gray borders.
    background = (255, 0, 0) if mode == "RGB" else 0
    foreground = (255, 255, 255) if mode == "RGB" else 255
    with Image.new(mode, (20, 10), background) as image:
        if mode == "P":
            image.putpalette([value for shade in range(256) for value in (shade,) * 3])
        image.paste(foreground, (9, 0, 11, 10))
        content = BytesIO()
        image.save(content, format="PNG", transparency=background)
    result = process_photo(content.getvalue(), max_dimension=5)
    with Image.open(BytesIO(result.content)) as output:
        assert output.mode == "RGBA"
        assert output.size == (5, 3)
        for x in (1, 2, 3):
            pixel = output.getpixel((x, 0))
            assert isinstance(pixel, tuple)
            red, green, blue, alpha = pixel
            assert (red, green, blue) == (255, 255, 255)
            assert 0 < alpha < 255
        for x in (0, 4):
            edge = output.getpixel((x, 0))
            assert isinstance(edge, tuple)
            assert edge[3] == 0


@pytest.mark.parametrize("transparent", [False, True])
def test_16_bit_png_preserves_tonal_range_and_original_transparency(
    transparent: bool,
) -> None:
    # 1000 and 1001 both map to 3; only the original transparency key may vanish.
    values = (0, 1000, 1001, 20000, 32768, 40000, 60000, 65535)
    with Image.new("I;16", (len(values), 1)) as image:
        for x, value in enumerate(values):
            image.putpixel((x, 0), value)
        content = BytesIO()
        options = {"transparency": 1000} if transparent else {}
        image.save(content, format="PNG", **options)
    result = process_photo(content.getvalue(), max_dimension=1280)
    with Image.open(BytesIO(result.content)) as output:
        assert output.mode == ("RGBA" if transparent else "RGB")
        for x, expected in enumerate((0, 3, 3, 77, 127, 155, 233, 255)):
            pixel = output.getpixel((x, 0))
            assert isinstance(pixel, tuple)
            assert pixel[:3] == (expected,) * 3
            if transparent:
                assert pixel[3] == (0 if x == 1 else 255)


@pytest.mark.parametrize("content", [b"", b"not an image", b"\xff\xd8\xfffake"])
def test_invalid_inputs_have_a_stable_error_without_decoder_details(
    content: bytes,
) -> None:
    with pytest.raises(PhotoValidationError) as caught:
        process_photo(content, max_dimension=1280)
    assert caught.value.code == "invalid_image"
    assert str(caught.value) == "invalid_image"


def test_truncated_jpeg_is_rejected_during_decoding() -> None:
    content = image_bytes()[:-30]
    with pytest.raises(PhotoValidationError, match="^invalid_image$"):
        process_photo(content, max_dimension=1280)


def test_png_with_invalid_checksum_is_rejected() -> None:
    content = bytearray(image_bytes((100, 50), "PNG"))
    content[content.index(b"IDAT") + 4] ^= 1
    photo = bytes(content)
    with pytest.raises(PhotoValidationError, match="^invalid_image$"):
        process_photo(photo, max_dimension=1280)


@pytest.mark.parametrize("image_format", ["GIF", "BMP", "WEBP"])
def test_other_decodable_formats_are_refused(image_format: str) -> None:
    content = image_bytes((100, 50), image_format)
    with pytest.raises(PhotoValidationError):
        process_photo(content, max_dimension=1280)


def test_animated_png_is_refused() -> None:
    content = BytesIO()
    with (
        Image.new("RGB", (10, 10), "red") as first,
        Image.new("RGB", (10, 10), "blue") as second,
    ):
        first.save(content, format="PNG", save_all=True, append_images=[second])
    photo = content.getvalue()
    with pytest.raises(PhotoValidationError, match="^animated_image$"):
        process_photo(photo, max_dimension=1280)


def test_byte_limit_accepts_boundary_and_rejects_above_it() -> None:
    content = image_bytes()
    process_photo(content, max_dimension=1280, max_bytes=len(content))
    byte_limit = len(content) - 1
    with pytest.raises(PhotoValidationError, match="^too_many_bytes$"):
        process_photo(content, max_dimension=1280, max_bytes=byte_limit)


def test_pixel_limit_accepts_boundary_and_rejects_before_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = image_bytes((100, 50), "PNG")
    process_photo(content, max_dimension=1280, max_pixels=5000)

    def unexpected_load(*args: object, **kwargs: object) -> None:
        pytest.fail("Oversized image must be refused before loading pixels")

    monkeypatch.setattr(Image.Image, "load", unexpected_load)
    with pytest.raises(PhotoValidationError, match="^too_many_pixels$"):
        process_photo(content, max_dimension=1280, max_pixels=4999)


@pytest.mark.parametrize("pillow_limit", [2000, 3000])
@pytest.mark.filterwarnings("error::PIL.Image.DecompressionBombWarning")
def test_pillow_bomb_protections_still_reject_images(
    monkeypatch: pytest.MonkeyPatch, pillow_limit: int
) -> None:
    content = image_bytes((100, 50), "PNG")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", pillow_limit)
    with pytest.raises(PhotoValidationError, match="^too_many_pixels$"):
        process_photo(content, max_dimension=1280)
    assert Image.MAX_IMAGE_PIXELS == pillow_limit


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
@pytest.mark.parametrize("name", ["max_dimension", "max_bytes", "max_pixels"])
def test_invalid_caller_limits_are_configuration_errors(
    name: str, limit: object
) -> None:
    options = {"max_dimension": 1280, name: limit}
    with pytest.raises(ValueError, match="positive integers"):
        process_photo(b"", **options)  # type: ignore[arg-type]
