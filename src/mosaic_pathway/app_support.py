"""Pure parsing, validation, state, and presentation helpers for the Streamlit app."""

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any

from anthropic import (
    APIConnectionError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import ValidationError

from mosaic_pathway.models import ChildProfile, FamilyIntake, GroundedPathwayResult
from mosaic_pathway.rag import GroundingError

EVIDENCE_PREVIEW_CHARACTERS = 250
RESULT_KEY = "grounded_result"
ERROR_KEY = "generation_error"

# Streamlit's session state, or any dict-like stand-in used in tests.
StateStore = MutableMapping[Any, Any]


@dataclass(frozen=True)
class ChildInput:
    """Raw widget values for one child, before any domain validation."""

    label: str
    age: int
    interests: str = ""
    learning_needs: str = ""


@dataclass(frozen=True)
class IntakeFormInput:
    """Raw widget values for the whole intake form."""

    children: list[ChildInput] = field(default_factory=list)
    leaving_behind: str = ""
    wants_to_preserve: str = ""
    wants_to_add: str = ""
    family_values: str = ""
    practical_constraints: str = ""
    additional_context: str = ""


def parse_comma_separated(value: str) -> list[str]:
    """Split on commas, trim, drop blanks, and drop case-insensitive repeats."""

    items: list[str] = []
    seen: set[str] = set()

    for part in value.split(","):
        item = part.strip()
        key = item.casefold()

        if not item or key in seen:
            continue

        seen.add(key)
        items.append(item)

    return items


def validate_form_input(form: IntakeFormInput) -> list[str]:
    """Check the rules Pydantic cannot express, before the intake is built."""

    messages = []

    if not form.children:
        messages.append("Add at least one child before creating a pathway.")

    for index, child in enumerate(form.children, start=1):
        if not child.label.strip():
            messages.append(f"Child {index} needs a label, such as 'older child'.")

    goals = (
        form.leaving_behind,
        form.wants_to_preserve,
        form.wants_to_add,
        form.family_values,
        form.practical_constraints,
        form.additional_context,
    )

    if not any(goal.strip() for goal in goals):
        messages.append(
            "Describe at least one thing your family wants to leave behind, keep, "
            "add, value, or work around."
        )

    return messages


def build_family_intake(form: IntakeFormInput) -> FamilyIntake:
    """Convert submitted form strings into the existing intake model."""

    context = form.additional_context.strip()

    return FamilyIntake(
        children=[
            ChildProfile(
                label=child.label.strip(),
                age=child.age,
                interests=parse_comma_separated(child.interests),
                learning_needs=parse_comma_separated(child.learning_needs),
            )
            for child in form.children
        ],
        leaving_behind=parse_comma_separated(form.leaving_behind),
        wants_to_preserve=parse_comma_separated(form.wants_to_preserve),
        wants_to_add=parse_comma_separated(form.wants_to_add),
        family_values=parse_comma_separated(form.family_values),
        practical_constraints=parse_comma_separated(form.practical_constraints),
        additional_context=context or None,
    )


def describe_validation_errors(error: ValidationError) -> list[str]:
    """Turn Pydantic errors into short field-and-message lines."""

    messages = []

    for item in error.errors():
        parts = [
            str(part + 1) if isinstance(part, int) else str(part).replace("_", " ")
            for part in item["loc"]
        ]
        location = " ".join(parts) or "form"
        messages.append(f"{location}: {item['msg']}")

    return messages


def describe_generation_failure(error: Exception) -> str:
    """Map an exception to one short sentence a family-facing view can show."""

    if isinstance(error, GroundingError):
        return (
            "The generated pathway cited passages that were not retrieved, so it was "
            "discarded. Try creating it again."
        )

    if "no mosaic records" in str(error).lower():
        return (
            "No Mosaic passages matched this family. Try describing the family's "
            "goals in a little more detail."
        )

    if isinstance(error, AuthenticationError | PermissionDeniedError):
        return (
            "The Anthropic API rejected the request. Check that ANTHROPIC_API_KEY in "
            "your .env file is a valid, active API key."
        )

    if isinstance(error, RateLimitError):
        return (
            "The Anthropic API is rate limiting requests right now. Wait a moment "
            "and try again."
        )

    if isinstance(error, APIConnectionError):
        return (
            "The Anthropic API could not be reached. Check your network connection "
            "and try again."
        )

    return "The pathway could not be created. See the technical details below."


def evidence_preview(text: str, limit: int = EVIDENCE_PREVIEW_CHARACTERS) -> str:
    """Collapse whitespace and truncate a retrieved passage to a short preview."""

    collapsed = " ".join(text.split())

    if len(collapsed) <= limit:
        return collapsed

    return collapsed[:limit].rstrip() + "..."


@dataclass(frozen=True)
class GenerationError:
    """A family-facing failure message with the technical detail kept opt-in."""

    message: str
    detail: str


@dataclass(frozen=True)
class OutputView:
    """What the output column should draw on this rerun."""

    result: GroundedPathwayResult | None = None
    error: GenerationError | None = None

    @property
    def show_placeholder(self) -> bool:
        return self.result is None and self.error is None

    @property
    def shows_previous_result(self) -> bool:
        return self.result is not None and self.error is not None


def read_output_view(state: StateStore) -> OutputView:
    """Read the stored result and error without mutating either."""

    return OutputView(result=state.get(RESULT_KEY), error=state.get(ERROR_KEY))


def clear_error(state: StateStore) -> None:
    """Drop the previous error so a new submission never shows a stale one."""

    state.pop(ERROR_KEY, None)


def clear_pathway(state: StateStore) -> None:
    """Drop both the stored pathway and any error."""

    state.pop(RESULT_KEY, None)
    state.pop(ERROR_KEY, None)


def store_result(state: StateStore, result: GroundedPathwayResult) -> None:
    """Replace the previous pathway only once generation has succeeded."""

    state[RESULT_KEY] = result
    state.pop(ERROR_KEY, None)


def store_error(state: StateStore, message: str, error: Exception) -> None:
    """Record a failure, leaving any earlier successful pathway in place."""

    state[ERROR_KEY] = GenerationError(
        message=message, detail=f"{type(error).__name__}: {error}"
    )
