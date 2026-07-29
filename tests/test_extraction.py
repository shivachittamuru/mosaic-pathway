from pathlib import Path

import pytest
from docx import Document

from mosaic_pathway.extraction import (
    UnsupportedFileTypeError,
    extract_docx_paragraphs,
    extract_paragraphs,
)


def _write_synthetic_docx(path: Path, paragraphs: list[str]) -> None:
    document = Document()

    for paragraph in paragraphs:
        document.add_paragraph(paragraph)

    document.save(str(path))


def test_extract_docx_preserves_paragraph_order(tmp_path: Path) -> None:
    docx_path = tmp_path / "synthetic.docx"
    _write_synthetic_docx(docx_path, ["First heading", "Second body", "Third body"])

    paragraphs = extract_docx_paragraphs(docx_path)

    assert paragraphs == ["First heading", "Second body", "Third body"]


def test_extract_paragraphs_dispatches_docx(tmp_path: Path) -> None:
    docx_path = tmp_path / "synthetic.docx"
    _write_synthetic_docx(docx_path, ["Only paragraph"])

    assert extract_paragraphs(docx_path) == ["Only paragraph"]


def test_extract_paragraphs_rejects_unsupported_type(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("some text", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError):
        extract_paragraphs(text_path)
