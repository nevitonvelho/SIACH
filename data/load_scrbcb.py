"""
Carrega dados do SCR/BCB 2025 (modalidade Financiamentos rurais), agrega
buckets entre os 12 meses do ano e gera casos individuais sintéticos
calibrados pelas estatísticas agregadas.

Cada bucket SCR é uma combinação (UF, segmento, cliente, cnae_ocupacao,
porte, submodalidade, origem) com totais (numero_de_operacoes, carteira
ativa em R$, carteira inadimplência em R$).

Para cada bucket com ops >= 1 geramos até MAX_PER_BUCKET casos individuais.
A taxa de inadimplência do bucket é replicada via Bernoulli; o valor
solicitado é amostrado de lognormal cuja média se aproxima de
carteira_ativa / numero_de_operacoes.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODALIDADE_RURAL = "Financiamentos rurais  (ex-financiamentos rurais e agroindustriais)"
MAX_PER_BUCKET = 5         # gera no máximo 5 casos por bucket
MIN_OPS = 1                # buckets com pelo menos 1 operação
MAX_CASOS = 5_000          # corta a base após N para manter prazo viável
SEED = 42

DATA_DIR = Path(__file__).parent / "scrdata_2025"
OUT_PATH = Path(__file__).parent / "casos_processados.csv"


def carregar_e_filtrar() -> pd.DataFrame:
    files = sorted(glob.glob(str(DATA_DIR / "scrdata_*.csv")))
    if not files:
        raise FileNotFoundError(f"Nenhum scrdata em {DATA_DIR}")
    print(f"Lendo {len(files)} arquivos...", file=sys.stderr)
    frames = []
    for f in files:
        df = pd.read_csv(f, sep=";", decimal=",", encoding="utf-8-sig")
        df = df[df["modalidade"] == MODALIDADE_RURAL]
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["numero_de_operacoes"] = pd.to_numeric(full["numero_de_operacoes"], errors="coerce").fillna(0).astype(int)
    full["carteira_ativa"] = pd.to_numeric(full["carteira_ativa"], errors="coerce").fillna(0)
    full["carteira_inadimplencia"] = pd.to_numeric(full["carteira_inadimplencia"], errors="coerce").fillna(0)
    print(f"Linhas rurais: {len(full):,}", file=sys.stderr)
    return full


def agregar_buckets(df: pd.DataFrame) -> pd.DataFrame:
    chaves = ["uf", "segmento", "cliente", "cnae_ocupacao", "porte", "submodalidade", "origem"]
    agg = (df.groupby(chaves, as_index=False)
             .agg(numero_de_operacoes=("numero_de_operacoes", "sum"),
                  carteira_ativa=("carteira_ativa", "sum"),
                  carteira_inadimplencia=("carteira_inadimplencia", "sum")))
    agg = agg[(agg["numero_de_operacoes"] >= MIN_OPS) & (agg["carteira_ativa"] > 0)]
    print(f"Buckets agregados: {len(agg):,}", file=sys.stderr)
    return agg


# Faixa de salários mínimos → range de renda anual estimada (R$).
# Considera salário mínimo nominal 2025 ~ R$ 1.518.
FAIXAS_PORTE_PF = {
    "Sem rendimento": (0, 18_000),
    "Até 1 salário mínimo": (10_000, 22_000),
    "Mais de 1 a 2 salários mínimos": (18_000, 36_500),
    "Mais de 2 a 3 salários mínimos": (36_000, 54_500),
    "Mais de 3 a 5 salários mínimos": (54_000, 91_000),
    "Mais de 5 a 10 salários mínimos": (90_000, 182_000),
    "Mais de 10 a 20 salários mínimos": (180_000, 364_000),
    "Acima de 20 salários mínimos": (360_000, 1_500_000),
    "Indisponível": (40_000, 200_000),
}
FAIXAS_PORTE_PJ = {
    "Micro":   (60_000, 360_000),
    "Pequeno": (360_000, 4_800_000),
    "Médio":   (4_800_000, 300_000_000),
    "Grande":  (300_000_000, 1_000_000_000),
    "Indisponível": (300_000, 5_000_000),
    "Sem rendimento": (60_000, 200_000),
}


def _amostra_renda(rng, porte: str, tipo_cliente: str) -> float:
    faixas = FAIXAS_PORTE_PF if tipo_cliente == "PF" else FAIXAS_PORTE_PJ
    lo, hi = faixas.get(porte, (60_000, 300_000))
    return float(rng.uniform(lo, hi))


def _amostra_lognormal(rng, media_alvo: float, sigma: float = 0.6) -> float:
    if media_alvo <= 0:
        return 1_000.0
    mu = np.log(media_alvo) - sigma**2 / 2
    return float(np.exp(rng.normal(mu, sigma)))


SUBM_PRAZOS = {
    "Custeio": (6, 24),
    "Investimento": (24, 60),
    "Comercialização": (6, 18),
    "Industrialização": (12, 36),
}
SUBM_FINALIDADES = {
    "Custeio": "custeio_agricola",
    "Investimento": "investimento_rural",
    "Comercialização": "comercializacao_safra",
    "Industrialização": "industrializacao_agro",
}
SUBM_GARANTIAS = {
    "Custeio": "penhor_agricola",
    "Investimento": "alienacao_fiduciaria",
    "Comercialização": "warrant_agropecuario",
    "Industrialização": "hipoteca_industrial",
}


def _normaliza_submodalidade(s: str) -> str:
    return {"Comercialização": "Comercializacao", "Industrialização": "Industrializacao"}.get(s, s)


def _atividade_principal(cnae: str, rng) -> str:
    cnae_lower = cnae.lower()
    if "agricultura" in cnae_lower or "pecu" in cnae_lower:
        return rng.choice(["agricultura", "pecuaria", "mista"], p=[0.4, 0.3, 0.3])
    return rng.choice(["agricultura", "pecuaria", "mista"], p=[0.5, 0.25, 0.25])


def gerar_casos_de_bucket(bucket: pd.Series, rng) -> list[dict]:
    n = min(int(bucket["numero_de_operacoes"]), MAX_PER_BUCKET)
    if n <= 0:
        return []
    media_valor = bucket["carteira_ativa"] / max(int(bucket["numero_de_operacoes"]), 1)
    p_inad = float(np.clip(bucket["carteira_inadimplencia"] / bucket["carteira_ativa"], 0.0, 1.0))
    submodalidade_norm = _normaliza_submodalidade(bucket["submodalidade"])
    prazo_lo, prazo_hi = SUBM_PRAZOS.get(bucket["submodalidade"], (6, 36))

    casos = []
    for _ in range(n):
        tipo_cliente = bucket["cliente"]
        renda = _amostra_renda(rng, bucket["porte"], tipo_cliente)
        valor = _amostra_lognormal(rng, media_valor, sigma=0.65)
        inadimpliu = bool(rng.random() < p_inad)

        idade = int(np.clip(rng.normal(48 if tipo_cliente == "PF" else 50, 12), 18, 90))
        dependentes = int(min(rng.poisson(1.5), 6))
        tempo_emprego = int(np.clip((idade - 20) * 12 + rng.normal(0, 36), 0, 600))
        prazo = int(rng.integers(prazo_lo, prazo_hi + 1))
        # Score: inadimplentes têm score em média mais baixo
        score_base = 700 if not inadimpliu else 520
        score = int(np.clip(rng.normal(score_base, 80), 200, 1000))
        # Dívida em aberto: fração da renda
        razao = rng.beta(2, 6) if not inadimpliu else rng.beta(4, 4)
        divida = float(min(razao * renda, renda * 0.9))

        casos.append({
            "uf": bucket["uf"],
            "tipo_cliente": tipo_cliente,
            "cnae_ocupacao": bucket["cnae_ocupacao"],
            "submodalidade": submodalidade_norm,
            "idade": idade,
            "renda_anual": round(renda, 2),
            "estado_civil": str(rng.choice(["solteiro", "casado", "divorciado"], p=[0.35, 0.55, 0.10])),
            "dependentes": dependentes,
            "tempo_emprego_meses": tempo_emprego,
            "valor_solicitado": round(min(valor, renda * 5), 2),
            "prazo_meses": prazo,
            "finalidade": SUBM_FINALIDADES.get(bucket["submodalidade"], "outros"),
            "score_interno": score,
            "divida_aberto": round(divida, 2),
            "tipo_garantia": SUBM_GARANTIAS.get(bucket["submodalidade"], "sem_garantia"),
            "area_propriedade_ha": round(float(rng.lognormal(mean=3.5, sigma=0.7) * (renda / 100_000) ** 0.5), 1),
            "var_produtividade_pct": round(float(rng.normal(-2 + (-8 if inadimpliu else 0), 8)), 1),
            "renegociacoes_recentes": int(rng.poisson(1.4 if inadimpliu else 0.4)),
            "atividade_principal": _atividade_principal(bucket["cnae_ocupacao"], rng),
            "inadimpliu": inadimpliu,
        })
    return casos


def main():
    rng = np.random.default_rng(SEED)
    df = carregar_e_filtrar()
    buckets = agregar_buckets(df)

    todos_casos: list[dict] = []
    for _, b in buckets.iterrows():
        todos_casos.extend(gerar_casos_de_bucket(b, rng))
        if len(todos_casos) >= MAX_CASOS:
            break

    out = pd.DataFrame(todos_casos[:MAX_CASOS])
    out.to_csv(OUT_PATH, index=False, encoding="utf-8")
    print(f"Salvos {len(out):,} casos em {OUT_PATH}", file=sys.stderr)
    print(f"Taxa de inadimplência empírica nos casos sintéticos: "
          f"{out['inadimpliu'].mean()*100:.2f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
