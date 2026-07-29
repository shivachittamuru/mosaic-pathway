from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChildProfile(BaseModel):
    """Information needed to personalize suggestions for one child."""

    label: str = Field(description="A non-identifying label such as 'older child'.")
    age: int = Field(ge=2, le=21)
    interests: list[str] = Field(min_length=1)
    learning_needs: list[str] = Field(default_factory=list)


class FamilyIntake(BaseModel):
    """Structured information collected from a family."""

    children: list[ChildProfile] = Field(min_length=1)

    leaving_behind: list[str] = Field(
        min_length=1,
        description="Aspects of conventional schooling the family wants to leave behind.",
    )
    wants_to_preserve: list[str] = Field(
        default_factory=list,
        description="Aspects of the family's current experience they want to preserve.",
    )
    wants_to_add: list[str] = Field(
        min_length=1,
        description="Experiences, values, or practices the family wants to add.",
    )

    family_values: list[str] = Field(min_length=1)
    practical_constraints: list[str] = Field(default_factory=list)
    additional_context: str | None = None


class SourceRecord(BaseModel):
    """A cleaned piece of Mosaic knowledge prepared for retrieval."""

    source_id: str
    title: str
    source_file: str

    content_type: Literal[
        "framework",
        "practical_guidance",
        "activity",
        "resource",
        "community",
        "story",
    ]

    authority_type: Literal[
        "mosaic_framework",
        "mosaic_guidance",
        "lived_experience",
        "external_resource",
    ]

    topics: list[str] = Field(min_length=1)
    age_min: int | None = Field(default=None, ge=0, le=21)
    age_max: int | None = Field(default=None, ge=0, le=21)

    text: str = Field(min_length=20)

    @model_validator(mode="after")
    def validate_age_range(self) -> "SourceRecord":
        if (
            self.age_min is not None
            and self.age_max is not None
            and self.age_min > self.age_max
        ):
            raise ValueError("age_min cannot be greater than age_max")

        return self


class RhythmPractice(BaseModel):
    """One concrete practice suggested for the family's first two weeks."""

    timing: str = Field(
        description="A simple cadence such as 'Daily' or 'Twice this week'."
    )
    practice: str
    why_it_fits: str


class ResourceRecommendation(BaseModel):
    """A Mosaic-grounded resource or activity recommendation."""

    title: str
    why_it_fits: str
    source_id: str
    url: str | None = None


class CommunitySuggestion(BaseModel):
    """A low-pressure suggestion for connecting with a community."""

    suggestion: str
    why_it_fits: str
    source_id: str | None = None


class LearningPathway(BaseModel):
    """The structured content rendered as a one-page family pathway."""

    family_reflection: str = Field(
        description="A warm reflection of the family's values and intentions."
    )

    starting_rhythm: list[RhythmPractice] = Field(
        min_length=2,
        max_length=6,
    )

    resources: list[ResourceRecommendation] = Field(
        min_length=2,
        max_length=3,
    )

    community_suggestion: CommunitySuggestion

    closing_note: str = Field(
        description="A short, warm, non-prescriptive closing message."
    )
