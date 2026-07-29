from mosaic_pathway.models import ChildProfile, FamilyIntake
from mosaic_pathway.prompts import SYSTEM_PROMPT, build_generation_prompt


def sample_intake() -> FamilyIntake:
    return FamilyIntake(
        children=[
            ChildProfile(
                label="child",
                age=8,
                interests=["animals"],
            )
        ],
        leaving_behind=["rigid schedules"],
        wants_to_add=["more outdoor exploration"],
        family_values=["curiosity"],
    )


def test_generation_prompt_contains_intake_and_context() -> None:
    context = [
        {
            "source_id": "source-nature",
            "title": "Nature Exploration",
            "text": "Children can follow curiosity through outdoor observation.",
        }
    ]

    prompt = build_generation_prompt(sample_intake(), context)

    assert "animals" in prompt
    assert "source-nature" in prompt
    assert "outdoor observation" in prompt


def test_system_prompt_requires_grounding_and_non_directive_tone() -> None:
    assert "Use only the supplied Mosaic context" in SYSTEM_PROMPT
    assert "non-directive language" in SYSTEM_PROMPT
    assert "source_id" in SYSTEM_PROMPT
