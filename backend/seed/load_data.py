"""
Carrega o CSV de casos sintéticos SCR/BCB (casos_processados.csv) em SQLite.
Aplica mapeamento de decisao_final. Os campos sintéticos rurais já vêm no CSV.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from backend.models import Caso
from backend.schemas import AtividadePrincipal, SolicitacaoCredito
from backend.services.embeddings import EmbeddingsClient
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import get_collection
from data.load_scrbcb import mapear_decisao_final


def carregar_csv_em_sqlite(csv_path: str, engine: Engine) -> int:
    df = pd.read_csv(csv_path)
    df["decisao_final"] = mapear_decisao_final(df)

    with Session(engine) as s:
        # Tabela é truncada antes do seed para reprodutibilidade
        s.query(Caso).delete()
        s.commit()

        for _, row in df.iterrows():
            s.add(Caso(
                uf=str(row["uf"]),
                tipo_cliente=str(row["tipo_cliente"]),
                cnae_ocupacao=str(row["cnae_ocupacao"]),
                submodalidade=str(row["submodalidade"]),
                idade=int(row["idade"]),
                renda_anual=float(row["renda_anual"]),
                estado_civil=str(row["estado_civil"]),
                dependentes=int(row["dependentes"]),
                tempo_emprego_meses=int(row["tempo_emprego_meses"]),
                valor_solicitado=float(row["valor_solicitado"]),
                prazo_meses=int(row["prazo_meses"]),
                finalidade=str(row["finalidade"]),
                score_interno=int(row["score_interno"]),
                divida_aberto=float(row["divida_aberto"]),
                tipo_garantia=str(row["tipo_garantia"]),
                area_propriedade_ha=float(row["area_propriedade_ha"]),
                var_produtividade_pct=float(row["var_produtividade_pct"]),
                renegociacoes_recentes=int(row["renegociacoes_recentes"]),
                atividade_principal=str(row["atividade_principal"]),
                decisao_final=str(row["decisao_final"]),
                inadimpliu=bool(row["inadimpliu"]),
            ))
        s.commit()
        return len(df)


def _caso_para_solicitacao(c: Caso) -> SolicitacaoCredito:
    return SolicitacaoCredito(
        uf=c.uf,
        tipo_cliente=c.tipo_cliente,
        cnae_ocupacao=c.cnae_ocupacao,
        submodalidade=c.submodalidade,
        idade=c.idade, renda_anual=c.renda_anual, estado_civil=c.estado_civil,
        dependentes=c.dependentes, tempo_emprego_meses=c.tempo_emprego_meses,
        valor_solicitado=c.valor_solicitado, prazo_meses=c.prazo_meses,
        finalidade=c.finalidade, score_interno=c.score_interno,
        divida_aberto=c.divida_aberto, tipo_garantia=c.tipo_garantia,
        area_propriedade_ha=c.area_propriedade_ha,
        var_produtividade_pct=c.var_produtividade_pct,
        renegociacoes_recentes=c.renegociacoes_recentes,
        atividade_principal=AtividadePrincipal(c.atividade_principal),
    )


def indexar_em_chroma(engine: Engine, batch_size: int = 50) -> int:
    """Embeda narrativas e indexa todos os Casos no Chroma. Limpa antes."""
    collection = get_collection()
    # Limpa coleção (idempotente)
    existing_ids = collection.get()["ids"]
    if existing_ids:
        collection.delete(ids=existing_ids)

    emb = EmbeddingsClient()
    total = 0

    with Session(engine) as s:
        casos = s.scalars(select(Caso)).all()

    for start in range(0, len(casos), batch_size):
        batch = casos[start : start + batch_size]
        narrativas = [gerar_narrativa(_caso_para_solicitacao(c)) for c in batch]
        vecs = emb.embed(narrativas)
        ids = [str(c.id) for c in batch]
        metas = [
            {
                "id_caso": c.id,
                "decisao_final": c.decisao_final,
                "inadimpliu": bool(c.inadimpliu) if c.inadimpliu is not None else False,
                "finalidade": c.finalidade,
                "atividade_principal": c.atividade_principal,
                "area_ha": float(c.area_propriedade_ha),
            }
            for c in batch
        ]
        collection.add(ids=ids, documents=narrativas, embeddings=vecs, metadatas=metas)
        total += len(batch)

    return total
