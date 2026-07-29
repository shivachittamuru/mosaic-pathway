from pytest import MonkeyPatch

from mosaic_pathway.settings import Settings


def test_settings_load_from_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AZURE_OPENAI_BASE_URL",
        "https://example.openai.azure.com/openai/v1/",
    )
    monkeypatch.setenv(
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "test-deployment",
    )

    settings = Settings(_env_file=None)

    assert settings.azure_openai_base_url.endswith("/openai/v1/")
    assert settings.azure_openai_chat_deployment == "test-deployment"
