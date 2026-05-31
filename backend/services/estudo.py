"""Estudo de avaliação da qualidade do RAG: gera as 10 análises do estudo,
registra notas dos analistas e agrega resultados para o TCC."""
from __future__ import annotations

import csv
import io
from datetime import datetime, UTC

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Avaliacao, Decisao, EstudoItem
from backend.schemas import AvaliacaoPayload, SolicitacaoCredito
from backend.services.analise_chain import AnaliseChain
from backend.services.humanizacao_chain import HumanizacaoChain
from backend.services.narrativa import gerar_narrativa
from backend.services.persistence import salvar_decisao
from backend.services.rag import RAGService

# 10 solicitações curadas — variadas em atividade, valor, score, prazo e perfil.
SOLICITACOES_ESTUDO: list[dict] = [
    {"uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Produtor rural", "submodalidade": "Custeio",
     "idade": 38, "renda_anual": 120000, "estado_civil": "casado", "dependentes": 2,
     "tempo_emprego_meses": 96, "valor_solicitado": 45000, "prazo_meses": 24, "finalidade": "custeio_agricola",
     "score_interno": 760, "divida_aberto": 8000, "tipo_garantia": "penhor_safra",
     "area_propriedade_ha": 60.0, "var_produtividade_pct": 4.5, "renegociacoes_recentes": 0,
     "atividade_principal": "agricultura"},
    {"uf": "RS", "tipo_cliente": "PF", "cnae_ocupacao": "Pecuarista", "submodalidade": "Investimento",
     "idade": 52, "renda_anual": 90000, "estado_civil": "casado", "dependentes": 3,
     "tempo_emprego_meses": 240, "valor_solicitado": 200000, "prazo_meses": 48, "finalidade": "aquisicao_animais",
     "score_interno": 540, "divida_aberto": 60000, "tipo_garantia": "hipoteca",
     "area_propriedade_ha": 120.0, "var_produtividade_pct": -8.0, "renegociacoes_recentes": 1,
     "atividade_principal": "pecuaria"},
    {"uf": "MT", "tipo_cliente": "PJ", "cnae_ocupacao": "Agroindústria", "submodalidade": "Industrializacao",
     "idade": 45, "renda_anual": 800000, "estado_civil": "solteiro", "dependentes": 0,
     "tempo_emprego_meses": 180, "valor_solicitado": 500000, "prazo_meses": 60, "finalidade": "beneficiamento",
     "score_interno": 820, "divida_aberto": 150000, "tipo_garantia": "aval",
     "area_propriedade_ha": 300.0, "var_produtividade_pct": 6.0, "renegociacoes_recentes": 0,
     "atividade_principal": "mista"},
    {"uf": "GO", "tipo_cliente": "PF", "cnae_ocupacao": "Produtor rural", "submodalidade": "Custeio",
     "idade": 29, "renda_anual": 48000, "estado_civil": "solteiro", "dependentes": 0,
     "tempo_emprego_meses": 36, "valor_solicitado": 30000, "prazo_meses": 18, "finalidade": "custeio_agricola",
     "score_interno": 610, "divida_aberto": 5000, "tipo_garantia": "fiador",
     "area_propriedade_ha": 25.0, "var_produtividade_pct": 1.0, "renegociacoes_recentes": 0,
     "atividade_principal": "agricultura"},
    {"uf": "BA", "tipo_cliente": "PF", "cnae_ocupacao": "Pecuarista", "submodalidade": "Custeio",
     "idade": 60, "renda_anual": 36000, "estado_civil": "viuvo", "dependentes": 1,
     "tempo_emprego_meses": 360, "valor_solicitado": 80000, "prazo_meses": 36, "finalidade": "custeio_pecuario",
     "score_interno": 430, "divida_aberto": 40000, "tipo_garantia": "sem_garantia",
     "area_propriedade_ha": 40.0, "var_produtividade_pct": -15.0, "renegociacoes_recentes": 2,
     "atividade_principal": "pecuaria"},
    {"uf": "MG", "tipo_cliente": "PF", "cnae_ocupacao": "Cafeicultor", "submodalidade": "Comercializacao",
     "idade": 41, "renda_anual": 150000, "estado_civil": "casado", "dependentes": 2,
     "tempo_emprego_meses": 144, "valor_solicitado": 90000, "prazo_meses": 12, "finalidade": "comercializacao",
     "score_interno": 700, "divida_aberto": 20000, "tipo_garantia": "penhor_safra",
     "area_propriedade_ha": 35.0, "var_produtividade_pct": 3.0, "renegociacoes_recentes": 0,
     "atividade_principal": "agricultura"},
    {"uf": "SP", "tipo_cliente": "PJ", "cnae_ocupacao": "Cooperativa", "submodalidade": "Investimento",
     "idade": 50, "renda_anual": 1200000, "estado_civil": "casado", "dependentes": 0,
     "tempo_emprego_meses": 300, "valor_solicitado": 400000, "prazo_meses": 60, "finalidade": "maquinario",
     "score_interno": 880, "divida_aberto": 100000, "tipo_garantia": "alienacao_fiduciaria",
     "area_propriedade_ha": 500.0, "var_produtividade_pct": 7.5, "renegociacoes_recentes": 0,
     "atividade_principal": "mista"},
    {"uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Produtor rural", "submodalidade": "Custeio",
     "idade": 33, "renda_anual": 70000, "estado_civil": "casado", "dependentes": 1,
     "tempo_emprego_meses": 72, "valor_solicitado": 55000, "prazo_meses": 24, "finalidade": "custeio_agricola",
     "score_interno": 660, "divida_aberto": 15000, "tipo_garantia": "fiador",
     "area_propriedade_ha": 45.0, "var_produtividade_pct": -3.0, "renegociacoes_recentes": 1,
     "atividade_principal": "agricultura"},
    {"uf": "MS", "tipo_cliente": "PF", "cnae_ocupacao": "Pecuarista", "submodalidade": "Investimento",
     "idade": 47, "renda_anual": 220000, "estado_civil": "casado", "dependentes": 2,
     "tempo_emprego_meses": 200, "valor_solicitado": 300000, "prazo_meses": 54, "finalidade": "aquisicao_animais",
     "score_interno": 720, "divida_aberto": 50000, "tipo_garantia": "hipoteca",
     "area_propriedade_ha": 250.0, "var_produtividade_pct": 2.0, "renegociacoes_recentes": 0,
     "atividade_principal": "pecuaria"},
    {"uf": "TO", "tipo_cliente": "PF", "cnae_ocupacao": "Produtor rural", "submodalidade": "Custeio",
     "idade": 26, "renda_anual": 30000, "estado_civil": "solteiro", "dependentes": 0,
     "tempo_emprego_meses": 18, "valor_solicitado": 25000, "prazo_meses": 12, "finalidade": "custeio_agricola",
     "score_interno": 380, "divida_aberto": 22000, "tipo_garantia": "sem_garantia",
     "area_propriedade_ha": 15.0, "var_produtividade_pct": -20.0, "renegociacoes_recentes": 3,
     "atividade_principal": "agricultura"},
]


