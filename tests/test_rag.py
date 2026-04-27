from unittest.mock import MagicMock
from backend.services.rag import RAGService


def test_recupera_k_similares():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["narrativa 1", "narrativa 2"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
            {"decisao_final": "recusado", "inadimpliu": True, "finalidade": "x", "atividade_principal": "agricultura"},
        ]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    casos = rag.recuperar("narrativa de teste", k=2)

    assert len(casos) == 2
    assert casos[0].caso_id == 1
    assert casos[0].decisao_final.value == "aprovado"
    assert casos[1].inadimpliu is True


def test_exclui_id():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["a", "b"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
        ]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    rag.recuperar("q", k=2, excluir_id=99)

    args, kwargs = fake_chroma.query.call_args
    where = kwargs.get("where")
    assert where == {"id_caso": {"$ne": 99}}


def test_recupera_zero_quando_vazio():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [[]], "documents": [[]], "distances": [[]], "metadatas": [[]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    assert rag.recuperar("x", k=5) == []
