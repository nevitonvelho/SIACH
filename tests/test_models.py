from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.db import Base
from backend.models import Caso, Decisao


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_caso_persiste_e_recupera():
    engine = setup_db()
    with Session(engine) as s:
        c = Caso(
            uf="PR", tipo_cliente="PF", cnae_ocupacao="Empresário", submodalidade="Custeio",
            idade=45, renda_anual=180_000.0, estado_civil="casado",
            dependentes=2, tempo_emprego_meses=120,
            valor_solicitado=120_000.0, prazo_meses=12,
            finalidade="custeio_agricola", score_interno=580,
            divida_aberto=45_000.0, tipo_garantia="penhor_agricola",
            area_propriedade_ha=80.0, var_produtividade_pct=-15.0,
            renegociacoes_recentes=2, atividade_principal="mista",
            decisao_final="recusado", inadimpliu=True,
        )
        s.add(c)
        s.commit()
        assert c.id is not None

        loaded = s.get(Caso, c.id)
        assert loaded.uf == "PR"
        assert loaded.idade == 45
        assert loaded.atividade_principal == "mista"
        assert loaded.inadimpliu is True


def test_decisao_persiste_com_json():
    engine = setup_db()
    with Session(engine) as s:
        d = Decisao(
            solicitacao_id=999,
            timestamp=datetime.now(UTC),
            dados_solicitante={"idade": 30},
            casos_similares=[{"caso_id": 1, "score": 0.92}],
            parecer_tecnico='{"recomendacao":"aprovado"}',
            parecer_humanizado="Sr. ...",
            recomendacao="aprovado",
            confianca=0.85,
            status_feedback="pendente",
        )
        s.add(d)
        s.commit()

        loaded = s.get(Decisao, d.id)
        assert loaded.dados_solicitante == {"idade": 30}
        assert loaded.casos_similares[0]["score"] == 0.92
