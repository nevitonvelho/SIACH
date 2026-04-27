from datetime import datetime, UTC
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Decisao


def _override_db(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'h.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    # Pré-popula
    with SessionLocal() as s:
        for i in range(3):
            s.add(Decisao(
                solicitacao_id=100 + i, timestamp=datetime.now(UTC),
                dados_solicitante={"idade": 30 + i},
                casos_similares=[],
                parecer_tecnico='{"recomendacao": "aprovado"}',
                parecer_humanizado=f"texto {i}",
                recomendacao="aprovado", confianca=0.8,
                status_feedback="pendente",
            ))
        s.commit()

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db


def test_historico_lista_decisoes(tmp_path_factory):
    app.dependency_overrides[get_db] = _override_db(tmp_path_factory)
    client = TestClient(app)
    r = client.get("/historico")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    items = r.json()
    assert len(items) == 3
    assert {it["recomendacao"] for it in items} == {"aprovado"}
    assert all("dados_solicitante" in it for it in items)


def test_historico_paginacao(tmp_path_factory):
    app.dependency_overrides[get_db] = _override_db(tmp_path_factory)
    client = TestClient(app)
    r = client.get("/historico?limit=2")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 2
