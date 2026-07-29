"""Persistent local Qdrant storage and search for Mosaic source records."""

import json
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FilterSelector,
    PointStruct,
    VectorParams,
)

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.knowledge_base import OUTPUT_PATH as SOURCE_RECORDS_PATH
from mosaic_pathway.knowledge_base import PROJECT_ROOT
from mosaic_pathway.models import SourceRecord

COLLECTION_NAME = "mosaic_sources"
VECTOR_STORE_PATH = PROJECT_ROOT / "data" / "vector_store"
INDEX_BATCH_SIZE = 64

# Fixed namespace so a record ID always maps to the same Qdrant point ID.
POINT_ID_NAMESPACE = uuid.UUID("8f4f6d2c-6f0a-5c4b-9a2e-2f7b1d3c5e70")


def point_id_for(source_id: str) -> str:
    """Convert a stable record ID into a deterministic Qdrant point ID."""

    return str(uuid.uuid5(POINT_ID_NAMESPACE, source_id))


def load_source_records(path: Path = SOURCE_RECORDS_PATH) -> list[SourceRecord]:
    """Load and validate the records produced by the knowledge base build."""

    raw_records = json.loads(path.read_text(encoding="utf-8"))

    return [SourceRecord.model_validate(record) for record in raw_records]


class MosaicVectorStore:
    """A persistent local Qdrant collection holding one point per source record."""

    def __init__(
        self,
        path: Path = VECTOR_STORE_PATH,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)

        self.path = path
        self.collection_name = collection_name
        self.client = QdrantClient(path=str(path))

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the local database lock."""

        self.client.close()

    def collection_exists(self) -> bool:
        return self.client.collection_exists(self.collection_name)

    def create_collection(self, dimension: int) -> None:
        """Create the collection with cosine distance, failing if it already exists."""

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def recreate_collection(self, dimension: int) -> None:
        """Drop and recreate the collection; only call this when rebuilding."""

        if self.collection_exists():
            # Local mode may fail to remove collection files that are still open,
            # so clear the points explicitly before dropping the collection.
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(filter=Filter()),
            )
            self.client.delete_collection(self.collection_name)

        self.create_collection(dimension)

    def count(self) -> int:
        """Return the number of indexed points."""

        return self.client.count(self.collection_name, exact=True).count

    def index_records(
        self,
        records: list[SourceRecord],
        embedding_model: LocalEmbeddingModel,
        batch_size: int = INDEX_BATCH_SIZE,
    ) -> int:
        """Embed and upsert records in batches, returning the number written."""

        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            vectors = embedding_model.embed_documents([record.text for record in batch])
            points = [
                PointStruct(
                    id=point_id_for(record.source_id),
                    vector=vector,
                    payload=record.model_dump(),
                )
                for record, vector in zip(batch, vectors, strict=True)
            ]

            self.client.upsert(collection_name=self.collection_name, points=points)

        return len(records)

    def search(
        self, query_vector: list[float], limit: int
    ) -> list[tuple[dict[str, Any], float]]:
        """Return candidate payloads and scores ordered by similarity."""

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )

        return [(point.payload or {}, point.score) for point in response.points]


def build_index(
    records_path: Path = SOURCE_RECORDS_PATH,
    store_path: Path = VECTOR_STORE_PATH,
    collection_name: str = COLLECTION_NAME,
    embedding_model: LocalEmbeddingModel | None = None,
) -> int:
    """Rebuild the local collection from the processed source records."""

    records = load_source_records(records_path)
    model = embedding_model or LocalEmbeddingModel()
    dimension = model.dimension

    with MosaicVectorStore(store_path, collection_name) as store:
        store.recreate_collection(dimension)
        store.index_records(records, model)
        indexed = store.count()

    if indexed != len(records):
        raise RuntimeError(
            f"Indexed {indexed} points but expected {len(records)} records."
        )

    return indexed


def main() -> None:
    """Rebuild the index and print a summary without private record text."""

    model = LocalEmbeddingModel()
    indexed = build_index(embedding_model=model)

    print(f"Embedding model: {model.model_name}")
    print(f"Embedding dimension: {model.dimension}")
    print(f"Records indexed: {indexed}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Local database path: {VECTOR_STORE_PATH}")


if __name__ == "__main__":
    main()
