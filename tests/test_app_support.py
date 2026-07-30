import httpx
import pytest
from anthropic import APITimeoutError, AuthenticationError, RateLimitError
from pydantic import ValidationError

from mosaic_pathway.app_support import (
    EVIDENCE_PREVIEW_CHARACTERS,
    ChildInput,
    IntakeFormInput,
    build_family_intake,
    describe_generation_failure,
    describe_validation_errors,
    evidence_preview,
    parse_comma_separated,
    validate_form_input,
)
from mosaic_pathway.rag import GroundingError


def make_form(**overrides: object) -> IntakeFormInput:
    defaults: dict[str, object] = {
        "children": [
            ChildInput(
                label="older child",
                age=10,
                interests="animals, drawing",
                learning_needs="movement breaks",
            )
        ],
        "leaving_behind": "rigid schedules",
        "wants_to_preserve": "reading together",
        "wants_to_add": "more outdoor learning",
        "family_values": "curiosity",
        "practical_constraints": "moderate budget",
        "additional_context": "  We are new to this.  ",
    }

    return IntakeFormInput(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("animals, drawing", ["animals", "drawing"]),
        ("  animals ,  drawing  ", ["animals", "drawing"]),
        ("animals,,drawing,", ["animals", "drawing"]),
        ("animals, Animals, ANIMALS", ["animals"]),
        ("drawing, animals", ["drawing", "animals"]),
        ("", []),
        ("   ,  , ", []),
    ],
)
def test_parse_comma_separated(value: str, expected: list[str]) -> None:
    assert parse_comma_separated(value) == expected


def test_one_child_intake_maps_every_field() -> None:
    intake = build_family_intake(make_form())

    assert len(intake.children) == 1
    assert intake.children[0].label == "older child"
    assert intake.children[0].age == 10
    assert intake.children[0].interests == ["animals", "drawing"]
    assert intake.children[0].learning_needs == ["movement breaks"]
    assert intake.leaving_behind == ["rigid schedules"]
    assert intake.wants_to_preserve == ["reading together"]
    assert intake.wants_to_add == ["more outdoor learning"]
    assert intake.family_values == ["curiosity"]
    assert intake.practical_constraints == ["moderate budget"]
    assert intake.additional_context == "We are new to this."


def test_two_child_intake_preserves_order() -> None:
    form = make_form(
        children=[
            ChildInput(label="older child", age=12, interests="robotics"),
            ChildInput(label="  younger child  ", age=6, interests="songs"),
        ]
    )
    intake = build_family_intake(form)

    assert [child.label for child in intake.children] == [
        "older child",
        "younger child",
    ]
    assert [child.age for child in intake.children] == [12, 6]
    assert intake.children[1].learning_needs == []


def test_blank_additional_context_becomes_none() -> None:
    intake = build_family_intake(make_form(additional_context="   "))

    assert intake.additional_context is None


def test_missing_family_goal_is_reported() -> None:
    form = make_form(
        leaving_behind="",
        wants_to_preserve="",
        wants_to_add="",
        family_values="",
        practical_constraints="",
        additional_context="",
    )
    messages = validate_form_input(form)

    assert len(messages) == 1
    assert "leave behind" in messages[0]


def test_a_single_family_goal_is_enough() -> None:
    form = make_form(
        leaving_behind="",
        wants_to_preserve="",
        wants_to_add="",
        family_values="",
        practical_constraints="",
        additional_context="We want calmer days.",
    )

    assert validate_form_input(form) == []


def test_blank_child_label_is_reported() -> None:
    form = make_form(children=[ChildInput(label="  ", age=9, interests="music")])
    messages = validate_form_input(form)

    assert messages == ["Child 1 needs a label, such as 'older child'."]


def test_missing_child_is_reported() -> None:
    assert "Add at least one child" in validate_form_input(make_form(children=[]))[0]


def test_a_complete_form_passes_validation() -> None:
    assert validate_form_input(make_form()) == []


def test_pydantic_still_rejects_a_child_without_interests() -> None:
    form = make_form(children=[ChildInput(label="only child", age=9, interests="")])

    with pytest.raises(ValidationError):
        build_family_intake(form)


def test_validation_errors_are_described_readably() -> None:
    form = make_form(children=[ChildInput(label="only child", age=9, interests="")])

    with pytest.raises(ValidationError) as error:
        build_family_intake(form)

    messages = describe_validation_errors(error.value)

    assert len(messages) == 1
    assert messages[0].startswith("interests: ")
    assert "at least 1 item" in messages[0]


def test_short_evidence_is_returned_whole() -> None:
    assert evidence_preview("A short passage.") == "A short passage."


def test_evidence_whitespace_is_collapsed() -> None:
    assert evidence_preview("A   short\n\npassage.") == "A short passage."


def test_long_evidence_is_truncated() -> None:
    preview = evidence_preview("word " * 200)

    assert preview.endswith("...")
    assert len(preview) <= EVIDENCE_PREVIEW_CHARACTERS + 3


def test_evidence_limit_is_configurable() -> None:
    assert evidence_preview("abcdefghij", limit=4) == "abcd..."


def test_grounding_failure_has_its_own_message() -> None:
    message = describe_generation_failure(GroundingError("cited invented-source-1"))

    assert "not retrieved" in message


def test_empty_retrieval_failure_has_its_own_message() -> None:
    error = RuntimeError("Retrieval returned no Mosaic records for this family intake.")

    assert "No Mosaic passages matched" in describe_generation_failure(error)


def test_authentication_failure_mentions_the_anthropic_api_key() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = AuthenticationError(
        "provider detail",
        response=httpx.Response(401, request=request),
        body=None,
    )

    assert "ANTHROPIC_API_KEY" in describe_generation_failure(error)


def test_rate_limit_failure_asks_the_family_to_wait() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = RateLimitError(
        "provider detail",
        response=httpx.Response(429, request=request),
        body=None,
    )

    assert "rate limiting" in describe_generation_failure(error)


def test_connection_failure_mentions_reaching_the_api() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    assert "could not be reached" in describe_generation_failure(
        APITimeoutError(request=request)
    )


def test_unknown_failure_falls_back_to_technical_details() -> None:
    assert "technical details" in describe_generation_failure(RuntimeError("boom"))
