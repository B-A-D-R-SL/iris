# AI contribution: 50% or more AI-generated

# Listing photo processing (FIX-02 / LLL)

The reusable processor is `backend/adapters/photos.py`. It accepts JPEG/PNG bytes
and returns `ProcessedPhoto`: the new bytes, content type and actual dimensions.
It has no Django settings, database, cloud, filesystem or logging dependency.

This is the image-processing part of FIX-02. The listing upload service uses the
configured private storage adapter, which calls this processor before upload.
Processing errors become translated photo validation errors. See
[listing photo storage](listing-photo-storage.md) for configuration, private
access, five-minute links and integration tests. No endpoint or UI is added.

## Processing order and documentation

1. Check the byte limit before parsing. Identify only JPEG/PNG, reject animated
   images, and check width times height before loading pixels.
2. Verify the file, reopen it, and load its pixels. Pillow's
   [Image reference](https://pillow.readthedocs.io/en/stable/reference/Image.html)
   explains that opening is lazy and verification does not fully decode an image.
   It also documents the decompression-bomb protections, which remain enabled.
3. Apply orientation with
   [ImageOps.exif_transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose).
   This applies the orientation to the pixels; it does not remove all private
   metadata. Removing orientation first would leave some phone photos sideways.
4. Normalize to RGB/RGBA before resizing so color-key and palette transparency
   participate in alpha-aware resampling. Scale 16-bit grayscale across the full
   0–65535 range to 0–255; compute any transparency mask from the original samples
   before reducing precision so neighboring shades do not become transparent.
5. Use `thumbnail` with LANCZOS resampling to fit the supplied maximum dimension,
   preserving proportions without enlargement. The listing rule's default is
   1280, but the processor requires callers to pass it rather than fixing it here.
6. Transfer only the resulting pixels into a fresh RGB/RGBA image, preserving PNG
   transparency, and encode in the original JPEG/PNG format. The
   [format documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
   describes EXIF and save options, including PNG EXIF becoming available after
   loading. Fresh output avoids copying EXIF/GPS, XMP, comments or PNG text.

Input defaults are 5 MiB and 20,000,000 pixels. These are separate limits:
compressed size does not determine decoded memory use. The pixel cap accepts
the 12-megapixel demonstration images while bounding larger inputs; it is an
initial resource limit, not a measured capacity guarantee for staging. The
future adapter must pass the active byte/dimension rules and a reviewed resource
cap. Do not raise the pixel limit without reviewing worker memory/concurrency.

JPEG output uses quality 85. Re-encoding does not guarantee fewer bytes, even for
a smaller image. Output preserves visual proportions, not identical JPEG pixels.
Embedded color profiles are not copied; this is not a color-managed archival
pipeline. Non-JPEG/PNG formats and animated PNGs are rejected.

## Run locally without Docker or Azure

From the repository root, using PowerShell and the same `uv` tool as CI:

```powershell
cd backend
uv sync --locked --no-build
uv run --locked python -m pytest -c photos.ini -q
uv run --locked python -m tools.photo_demo --output-dir ../tmp/photo-demo
```

The standalone `photos.ini` disables Django initialization for these two test
files. No secret key, database credentials or running PostgreSQL are needed.
The normal CI suite still discovers both files using `pyproject.toml`.

The demo refuses to overwrite an existing directory. For another run, choose a
new name, such as `../tmp/photo-demo-2`. Only synthetic data is generated; the
fake GPS coordinates and camera name are not taken from anyone's photographs.
Generated files stay under the git-ignored `tmp/` directory. The demo is invoked
explicitly by a developer and never runs on application startup.

When using Docker instead, rebuild the backend for the new locked dependency,
then run these commands from the repository root:

```powershell
docker compose build backend
docker compose run --rm --no-deps backend python -m pytest -c photos.ini -q
docker compose run --rm --no-deps backend python -m tools.photo_demo --output-dir /app/tmp/photo-demo
```

The bind mount exposes the Docker demo under `backend/tmp/photo-demo` on the
host. Choose another output directory if that folder already exists.

## Visually check the output

Open `tmp/photo-demo` in Windows Explorer (or `backend/tmp/photo-demo` for Docker).
Open each original/processed pair in Photos. View at comparable zoom levels:
an image viewer can make different resolutions appear the same size.

| Files | Expected observation |
| --- | --- |
| `landscape-original.jpg` / `landscape-processed.jpg` | 4000 x 3000 becomes 1280 x 960; the complete pattern remains visible. |
| `portrait-original.png` / `portrait-processed.png` | 3000 x 4000 becomes 960 x 1280, without stretching. |
| `small-original.jpg` / `small-processed.jpg` | Both remain 640 x 480; the image is not enlarged. |
| `orientation-raw-pixels.png` / `orientation-processed.jpg` | Raw pixels are sideways; processed TOP text and arrow are upright. Viewers may automatically rotate the original JPEG, so use the raw-pixel preview for this comparison. |
| `transparency-original.png` / `transparency-processed.png` | The transparent top-left area survives. Viewer backgrounds vary; automated tests check the alpha values. |
| `results.txt` | Input EXIF/GPS is present; output EXIF/GPS is absent. PNG text is removed, and corrupted/pixel-limit examples are rejected. |

Windows Properties > Details helps inspect dimensions and some metadata, but a
blank GPS panel alone does not prove metadata removal. The tests reopen output
bytes and inspect EXIF, GPS, XMP, comments, PNG text, transparency and orientation.

## Automated evidence and integration handoff

Tests cover large/small images, JPEG/PNG decoding, all eight EXIF orientations,
synthetic metadata, palette/alpha/color-key transparency during shrinking,
16-bit grayscale tones and transparency, corrupted signatures, truncated
JPEG, PNG checksum failure, disallowed formats, animated PNG, byte/pixel limit
boundaries, Pillow bomb protections and caller configuration errors. The demo's
command and refusal to overwrite existing files are also exercised.

```powershell
uv run --locked python -m pytest -c photos.ini --cov=adapters.photos --cov-report=term-missing --cov-fail-under=90
uv run --locked ruff check adapters/photos.py tools tests/test_photos.py tests/test_photo_demo.py
uv run --locked ruff format --check adapters/photos.py tools tests/test_photos.py tests/test_photo_demo.py
```

`BlobPhotoStore.put_image` calls `process_photo` with the active limits, uploads
only `ProcessedPhoto.content` with its matching content type, and returns an
opaque reference. Processing errors prevent upload. The separate storage tests
cover backend permissions, private access and expiry; this visual demo proves
only image-processing properties. Real Azure staging still needs verification.

For the Release 2 LLL log, keep the actual commands/results, links to the
implementation and tests, the documentation consulted, and your own explanation
of what you learned. These implementation notes are AI-assisted technical
documentation, not a claim that the author's individual learning or reflection
has already been completed.
