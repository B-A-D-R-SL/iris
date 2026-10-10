# AI contribution: 50% or more AI-generated
"""Turn a notice PDF into a phone photo of the paper notice lying on a table.

Steps: render the page, uneven lighting, rotate -7 to +7 degrees, soft shadow,
table background, blur, JPEG quality 60. Every random choice comes from the
`rng` passed in, so the same seed gives the same photo.
"""

from __future__ import annotations

import io
import random

import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

RENDER_DPI = 110
MAX_ANGLE = 7.0
JPEG_QUALITY = 60
# (dark, light) colour pairs for the table top: oak, walnut, grey laminate.
TABLE_COLOURS = (
    ((122, 84, 48), (176, 128, 80)),
    ((74, 50, 34), (120, 84, 56)),
    ((118, 116, 110), (164, 162, 154)),
)


def render_page(pdf_bytes: bytes, dpi: int = RENDER_DPI) -> Image.Image:
    """Render the first page of a PDF to an RGB image."""
    document = pdfium.PdfDocument(pdf_bytes)
    try:
        page = document[0]
        image = page.render(scale=dpi / 72).to_pil().convert("RGB")
        page.close()
    finally:
        document.close()
    return image


def _noise(rng: random.Random, size: tuple[int, int]) -> Image.Image:
    """Seeded grey noise (Pillow's own noise generators cannot be seeded)."""
    width, height = size
    return Image.frombytes("L", size, rng.randbytes(width * height))


def table_background(rng: random.Random, size: tuple[int, int]) -> Image.Image:
    """Wood-like table top: horizontal grain, blotches and plank seams."""
    width, height = size
    grain = _noise(rng, (1, height // 10)).resize(size, Image.Resampling.BICUBIC)
    blotches = _noise(rng, (6, 8)).resize(size, Image.Resampling.BICUBIC)
    texture = Image.blend(grain, blotches, 0.45)
    texture = ImageOps.autocontrast(texture, cutoff=2)
    dark, light = rng.choice(TABLE_COLOURS)
    table = ImageOps.colorize(texture, dark, light)

    draw = ImageDraw.Draw(table)
    seam_dark = tuple(channel // 2 for channel in dark)
    y = rng.randint(height // 6, height // 3)
    while y < height:
        draw.line([(0, y), (width, y + rng.randint(-4, 4))], fill=seam_dark, width=2)
        y += rng.randint(height // 4, height // 2)
    return table


def _uneven_light(rng: random.Random, paper: Image.Image) -> Image.Image:
    """Darken the page towards one side, as with a lamp or window light."""
    # Rotate a large gradient and keep its centre, so no empty corners show up.
    gradient = Image.linear_gradient("L").resize((512, 512))
    gradient = gradient.rotate(rng.uniform(0, 360), resample=Image.Resampling.BICUBIC)
    gradient = gradient.crop((128, 128, 384, 384)).resize(paper.size, Image.Resampling.BICUBIC)
    strength = rng.randint(35, 70)
    gradient = gradient.point(lambda value: 255 - strength + value * strength // 255)
    paper = ImageChops.multiply(paper, Image.merge("RGB", (gradient, gradient, gradient)))
    warm = Image.new("RGB", paper.size, (255, 249, 236))
    return ImageChops.multiply(paper, warm)


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def phone_photo(pdf_bytes: bytes, rng: random.Random, *, unreadable: bool = False) -> Image.Image:
    """A phone photo of the notice. `unreadable` wrecks it so no value can be read."""
    paper = _uneven_light(rng, render_page(pdf_bytes))
    angle = rng.uniform(-MAX_ANGLE, MAX_ANGLE)

    # Canvas a bit larger than the page, as when the phone is held above the table.
    canvas_size = (round(paper.width * 1.22), round(paper.height * 1.16))
    photo = table_background(rng, canvas_size)

    sheet = paper.convert("RGBA").rotate(
        angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0)
    )
    left = (canvas_size[0] - sheet.width) // 2 + rng.randint(-20, 20)
    top = (canvas_size[1] - sheet.height) // 2 + rng.randint(-20, 20)

    shadow_mask = sheet.getchannel("A").point(lambda alpha: alpha * 150 // 255)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(14))
    shadow_offset = (rng.randint(8, 22), rng.randint(10, 26))
    shadow = Image.new("RGB", canvas_size, (20, 16, 12))
    mask = Image.new("L", canvas_size, 0)
    mask.paste(shadow_mask, (left + shadow_offset[0], top + shadow_offset[1]))
    photo = Image.composite(shadow, photo, mask)
    photo.paste(sheet, (left, top), sheet)

    photo = photo.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 1.1)))
    if unreadable:
        small = (photo.width // 6, photo.height // 6)
        photo = photo.resize(small, Image.Resampling.BILINEAR).resize(photo.size)
        photo = photo.filter(ImageFilter.GaussianBlur(5))
        photo = ImageEnhance.Brightness(photo).enhance(1.55)
        photo = ImageEnhance.Contrast(photo).enhance(0.45)
        photo = _jpeg(photo, 8)
    return _jpeg(photo, JPEG_QUALITY)
