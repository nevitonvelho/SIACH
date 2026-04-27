from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.db import Base, get_db
from backend.main import app
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


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


def _override_db(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'t.db'}")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db


def test_analise_e2e_com_mocks(tmp_path_factory):
    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    fake_analise = MagicMock()
    fake_analise.run.return_value = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda"], fatores_de_risco=["queda"],
        comparacao_historica="x", recomendacoes_acao=["rev"],
    )
    fake_humaniz = MagicMock()
    fake_humaniz.run.return_value = "Olá, Sr(a)..."

    app.dependency_overrides[get_db] = _override_db(tmp_path_factory)

    with patch("backend.routes.analise.RAGService", return_value=fake_rag), \
         patch("backend.routes.analise.AnaliseChain", return_value=fake_analise), \
         patch("backend.routes.analise.HumanizacaoChain", return_value=fake_humaniz):
        client = TestClient(app)
        r = client.post("/analise", json=_payload())

    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["parecer_tecnico"]["recomendacao"] == "aprovado_com_ressalvas"
    assert body["parecer_humanizado"].startswith("Olá")
    assert body["decisao_id"] >= 1


def test_analise_payload_invalido_retorna_422():
    client = TestClient(app)
    r = client.post("/analise", json={"idade": -1})
    assert r.status_code == 422
