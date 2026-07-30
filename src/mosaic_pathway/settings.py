"""Anthropic Claude configuration loaded from the environment or a local ``.env`` file."""

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MAX_TOKENS = 4096


class Settings(BaseSettings):
    """Configuration required for Anthropic Claude generation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr = Field(
        alias="ANTHROPIC_API_KEY",
    )
    anthropic_model: str = Field(
        alias="ANTHROPIC_MODEL",
    )
    anthropic_max_tokens: int = Field(
        default=DEFAULT_MAX_TOKENS,
        alias="ANTHROPIC_MAX_TOKENS",
        gt=0,
    )

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_api_key_is_not_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("ANTHROPIC_API_KEY must not be blank")

        return value

    @field_validator("anthropic_model")
    @classmethod
    def validate_model_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ANTHROPIC_MODEL must not be blank")

        return value

    @field_validator("anthropic_max_tokens", mode="before")
    @classmethod
    def use_default_when_unset(cls, value: object) -> object:
        # .env.example ships this key blank, which must mean "use the default".
        if isinstance(value, str) and not value.strip():
            return DEFAULT_MAX_TOKENS

        return value


def load_settings() -> Settings:
    """Load application settings from environment variables or .env."""

    return Settings()  # type: ignore[call-arg]
