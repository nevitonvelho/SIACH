from unittest.mock import MagicMock, patch
import numpy as np
from backend.services.embeddings import EmbeddingsClient


def test_voyage_chama_client_e_retorna_vetor(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "voyage")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_voyage = MagicMock()
    fake_voyage.Client.return_value.embed.return_value.embeddings = [
        [0.1] * 1024,
        [0.2] * 1024,
    ]
    with patch.dict("sys.modules", {"voyageai": fake_voyage}):
        c = EmbeddingsClient()
        out = c.embed(["texto a", "texto b"])
        assert len(out) == 2
        assert len(out[0]) == 1024


def test_local_usa_sentence_transformers(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_st_class = MagicMock()
    fake_model = MagicMock()
    fake_model.encode.return_value = np.array([[0.0] * 384])
    fake_st_class.return_value = fake_model
    fake_module = MagicMock(SentenceTransformer=fake_st_class)
    with patch.dict("sys.modules", {"sentence_transformers": fake_module}):
        c = EmbeddingsClient()
        out = c.embed(["texto"])
        assert len(out) == 1


def test_dimensao_consistente(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "voyage")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_voyage = MagicMock()
    fake_voyage.Client.return_value.embed.return_value.embeddings = [[0.1] * 1024]
    with patch.dict("sys.modules", {"voyageai": fake_voyage}):
        c = EmbeddingsClient()
        assert c.dim == 1024
