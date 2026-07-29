"""Structured pathway generation through Azure OpenAI."""

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

from mosaic_pathway.models import FamilyIntake, LearningPathway
from mosaic_pathway.prompts import SYSTEM_PROMPT, build_generation_prompt
from mosaic_pathway.settings import Settings


class AzureOpenAIPathwayGenerator:
    """Generate structured pathways with Azure OpenAI and Entra ID."""

    def __init__(self, settings: Settings) -> None:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://ai.azure.com/.default",
        )

        self._client = OpenAI(
            base_url=settings.azure_openai_base_url,
            api_key=token_provider,
        )
        self._deployment = settings.azure_openai_chat_deployment

    def generate(
        self,
        intake: FamilyIntake,
        context: list[dict[str, str]],
    ) -> LearningPathway:
        prompt = build_generation_prompt(intake, context)

        completion = self._client.beta.chat.completions.parse(
            model=self._deployment,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format=LearningPathway,
        )

        message = completion.choices[0].message

        if message.refusal:
            raise RuntimeError(f"Model refused the request: {message.refusal}")

        if message.parsed is None:
            raise RuntimeError("Model did not return a valid LearningPathway")

        return message.parsed
