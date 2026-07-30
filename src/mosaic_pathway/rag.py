"""End-to-end grounded pathway generation over the local Mosaic knowledge base."""

from mosaic_pathway.generation import ClaudePathwayGenerator
from mosaic_pathway.models import (
    FamilyIntake,
    GroundedPathwayResult,
    LearningPathway,
    RetrievedRecord,
)
from mosaic_pathway.query_builder import build_retrieval_query
from mosaic_pathway.retrieval import MosaicRetriever, inventory_source_id

DEFAULT_TOP_K = 6
DEFAULT_MAX_PER_SOURCE = 2


class GroundingError(RuntimeError):
    """Raised when a generated pathway cites a passage that was not retrieved."""


def build_context(records: list[RetrievedRecord]) -> list[dict[str, str]]:
    """Convert retrieved records into the context the generator expects."""

    return [
        {
            "source_id": retrieved.record.source_id,
            "inventory_source_id": inventory_source_id(retrieved.record),
            "title": retrieved.record.title,
            "text": retrieved.record.text,
        }
        for retrieved in records
    ]


def cited_source_ids(pathway: LearningPathway) -> list[str]:
    """Collect every non-empty source ID the pathway references."""

    cited = [resource.source_id for resource in pathway.resources]
    cited.append(pathway.community_suggestion.source_id or "")

    return [source_id for source_id in cited if source_id.strip()]


class MosaicPathwayService:
    """Retrieves Mosaic passages and generates a pathway grounded in them."""

    def __init__(
        self,
        retriever: MosaicRetriever,
        generator: ClaudePathwayGenerator,
    ) -> None:
        self.retriever = retriever
        self.generator = generator

    def generate_pathway(
        self,
        intake: FamilyIntake,
        top_k: int = DEFAULT_TOP_K,
        max_per_source: int = DEFAULT_MAX_PER_SOURCE,
    ) -> GroundedPathwayResult:
        """Retrieve, generate, and verify that every citation was retrieved."""

        if top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        if max_per_source < 1:
            raise ValueError("max_per_source must be a positive integer.")

        query = build_retrieval_query(intake)
        result = self.retriever.retrieve(
            query, top_k=top_k, max_per_source=max_per_source
        )

        if not result.records:
            raise RuntimeError(
                "Retrieval returned no Mosaic records for this family intake."
            )

        pathway = self.generator.generate(intake, build_context(result.records))
        retrieved_ids = {retrieved.record.source_id for retrieved in result.records}
        missing = sorted(set(cited_source_ids(pathway)) - retrieved_ids)

        if missing:
            raise GroundingError(
                "The generated pathway cited source IDs that were not retrieved: "
                f"{', '.join(missing)}"
            )

        return GroundedPathwayResult(
            intake=intake,
            retrieval_query=query,
            retrieved_records=result.records,
            pathway=pathway,
        )
