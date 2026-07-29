"""Generate one end-to-end grounded pathway for an example family."""

import json

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.generation import AzureOpenAIPathwayGenerator
from mosaic_pathway.knowledge_base import PROJECT_ROOT
from mosaic_pathway.models import FamilyIntake
from mosaic_pathway.rag import MosaicPathwayService
from mosaic_pathway.retrieval import MosaicRetriever
from mosaic_pathway.settings import load_settings
from mosaic_pathway.vector_store import MosaicVectorStore

FAMILY_PATH = PROJECT_ROOT / "examples" / "family_nature.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "manual" / "grounded_pathway_output.json"


def main() -> None:
    intake = FamilyIntake.model_validate(
        json.loads(FAMILY_PATH.read_text(encoding="utf-8"))
    )
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
        result = service.generate_pathway(intake)

    print("RETRIEVAL QUERY")
    print(result.retrieval_query)
    print("\nRETRIEVED RECORDS")

    for rank, retrieved in enumerate(result.retrieved_records, start=1):
        print(
            f"  {rank}. score={retrieved.score:.3f} "
            f"{retrieved.record.source_id} | {retrieved.record.title}"
        )

    print("\nPATHWAY")
    print(result.pathway.model_dump_json(indent=2))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    print(f"\nSaved grounded result to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
