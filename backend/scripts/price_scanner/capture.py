"""Pages for the extractor: text and/or images, and where they came from.

Captures come from the browser (browser.py) or from local files (`--from-files`): flyer
pages as PNG/JPEG/WebP, flyer PDFs (one image per page) or text saved from a shop page.
"""

import io
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.price_scanner.config import ScannerError

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
TEXT_SUFFIXES = frozenset({".txt", ".json", ".md"})
SUPPORTED_SUFFIXES = frozenset({*IMAGE_TYPES, ".pdf", *TEXT_SUFFIXES})
# PDF pages rendered at 144 dpi: the small print of a flyer stays legible for the model.
PDF_SCALE = 2.0
JPEG_QUALITY = 85


@dataclass(frozen=True)
class PageImage:
    data: bytes
    media_type: str


@dataclass(frozen=True)
class Capture:
    """One page for the extractor: one OpenAI call."""

    source: str  # URL, file path, or "flyer.pdf#page=3"
    text: str | None = None
    images: tuple[PageImage, ...] = ()
    screenshot: str | None = None  # saved screenshot of a browser page, for review


def clean_text(text: str) -> str:
    """Page text without blank lines or runs of whitespace."""
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def expand_paths(paths: Sequence[Path]) -> list[Path]:
    """Files to read: each given file, and the supported files in each given folder."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
            )
        elif not path.is_file():
            raise ScannerError(f"{path}: no such file")
        elif path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ScannerError(
                f"{path}: unsupported file type; use " + ", ".join(sorted(SUPPORTED_SUFFIXES))
            )
        else:
            files.append(path)
    if not files:
        raise ScannerError("no flyer files found")
    return files


def load_files(paths: Sequence[Path]) -> list[Capture]:
    captures: list[Capture] = []
    for path in expand_paths(paths):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            captures.extend(pdf_pages(path))
        elif suffix in TEXT_SUFFIXES:
            text = clean_text(path.read_text(encoding="utf-8"))
            captures.append(Capture(source=str(path), text=text))
        else:
            image = PageImage(path.read_bytes(), IMAGE_TYPES[suffix])
            captures.append(Capture(source=str(path), images=(image,)))
    return captures


def pdf_pages(path: Path) -> list[Capture]:
    """One JPEG per page of a flyer PDF."""
    try:
        import pypdfium2 as pdfium  # requirements-scraper.txt (with pillow, for to_pil)
    except ImportError as e:
        raise ScannerError(
            "Reading PDFs needs pypdfium2 and pillow: pip install -r requirements-scraper.txt"
        ) from e
    try:
        pdf = pdfium.PdfDocument(path)
    except pdfium.PdfiumError as e:
        raise ScannerError(f"{path}: not a readable PDF ({e})") from e
    captures = []
    try:
        for index in range(len(pdf)):
            image = pdf[index].render(scale=PDF_SCALE).to_pil()
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY)
            captures.append(
                Capture(
                    source=f"{path}#page={index + 1}",
                    images=(PageImage(buffer.getvalue(), "image/jpeg"),),
                )
            )
    finally:
        pdf.close()
    return captures
