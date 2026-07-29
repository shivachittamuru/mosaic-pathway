from conftest import make_source_record

from mosaic_pathway.models import (
    ChildProfile,
    CommunitySuggestion,
    FamilyIntake,
    GroundedPathwayResult,
    LearningPathway,
    ResourceRecommendation,
    RetrievedRecord,
    RhythmPractice,
)
from mosaic_pathway.pathway_evaluation import (
    MAX_TOTAL_WORDS,
    evaluate_grounded_pathway,
    summarize_evaluations,
)

RESOURCE_CHUNK_ID = "mosaic-web-resources-0001"
COMMUNITY_CHUNK_ID = "podcast-affording-path-0016"

EXPECTED_CHECK_ORDER = [
    "required_sections_populated",
    "resource_count_within_range",
    "resource_source_ids_grounded",
    "community_source_id_grounded",
    "no_citations_in_prose",
    "no_duplicate_recommendations",
    "word_count_guardrails",
    "no_prohibited_phrases",
    "interest_personalization_indicator",
    "family_context_personalization_indicator",
]


def make_intake(**overrides: object) -> FamilyIntake:
    defaults: dict[str, object] = {
        "children": [
            ChildProfile(
                label="younger child",
                age=7,
                interests=["animals", "drawing"],
            )
        ],
        "leaving_behind": ["frequent worksheets"],
        "wants_to_preserve": ["reading together"],
        "wants_to_add": ["a calmer rhythm"],
        "family_values": ["curiosity"],
        "practical_constraints": ["moderate budget"],
    }

    return FamilyIntake.model_validate(defaults | overrides)


def make_resources(
    titles: list[str] | None = None,
    rationale: str = "It gives your child a gentle way to notice animals nearby.",
    source_ids: list[str] | None = None,
) -> list[ResourceRecommendation]:
    resolved_titles = titles or ["Observation Journal", "Family Reading Basket"]
    resolved_ids = source_ids or [RESOURCE_CHUNK_ID] * len(resolved_titles)

    return [
        ResourceRecommendation(title=title, why_it_fits=rationale, source_id=source_id)
        for title, source_id in zip(resolved_titles, resolved_ids, strict=True)
    ]


def make_pathway(
    family_reflection: str = (
        "Your family cares about curiosity and unhurried days. Your younger child "
        "lights up around animals and drawing."
    ),
    rhythm_rationale: str = "Short outdoor time suits a calm rhythm.",
    resources: list[ResourceRecommendation] | None = None,
    community_source_id: str | None = COMMUNITY_CHUNK_ID,
    community_rationale: str = "It offers connection without a commitment.",
    closing_note: str = "Go gently and follow what your family enjoys.",
) -> LearningPathway:
    return LearningPathway(
        family_reflection=family_reflection,
        starting_rhythm=[
            RhythmPractice(
                timing="Daily",
                practice="Spend twenty quiet minutes outdoors together.",
                why_it_fits=rhythm_rationale,
            ),
            RhythmPractice(
                timing="Once this week",
                practice="Borrow library books about animals.",
                why_it_fits=rhythm_rationale,
            ),
        ],
        resources=resources if resources is not None else make_resources(),
        community_suggestion=CommunitySuggestion(
            suggestion="You might join one relaxed park meetup this month.",
            why_it_fits=community_rationale,
            source_id=community_source_id,
        ),
        closing_note=closing_note,
    )


def make_result(
    pathway: LearningPathway | None = None,
    intake: FamilyIntake | None = None,
) -> GroundedPathwayResult:
    return GroundedPathwayResult(
        intake=intake or make_intake(),
        retrieval_query="a synthetic retrieval query",
        retrieved_records=[
            RetrievedRecord(record=make_source_record(chunk_id), score=score)
            for chunk_id, score in (
                (RESOURCE_CHUNK_ID, 0.9),
                (COMMUNITY_CHUNK_ID, 0.8),
            )
        ],
        pathway=pathway or make_pathway(),
    )


def failures(result: GroundedPathwayResult) -> list[str]:
    return evaluate_grounded_pathway("case", result).failed_check_names


def detail_for(result: GroundedPathwayResult, check_name: str) -> str:
    evaluation = evaluate_grounded_pathway("case", result)
    check = next(item for item in evaluation.checks if item.check_name == check_name)

    return check.details or ""


def long_text(words: int) -> str:
    return " ".join(["gentle"] * words)


def test_a_well_formed_pathway_passes_every_check() -> None:
    evaluation = evaluate_grounded_pathway("gentle-transition", make_result())

    assert evaluation.case_id == "gentle-transition"
    assert evaluation.passed
    assert evaluation.failed_check_names == []
    assert len(evaluation.checks) == len(EXPECTED_CHECK_ORDER)


