"""Run the end-to-end pathway workflow across the synthetic evaluation cases."""

import json
from pathlib import Path

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.generation import AzureOpenAIPathwayGenerator
from mosaic_pathway.knowledge_base import PROJECT_ROOT
from mosaic_pathway.models import EvaluationCase, GroundedPathwayResult
from mosaic_pathway.pathway_evaluation import (
    EvaluationReport,
    PathwayEvaluationResult,
    evaluate_grounded_pathway,
    summarize_evaluations,
)
from mosaic_pathway.rag import MosaicPathwayService
from mosaic_pathway.retrieval import MosaicRetriever
from mosaic_pathway.settings import load_settings
from mosaic_pathway.vector_store import MosaicVectorStore

CASES_DIR = PROJECT_ROOT / "examples" / "evaluation"
EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
GROUNDED_RESULTS_DIR = EVALUATION_DIR / "grounded_results"
REPORT_PATH = EVALUATION_DIR / "deterministic_report.json"


def load_cases(directory: Path = CASES_DIR) -> list[EvaluationCase]:
    """Load every synthetic case, ordered by filename, rejecting duplicate IDs."""

    if not directory.is_dir():
        raise RuntimeError(f"Evaluation cases directory was not found at {directory}.")

    paths = sorted(directory.glob("*.json"))

    if not paths:
        raise RuntimeError(f"No evaluation cases were found in {directory}.")

    cases = [
        EvaluationCase.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    case_ids = [case.case_id for case in cases]
    duplicates = sorted({key for key in case_ids if case_ids.count(key) > 1})

    if duplicates:
        raise ValueError(f"Duplicate case IDs in {directory}: {', '.join(duplicates)}")

    return cases


def save_grounded_result(
    case_id: str,
    result: GroundedPathwayResult,
    directory: Path = GROUNDED_RESULTS_DIR,
) -> Path:
    """Write the private grounded result to the ignored evaluation directory."""

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{case_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    return path


def generate_and_evaluate(
    service: MosaicPathwayService, cases: list[EvaluationCase]
) -> list[PathwayEvaluationResult]:
    """Generate one pathway per case, persist it privately, then evaluate it."""

    evaluations = []

    for case in cases:
        result = service.generate_pathway(case.intake)
        save_grounded_result(case.case_id, result)
        evaluations.append(evaluate_grounded_pathway(case.case_id, result))

    return evaluations


def print_report(report: EvaluationReport) -> None:
    """Print outcomes only, never retrieved passages or generated pathway text."""

    for result in report.results:
        outcome = "PASS" if result.passed else "FAIL"
        failures = ", ".join(result.failed_check_names) or "-"
        print(f"{result.case_id}: {outcome} | failed: {failures}")

    print(f"\nCases passed: {report.cases_passed}/{report.cases_evaluated}")
    print(
        f"Check pass rate: {report.check_pass_rate:.2f} "
        f"({report.checks_passed}/{report.checks_evaluated})"
    )
    print(f"\nGrounded results: {GROUNDED_RESULTS_DIR}")
    print(f"Deterministic report: {REPORT_PATH}")


def main() -> None:
    """Evaluate every synthetic case against the already-built local index."""

    cases = load_cases()
    generator = AzureOpenAIPathwayGenerator(load_settings())

    with MosaicVectorStore() as store:
        if not store.collection_exists():
            raise RuntimeError(
                f"Collection '{store.collection_name}' was not found at {store.path}. "
                "Build it first with: uv run python -m mosaic_pathway.vector_store"
            )

        service = MosaicPathwayService(
            MosaicRetriever(LocalEmbeddingModel(), store), generator
        )
        evaluations = generate_and_evaluate(service, cases)

    report = summarize_evaluations(evaluations)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print_report(report)


if __name__ == "__main__":
    main()
