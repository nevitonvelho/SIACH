from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Caso, Decisao


def _setup(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'f.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as s:
        d = Decisao(
            solicitacao_id=1, timestamp=datetime.now(UTC),
            dados_solicitante={
                "uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Empresário",
                "submodalidade": "Custeio",
                "idade": 40, "renda_anual": 100_000, "estado_civil": "casado",
                "dependentes": 1, "tempo_emprego_meses": 60,
                "valor_solicitado": 30_000, "prazo_meses": 24,
                "finalidade": "custeio_agricola", "score_interno": 700,
                "divida_aberto": 10_000, "tipo_garantia": "fiador",
                "area_propriedade_ha": 50.0, "var_produtividade_pct": -2.0,
                "renegociacoes_recentes": 0, "atividade_principal": "agricultura",
            },
            casos_similares=[],
            parecer_tecnico='{"recomendacao": "aprovado"}',
            parecer_humanizado="x",
            recomendacao="aprovado", confianca=0.85,
            status_feedback="pendente",
        )
        s.add(d)
        s.commit()
        decisao_id = d.id

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db, SessionLocal, decisao_id


def test_feedback_aprovado_cria_caso_e_indexa(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(f"/feedback/{decisao_id}", json={"status": "aprovado"})

    app.dependency_overrides.clear()

    assert r.status_code == 200
    with Session() as s:
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "aprovado"
        casos = s.query(Caso).all()
        assert len(casos) == 1
        assert casos[0].decisao_final == "aprovado"
        assert casos[0].inadimpliu is None  # ainda desconhecido
        assert casos[0].uf == "PR"  # campos SCR preservados
        assert casos[0].tipo_cliente == "PF"
    fake_coll.add.assert_called_once()


def test_feedback_ajustado_grava_texto(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(
            f"/feedback/{decisao_id}",
            json={"status": "ajustado", "parecer_ajustado": "Texto revisado pelo analista."},
        )

    app.dependency_overrides.clear()
    assert r.status_code == 200
    with Session() as s:
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "ajustado"
        assert d.parecer_ajustado == "Texto revisado pelo analista."


def test_feedback_rejeitado_nao_indexa(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock()
    fake_coll = MagicMock()
    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(f"/feedback/{decisao_id}", json={"status": "rejeitado"})

    app.dependency_overrides.clear()
    assert r.status_code == 200
    fake_coll.add.assert_not_called()
    with Session() as s:
        casos = s.query(Caso).all()
        assert len(casos) == 0
