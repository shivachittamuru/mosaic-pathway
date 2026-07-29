"""Deterministic quality checks for generated Mosaic family pathways."""

import re

from pydantic import BaseModel, computed_field

from mosaic_pathway.models import FamilyIntake, GroundedPathwayResult, LearningPathway
from mosaic_pathway.retrieval import inventory_source_id

MIN_RESOURCES = 2
MAX_RESOURCES = 3

MAX_FAMILY_REFLECTION_WORDS = 300
MAX_RATIONALE_WORDS = 200
MAX_CLOSING_NOTE_WORDS = 200
MAX_TOTAL_WORDS = 1500

# A phrase counts as mentioned when the whole phrase or one of its longer words appears.
MIN_INDICATOR_WORD_LENGTH = 5

CITATION_MARKER_PATTERN = re.compile(r"\[[^\]\n]{2,}\]")

PROHIBITED_PHRASES = (
    "you must",
    "you have to",
    "you need to",
    "the only way",
    "the right way",
    "every family should",
    "guaranteed",
    "diagnose",
    "diagnosis",
    "disorder",
    "symptoms",
    "treatment plan",
    "prescribe",
)


class DeterministicCheck(BaseModel):
    """The outcome of one inspectable quality check."""

    check_name: str
    passed: bool
    details: str | None = None


class PathwayEvaluationResult(BaseModel):
    """Every deterministic check run against one generated pathway."""

    case_id: str
    checks: list[DeterministicCheck]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failed_check_names(self) -> list[str]:
        return [check.check_name for check in self.checks if not check.passed]


class EvaluationReport(BaseModel):
    """Aggregate outcomes across every evaluated case."""

    cases_evaluated: int
    cases_passed: int
    checks_evaluated: int
    checks_passed: int
    check_pass_rate: float
    results: list[PathwayEvaluationResult]


def normalize(text: str) -> str:
    """Lowercase the text and collapse all runs of whitespace."""

    return " ".join(text.split()).lower()


def word_count(text: str) -> int:
    return len(text.split())


def prose_fields(pathway: LearningPathway) -> list[tuple[str, str]]:
    """Pair every family-facing string with a readable field path."""

    fields = [("family_reflection", pathway.family_reflection)]

    for index, practice in enumerate(pathway.starting_rhythm):
        prefix = f"starting_rhythm[{index}]"
        fields.append((f"{prefix}.timing", practice.timing))
        fields.append((f"{prefix}.practice", practice.practice))
        fields.append((f"{prefix}.why_it_fits", practice.why_it_fits))

    for index, resource in enumerate(pathway.resources):
        prefix = f"resources[{index}]"
        fields.append((f"{prefix}.title", resource.title))
        fields.append((f"{prefix}.why_it_fits", resource.why_it_fits))

    fields.append(
        ("community_suggestion.suggestion", pathway.community_suggestion.suggestion)
    )
    fields.append(
        ("community_suggestion.why_it_fits", pathway.community_suggestion.why_it_fits)
    )
    fields.append(("closing_note", pathway.closing_note))

    return fields


def pathway_text(pathway: LearningPathway) -> str:
    """Join every family-facing string into one searchable block."""

    return " ".join(text for _, text in prose_fields(pathway))


def known_record_ids(result: GroundedPathwayResult) -> set[str]:
    """Collect chunk IDs and their inventory-level IDs from the retrieval."""

    ids = {retrieved.record.source_id for retrieved in result.retrieved_records}
    ids.update(
        inventory_source_id(retrieved.record) for retrieved in result.retrieved_records
    )

    return ids


def mentions_any(text: str, phrases: list[str]) -> list[str]:
    """Return the phrases loosely present in the text, by phrase or by long word."""

    haystack = normalize(text)
    matched = []

    for phrase in phrases:
        candidate = normalize(phrase)

        if not candidate:
            continue

        words = [
            word
            for word in re.findall(r"[a-z]+", candidate)
            if len(word) >= MIN_INDICATOR_WORD_LENGTH
        ]

        if candidate in haystack or any(word in haystack for word in words):
            matched.append(phrase)

    return matched


