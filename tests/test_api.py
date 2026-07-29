from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from typing import Any

import pytest
from conftest import make_source_record
from fastapi.testclient import TestClient

from mosaic_pathway.api import (
    PREVIEW_CHARACTERS,
    create_app,
    parse_allowed_origins,
    summarize_sources,
)
from mosaic_pathway.models import (
    CommunitySuggestion,
    FamilyIntake,
    GroundedPathwayResult,
    LearningPathway,
    ResourceRecommendation,
    RetrievedRecord,
    RhythmPractice,
)
from mosaic_pathway.rag import GroundingError, MosaicPathwayService

LONG_TEXT = "Synthetic Mosaic guidance sentence. " * 40
SECRET_MARKER = "PRIVATE-TAIL-MARKER"

VALID_REQUEST: dict[str, Any] = {
    "children": [
        {
            "label": "older child",
            "age": 10,
            "interests": ["animals", "drawing"],
            "learning_needs": ["movement breaks"],
        }
    ],
    "leaving_behind": ["rigid daily schedules"],
    "wants_to_preserve": ["reading together"],
    "wants_to_add": ["more outdoor learning"],
    "family_values": ["curiosity"],
    "practical_constraints": ["moderate budget"],
    "additional_context": "We are new to self-directed learning.",
}


def build_pathway() -> LearningPathway:
    return LearningPathway(
        family_reflection="Your family values curiosity and outdoor time.",
        starting_rhythm=[
            RhythmPractice(
                timing="Daily",
                practice="Take one short curiosity walk.",
                why_it_fits="It adds outdoor time without a rigid schedule.",
            ),
            RhythmPractice(
                timing="Once this week",
                practice="Visit the local library.",
                why_it_fits="It opens access to interest-led resources.",
            ),
        ],
        resources=[
            ResourceRecommendation(
                title="Create an interest catalog",
                why_it_fits="It honors the child's interest in animals.",
                source_id="synthetic-0001",
            ),
            ResourceRecommendation(
                title="Build a bored list together",
                why_it_fits="It supports autonomy on unstructured days.",
                source_id="synthetic-0002",
            ),
        ],
        community_suggestion=CommunitySuggestion(
            suggestion="You might attend one informal meetup.",
            why_it_fits="It is a low-pressure way to connect.",
            source_id="synthetic-0001",
        ),
        closing_note="Go gently and follow what your family enjoys.",
    )


def build_result(intake: FamilyIntake) -> GroundedPathwayResult:
    return GroundedPathwayResult(
        intake=intake,
        retrieval_query="synthetic retrieval query",
        retrieved_records=[
            RetrievedRecord(
                record=make_source_record(
                    "synthetic-0001", text=LONG_TEXT + SECRET_MARKER
                ),
                score=0.8123456,
            ),
            RetrievedRecord(
                record=make_source_record("synthetic-0002"),
                score=0.7,
            ),
        ],
        pathway=build_pathway(),
    )


