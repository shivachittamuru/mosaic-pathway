import json
from pathlib import Path

from docx import Document

from mosaic_pathway.knowledge_base import (
    MAX_CHUNK_CHARS,
    build_knowledge_base,
    build_source_records,
    chunk_paragraphs,
    load_inventory,
)
from mosaic_pathway.models import SourceRecord

FILENAME = "synthetic-source.docx"


def _inventory_item() -> dict[str, object]:
    return {
        "source_id": "synthetic-source",
        "filename": FILENAME,
        "title": "Synthetic Source",
        "format": "docx",
        "content_type": "podcast_transcript",
        "primary_topics": ["synthetic topic"],
        "audience": "test families",
        "rag_priority": "core",
        "authority_type": "lived_experience",
        "requires_cleaning": True,
        "notes": "Synthetic fixture used only for offline tests.",
    }


def _build_workspace(tmp_path: Path, paragraphs: list[str]) -> tuple[Path, Path, Path]:
    inventory_path = tmp_path / "sources.json"
    inventory_path.write_text(json.dumps([_inventory_item()]), encoding="utf-8")

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    document = Document()

    for paragraph in paragraphs:
        document.add_paragraph(paragraph)

    document.save(str(raw_dir / FILENAME))

    return inventory_path, raw_dir, tmp_path / "processed" / "source_records.json"


def test_chunk_paragraphs_respects_maximum_size() -> None:
    paragraphs = [f"Paragraph number {index}. " * 20 for index in range(40)]

    chunks = chunk_paragraphs(paragraphs)

    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in chunks)


def test_chunk_paragraphs_preserves_paragraph_order() -> None:
    paragraphs = [f"Paragraph {index}. " * 15 for index in range(30)]

    joined = "\n\n".join(chunk_paragraphs(paragraphs))
    positions = [joined.index(f"Paragraph {index}.") for index in range(30)]

    assert positions == sorted(positions)


def test_chunk_paragraphs_keeps_short_input_in_one_chunk() -> None:
    paragraphs = ["A short paragraph.", "Another short paragraph."]

    assert chunk_paragraphs(paragraphs) == [
        "A short paragraph.\n\nAnother short paragraph."
    ]


def test_chunk_paragraphs_splits_single_oversized_paragraph() -> None:
    chunks = chunk_paragraphs(["word " * 1_200])

    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in chunks)


def test_build_source_records_creates_valid_records_with_stable_ids(
    tmp_path: Path,
) -> None:
    inventory_path, _, _ = _build_workspace(tmp_path, ["placeholder"])
    item = load_inventory(inventory_path)[0]

    records = build_source_records(
        item, [f"Paragraph {index}. " * 20 for index in range(40)]
    )

    assert len(records) > 1
    assert all(isinstance(record, SourceRecord) for record in records)
    assert records[0].source_id == "synthetic-source-0001"
    assert records[1].source_id == "synthetic-source-0002"
    assert records[0].source_file == FILENAME
    assert records[0].content_type == "story"
    assert records[0].authority_type == "lived_experience"
    assert records[0].topics == ["synthetic topic"]


def test_build_knowledge_base_writes_deterministic_output(tmp_path: Path) -> None:
    paragraphs = ["Home", "Log in"] + [
        f"Body paragraph {index}." * 10 for index in range(30)
    ]
    inventory_path, raw_dir, output_path = _build_workspace(tmp_path, paragraphs)

    first = build_knowledge_base(inventory_path, raw_dir, output_path)
    first_output = output_path.read_text(encoding="utf-8")

    second = build_knowledge_base(inventory_path, raw_dir, output_path)
    second_output = output_path.read_text(encoding="utf-8")

    assert first
    assert [record.model_dump() for record in first] == [
        record.model_dump() for record in second
    ]
    assert first_output == second_output

    written = json.loads(first_output)

    assert [record["source_id"] for record in written] == [
        record.source_id for record in first
    ]
    assert all("Log in" not in record["text"] for record in written)
