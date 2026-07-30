import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from mosaic_pathway.settings import DEFAULT_MAX_TOKENS, Settings

API_KEY = "test-anthropic-key"
MODEL = "test-claude-model"


def set_required(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", MODEL)


def test_settings_load_from_environment(monkeypatch: MonkeyPatch) -> None:
    set_required(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "2048")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key.get_secret_value() == API_KEY
    assert settings.anthropic_model == MODEL
    assert settings.anthropic_max_tokens == 2048


def test_the_api_key_is_hidden_from_representations(monkeypatch: MonkeyPatch) -> None:
    set_required(monkeypatch)

    assert API_KEY not in repr(Settings(_env_file=None))


def test_max_tokens_defaults_when_unset(monkeypatch: MonkeyPatch) -> None:
    set_required(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_MAX_TOKENS", raising=False)

    assert Settings(_env_file=None).anthropic_max_tokens == DEFAULT_MAX_TOKENS


def test_max_tokens_defaults_when_left_blank(monkeypatch: MonkeyPatch) -> None:
    set_required(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "  ")

    assert Settings(_env_file=None).anthropic_max_tokens == DEFAULT_MAX_TOKENS


def test_missing_api_key_fails(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_MODEL", MODEL)

    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
        Settings(_env_file=None)


def test_blank_api_key_fails(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    monkeypatch.setenv("ANTHROPIC_MODEL", MODEL)

    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY must not be blank"):
        Settings(_env_file=None)


def test_missing_model_fails(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", API_KEY)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

    with pytest.raises(ValidationError, match="ANTHROPIC_MODEL"):
        Settings(_env_file=None)


def test_blank_model_fails(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", "  ")

    with pytest.raises(ValidationError, match="ANTHROPIC_MODEL must not be blank"):
        Settings(_env_file=None)


@pytest.mark.parametrize("value", ["0", "-1"])
def test_non_positive_max_tokens_fails(value: str, monkeypatch: MonkeyPatch) -> None:
    set_required(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", value)

    with pytest.raises(ValidationError, match="greater than 0"):
        Settings(_env_file=None)
