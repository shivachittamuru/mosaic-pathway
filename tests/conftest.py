import hashlib
import math
from typing import Any

import pytest

from mosaic_pathway.models import SourceRecord

FAKE_DIMENSION = 8


class FakeEmbeddingModel:
    """Deterministic offline stand-in for the local sentence-transformer model."""

    model_name = "fake-embedding-model"

    def __init__(self, dimension: int = FAKE_DIMENSION) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [digest[index] / 255 for index in range(self.dimension)]
        length = math.sqrt(sum(value * value for value in raw)) or 1.0

        return [value / length for value in raw]


class FakeVectorStore:
    """Returns pre-built payload and score pairs without touching Qdrant."""

    def __init__(
        self,
        results: list[tuple[dict[str, Any], float]],
        collection_size: int | None = None,
    ) -> None:
        self.results = results
        self.collection_size = (
            len(results) if collection_size is None else collection_size
        )
        self.requested_limits: list[int] = []

    def count(self) -> int:
        return self.collection_size

    def search(
        self, query_vector: list[float], limit: int
    ) -> list[tuple[dict[str, Any], float]]:
        self.requested_limits.append(limit)

        return self.results[:limit]


def make_source_record(source_id: str, text: str | None = None) -> SourceRecord:
    """Build a synthetic record that satisfies the SourceRecord constraints."""

    return SourceRecord(
        source_id=source_id,
        title=f"Synthetic source {source_id}",
        source_file="synthetic.docx",
        content_type="story",
        authority_type="lived_experience",
        topics=["synthetic topic"],
        text=text or f"Synthetic body text for record {source_id}.",
    )


@pytest.fixture
def fake_embedding_model() -> FakeEmbeddingModel:
    return FakeEmbeddingModel()
