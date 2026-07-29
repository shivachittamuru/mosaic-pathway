"""Print local retrieval results for a few synthetic family queries."""

from mosaic_pathway.embeddings import LocalEmbeddingModel
from mosaic_pathway.retrieval import MosaicRetriever
from mosaic_pathway.vector_store import MosaicVectorStore

PREVIEW_CHARS = 160
TOP_K = 5

DEMO_QUERIES = [
    "We want a gentle transition away from rigid schooling without overwhelming our kids.",
    "Our neurodivergent teenager wants interest-led learning and a community of peers.",
    "We are looking for affordable STEM activities we can do on a tight budget.",
]


def preview(text: str) -> str:
    """Return a short, truncated snippet so full private chunks are never printed."""

    snippet = " ".join(text.split())[:PREVIEW_CHARS]

    return f"{snippet}..." if len(text) > PREVIEW_CHARS else snippet


def main() -> None:
    embedding_model = LocalEmbeddingModel()

    with MosaicVectorStore() as store:
        retriever = MosaicRetriever(embedding_model, store)

        for query in DEMO_QUERIES:
            result = retriever.retrieve(query, top_k=TOP_K)

            print(f"\nQuery: {query}")

            for rank, retrieved in enumerate(result.records, start=1):
                record = retrieved.record
                print(
                    f"  {rank}. score={retrieved.score:.3f} "
                    f"{record.source_id} | {record.title}"
                )
                print(f"     {preview(record.text)}")


if __name__ == "__main__":
    main()
