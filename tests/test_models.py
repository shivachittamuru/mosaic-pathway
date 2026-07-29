import pytest
from pydantic import ValidationError

from mosaic_pathway.models import (
    ChildProfile,
    CommunitySuggestion,
    FamilyIntake,
    LearningPathway,
    ResourceRecommendation,
    RhythmPractice,
    SourceRecord,
)


def test_valid_family_intake() -> None:
    intake = FamilyIntake(
        children=[
            ChildProfile(
                label="younger child",
                age=7,
                interests=["nature", "drawing"],
            )
        ],
        leaving_behind=["rigid schedules"],
        wants_to_preserve=["reading together"],
        wants_to_add=["more outdoor exploration"],
        family_values=["curiosity", "connection"],
    )

    assert intake.children[0].age == 7
    assert "curiosity" in intake.family_values


def test_child_requires_at_least_one_interest() -> None:
    with pytest.raises(ValidationError):
        ChildProfile(
            label="child",
            age=8,
            interests=[],
        )


def test_source_record_rejects_invalid_age_range() -> None:
    with pytest.raises(ValidationError):
        SourceRecord(
            source_id="source-001",
            title="Teen College Guidance",
            source_file="college.pdf",
            content_type="practical_guidance",
            authority_type="mosaic_guidance",
            topics=["college"],
            age_min=18,
            age_max=14,
            text="This is a sufficiently long source record for testing.",
        )


def test_learning_pathway_requires_two_resources() -> None:
    with pytest.raises(ValidationError):
        LearningPathway(
            family_reflection="Your family values curiosity and time together.",
            starting_rhythm=[
                RhythmPractice(
                    timing="Daily",
                    practice="Spend twenty minutes following a shared interest.",
                    why_it_fits="It supports curiosity without creating a rigid schedule.",
                ),
                RhythmPractice(
                    timing="Once this week",
                    practice="Visit a local library.",
                    why_it_fits="It creates access to interest-led resources.",
                ),
            ],
            resources=[
                ResourceRecommendation(
                    title="Libraries as Learning Centers",
                    why_it_fits="The family wants accessible community resources.",
                    source_id="source-library",
                )
            ],
            community_suggestion=CommunitySuggestion(
                suggestion="Look for a local self-directed learning meetup.",
                why_it_fits="The family wants more connection.",
            ),
            closing_note="You might begin with what feels easiest this week.",
        )


def test_valid_learning_pathway() -> None:
    pathway = LearningPathway(
        family_reflection=(
            "Your family is looking for a gentler rhythm centered on curiosity, "
            "connection, and time outdoors."
        ),
        starting_rhythm=[
            RhythmPractice(
                timing="Daily",
                practice="Let each child choose one question to explore.",
                why_it_fits="This protects learner agency and curiosity.",
            ),
            RhythmPractice(
                timing="Twice this week",
                practice="Take an unhurried nature walk and follow what interests them.",
                why_it_fits="It connects outdoor time with self-directed exploration.",
            ),
        ],
        resources=[
            ResourceRecommendation(
                title="Libraries as Learning Centers",
                why_it_fits="Libraries provide flexible and affordable exploration.",
                source_id="source-library",
            ),
            ResourceRecommendation(
                title="Exploring STEM as a Self-Directed Learner",
                why_it_fits="It offers practical interest-led STEM ideas.",
                source_id="source-stem",
            ),
        ],
        community_suggestion=CommunitySuggestion(
            suggestion="Consider attending one local homeschool or unschooling meetup.",
            why_it_fits="It offers connection without requiring a large commitment.",
            source_id="source-community",
        ),
        closing_note=(
            "You might begin with one practice that feels natural and adjust from there."
        ),
    )

    assert len(pathway.resources) == 2
    assert len(pathway.starting_rhythm) == 2