def seed_estudo(session: Session) -> list[int]:
    """Gera as 10 análises do estudo pelo pipeline real. Idempotente:
    se já há 10 itens, retorna os decisao_id existentes sem recriar."""
    existentes = session.scalars(
        select(EstudoItem).order_by(EstudoItem.ordem)
    ).all()
    if len(existentes) >= len(SOLICITACOES_ESTUDO):
        return [e.decisao_id for e in existentes]

    ids: list[int] = []
    for ordem, dados in enumerate(SOLICITACOES_ESTUDO, start=1):
        solicitacao = SolicitacaoCredito(**dados)
        narrativa = gerar_narrativa(solicitacao)
        similares = RAGService().recuperar(narrativa, k=5)
        parecer = AnaliseChain().run(narrativa=narrativa, casos_similares=similares)
        humanizado = HumanizacaoChain().run(
            parecer=parecer, atividade_principal=solicitacao.atividade_principal,
        )
        decisao = salvar_decisao(
            session=session, solicitacao_id=ordem, solicitacao=solicitacao,
            parecer=parecer, parecer_humanizado=humanizado, casos_similares=similares,
        )
        session.add(EstudoItem(decisao_id=decisao.id, ordem=ordem))
        session.commit()
        ids.append(decisao.id)
    return ids


def upsert_avaliacao(session: Session, payload: AvaliacaoPayload) -> Avaliacao:
    av = session.scalar(
        select(Avaliacao).where(
            Avaliacao.analista == payload.analista,
            Avaliacao.decisao_id == payload.decisao_id,
        )
    )
    if av is None:
        av = Avaliacao(
            analista=payload.analista, decisao_id=payload.decisao_id,
            nota=payload.nota, timestamp=datetime.now(UTC),
        )
        session.add(av)
    else:
        av.nota = payload.nota
        av.timestamp = datetime.now(UTC)
    session.commit()
    session.refresh(av)
    return av


def agregar_resultados(session: Session) -> dict:
    total_itens = session.scalar(select(func.count()).select_from(EstudoItem)) or 0

    por_analise = []
    itens = session.scalars(select(EstudoItem).order_by(EstudoItem.ordem)).all()
    for item in itens:
        d = session.get(Decisao, item.decisao_id)
        notas = session.scalars(
            select(Avaliacao.nota).where(Avaliacao.decisao_id == item.decisao_id)
        ).all()
        media = round(sum(notas) / len(notas), 2) if notas else None
        por_analise.append({
            "decisao_id": item.decisao_id, "ordem": item.ordem,
            "recomendacao": d.recomendacao if d else None,
            "media": media, "n_notas": len(notas),
        })

    por_analista = []
    analistas = session.scalars(
        select(Avaliacao.analista).distinct().order_by(Avaliacao.analista)
    ).all()
    for nome in analistas:
        notas = session.scalars(
            select(Avaliacao.nota).where(Avaliacao.analista == nome)
        ).all()
        media = round(sum(notas) / len(notas), 2) if notas else None
        por_analista.append({
            "analista": nome, "media": media,
            "avaliadas": len(notas), "faltam": max(total_itens - len(notas), 0),
        })

    return {"total_itens": total_itens, "por_analise": por_analise, "por_analista": por_analista}


def gerar_csv(session: Session) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["analista", "decisao_id", "ordem", "recomendacao", "nota", "timestamp"])
    ordem_por_decisao = {
        e.decisao_id: e.ordem for e in session.scalars(select(EstudoItem)).all()
    }
    avals = session.scalars(
        select(Avaliacao).order_by(Avaliacao.analista, Avaliacao.decisao_id)
    ).all()
    for a in avals:
        d = session.get(Decisao, a.decisao_id)
        w.writerow([
            a.analista, a.decisao_id, ordem_por_decisao.get(a.decisao_id, ""),
            d.recomendacao if d else "", a.nota, a.timestamp.isoformat(),
        ])
    return buf.getvalue()