def test_checks_always_run_in_the_same_order() -> None:
    first = evaluate_grounded_pathway("case", make_result())
    second = evaluate_grounded_pathway("case", make_result())

    assert [check.check_name for check in first.checks] == EXPECTED_CHECK_ORDER
    assert first.model_dump() == second.model_dump()


def test_empty_required_content_fails() -> None:
    result = make_result(make_pathway(closing_note="   "))

    assert "required_sections_populated" in failures(result)
    assert "closing_note" in detail_for(result, "required_sections_populated")


def test_resource_citing_an_unretrieved_chunk_fails() -> None:
    resources = make_resources(
        titles=["Observation Journal", "Family Reading Basket"],
        source_ids=[RESOURCE_CHUNK_ID, "invented-source-9999"],
    )
    result = make_result(make_pathway(resources=resources))

    assert "resource_source_ids_grounded" in failures(result)
    assert "invented-source-9999" in detail_for(result, "resource_source_ids_grounded")


def test_community_suggestion_citing_an_unretrieved_chunk_fails() -> None:
    result = make_result(make_pathway(community_source_id="invented-source-9999"))

    assert "community_source_id_grounded" in failures(result)


def test_missing_community_source_id_is_accepted() -> None:
    result = make_result(make_pathway(community_source_id=None))

    assert "community_source_id_grounded" not in failures(result)


def test_bracketed_citation_in_prose_fails() -> None:
    result = make_result(make_pathway(closing_note="Go gently [see source 4]."))

    assert "no_citations_in_prose" in failures(result)


def test_record_id_leaking_into_prose_fails() -> None:
    result = make_result(
        make_pathway(closing_note=f"Go gently, as {RESOURCE_CHUNK_ID} suggests.")
    )

    assert "no_citations_in_prose" in failures(result)
    assert RESOURCE_CHUNK_ID in detail_for(result, "no_citations_in_prose")


def test_exact_duplicate_recommendations_fail() -> None:
    resources = make_resources(titles=["Observation Journal", "Observation Journal"])
    result = make_result(make_pathway(resources=resources))

    assert "no_duplicate_recommendations" in failures(result)


def test_excessive_total_length_fails() -> None:
    result = make_result(
        make_pathway(
            family_reflection=long_text(300),
            rhythm_rationale=long_text(200),
            resources=make_resources(rationale=long_text(200)),
            community_rationale=long_text(200),
            closing_note=long_text(200),
        )
    )

    assert "word_count_guardrails" in failures(result)
    assert f"limit {MAX_TOTAL_WORDS}" in detail_for(result, "word_count_guardrails")


def test_prohibited_prescriptive_phrase_fails() -> None:
    result = make_result(
        make_pathway(closing_note="You must follow this plan every single day.")
    )

    assert "no_prohibited_phrases" in failures(result)
    assert "you must" in detail_for(result, "no_prohibited_phrases")


def test_interest_indicator_passes_when_an_interest_appears() -> None:
    result = make_result()

    assert "interest_personalization_indicator" not in failures(result)
    assert "animals" in detail_for(result, "interest_personalization_indicator")


def test_interest_indicator_fails_when_no_interest_appears() -> None:
    intake = make_intake(
        children=[ChildProfile(label="only child", age=9, interests=["astronomy"])]
    )
    result = make_result(intake=intake)

    assert "interest_personalization_indicator" in failures(result)


def test_family_context_indicator_reports_the_matched_phrase() -> None:
    result = make_result()

    assert "family_context_personalization_indicator" not in failures(result)
    assert "curiosity" in detail_for(result, "family_context_personalization_indicator")


def test_family_context_indicator_fails_when_nothing_matches() -> None:
    intake = make_intake(
        wants_to_preserve=[],
        practical_constraints=[],
        family_values=["stewardship"],
        wants_to_add=["woodworking"],
    )
    result = make_result(intake=intake)

    assert "family_context_personalization_indicator" in failures(result)


def test_report_aggregates_cases_and_checks() -> None:
    passing = evaluate_grounded_pathway("passing", make_result())
    failing = evaluate_grounded_pathway(
        "failing", make_result(make_pathway(closing_note="   "))
    )
    report = summarize_evaluations([passing, failing, passing])

    assert report.cases_evaluated == 3
    assert report.cases_passed == 2
    assert report.checks_evaluated == 30
    assert report.checks_passed == 30 - len(failing.failed_check_names)
    assert report.check_pass_rate == report.checks_passed / 30


def test_empty_report_has_a_zero_pass_rate() -> None:
    report = summarize_evaluations([])

    assert report.cases_evaluated == 0
    assert report.check_pass_rate == 0.0
