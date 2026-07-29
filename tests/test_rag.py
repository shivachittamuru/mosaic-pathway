import pytest
from conftest import make_source_record

from mosaic_pathway.models import (
    ChildProfile,
    CommunitySuggestion,
    FamilyIntake,
    LearningPathway,
    ResourceRecommendation,
    RetrievalResult,
    RetrievedRecord,
    RhythmPractice,
)
from mosaic_pathway.query_builder import build_retrieval_query
from mosaic_pathway.rag import GroundingError, MosaicPathwayService, build_context


class FakeRetriever:
    """Returns fixed records and records how it was called."""

    def __init__(self, chunk_ids: list[str]) -> None:
        self.chunk_ids = chunk_ids
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
                for index, chunk_id in enumerate(self.chunk_ids)
            ],
        )


class FakeGenerator:
    """Returns a fixed pathway and records the context it received."""

    def __init__(self, pathway: LearningPathway) -> None:
        self.pathway = pathway
        self.calls: list[tuple[FamilyIntake, list[dict[str, str]]]] = []

    def generate(
        self, intake: FamilyIntake, context: list[dict[str, str]]
    ) -> LearningPathway:
        self.calls.append((intake, context))

        return self.pathway


def build_intake() -> FamilyIntake:
    return FamilyIntake(
        children=[ChildProfile(label="only child", age=9, interests=["music"])],
        leaving_behind=["worksheets"],
        wants_to_add=["more choice"],
        family_values=["creativity"],
    )


def build_pathway(
    resource_source_ids: list[str], community_source_id: str | None
) -> LearningPathway:
    return LearningPathway(
        family_reflection="Your family values creativity and choice.",
        starting_rhythm=[
            RhythmPractice(
                timing="Daily",
                practice="Follow one shared interest for twenty minutes.",
                why_it_fits="It protects curiosity without a rigid schedule.",
            ),
            RhythmPractice(
                timing="Once this week",
                practice="Visit the local library.",
                why_it_fits="It opens access to interest-led resources.",
            ),
        ],
        resources=[
            ResourceRecommendation(
                title=f"Resource {index}",
                why_it_fits="It matches the family's stated interests.",
                source_id=source_id,
            )
            for index, source_id in enumerate(resource_source_ids, start=1)
        ],
        community_suggestion=CommunitySuggestion(
            suggestion="You might attend one informal meetup.",
            why_it_fits="It is a low-pressure way to connect.",
            source_id=community_source_id,
        ),
        closing_note="Go gently and follow what your family enjoys.",
    )


def build_service(
    chunk_ids: list[str], pathway: LearningPathway
) -> tuple[MosaicPathwayService, FakeRetriever, FakeGenerator]:
    retriever = FakeRetriever(chunk_ids)
    generator = FakeGenerator(pathway)
    service = MosaicPathwayService(retriever, generator)  # type: ignore[arg-type]

    return service, retriever, generator


def test_build_context_uses_exact_chunk_ids_and_source_level_ids() -> None:
    records = [
        RetrievedRecord(
            record=make_source_record("podcast-affording-path-0016"), score=1.0
        )
    ]

    assert build_context(records) == [
        {
            "source_id": "podcast-affording-path-0016",
            "inventory_source_id": "podcast-affording-path",
            "title": "Synthetic source podcast-affording-path-0016",
            "text": "Synthetic body text for record podcast-affording-path-0016.",
        }
    ]


def test_generate_pathway_returns_a_grounded_result() -> None:
    chunk_ids = ["mosaic-web-resources-0001", "podcast-affording-path-0016"]
    pathway = build_pathway(chunk_ids, "mosaic-web-resources-0001")
    service, retriever, generator = build_service(chunk_ids, pathway)
    intake = build_intake()

    result = service.generate_pathway(intake)

    assert result.intake == intake
    assert result.retrieval_query == build_retrieval_query(intake)
    assert result.pathway == pathway
    assert len(generator.calls) == 1
    assert retriever.calls == [(build_retrieval_query(intake), 6, 2)]


def test_retriever_receives_the_configured_limits() -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    service, retriever, _ = build_service(chunk_ids, build_pathway(chunk_ids, None))

    service.generate_pathway(build_intake(), top_k=3, max_per_source=1)

    assert retriever.calls[0][1:] == (3, 1)


def test_retrieved_record_order_is_preserved() -> None:
    chunk_ids = [
        "podcast-school-harm-0003",
        "mosaic-web-resources-0001",
        "podcast-affording-path-0016",
    ]
    service, _, generator = build_service(
        chunk_ids, build_pathway(chunk_ids[:2], chunk_ids[2])
    )

    result = service.generate_pathway(build_intake())

    assert [
        retrieved.record.source_id for retrieved in result.retrieved_records
    ] == chunk_ids
    assert [entry["source_id"] for entry in generator.calls[0][1]] == chunk_ids


def test_empty_retrieval_fails_before_generation() -> None:
    service, _, generator = build_service([], build_pathway(["a", "b"], None))

    with pytest.raises(RuntimeError, match="no Mosaic records"):
        service.generate_pathway(build_intake())

    assert generator.calls == []


@pytest.mark.parametrize("top_k", [0, -1])
def test_non_positive_top_k_is_rejected(top_k: int) -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    service, retriever, _ = build_service(chunk_ids, build_pathway(chunk_ids, None))

    with pytest.raises(ValueError, match="top_k"):
        service.generate_pathway(build_intake(), top_k=top_k)

    assert retriever.calls == []


@pytest.mark.parametrize("max_per_source", [0, -2])
def test_non_positive_max_per_source_is_rejected(max_per_source: int) -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    service, retriever, _ = build_service(chunk_ids, build_pathway(chunk_ids, None))

    with pytest.raises(ValueError, match="max_per_source"):
        service.generate_pathway(build_intake(), max_per_source=max_per_source)

    assert retriever.calls == []


def test_resource_citing_an_unretrieved_source_is_rejected() -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    pathway = build_pathway(["mosaic-web-resources-0001", "invented-source-9999"], None)
    service, _, _ = build_service(chunk_ids, pathway)

    with pytest.raises(GroundingError, match="invented-source-9999"):
        service.generate_pathway(build_intake())


def test_community_suggestion_citing_an_unretrieved_source_is_rejected() -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    pathway = build_pathway(chunk_ids, "invented-source-9999")
    service, _, _ = build_service(chunk_ids, pathway)

    with pytest.raises(GroundingError, match="invented-source-9999"):
        service.generate_pathway(build_intake())


def test_missing_community_source_id_is_allowed() -> None:
    chunk_ids = ["mosaic-web-resources-0001", "mosaic-web-resources-0002"]
    service, _, _ = build_service(chunk_ids, build_pathway(chunk_ids, None))

    assert (
        service.generate_pathway(build_intake()).pathway.community_suggestion.source_id
        is None
    )
