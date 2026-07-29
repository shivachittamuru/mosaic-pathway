"""Semantic retrieval over the local Mosaic vector store."""

from collections import Counter
from typing import Any

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.models import RetrievalResult, RetrievedRecord, SourceRecord
from mosaic_pathway.vector_store import MosaicVectorStore

DEFAULT_TOP_K = 5
DEFAULT_MAX_PER_SOURCE = 2
CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATES = 20
CANDIDATE_EXPANSION_FACTOR = 2


def inventory_source_id(record: SourceRecord) -> str:
    """Return the inventory source a chunk belongs to, e.g. 'mosaic-web-resources'."""

    return record.source_id.rsplit("-", 1)[0]


def candidate_limit(top_k: int) -> int:
    """Over-fetch so the per-source cap still leaves enough results."""

    return max(top_k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)


def select_diverse_records(
    candidates: list[tuple[dict[str, Any], float]],
    top_k: int,
    max_per_source: int,
) -> list[RetrievedRecord]:
    """Keep the highest scoring candidates, capped per inventory source."""

    selected: list[RetrievedRecord] = []
    per_source: Counter[str] = Counter()

    for payload, score in candidates:
        record = SourceRecord.model_validate(payload)
        source_id = inventory_source_id(record)

        if per_source[source_id] >= max_per_source:
            continue

        per_source[source_id] += 1
        selected.append(RetrievedRecord(record=record, score=score))

        if len(selected) >= top_k:
            break

    return selected


class MosaicRetriever:
    """Combines the local embedding model with the local vector store."""

    def __init__(
        self,
        embedding_model: LocalEmbeddingModel,
        vector_store: MosaicVectorStore,
    ) -> None:
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        max_per_source: int = DEFAULT_MAX_PER_SOURCE,
    ) -> RetrievalResult:
        """Return the top matching records, capped per inventory source."""

        if not query.strip():
            raise ValueError("Query must not be blank.")

        query_vector = self.embedding_model.embed_query(query)
        collection_size = self.vector_store.count()
        limit = min(candidate_limit(top_k), collection_size)

        # One dominant source can fill the first window, so widen it until the
        # per-source cap can be satisfied or the whole collection is considered.
        while True:
            candidates = self.vector_store.search(query_vector, limit)
            selected = select_diverse_records(candidates, top_k, max_per_source)

            if len(selected) >= top_k or limit >= collection_size:
                return RetrievalResult(query=query, records=selected)

            limit = min(limit * CANDIDATE_EXPANSION_FACTOR, collection_size)
