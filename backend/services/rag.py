"""
Wrapper sobre a collection Chroma. Recupera k casos similares, excluindo
um id se solicitado (anti-leak na avaliação experimental).
"""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from backend.config import get_settings
from backend.schemas import CasoSimilar, Recomendacao
from backend.services.embeddings import EmbeddingsClient

_COLLECTION_NAME = "casos"


def get_collection() -> Collection:
    s = get_settings()
    Path(s.chroma_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=s.chroma_dir)
    return client.get_or_create_collection(_COLLECTION_NAME)


class RAGService:
    def __init__(
        self,
        collection: Collection | None = None,
        embeddings: EmbeddingsClient | None = None,
    ):
        self._coll = collection if collection is not None else get_collection()
        self._emb = embeddings if embeddings is not None else EmbeddingsClient()

    def recuperar(
        self, narrativa: str, k: int = 5, excluir_id: int | None = None,
    ) -> list[CasoSimilar]:
        if not narrativa.strip():
            return []
        query_vec = self._emb.embed([narrativa])[0]
        kwargs = {"query_embeddings": [query_vec], "n_results": k}
        if excluir_id is not None:
            kwargs["where"] = {"id_caso": {"$ne": excluir_id}}
        result = self._coll.query(**kwargs)

        out: list[CasoSimilar] = []
        ids = result["ids"][0]
        docs = result["documents"][0]
        dists = result["distances"][0]
        metas = result["metadatas"][0]
        for i, doc, dist, meta in zip(ids, docs, dists, metas):
            out.append(CasoSimilar(
                caso_id=int(i),
                score=1.0 - float(dist),
                narrativa=doc,
                decisao_final=Recomendacao(meta["decisao_final"]),
                inadimpliu=meta.get("inadimpliu"),
            ))
        return out
