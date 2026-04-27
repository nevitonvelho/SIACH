"""
Teste E2E que exercita /analise (com mocks de LLM e RAG), /feedback e /historico.
Verifica que o ciclo completo funciona e que aprovar uma análise indexa um caso.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Caso, Decisao
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


def _override_db(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'e.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db, SessionLocal


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


def test_ciclo_completo(tmp_path_factory):
    override, Session = _override_db(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    fake_analise = MagicMock()
    fake_analise.run.return_value = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="x",
        recomendacoes_acao=["revisar planejamento"],
    )
    fake_humaniz = MagicMock()
    fake_humaniz.run.return_value = "Olá, Sr(a)..."

    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    client = TestClient(app)

    with patch("backend.routes.analise.RAGService", return_value=fake_rag), \
         patch("backend.routes.analise.AnaliseChain", return_value=fake_analise), \
         patch("backend.routes.analise.HumanizacaoChain", return_value=fake_humaniz), \
         patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):

        # 1) POST /analise
        r1 = client.post("/analise", json=_payload())
        assert r1.status_code == 200
        body = r1.json()
        decisao_id = body["decisao_id"]

        # 2) /historico já mostra a análise
        r2 = client.get("/historico")
        assert r2.status_code == 200
        assert any(it["id"] == decisao_id for it in r2.json())

        # 3) POST /feedback aprovado
        r3 = client.post(f"/feedback/{decisao_id}", json={"status": "aprovado"})
        assert r3.status_code == 200

    app.dependency_overrides.clear()

    # 4) Verifica que um novo Caso foi criado e indexado
    with Session() as s:
        casos = s.query(Caso).all()
        assert len(casos) == 1
        assert casos[0].decisao_final == "aprovado_com_ressalvas"
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "aprovado"
    fake_coll.add.assert_called_once()
