"""Build validated ``SourceRecord`` chunks from the private Mosaic documents."""

import json
from collections import Counter
from pathlib import Path

from mosaic_pathway.cleaning import clean_paragraphs
from mosaic_pathway.extraction import extract_paragraphs
from mosaic_pathway.models import (
    AuthorityType,
    ContentType,
    SourceInventoryItem,
    SourceRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "data" / "inventory" / "sources.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "source_records.json"

TARGET_CHUNK_CHARS = 1_500
MAX_CHUNK_CHARS = 2_000
MIN_RECORD_CHARS = 20
CHUNK_SEPARATOR = "\n\n"

CONTENT_TYPE_BY_INVENTORY_TYPE: dict[str, ContentType] = {
    "mixed": "resource",
    "podcast_transcript": "story",
}

AUTHORITY_TYPE_BY_INVENTORY_TYPE: dict[str, AuthorityType] = {
    "mosaic_guidance": "mosaic_guidance",
    "expert_guidance": "mosaic_guidance",
    "lived_experience": "lived_experience",
    "mixed_expert_and_lived_experience": "lived_experience",
}


def load_inventory(inventory_path: Path = INVENTORY_PATH) -> list[SourceInventoryItem]:
    """Load and validate the human-reviewed source inventory."""

    raw_items = json.loads(inventory_path.read_text(encoding="utf-8"))

    return [SourceInventoryItem.model_validate(item) for item in raw_items]


def split_long_paragraph(paragraph: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split a single oversized paragraph on word boundaries."""

    if len(paragraph) <= max_chars:
        return [paragraph]

    pieces: list[str] = []
    remaining = paragraph

    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars)

        if split_at <= 0:
            split_at = max_chars

        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        pieces.append(remaining)

    return pieces


def _joined_length(paragraphs: list[str]) -> int:
    return len(CHUNK_SEPARATOR.join(paragraphs))


def chunk_paragraphs(
    paragraphs: list[str],
    target_chars: int = TARGET_CHUNK_CHARS,
    max_chars: int = MAX_CHUNK_CHARS,
) -> list[str]:
    """Group cleaned paragraphs into ordered, paragraph-aware chunks."""

    units: list[str] = []

    for paragraph in paragraphs:
        units.extend(split_long_paragraph(paragraph, max_chars))

    chunks: list[str] = []
    current: list[str] = []
    carried = 0

    def flush() -> None:
        nonlocal current, carried

        chunks.append(CHUNK_SEPARATOR.join(current))
        overlap = current[-1]
        current = [overlap] if len(overlap) <= max_chars // 4 else []
        carried = len(current)

    for unit in units:
        if current and _joined_length(current + [unit]) > max_chars:
            flush()

            if current and _joined_length(current + [unit]) > max_chars:
                current = []
                carried = 0

        current.append(unit)

        if _joined_length(current) >= target_chars:
            flush()

    if len(current) > carried:
        chunks.append(CHUNK_SEPARATOR.join(current))

    return chunks


def build_source_records(
    item: SourceInventoryItem, paragraphs: list[str]
) -> list[SourceRecord]:
    """Convert cleaned paragraphs of one source into validated records."""

    records: list[SourceRecord] = []

    for chunk in chunk_paragraphs(paragraphs):
        if len(chunk) < MIN_RECORD_CHARS:
            continue

        records.append(
            SourceRecord(
                source_id=f"{item.source_id}-{len(records) + 1:04d}",
                title=item.title,
                source_file=item.filename,
                content_type=CONTENT_TYPE_BY_INVENTORY_TYPE[item.content_type],
                authority_type=AUTHORITY_TYPE_BY_INVENTORY_TYPE[item.authority_type],
                topics=list(item.primary_topics),
                text=chunk,
            )
        )

    return records


def write_records(records: list[SourceRecord], output_path: Path = OUTPUT_PATH) -> None:
    """Write records as readable JSON, creating the output directory if needed."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.model_dump() for record in records]
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_knowledge_base(
    inventory_path: Path = INVENTORY_PATH,
    raw_dir: Path = RAW_DIR,
    output_path: Path = OUTPUT_PATH,
) -> list[SourceRecord]:
    """Extract, clean, chunk, and persist every included inventory source."""

    records: list[SourceRecord] = []

    for item in load_inventory(inventory_path):
        if item.rag_priority == "exclude":
            continue

        source_path = raw_dir / item.filename

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Source file for '{item.source_id}' is missing: {source_path}"
            )

        paragraphs = clean_paragraphs(extract_paragraphs(source_path))
        records.extend(build_source_records(item, paragraphs))

    write_records(records, output_path)

    return records


def main() -> None:
    """Build the knowledge base and print a summary without private content."""

    records = build_knowledge_base()
    counts = Counter(record.source_id.rsplit("-", 1)[0] for record in records)

    print(f"Documents processed: {len(counts)}")
    print(f"Records generated: {len(records)}")
    print(f"Output path: {OUTPUT_PATH}")
    print("Records per source:")

    for source_id, count in counts.items():
        print(f"  {source_id}: {count}")


if __name__ == "__main__":
    main()
