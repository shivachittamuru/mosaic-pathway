from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


ContentType = Literal[
    "framework",
    "practical_guidance",
    "activity",
    "resource",
    "community",
    "story",
]

AuthorityType = Literal[
    "mosaic_framework",
    "mosaic_guidance",
    "lived_experience",
    "external_resource",
]


class SourceRecord(BaseModel):
    """A cleaned piece of Mosaic knowledge prepared for retrieval."""

    source_id: str
    title: str
    source_file: str

    content_type: ContentType

    authority_type: AuthorityType

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


class RetrievedRecord(BaseModel):
    """One source record returned by semantic search, with its similarity score."""

    record: SourceRecord
    score: float


class RetrievalResult(BaseModel):
    """The ranked records retrieved for a single query."""

    query: str
    records: list[RetrievedRecord]


class RetrievalExample(BaseModel):
    """One synthetic query paired with the sources a good answer should cite."""

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_source_ids: list[str] = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def validate_query_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")

        return value


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


class SourceInventoryItem(BaseModel):
    """Human-reviewed description of one supplied knowledge source."""

    source_id: str = Field(min_length=3)
    filename: str = Field(min_length=3)
    title: str = Field(min_length=3)

    format: Literal["pdf", "docx"]

    content_type: Literal[
        "mixed",
        "podcast_transcript",
    ]

    primary_topics: list[str] = Field(min_length=1)
    audience: str = Field(min_length=3)

    rag_priority: Literal[
        "core",
        "situational",
        "exclude",
    ]

    authority_type: Literal[
        "mosaic_guidance",
        "expert_guidance",
        "lived_experience",
        "mixed_expert_and_lived_experience",
    ]

    requires_cleaning: bool
    notes: str = Field(min_length=10)
