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


def _mock_pipeline(estudo):
    fake_parecer = MagicMock()
    fake_parecer.recomendacao.value = "aprovado"
    fake_parecer.confianca = 0.8
    fake_parecer.model_dump_json.return_value = '{"recomendacao":"aprovado"}'
    rag = patch.object(estudo, "RAGService")
    ac = patch.object(estudo, "AnaliseChain")
    hc = patch.object(estudo, "HumanizacaoChain")
    narr = patch.object(estudo, "gerar_narrativa", return_value="n")
    RAG, AC, HC, _ = rag.start(), ac.start(), hc.start(), narr.start()
    RAG.return_value.recuperar.return_value = []
    AC.return_value.run.return_value = fake_parecer
    HC.return_value.run.return_value = "humanizado"
    return [rag, ac, hc, narr]


def test_seed_estudo_idempotente(tmp_path):
    from backend.services import estudo
    Session = _session(tmp_path)
    patches = _mock_pipeline(estudo)
    try:
        with Session() as s:
            ids1 = estudo.seed_estudo(s, "analista-1")
            ids2 = estudo.seed_estudo(s, "analista-1")  # idempotente
    finally:
        for p in patches:
            p.stop()

    assert len(ids1) == 10
    assert ids1 == ids2
    with Session() as s:
        assert s.query(EstudoItem).count() == 10
        assert s.query(Decisao).count() == 10
        itens = s.query(EstudoItem).all()
        assert all(i.analista == "analista-1" for i in itens)


def test_seed_estudo_conjuntos_distintos_por_analista(tmp_path):
    from backend.services import estudo
    Session = _session(tmp_path)
    patches = _mock_pipeline(estudo)
    try:
        with Session() as s:
            estudo.seed_estudo(s, "analista-2")
            estudo.seed_estudo(s, "analista-3")
    finally:
        for p in patches:
            p.stop()

    with Session() as s:
        assert s.query(EstudoItem).count() == 20
        a2 = s.query(EstudoItem).filter(EstudoItem.analista == "analista-2").count()
        a3 = s.query(EstudoItem).filter(EstudoItem.analista == "analista-3").count()
        assert a2 == 10 and a3 == 10


def test_seed_estudo_analista_desconhecido(tmp_path):
    import pytest
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        with pytest.raises(ValueError):
            estudo.seed_estudo(s, "fulano")


def test_solicitacoes_por_analista_todas_validas():
    from backend.schemas import SolicitacaoCredito
    from backend.services.estudo import ANALISTAS, SOLICITACOES_POR_ANALISTA
    assert set(SOLICITACOES_POR_ANALISTA) == set(ANALISTAS)
    total = 0
    for nome in ANALISTAS:
        sols = SOLICITACOES_POR_ANALISTA[nome]
        assert len(sols) == 10
        for d in sols:
            SolicitacaoCredito(**d)  # valida (levanta se inválido)
        total += len(sols)
    assert total == len(ANALISTAS) * 10


def test_upsert_avaliacao_atualiza(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id

    with Session() as s:
        estudo.upsert_avaliacao(
            s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=2, comentario="primeiro"))
        estudo.upsert_avaliacao(
            s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=5, comentario="revisado"))
    with Session() as s:
        rows = s.query(Avaliacao).all()
        assert len(rows) == 1
        assert rows[0].nota == 5
        assert rows[0].comentario == "revisado"


def test_resetar_avaliacoes(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=4))
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="bob", decisao_id=did, nota=2))

    with Session() as s:
        removidas = estudo.resetar_avaliacoes(s, analista="ana")
        assert removidas == 1
        assert s.query(Avaliacao).count() == 1  # restou só a do bob

    with Session() as s:
        removidas = estudo.resetar_avaliacoes(s)  # todas
        assert removidas == 1
        assert s.query(Avaliacao).count() == 0


def test_agregar_resultados(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id
        s.add(EstudoItem(decisao_id=did, ordem=1)); s.commit()
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=4))
        estudo.upsert_avaliacao(
            s, AvaliacaoPayload(analista="bob", decisao_id=did, nota=2, comentario="muito genérica"))

    with Session() as s:
        res = estudo.agregar_resultados(s)
    por_analise = {p["decisao_id"]: p for p in res["por_analise"]}
    assert por_analise[did]["media"] == 3.0
    assert por_analise[did]["n_notas"] == 2
    assert por_analise[did]["comentarios"] == [{"analista": "bob", "texto": "muito genérica"}]


def test_agregar_faltam_por_conjunto(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d1 = _decisao(); d2 = _decisao(); s.add_all([d1, d2]); s.commit()
        s.add(EstudoItem(decisao_id=d1.id, ordem=1, analista="analista-2"))
        s.add(EstudoItem(decisao_id=d2.id, ordem=2, analista="analista-2"))
        s.commit()
        estudo.upsert_avaliacao(s, AvaliacaoPayload(analista="analista-2", decisao_id=d1.id, nota=4))

    with Session() as s:
        res = estudo.agregar_resultados(s)
    pa = {p["analista"]: p for p in res["por_analista"]}
    assert pa["analista-2"]["atribuidas"] == 2
    assert pa["analista-2"]["avaliadas"] == 1
    assert pa["analista-2"]["faltam"] == 1


def test_gerar_csv(tmp_path):
    from backend.schemas import AvaliacaoPayload
    from backend.services import estudo
    Session = _session(tmp_path)
    with Session() as s:
        d = _decisao(); s.add(d); s.commit(); did = d.id
        s.add(EstudoItem(decisao_id=did, ordem=1)); s.commit()
        estudo.upsert_avaliacao(
            s, AvaliacaoPayload(analista="ana", decisao_id=did, nota=4, comentario="ok"))
    with Session() as s:
        csv_text = estudo.gerar_csv(s)
    linhas = csv_text.strip().splitlines()
    assert linhas[0] == "analista,decisao_id,ordem,recomendacao,nota,comentario,timestamp"
    linha_ana = next(l for l in linhas[1:] if l.startswith("ana,"))
    assert ",ok," in linha_ana
