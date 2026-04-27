from backend.config import Settings


def test_settings_lê_variáveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")

    s = Settings()

    assert s.anthropic_api_key == "sk-test"
    assert s.voyage_api_key == "pa-test"
    assert s.embeddings_provider == "local"
    assert s.database_url == "sqlite:///./siach.db"  # default


def test_settings_provider_inválido_levanta(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "invalido")

    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
