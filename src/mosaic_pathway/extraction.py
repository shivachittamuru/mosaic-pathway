"""Deterministic text extraction from the supplied Mosaic source documents."""

from pathlib import Path

import pymupdf
from docx import Document


class UnsupportedFileTypeError(ValueError):
    """Raised when a source file uses a format this project cannot extract."""


def extract_docx_paragraphs(path: Path) -> list[str]:
    """Return the paragraphs of a DOCX file in document order."""

    document = Document(str(path))

    return [paragraph.text for paragraph in document.paragraphs]


def extract_pdf_pages(path: Path) -> list[str]:
    """Return the text of each PDF page in page order."""

    pages: list[str] = []

    with pymupdf.open(path) as document:
        for page in document:
            blocks = page.get_text("blocks")
            # A block tuple ends with the block type; 0 marks a text block.
            texts = [str(block[4]) for block in blocks if block[6] == 0]
            pages.append("\n\n".join(texts))

    return pages


def extract_pdf_paragraphs(path: Path) -> list[str]:
    """Return the text blocks of a PDF in page and block order."""

    return [
        block
        for page_text in extract_pdf_pages(path)
        for block in page_text.split("\n\n")
    ]


def extract_paragraphs(path: Path) -> list[str]:
    """Return ordered raw paragraphs for a supported source document."""

    suffix = path.suffix.lower()

    if suffix == ".docx":
        return extract_docx_paragraphs(path)

    if suffix == ".pdf":
        return extract_pdf_paragraphs(path)

    raise UnsupportedFileTypeError(
        f"Unsupported source file type '{path.suffix}' for {path.name}. "
        "Supported types are .docx and .pdf."
    )
