"""
Carrega o CSV de casos sintéticos SCR/BCB (casos_processados.csv) em SQLite.
Aplica mapeamento de decisao_final. Os campos sintéticos rurais já vêm no CSV.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.models import Caso
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
