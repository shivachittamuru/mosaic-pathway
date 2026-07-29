import pytest
from conftest import FakeEmbeddingModel, FakeVectorStore, make_source_record
from pydantic import ValidationError

from mosaic_pathway.retrieval import (
    MosaicRetriever,
    candidate_limit,
    inventory_source_id,
)


def build_retriever(
    results: list[tuple[dict, float]],
) -> tuple[MosaicRetriever, FakeVectorStore]:
    store = FakeVectorStore(results)
    retriever = MosaicRetriever(FakeEmbeddingModel(), store)  # type: ignore[arg-type]

    return retriever, store


def scored_payloads(source_ids: list[str]) -> list[tuple[dict, float]]:
    return [
        (make_source_record(source_id).model_dump(), 1.0 - index / 100)
        for index, source_id in enumerate(source_ids)
    ]


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_blank_queries_are_rejected(query: str) -> None:
    retriever, _ = build_retriever(scored_payloads(["synthetic-source-0001"]))

    with pytest.raises(ValueError):
        retriever.retrieve(query)


def test_inventory_source_id_strips_the_chunk_suffix() -> None:
    record = make_source_record("mosaic-web-resources-0042")

    assert inventory_source_id(record) == "mosaic-web-resources"


def test_candidate_limit_over_fetches() -> None:
    assert candidate_limit(2) == 20
    assert candidate_limit(10) == 40


def test_results_follow_similarity_order() -> None:
    retriever, store = build_retriever(
        scored_payloads([f"source-{index}-0001" for index in range(5)])
    )

    result = retriever.retrieve("a real query", top_k=5)
    scores = [retrieved.score for retrieved in result.records]

    assert result.query == "a real query"
    assert scores == sorted(scores, reverse=True)
    assert [retrieved.record.source_id for retrieved in result.records] == [
        f"source-{index}-0001" for index in range(5)
    ]
    assert store.requested_limits == [20]


def test_source_diversity_cap_limits_records_per_source() -> None:
    source_ids = [f"mosaic-web-resources-{index:04d}" for index in range(6)] + [
        "podcast-affording-path-0001",
        "podcast-neurodivergence-0001",
    ]
    retriever, _ = build_retriever(scored_payloads(source_ids))

    result = retriever.retrieve("a real query", top_k=4, max_per_source=2)
    selected = [retrieved.record.source_id for retrieved in result.records]

    assert selected == [
        "mosaic-web-resources-0000",
        "mosaic-web-resources-0001",
        "podcast-affording-path-0001",
        "podcast-neurodivergence-0001",
    ]


def test_top_k_limits_the_number_of_results() -> None:
    retriever, _ = build_retriever(
        scored_payloads([f"source-{index}-0001" for index in range(10)])
    )

    assert len(retriever.retrieve("a real query", top_k=3).records) == 3


def test_retrieval_is_deterministic_across_calls() -> None:
    retriever, _ = build_retriever(
        scored_payloads([f"source-{index}-0001" for index in range(8)])
    )

    first = retriever.retrieve("a real query", top_k=5)
    second = retriever.retrieve("a real query", top_k=5)

    assert first.model_dump() == second.model_dump()


def test_invalid_payload_fails_validation() -> None:
    retriever, _ = build_retriever(
        [({"source_id": "broken", "text": "too short"}, 0.9)]
    )

    with pytest.raises(ValidationError):
        retriever.retrieve("a real query")
