from datetime import datetime, UTC

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings
from backend.db import Base, get_db
from backend.main import app
from backend.models import Decisao, EstudoItem


def _setup(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'a.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        d = Decisao(
            solicitacao_id=1, timestamp=datetime.now(UTC),
            dados_solicitante={"atividade_principal": "agricultura", "valor_solicitado": 1000},
            casos_similares=[], parecer_tecnico='{"recomendacao":"aprovado"}',
            parecer_humanizado="texto", recomendacao="aprovado", confianca=0.8,
            status_feedback="pendente",
        )
        s.add(d); s.commit()
        s.add(EstudoItem(decisao_id=d.id, ordem=1)); s.commit()
        did = d.id

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()
    return _get_db, Session, did


def test_post_avaliacao_e_retomar(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)

    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 7})
    assert r.status_code == 200
    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 9})
    assert r.status_code == 200

    r = client.get("/avaliacoes/ana")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {str(did): 9}


def test_post_avaliacao_nota_invalida(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 11})
    app.dependency_overrides.clear()
    assert r.status_code == 422


def test_resultados_dados_exige_token(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    token = get_settings().estudo_token

    r = client.get("/resultados/dados")
    assert r.status_code == 403
    r = client.get(f"/resultados/dados?token={token}")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert body["total_itens"] == 1
    assert body["por_analise"][0]["decisao_id"] == did


def test_estudo_analises_lista(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    r = client.get("/estudo/analises")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    itens = r.json()
    assert len(itens) == 1
    assert itens[0]["decisao_id"] == did
    assert itens[0]["parecer_humanizado"] == "texto"


def test_estudo_analises_filtra_por_analista(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db2')/'b.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        for nome in ("analista-1", "analista-2"):
            d = Decisao(
                solicitacao_id=1, timestamp=datetime.now(UTC),
                dados_solicitante={"atividade_principal": "agricultura"},
                casos_similares=[], parecer_tecnico='{"recomendacao":"aprovado"}',
                parecer_humanizado="t", recomendacao="aprovado", confianca=0.8,
                status_feedback="pendente",
            )
            s.add(d); s.commit()
            s.add(EstudoItem(decisao_id=d.id, ordem=1, analista=nome)); s.commit()

    def _get_db():
        ss = Session()
        try:
            yield ss
        finally:
            ss.close()

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    r_filtrado = client.get("/estudo/analises?analista=analista-2")
    r_todos = client.get("/estudo/analises")
    app.dependency_overrides.clear()
    assert len(r_filtrado.json()) == 1
    assert r_filtrado.json()[0]["analista"] == "analista-2"
    assert len(r_todos.json()) == 2