def check_required_sections(pathway: LearningPathway) -> DeterministicCheck:
    """Every family-facing field must contain something other than whitespace."""

    empty = [label for label, text in prose_fields(pathway) if not text.strip()]

    return DeterministicCheck(
        check_name="required_sections_populated",
        passed=not empty,
        details=f"Empty fields: {', '.join(empty)}." if empty else None,
    )


def check_resource_count(pathway: LearningPathway) -> DeterministicCheck:
    """The pathway must recommend the number of resources the schema expects."""

    count = len(pathway.resources)

    return DeterministicCheck(
        check_name="resource_count_within_range",
        passed=MIN_RESOURCES <= count <= MAX_RESOURCES,
        details=(
            None
            if MIN_RESOURCES <= count <= MAX_RESOURCES
            else f"Found {count} resources, expected {MIN_RESOURCES}-{MAX_RESOURCES}."
        ),
    )


def check_resource_grounding(
    pathway: LearningPathway, retrieved_ids: set[str]
) -> DeterministicCheck:
    """Every resource must cite a chunk that retrieval actually returned."""

    unknown = sorted(
        {resource.source_id for resource in pathway.resources} - retrieved_ids
    )

    return DeterministicCheck(
        check_name="resource_source_ids_grounded",
        passed=not unknown,
        details=f"Unretrieved source IDs: {', '.join(unknown)}." if unknown else None,
    )


def check_community_grounding(
    pathway: LearningPathway, retrieved_ids: set[str]
) -> DeterministicCheck:
    """The community suggestion must cite a retrieved chunk when it cites one."""

    source_id = pathway.community_suggestion.source_id
    grounded = source_id is None or source_id in retrieved_ids

    return DeterministicCheck(
        check_name="community_source_id_grounded",
        passed=grounded,
        details=None if grounded else f"Unretrieved source ID: {source_id}.",
    )


def check_no_citations_in_prose(
    pathway: LearningPathway, record_ids: set[str]
) -> DeterministicCheck:
    """Citations belong in the structured source_id fields, never in the prose."""

    leaks = []

    for label, text in prose_fields(pathway):
        haystack = text.lower()

        for marker in CITATION_MARKER_PATTERN.findall(text):
            leaks.append(f"{label}: {marker}")

        leaks.extend(
            f"{label}: {record_id}"
            for record_id in sorted(record_ids)
            if record_id.lower() in haystack
        )

    return DeterministicCheck(
        check_name="no_citations_in_prose",
        passed=not leaks,
        details=f"Citation markers found in {'; '.join(leaks)}." if leaks else None,
    )


def check_no_duplicate_recommendations(pathway: LearningPathway) -> DeterministicCheck:
    """Two recommendations must not normalize to exactly the same text."""

    seen: set[str] = set()
    duplicates = []

    for resource in pathway.resources:
        key = f"{normalize(resource.title)}|{normalize(resource.why_it_fits)}"

        if key in seen:
            duplicates.append(resource.title)

        seen.add(key)

    return DeterministicCheck(
        check_name="no_duplicate_recommendations",
        passed=not duplicates,
        details=(
            f"Duplicate recommendations: {', '.join(duplicates)}."
            if duplicates
            else None
        ),
    )


