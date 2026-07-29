"""Baseline evaluation of local retrieval against the synthetic query set."""

import json
from pathlib import Path

from pydantic import BaseModel

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.knowledge_base import PROJECT_ROOT
from mosaic_pathway.models import RetrievalExample
from mosaic_pathway.retrieval import (
    DEFAULT_MAX_PER_SOURCE,
    DEFAULT_TOP_K,
    MosaicRetriever,
    inventory_source_id,
)
from mosaic_pathway.vector_store import MosaicVectorStore

EXAMPLES_PATH = PROJECT_ROOT / "examples" / "retrieval_queries.json"


class QueryEvaluation(BaseModel):
    """The outcome of running one evaluation example through retrieval."""

    query_id: str
    query: str
    expected_source_ids: list[str]
    retrieved_source_ids: list[str]
    first_hit_rank: int | None = None

    @property
    def hit(self) -> bool:
        return self.first_hit_rank is not None


class EvaluationSummary(BaseModel):
    """Aggregate metrics across all evaluated queries."""

    queries_evaluated: int
    hits_at_k: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float


def load_examples(path: Path = EXAMPLES_PATH) -> list[RetrievalExample]:
    """Load, validate, and de-duplicate the synthetic evaluation queries."""

    raw_examples = json.loads(path.read_text(encoding="utf-8"))
    examples = [RetrievalExample.model_validate(item) for item in raw_examples]
    query_ids = [example.query_id for example in examples]
    duplicates = sorted({key for key in query_ids if query_ids.count(key) > 1})

    if duplicates:
        raise ValueError(f"Duplicate query IDs in {path.name}: {', '.join(duplicates)}")

    return examples


def evaluate_query(
    retriever: MosaicRetriever,
    example: RetrievalExample,
    top_k: int = DEFAULT_TOP_K,
    max_per_source: int = DEFAULT_MAX_PER_SOURCE,
) -> QueryEvaluation:
    """Retrieve for one example and record whether an expected source appears."""

    result = retriever.retrieve(
        example.query, top_k=top_k, max_per_source=max_per_source
    )
    retrieved = [inventory_source_id(retrieved.record) for retrieved in result.records]
    expected = set(example.expected_source_ids)
    first_hit_rank = next(
        (
            rank
            for rank, source_id in enumerate(retrieved, start=1)
            if source_id in expected
        ),
        None,
    )

    return QueryEvaluation(
        query_id=example.query_id,
        query=example.query,
        expected_source_ids=example.expected_source_ids,
        retrieved_source_ids=retrieved,
        first_hit_rank=first_hit_rank,
    )


def evaluate_examples(
    retriever: MosaicRetriever,
    examples: list[RetrievalExample],
    top_k: int = DEFAULT_TOP_K,
    max_per_source: int = DEFAULT_MAX_PER_SOURCE,
) -> list[QueryEvaluation]:
    """Evaluate every example, preserving the input order."""

    return [
        evaluate_query(retriever, example, top_k, max_per_source)
        for example in examples
    ]


def summarize(evaluations: list[QueryEvaluation]) -> EvaluationSummary:
    """Compute hit rate and the mean reciprocal rank of the successful matches."""

    ranks = [
        evaluation.first_hit_rank
        for evaluation in evaluations
        if evaluation.first_hit_rank is not None
    ]
    evaluated = len(evaluations)

    return EvaluationSummary(
        queries_evaluated=evaluated,
        hits_at_k=len(ranks),
        hit_rate_at_k=len(ranks) / evaluated if evaluated else 0.0,
        mean_reciprocal_rank=sum(1 / rank for rank in ranks) / len(ranks)
        if ranks
        else 0.0,
    )


def print_report(
    evaluations: list[QueryEvaluation],
    summary: EvaluationSummary,
    top_k: int = DEFAULT_TOP_K,
) -> None:
    """Print metrics and per-query outcomes without any private record text."""

    print(f"Queries evaluated: {summary.queries_evaluated}")
    print(f"Hits at {top_k}: {summary.hits_at_k}")
    print(f"Hit rate at {top_k}: {summary.hit_rate_at_k:.2f}")
    print(f"Mean reciprocal rank (hits only): {summary.mean_reciprocal_rank:.3f}")
    print()

    for evaluation in evaluations:
        outcome = "HIT" if evaluation.hit else "MISS"
        rank = f"rank={evaluation.first_hit_rank}" if evaluation.hit else "rank=-"
        retrieved = ", ".join(evaluation.retrieved_source_ids) or "(none)"
        print(f"{evaluation.query_id}: {outcome} {rank} | retrieved: {retrieved}")

    misses = [evaluation for evaluation in evaluations if not evaluation.hit]

    print("\nMisses:")

    if not misses:
        print("  (none)")
        return

    for evaluation in misses:
        print(f"  {evaluation.query_id}: {evaluation.query}")


def main() -> None:
    """Evaluate the synthetic query set against the already-built local index."""

    examples = load_examples()
    embedding_model = LocalEmbeddingModel()

    with MosaicVectorStore() as store:
        if not store.collection_exists():
            raise RuntimeError(
                f"Collection '{store.collection_name}' was not found at {store.path}. "
                "Build it first with: uv run python -m mosaic_pathway.vector_store"
            )

        evaluations = evaluate_examples(
            MosaicRetriever(embedding_model, store), examples
        )

    print_report(evaluations, summarize(evaluations))


if __name__ == "__main__":
    main()
