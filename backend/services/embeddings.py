"""
Wrapper sobre Voyage AI ou sentence-transformers.
A escolha é controlada pela env var EMBEDDINGS_PROVIDER (voyage|local).
"""
from __future__ import annotations

from typing import Protocol

from backend.config import get_settings


class EmbeddingsBackend(Protocol):
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class _VoyageBackend:
    def __init__(self, api_key: str, model: str):
        import voyageai
        self._client = voyageai.Client(api_key=api_key)
        self._model = model
        self.dim = 1024  # voyage-3-large

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.embed(texts, model=self._model, input_type="document")
        return list(result.embeddings)


class _LocalBackend:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer("intfloat/multilingual-e5-large")
        self.dim = 1024

    def embed(self, texts: list[str]) -> list[list[float]]:
        # e5 espera prefixo "passage:" para documentos
        prefixed = [f"passage: {t}" for t in texts]
        vecs = self._model.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True)
        return vecs.tolist()


class EmbeddingsClient:
    def __init__(self):
        s = get_settings()
        if s.embeddings_provider == "voyage":
            if not s.voyage_api_key:
                raise RuntimeError("VOYAGE_API_KEY não configurada para EMBEDDINGS_PROVIDER=voyage")
            self._backend: EmbeddingsBackend = _VoyageBackend(s.voyage_api_key, s.voyage_model)
        else:
            self._backend = _LocalBackend()

    @property
    def dim(self) -> int:
        return self._backend.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._backend.embed(texts)