def check_word_count_guardrails(pathway: LearningPathway) -> DeterministicCheck:
    """Broad upper and lower bounds that catch empty or runaway sections."""

    limits = [("family_reflection", MAX_FAMILY_REFLECTION_WORDS)]
    limits.extend(
        (f"starting_rhythm[{index}].why_it_fits", MAX_RATIONALE_WORDS)
        for index in range(len(pathway.starting_rhythm))
    )
    limits.extend(
        (f"resources[{index}].why_it_fits", MAX_RATIONALE_WORDS)
        for index in range(len(pathway.resources))
    )
    limits.append(("community_suggestion.why_it_fits", MAX_RATIONALE_WORDS))
    limits.append(("closing_note", MAX_CLOSING_NOTE_WORDS))

    texts = dict(prose_fields(pathway))
    violations = []

    for label, maximum in limits:
        counted = word_count(texts[label])

        if counted == 0:
            violations.append(f"{label} is empty")
        elif counted > maximum:
            violations.append(f"{label} has {counted} words, limit {maximum}")

    total = word_count(pathway_text(pathway))

    if total > MAX_TOTAL_WORDS:
        violations.append(f"total pathway has {total} words, limit {MAX_TOTAL_WORDS}")

    return DeterministicCheck(
        check_name="word_count_guardrails",
        passed=not violations,
        details="; ".join(violations) + "." if violations else None,
    )


def check_prohibited_phrases(pathway: LearningPathway) -> DeterministicCheck:
    """A short, explicit list of diagnostic, absolute, or prescriptive wording."""

    haystack = normalize(pathway_text(pathway))
    found = sorted(phrase for phrase in PROHIBITED_PHRASES if phrase in haystack)

    return DeterministicCheck(
        check_name="no_prohibited_phrases",
        passed=not found,
        details=f"Prohibited phrases: {', '.join(found)}." if found else None,
    )


def check_interest_personalization_indicator(
    intake: FamilyIntake, pathway: LearningPathway
) -> DeterministicCheck:
    """Weak lexical signal only: a matched interest word is not real personalization."""

    interests = [interest for child in intake.children for interest in child.interests]
    matched = mentions_any(pathway_text(pathway), interests)

    return DeterministicCheck(
        check_name="interest_personalization_indicator",
        passed=bool(matched),
        details=(
            f"Matched interests: {', '.join(matched)}."
            if matched
            else "No stated child interest appears in the pathway text."
        ),
    )


def check_family_context_personalization_indicator(
    intake: FamilyIntake, pathway: LearningPathway
) -> DeterministicCheck:
    """Weak lexical signal only: a matched phrase is not proof the pathway fits."""

    phrases = (
        intake.family_values
        + intake.wants_to_add
        + intake.wants_to_preserve
        + intake.practical_constraints
    )
    matched = mentions_any(pathway_text(pathway), phrases)

    return DeterministicCheck(
        check_name="family_context_personalization_indicator",
        passed=bool(matched),
        details=(
            f"Matched family context: {', '.join(matched)}."
            if matched
            else "No stated value, addition, preserved practice, or constraint appears."
        ),
    )


def evaluate_grounded_pathway(
    case_id: str, result: GroundedPathwayResult
) -> PathwayEvaluationResult:
    """Run every deterministic check, always in the same order."""

    pathway = result.pathway
    retrieved_ids = {
        retrieved.record.source_id for retrieved in result.retrieved_records
    }

    return PathwayEvaluationResult(
        case_id=case_id,
        checks=[
            check_required_sections(pathway),
            check_resource_count(pathway),
            check_resource_grounding(pathway, retrieved_ids),
            check_community_grounding(pathway, retrieved_ids),
            check_no_citations_in_prose(pathway, known_record_ids(result)),
            check_no_duplicate_recommendations(pathway),
            check_word_count_guardrails(pathway),
            check_prohibited_phrases(pathway),
            check_interest_personalization_indicator(result.intake, pathway),
            check_family_context_personalization_indicator(result.intake, pathway),
        ],
    )


def summarize_evaluations(
    results: list[PathwayEvaluationResult],
) -> EvaluationReport:
    """Aggregate case-level and check-level pass counts."""

    checks = [check for result in results for check in result.checks]
    checks_passed = sum(1 for check in checks if check.passed)

    return EvaluationReport(
        cases_evaluated=len(results),
        cases_passed=sum(1 for result in results if result.passed),
        checks_evaluated=len(checks),
        checks_passed=checks_passed,
        check_pass_rate=checks_passed / len(checks) if checks else 0.0,
        results=results,
    )
