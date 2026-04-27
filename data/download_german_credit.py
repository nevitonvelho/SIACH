"""
Baixa o German Credit Data e converte para CSV padronizado.
Fonte: UCI ML Repository — Statlog (German Credit Data).

Dataset original tem 1.000 linhas, 20 atributos + 1 label (1=bom risco, 2=mau risco).
Convertemos para os campos esperados pelo modelo `Caso`.
"""
from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"

COLUNAS_ORIGINAIS = [
    "status_conta_corrente", "duracao_meses", "historico_credito", "finalidade_orig",
    "valor_credito", "poupanca", "tempo_emprego_orig", "taxa_parcela_pct",
    "estado_civil_genero", "outros_devedores", "tempo_residencia_anos", "propriedade",
    "idade", "outros_planos", "habitacao", "creditos_existentes",
    "trabalho", "dependentes", "telefone", "estrangeiro", "label",
]

# Mapeamentos do código original para texto legível.
MAP_FINALIDADE = {
    "A40": "carro_novo", "A41": "carro_usado", "A42": "moveis",
    "A43": "tv_eletronicos", "A44": "eletrodomestico", "A45": "reformas",
    "A46": "educacao", "A47": "ferias", "A48": "treinamento",
    "A49": "negocio", "A410": "outros",
}
MAP_ESTADO_CIVIL = {
    "A91": "divorciado", "A92": "casada", "A93": "solteiro",
    "A94": "casado", "A95": "solteira",
}
MAP_TEMPO_EMPREGO_MESES = {
    "A71": 0, "A72": 6, "A73": 30, "A74": 72, "A75": 120,
}
MAP_GARANTIA = {
    "A101": "sem_garantia", "A102": "co-aplicante", "A103": "fiador",
}


def baixar() -> pd.DataFrame:
    print(f"Baixando {URL}...", file=sys.stderr)
    with urllib.request.urlopen(URL) as resp:
        raw = resp.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), sep=" ", header=None, names=COLUNAS_ORIGINAIS)
    return df


def converter(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["idade"] = df["idade"].astype(int)
    # renda anual estimada a partir do valor de crédito e da taxa de parcela.
    out["renda_anual"] = (df["valor_credito"] * 12 / df["taxa_parcela_pct"] * 100).round(2)
    out["estado_civil"] = df["estado_civil_genero"].map(MAP_ESTADO_CIVIL).fillna("solteiro")
    out["dependentes"] = df["dependentes"].astype(int)
    out["tempo_emprego_meses"] = df["tempo_emprego_orig"].map(MAP_TEMPO_EMPREGO_MESES).astype(int)
    out["valor_solicitado"] = df["valor_credito"].astype(float)
    # prazo do dataset vem em meses, mas pode ultrapassar 60. Saturamos em 60.
    out["prazo_meses"] = df["duracao_meses"].clip(6, 60).astype(int)
    out["finalidade"] = df["finalidade_orig"].map(MAP_FINALIDADE).fillna("outros")
    # score interno aproximado: histórico_credito tem ranking A30..A34.
    rank = {"A30": 850, "A31": 750, "A32": 650, "A33": 550, "A34": 400}
    out["score_interno"] = df["historico_credito"].map(rank).fillna(600).astype(int)
    out["divida_aberto"] = df["valor_credito"] * 0.25  # heurística
    out["tipo_garantia"] = df["outros_devedores"].map(MAP_GARANTIA).fillna("sem_garantia")
    # Label original: 1=bom risco (não inadimpliu), 2=mau risco (inadimpliu)
    out["inadimpliu"] = (df["label"] == 2)
    return out


def main():
    out_path = Path(__file__).parent / "german_credit.csv"
    df = baixar()
    df = converter(df)
    df.to_csv(out_path, index=False)
    print(f"Salvo em {out_path} ({len(df)} linhas).", file=sys.stderr)


if __name__ == "__main__":
    main()
