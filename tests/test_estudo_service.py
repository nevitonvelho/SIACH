from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base
from backend.models import Avaliacao, Decisao, EstudoItem


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'e.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _decisao(rec="aprovado"):
    return Decisao(
        solicitacao_id=1, timestamp=datetime.now(UTC),
        dados_solicitante={"atividade_principal": "agricultura", "valor_solicitado": 1000},
        casos_similares=[], parecer_tecnico='{"recomendacao": "%s"}' % rec,
        parecer_humanizado="texto", recomendacao=rec, confianca=0.8,
        status_feedback="pendente",
    )


def test_seed_estudo_idempotente(tmp_path):
    from backend.services import estudo
    Session = _session(tmp_path)

    fake_parecer = MagicMock()
    fake_parecer.recomendacao.value = "aprovado"
    fake_parecer.confianca = 0.8
    fake_parecer.model_dump_json.return_value = '{"recomendacao":"aprovado"}'

    with patch.object(estudo, "RAGService") as RAG, \
         patch.object(estudo, "AnaliseChain") as AC, \
         patch.object(estudo, "HumanizacaoChain") as HC, \
         patch.object(estudo, "gerar_narrativa", return_value="n"):
        RAG.return_value.recuperar.return_value = []
        AC.return_value.run.return_value = fake_parecer
        HC.return_value.run.return_value = "humanizado"
        with Session() as s:
            ids1 = estudo.seed_estudo(s)
            ids2 = estudo.seed_estudo(s)  # idempotente

    assert len(ids1) == 10
    assert ids1 == ids2
    with Session() as s:
        assert s.query(EstudoItem).count() == 10
        assert s.query(Decisao).count() == 10


def test_upsert_avaliacao_atualiza(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id

    with Session() as s:
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=5))
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=9))
    with Session() as s:
        rows = s.query(Avaliacao).all()
        assert len(rows) == 1
        assert rows[0].nota == 9


def test_agregar_resultados(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id
        s.add(EstudoItem(decisao_id=did, ordem=1)); s.commit()
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=8))
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="bob", decisao_id=did, nota=6))

    with Session() as s:
        res = estudo.agregar_resultados(s)
    por_analise = {p["decisao_id"]: p for p in res["por_analise"]}
    assert por_analise[did]["media"] == 7.0
    assert por_analise[did]["n_notas"] == 2


def test_gerar_csv(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id
        s.add(EstudoItem(decisao_id=did, ordem=1)); s.commit()
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=8))
    with Session() as s:
        csv_text = estudo.gerar_csv(s)
    linhas = csv_text.strip().splitlines()
    assert linhas[0] == "analista,decisao_id,ordem,recomendacao,nota,timestamp"
    assert any(l.startswith("ana,") for l in linhas[1:])
