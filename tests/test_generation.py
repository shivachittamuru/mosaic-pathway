import sys
from typing import Any

import pytest

from mosaic_pathway.generation import ClaudePathwayGenerator
from mosaic_pathway.models import (
    ChildProfile,
    CommunitySuggestion,
    FamilyIntake,
    LearningPathway,
    ResourceRecommendation,
    RhythmPractice,
)
from mosaic_pathway.prompts import SYSTEM_PROMPT
from mosaic_pathway.settings import Settings

MODEL = "test-claude-model"
MAX_TOKENS = 1234
CONTEXT_MARKER = "Retrieved Mosaic passage about unhurried mornings."


class FakeParsedResponse:
    def __init__(self, parsed_output: LearningPathway | None) -> None:
        self.parsed_output = parsed_output


class FakeMessages:
    """Records every parse call instead of contacting the Anthropic API."""

    def __init__(self, response: FakeParsedResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> FakeParsedResponse:
        self.calls.append(kwargs)

        if isinstance(self.response, Exception):
            raise self.response

        return self.response


class FakeAnthropicClient:
    def __init__(self, response: FakeParsedResponse | Exception) -> None:
        self.messages = FakeMessages(response)


def build_settings() -> Settings:
    return Settings(
        ANTHROPIC_API_KEY="test-anthropic-key",  # type: ignore[call-arg]
        ANTHROPIC_MODEL=MODEL,
        ANTHROPIC_MAX_TOKENS=MAX_TOKENS,
        _env_file=None,
    )


def build_intake() -> FamilyIntake:
    return FamilyIntake(
        children=[ChildProfile(label="older child", age=10, interests=["animals"])],
        leaving_behind=["rigid daily schedules"],
        wants_to_add=["more outdoor learning"],
        family_values=["curiosity"],
    )


def build_context() -> list[dict[str, str]]:
    return [
        {
            "source_id": "synthetic-0001",
            "inventory_source_id": "synthetic",
            "title": "Unhurried mornings",
            "text": CONTEXT_MARKER,
        }
    ]


def build_pathway() -> LearningPathway:
    return LearningPathway(
        family_reflection="Your family values curiosity.",
        starting_rhythm=[
            RhythmPractice(
                timing="Daily",
                practice="Take one short curiosity walk.",
                why_it_fits="It adds outdoor time gently.",
            ),
            RhythmPractice(
                timing="Once this week",
                practice="Visit the local library.",
                why_it_fits="It opens interest-led resources.",
            ),
        ],
        resources=[
            ResourceRecommendation(
                title="Create an interest catalog",
                why_it_fits="It honors the interest in animals.",
                source_id="synthetic-0001",
            ),
            ResourceRecommendation(
                title="Build a bored list together",
                why_it_fits="It supports autonomy.",
                source_id="synthetic-0001",
            ),
        ],
        community_suggestion=CommunitySuggestion(
            suggestion="You might attend one informal meetup.",
            why_it_fits="It is a low-pressure way to connect.",
            source_id="synthetic-0001",
        ),
        closing_note="Go gently.",
    )


def build_generator(
    response: FakeParsedResponse | Exception,
) -> tuple[ClaudePathwayGenerator, FakeAnthropicClient]:
    client = FakeAnthropicClient(response)
    generator = ClaudePathwayGenerator(build_settings(), client)  # type: ignore[arg-type]

    return generator, client


def test_generation_calls_messages_parse_exactly_once() -> None:
    generator, client = build_generator(FakeParsedResponse(build_pathway()))

    generator.generate(build_intake(), build_context())

    assert len(client.messages.calls) == 1


def test_the_system_prompt_uses_the_top_level_system_parameter() -> None:
    generator, client = build_generator(FakeParsedResponse(build_pathway()))

    generator.generate(build_intake(), build_context())

    call = client.messages.calls[0]

    assert call["system"] == SYSTEM_PROMPT
    assert [message["role"] for message in call["messages"]] == ["user"]


def test_the_user_message_carries_the_intake_and_the_context() -> None:
    generator, client = build_generator(FakeParsedResponse(build_pathway()))

    generator.generate(build_intake(), build_context())

    content = client.messages.calls[0]["messages"][0]["content"]

    assert "older child" in content
    assert "more outdoor learning" in content
    assert "synthetic-0001" in content
    assert CONTEXT_MARKER in content


def test_the_pathway_model_is_the_structured_output_format() -> None:
    generator, client = build_generator(FakeParsedResponse(build_pathway()))

    generator.generate(build_intake(), build_context())

    assert client.messages.calls[0]["output_format"] is LearningPathway


def test_the_configured_model_and_max_tokens_are_used() -> None:
    generator, client = build_generator(FakeParsedResponse(build_pathway()))

    generator.generate(build_intake(), build_context())

    call = client.messages.calls[0]

    assert call["model"] == MODEL
    assert call["max_tokens"] == MAX_TOKENS


def test_the_parsed_output_is_returned() -> None:
    pathway = build_pathway()
    generator, _ = build_generator(FakeParsedResponse(pathway))

    assert generator.generate(build_intake(), build_context()) is pathway


def test_missing_parsed_output_raises_a_clear_error() -> None:
    generator, _ = build_generator(FakeParsedResponse(None))

    with pytest.raises(RuntimeError, match="valid LearningPathway"):
        generator.generate(build_intake(), build_context())


def test_provider_errors_are_not_retried_or_swallowed() -> None:
    generator, client = build_generator(RuntimeError("provider failure"))

    with pytest.raises(RuntimeError, match="provider failure"):
        generator.generate(build_intake(), build_context())

    assert len(client.messages.calls) == 1


def test_no_azure_or_openai_client_is_imported() -> None:
    assert "openai" not in sys.modules
    assert not [name for name in sys.modules if name.startswith("azure")]
