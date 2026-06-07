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

# Os 5 analistas do estudo. Cada um recebe 10 análises EXCLUSIVas (50 no total).
ANALISTAS: list[str] = [f"analista-{i}" for i in range(1, 6)]

_UFS = ["PR", "RS", "MT", "GO", "BA", "MG", "SP", "MS", "TO", "SC", "PA", "CE", "DF", "ES"]
_ATIVIDADES = ["agricultura", "pecuaria", "mista"]
_SUBMOD = ["Custeio", "Investimento", "Comercializacao", "Industrializacao"]
_GARANTIAS = ["penhor_safra", "hipoteca", "aval", "fiador", "sem_garantia", "alienacao_fiduciaria"]
_FINALIDADES = [
    "custeio_agricola", "aquisicao_animais", "beneficiamento",
    "comercializacao", "maquinario", "custeio_pecuario",
]
_CIVIL = ["solteiro", "casado", "viuvo", "divorciado"]
_OCUPACOES = ["Produtor rural", "Pecuarista", "Agroindústria", "Cafeicultor", "Cooperativa"]


def _solicitacoes_variadas(n: int, offset: int = 0) -> list[dict]:
    """Gera n solicitações sintéticas variadas e válidas, de forma determinística
    (sem aleatoriedade), usando o índice para percorrer perfis distintos."""
    out: list[dict] = []
    for k in range(n):
        i = offset + k
        out.append({
            "uf": _UFS[i % len(_UFS)],
            "tipo_cliente": "PJ" if i % 5 == 0 else "PF",
            "cnae_ocupacao": _OCUPACOES[i % len(_OCUPACOES)],
            "submodalidade": _SUBMOD[i % len(_SUBMOD)],
            "idade": 25 + (i * 3) % 50,                       # 25..74
            "renda_anual": float(30000 + (i * 25000) % 970000),
            "estado_civil": _CIVIL[i % len(_CIVIL)],
            "dependentes": i % 4,
            "tempo_emprego_meses": 12 + (i * 11) % 348,
            "valor_solicitado": float(20000 + (i * 15000) % 480000),
            "prazo_meses": 12 + (i * 6) % 48,                 # 12..59
            "finalidade": _FINALIDADES[i % len(_FINALIDADES)],
            "score_interno": 350 + (i * 37) % 600,            # 350..949
            "divida_aberto": float((i * 5000) % 120000),
            "tipo_garantia": _GARANTIAS[i % len(_GARANTIAS)],
            "area_propriedade_ha": float(10 + (i * 13) % 490),  # >0
            "var_produtividade_pct": float(-20 + (i * 7) % 40),
            "renegociacoes_recentes": i % 4,
            "atividade_principal": _ATIVIDADES[i % len(_ATIVIDADES)],
        })
    return out


# Conjunto de 10 solicitações por analista (50 distintas, sem sobreposição).
# analista-1 reaproveita as 10 curadas; os demais recebem conjuntos gerados.
SOLICITACOES_POR_ANALISTA: dict[str, list[dict]] = {
    "analista-1": SOLICITACOES_ESTUDO,
    "analista-2": _solicitacoes_variadas(10, offset=10),
    "analista-3": _solicitacoes_variadas(10, offset=20),
    "analista-4": _solicitacoes_variadas(10, offset=30),
    "analista-5": _solicitacoes_variadas(10, offset=40),
}


def seed_estudo(session: Session, analista: str) -> list[int]:
    """Gera as 10 análises do conjunto de um analista, pelo pipeline real.
    Idempotente: se o analista já tem o conjunto completo, retorna os
    decisao_id existentes sem recriar."""
    sols = SOLICITACOES_POR_ANALISTA.get(analista)
    if sols is None:
        raise ValueError(f"Analista desconhecido: {analista}")

    existentes = session.scalars(
        select(EstudoItem).where(EstudoItem.analista == analista).order_by(EstudoItem.ordem)
    ).all()
    if len(existentes) >= len(sols):
        return [e.decisao_id for e in existentes]

    ids: list[int] = []
    for ordem, dados in enumerate(sols, start=1):
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
        session.add(EstudoItem(decisao_id=decisao.id, ordem=ordem, analista=analista))
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
            nota=payload.nota, comentario=payload.comentario,
            timestamp=datetime.now(UTC),
        )
        session.add(av)
    else:
        av.nota = payload.nota
        av.comentario = payload.comentario
        av.timestamp = datetime.now(UTC)
    session.commit()
    session.refresh(av)
    return av


def agregar_resultados(session: Session) -> dict:
    itens = session.scalars(select(EstudoItem).order_by(EstudoItem.analista, EstudoItem.ordem)).all()
    total_itens = len(itens)

    por_analise = []
    itens_por_analista: dict[str, int] = {}
    for item in itens:
        d = session.get(Decisao, item.decisao_id)
        avals = session.scalars(
            select(Avaliacao).where(Avaliacao.decisao_id == item.decisao_id)
        ).all()
        notas = [a.nota for a in avals]
        media = round(sum(notas) / len(notas), 2) if notas else None
        comentarios = [
            {"analista": a.analista, "texto": a.comentario}
            for a in avals if a.comentario
        ]
        por_analise.append({
            "decisao_id": item.decisao_id, "ordem": item.ordem,
            "analista": item.analista,
            "recomendacao": d.recomendacao if d else None,
            "media": media, "n_notas": len(notas),
            "comentarios": comentarios,
        })
        if item.analista:
            itens_por_analista[item.analista] = itens_por_analista.get(item.analista, 0) + 1

    # Considera tanto analistas com itens atribuídos quanto os que já avaliaram.
    nomes = set(itens_por_analista) | set(
        session.scalars(select(Avaliacao.analista).distinct()).all()
    )
    por_analista = []
    for nome in sorted(nomes):
        notas = session.scalars(
            select(Avaliacao.nota).where(Avaliacao.analista == nome)
        ).all()
        media = round(sum(notas) / len(notas), 2) if notas else None
        atribuidas = itens_por_analista.get(nome, 0)
        por_analista.append({
            "analista": nome, "media": media,
            "avaliadas": len(notas), "atribuidas": atribuidas,
            "faltam": max(atribuidas - len(notas), 0),
        })

    return {"total_itens": total_itens, "por_analise": por_analise, "por_analista": por_analista}


def gerar_csv(session: Session) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "analista", "decisao_id", "ordem", "recomendacao",
        "nota", "comentario", "timestamp",
    ])
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
            d.recomendacao if d else "", a.nota, a.comentario or "",
            a.timestamp.isoformat(),
        ])
    return buf.getvalue()
