from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import CasoSimilar, Recomendacao


def _payload():
    return {
        "uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Empresário",
        "submodalidade": "Custeio",
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def test_analise_retorna_similares():
    similares = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="n1",
        decisao_final=Recomendacao.RECUSADO, inadimpliu=True,
    )]
    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = similares

    with patch("backend.routes.analise.RAGService", return_value=fake_rag):
        client = TestClient(app)
        r = client.post("/analise", json=_payload())

    assert r.status_code == 200
    body = r.json()
    assert "casos_similares" in body
    assert body["casos_similares"][0]["caso_id"] == 1
    assert "narrativa" in body  # preview da narrativa gerada


def test_analise_payload_invalido_retorna_422():
    client = TestClient(app)
    r = client.post("/analise", json={"idade": -1})
    assert r.status_code == 422
