"""Structured pathway generation through the Anthropic Claude API."""

from anthropic import Anthropic

from mosaic_pathway.models import FamilyIntake, LearningPathway
from mosaic_pathway.prompts import SYSTEM_PROMPT, build_generation_prompt
from mosaic_pathway.settings import Settings


class ClaudePathwayGenerator:
    """Generate structured pathways with Claude's native structured outputs."""

    def __init__(self, settings: Settings, client: Anthropic | None = None) -> None:
        # The client is injectable so tests can exercise this class offline.
        self._client = client or Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens

    def generate(
        self,
        intake: FamilyIntake,
        context: list[dict[str, str]],
    ) -> LearningPathway:
        prompt = build_generation_prompt(intake, context)

        response = self._client.messages.parse(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            output_format=LearningPathway,
        )

        pathway = response.parsed_output

        if pathway is None:
            raise RuntimeError("Claude did not return a valid LearningPathway")

        return pathway
