import json
from pathlib import Path

import pytest
from conftest import make_source_record
from pydantic import ValidationError

from mosaic_pathway.models import RetrievalExample, RetrievalResult, RetrievedRecord
from mosaic_pathway.retrieval_evaluation import (
    EXAMPLES_PATH,
    QueryEvaluation,
    evaluate_examples,
    evaluate_query,
    load_examples,
    summarize,
)


class FakeRetriever:
    """Returns pre-built chunk records per query without embedding anything."""

    def __init__(self, chunk_ids_by_query: dict[str, list[str]]) -> None:
        self.chunk_ids_by_query = chunk_ids_by_query
        self.calls: list[tuple[str, int, int]] = []

    def retrieve(
        self, query: str, top_k: int = 5, max_per_source: int = 2
    ) -> RetrievalResult:
        self.calls.append((query, top_k, max_per_source))

        return RetrievalResult(
            query=query,
            records=[
                RetrievedRecord(
                    record=make_source_record(chunk_id), score=1.0 - index / 100
                )
                for index, chunk_id in enumerate(self.chunk_ids_by_query[query])
            ],
        )


def example(query_id: str, query: str, expected: list[str]) -> RetrievalExample:
    return RetrievalExample(
        query_id=query_id, query=query, expected_source_ids=expected
    )


def write_examples(tmp_path: Path, items: list[dict[str, object]]) -> Path:
    path = tmp_path / "retrieval_queries.json"
    path.write_text(json.dumps(items), encoding="utf-8")

    return path


def test_query_is_a_hit_when_an_expected_source_appears() -> None:
    retriever = FakeRetriever(
        {
            "affordable stem": [
                "mosaic-web-resources-0002",
                "podcast-affording-path-0016",
            ]
        }
    )

    evaluation = evaluate_query(
        retriever,  # type: ignore[arg-type]
        example("affordability", "affordable stem", ["podcast-affording-path"]),
    )

    assert evaluation.hit
    assert evaluation.first_hit_rank == 2
    assert evaluation.retrieved_source_ids == [
        "mosaic-web-resources",
        "podcast-affording-path",
    ]
    assert retriever.calls == [("affordable stem", 5, 2)]


def test_query_is_a_miss_when_no_expected_source_appears() -> None:
    retriever = FakeRetriever(
        {"college": ["mosaic-web-resources-0002", "podcast-school-harm-0001"]}
    )

    evaluation = evaluate_query(
        retriever,  # type: ignore[arg-type]
        example("college", "college", ["podcast-college-application"]),
    )

    assert not evaluation.hit
    assert evaluation.first_hit_rank is None


def test_first_matching_rank_is_the_earliest_expected_source() -> None:
    retriever = FakeRetriever(
        {
            "community": [
                "mosaic-web-resources-0002",
                "podcast-neurodivergence-0003",
                "podcast-affording-path-0004",
            ]
        }
    )

    evaluation = evaluate_query(
        retriever,  # type: ignore[arg-type]
        example(
            "community",
            "community",
            ["podcast-affording-path", "podcast-neurodivergence"],
        ),
    )

    assert evaluation.first_hit_rank == 2


def test_evaluate_examples_preserves_input_order() -> None:
    retriever = FakeRetriever(
        {
            "first query": ["mosaic-web-resources-0001"],
            "second query": ["podcast-affording-path-0001"],
            "third query": ["podcast-school-harm-0001"],
        }
    )
    examples = [
        example("one", "first query", ["mosaic-web-resources"]),
        example("two", "second query", ["podcast-affording-path"]),
        example("three", "third query", ["podcast-school-harm"]),
    ]

    evaluations = evaluate_examples(retriever, examples)  # type: ignore[arg-type]

    assert [evaluation.query_id for evaluation in evaluations] == [
        "one",
        "two",
        "three",
    ]
    assert [call[0] for call in retriever.calls] == [
        "first query",
        "second query",
        "third query",
    ]


def test_summary_reports_hit_rate_and_mean_reciprocal_rank() -> None:
    evaluations = [
        QueryEvaluation(
            query_id="one",
            query="first",
            expected_source_ids=["a"],
            retrieved_source_ids=["a"],
            first_hit_rank=1,
        ),
        QueryEvaluation(
            query_id="two",
            query="second",
            expected_source_ids=["b"],
            retrieved_source_ids=["c", "d", "e", "b"],
            first_hit_rank=4,
        ),
        QueryEvaluation(
            query_id="three",
            query="third",
            expected_source_ids=["f"],
            retrieved_source_ids=["g"],
        ),
    ]

    summary = summarize(evaluations)

    assert summary.queries_evaluated == 3
    assert summary.hits_at_k == 2
    assert summary.hit_rate_at_k == pytest.approx(2 / 3)
    assert summary.mean_reciprocal_rank == pytest.approx(0.625)


def test_summary_of_all_misses_reports_zero_metrics() -> None:
    summary = summarize(
        [
            QueryEvaluation(
                query_id="one",
                query="first",
                expected_source_ids=["a"],
                retrieved_source_ids=["b"],
            )
        ]
    )

    assert summary.hits_at_k == 0
    assert summary.hit_rate_at_k == 0.0
    assert summary.mean_reciprocal_rank == 0.0


def test_duplicate_query_ids_are_rejected(tmp_path: Path) -> None:
    path = write_examples(
        tmp_path,
        [
            {"query_id": "same", "query": "first", "expected_source_ids": ["a"]},
            {"query_id": "same", "query": "second", "expected_source_ids": ["b"]},
        ],
    )

    with pytest.raises(ValueError, match="Duplicate query IDs"):
        load_examples(path)


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_queries_are_rejected(tmp_path: Path, query: str) -> None:
    path = write_examples(
        tmp_path, [{"query_id": "one", "query": query, "expected_source_ids": ["a"]}]
    )

    with pytest.raises(ValidationError):
        load_examples(path)


def test_missing_query_id_is_rejected(tmp_path: Path) -> None:
    path = write_examples(
        tmp_path, [{"query": "a query", "expected_source_ids": ["a"]}]
    )

    with pytest.raises(ValidationError):
        load_examples(path)


def test_empty_expected_source_list_is_rejected(tmp_path: Path) -> None:
    path = write_examples(
        tmp_path, [{"query_id": "one", "query": "a query", "expected_source_ids": []}]
    )

    with pytest.raises(ValidationError):
        load_examples(path)


def test_bundled_example_query_set_is_valid() -> None:
    examples = load_examples(EXAMPLES_PATH)

    assert len(examples) >= 8
    assert all(example.expected_source_ids for example in examples)
