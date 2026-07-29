from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration required for Azure OpenAI generation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_openai_base_url: str = Field(
        alias="AZURE_OPENAI_BASE_URL",
    )
    azure_openai_chat_deployment: str = Field(
        alias="AZURE_OPENAI_CHAT_DEPLOYMENT",
    )


def load_settings() -> Settings:
    """Load application settings from environment variables or .env."""

    return Settings()  # type: ignore[call-arg]