class FakePathwayService:
    """Returns a fixed result, or raises, without touching any real dependency."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[FamilyIntake] = []

    def generate_pathway(self, intake: FamilyIntake) -> GroundedPathwayResult:
        self.calls.append(intake)

        if self.error is not None:
            raise self.error

        return build_result(intake)


def build_client(
    service: FakePathwayService | None = None,
    allowed_origins: list[str] | None = None,
) -> tuple[TestClient, FakePathwayService]:
    fake = service or FakePathwayService()

    def provider() -> AbstractContextManager[MosaicPathwayService]:
        return nullcontext(fake)  # type: ignore[arg-type]

    app = create_app(
        service_provider=provider,
        allowed_origins=allowed_origins or ["http://localhost:5173"],
    )

    return TestClient(app), fake


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://localhost:5173", ["http://localhost:5173"]),
        (" http://a.test , http://b.test ", ["http://a.test", "http://b.test"]),
        ("http://a.test,,http://a.test", ["http://a.test"]),
        ("", ["http://localhost:5173", "http://localhost:3000"]),
        ("   ", ["http://localhost:5173", "http://localhost:3000"]),
    ],
)
def test_parse_allowed_origins(value: str, expected: list[str]) -> None:
    assert parse_allowed_origins(value) == expected


def test_health_returns_ok_without_touching_the_service() -> None:
    client, fake = build_client()

    with client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake.calls == []


def test_valid_request_returns_the_generated_pathway() -> None:
    client, _ = build_client()

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 200

    body = response.json()

    assert body["pathway"]["family_reflection"].startswith("Your family values")
    assert len(body["pathway"]["resources"]) == 2


def test_request_maps_into_a_family_intake_exactly_once() -> None:
    client, fake = build_client()

    with client:
        client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert len(fake.calls) == 1

    intake = fake.calls[0]

    assert isinstance(intake, FamilyIntake)
    assert intake.children[0].label == "older child"
    assert intake.children[0].interests == ["animals", "drawing"]
    assert intake.family_values == ["curiosity"]


def test_response_summarizes_sources_in_retrieval_order() -> None:
    client, _ = build_client()

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    sources = response.json()["sources"]

    assert [source["source_id"] for source in sources] == [
        "synthetic-0001",
        "synthetic-0002",
    ]
    assert sources[0]["title"] == "Synthetic source synthetic-0001"
    assert sources[0]["score"] == pytest.approx(0.8123)


def test_response_never_returns_the_complete_source_text() -> None:
    client, _ = build_client()

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert SECRET_MARKER not in response.text

    preview = response.json()["sources"][0]["preview"]

    assert len(preview) <= PREVIEW_CHARACTERS + len("...")
    assert preview.endswith("...")


def test_malformed_request_returns_422() -> None:
    client, fake = build_client()

    with client:
        response = client.post("/api/v1/pathways", json={"children": []})

    assert response.status_code == 422
    assert fake.calls == []


def test_authentication_failure_maps_to_503() -> None:
    client, _ = build_client(
        FakePathwayService(RuntimeError("Tenant provided in token does not match"))
    )

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "azure_authentication_failed"


def test_missing_service_maps_to_503() -> None:
    @contextmanager
    def failing_provider() -> Iterator[MosaicPathwayService]:
        raise RuntimeError("The local collection 'mosaic_sources' was not found.")
        yield  # pragma: no cover - unreachable, keeps this a generator

    app = create_app(
        service_provider=failing_provider, allowed_origins=["http://localhost:5173"]
    )

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "service_unavailable"
    assert "mosaic_sources" in response.json()["detail"]["message"]


def test_generation_failure_maps_to_502() -> None:
    client, _ = build_client(
        FakePathwayService(RuntimeError("Model did not return a valid LearningPathway"))
    )

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "pathway_generation_failed"


def test_ungrounded_pathway_maps_to_502() -> None:
    client, _ = build_client(FakePathwayService(GroundingError("cited unknown ids")))

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "pathway_not_grounded"


def test_empty_retrieval_maps_to_422() -> None:
    client, _ = build_client(
        FakePathwayService(
            RuntimeError("Retrieval returned no Mosaic records for this family intake.")
        )
    )

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "no_sources_retrieved"


def test_unexpected_error_hides_the_traceback() -> None:
    client, _ = build_client(FakePathwayService(TypeError("secret internal detail")))

    with client:
        response = client.post("/api/v1/pathways", json=VALID_REQUEST)

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


def test_configured_origin_receives_the_cors_header() -> None:
    client, _ = build_client(allowed_origins=["http://localhost:5173"])

    with client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unconfigured_origin_receives_no_cors_header() -> None:
    client, _ = build_client(allowed_origins=["http://localhost:5173"])

    with client:
        response = client.get("/health", headers={"Origin": "http://evil.test"})

    assert "access-control-allow-origin" not in response.headers


def test_summarize_sources_truncates_and_rounds() -> None:
    records = [
        RetrievedRecord(
            record=make_source_record("synthetic-0003", text=LONG_TEXT),
            score=0.123456789,
        )
    ]

    summaries = summarize_sources(records)

    assert summaries[0].score == pytest.approx(0.1235)
    assert len(summaries[0].preview) <= PREVIEW_CHARACTERS + len("...")
