# SIACH — Plano de Implementação (S1 a S4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o sistema SIACH E2E (frontend + API + pipeline RAG completo + persistência + aprendizado contínuo) em 4 semanas, deixando S5–S6 prontas para a validação experimental.

**Architecture:** FastAPI servindo um pipeline orquestrado por LangChain. Pipeline tem 6 etapas — etapas 1, 2, 6 são determinísticas (Pydantic, Jinja2, SQLAlchemy); etapas 3, 4, 5 usam Chroma + Anthropic Claude (Sonnet para análise técnica, Haiku para humanização) com narrativas textuais embedadas via Voyage. Frontend é HTML + Bootstrap servido como `StaticFiles` pelo próprio FastAPI.

**Tech Stack:** Python 3.12 · FastAPI 0.115 · Pydantic 2 · SQLAlchemy 2 · LangChain 0.3 · langchain-anthropic · langchain-chroma · ChromaDB 0.5 · Anthropic SDK · Voyage AI · Jinja2 · pytest · uv (gerenciador de pacotes).

**Pré-requisitos para começar:**

- Python 3.12 instalado.
- `uv` instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh` ou `pip install uv`).
- Chave de API Anthropic (`ANTHROPIC_API_KEY`).
- Chave de API Voyage (`VOYAGE_API_KEY`). Se ainda não tem, segue com `EMBEDDINGS_PROVIDER=local` na S2 e troca depois.
- Arquivos brutos SCR/BCB 2025 em `data/scrdata_2025/` (12 arquivos .csv, ~1.2 GB total). Gerados pelo `data/load_scrbcb.py` que produz `data/casos_processados.csv` com 5.000 casos sintéticos calibrados pelos dados reais do Banco Central.

---

## Estrutura de arquivos a criar

```
backend/
  __init__.py
  main.py                       — entrypoint FastAPI + StaticFiles
  config.py                     — Settings via pydantic-settings
  db.py                         — engine + SessionLocal + Base
  models.py                     — Caso, Decisao (SQLAlchemy)
  schemas.py                    — SolicitacaoCredito, ParecerTecnico, etc.
  routes/
    __init__.py
    analise.py                  — POST /analise
    feedback.py                 — POST /feedback/{decisao_id}
    historico.py                — GET /historico
  services/
    __init__.py
    narrativa.py                — etapa 2 (Jinja2)
    embeddings.py               — wrapper Voyage / sentence-transformers
    rag.py                      — etapa 3 (Chroma retriever)
    analise_chain.py            — etapa 4 (LangChain LCEL + Sonnet)
    humanizacao_chain.py        — etapa 5 (Haiku)
    persistence.py              — etapa 6 (escreve Decisao + reindexa)
  prompts/
    narrativa.j2
    analise_system.j2
    humanizacao_system.j2
  seed/
    __init__.py
    load_data.py                — CSV → SQLite + Chroma

data/
  load_scrbcb.py                — carrega SCR/BCB 2025 e gera casos sintéticos calibrados
  scrdata_2025/                 — arquivos brutos BCB (~1.2 GB, no .gitignore)

frontend/
  index.html                    — formulário de nova análise
  resultado.html                — exibe parecer + botões de feedback
  historico.html                — lista de decisões
  style.css
  app.js

tests/
  conftest.py                   — fixtures (db em memória, mocks LLM)
  test_narrativa.py
  test_embeddings.py
  test_rag.py
  test_analise_chain.py
  test_humanizacao_chain.py
  test_persistence.py
  test_api_analise.py
  test_api_feedback.py
  test_api_historico.py
  test_e2e.py
  golden/                       — respostas reais gravadas
    .gitkeep

scripts/
  seed.sh
  dev.sh

pyproject.toml
.env.example
README.md
```

---

# Milestone 1 — Setup e Dataset (Semana 1)

## Task 1.1: Inicializar projeto com uv

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`

- [ ] **Step 1: Inicializar projeto uv**

Run:
```bash
cd C:/Users/nevit/code/tcc
uv init --python 3.12 --no-readme --no-pin-python
```

Expected: cria `pyproject.toml` e arquivos básicos. Pode aparecer um `hello.py` — apague-o.

- [ ] **Step 2: Editar pyproject.toml com dependências**

Substituir conteúdo de `pyproject.toml` por:

```toml
[project]
name = "siach"
version = "0.1.0"
description = "Sistema Inteligente de Análise de Crédito Humanizada — TCC UTFPR"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "sqlalchemy>=2.0",
    "langchain>=0.3",
    "langchain-anthropic>=0.3",
    "langchain-chroma>=0.2",
    "langchain-core>=0.3",
    "chromadb>=0.5",
    "anthropic>=0.40",
    "voyageai>=0.3",
    "jinja2>=3.1",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "python-multipart>=0.0.12",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "ruff>=0.7",
    "ipykernel>=6.29",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 3: Criar .python-version**

Conteúdo: `3.12`

- [ ] **Step 4: Criar .env.example**

```
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Voyage AI (embeddings) — opcional se EMBEDDINGS_PROVIDER=local
VOYAGE_API_KEY=pa-...

# Configuração
EMBEDDINGS_PROVIDER=voyage          # voyage | local
DATABASE_URL=sqlite:///./siach.db
CHROMA_DIR=./chroma_db
LOG_LEVEL=INFO

# Modelos
ANTHROPIC_MODEL_ANALISE=claude-sonnet-4-6
ANTHROPIC_MODEL_HUMANIZACAO=claude-haiku-4-5-20251001
VOYAGE_MODEL=voyage-3-large
```

- [ ] **Step 5: Sincronizar dependências**

Run: `uv sync`
Expected: cria `.venv/`, instala todas as dependências, gera `uv.lock`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .python-version .env.example
git commit -m "chore: setup inicial com uv e dependências do SIACH"
```

---

## Task 1.2: Estrutura de pastas e Settings

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/config.py`
- Create: `backend/main.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Criar pastas vazias**

Run:
```bash
mkdir -p backend/routes backend/services backend/prompts backend/seed
mkdir -p data frontend tests/golden experiments scripts
touch backend/__init__.py backend/routes/__init__.py backend/services/__init__.py backend/seed/__init__.py
touch tests/__init__.py tests/golden/.gitkeep
```

- [ ] **Step 2: Escrever teste de Settings (deve falhar)**

`tests/test_config.py`:
```python
import os
from backend.config import Settings


def test_settings_lê_variáveis_de_ambiente(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")

    s = Settings()

    assert s.anthropic_api_key == "sk-test"
    assert s.voyage_api_key == "pa-test"
    assert s.embeddings_provider == "local"
    assert s.database_url == "sqlite:///./siach.db"  # default


def test_settings_provider_inválido_levanta(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "invalido")

    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
```

- [ ] **Step 3: Rodar teste e ver falhar**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'backend.config'`.

- [ ] **Step 4: Implementar Settings**

`backend/config.py`:
```python
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field(...)
    voyage_api_key: str | None = None

    embeddings_provider: Literal["voyage", "local"] = "voyage"
    database_url: str = "sqlite:///./siach.db"
    chroma_dir: str = "./chroma_db"
    log_level: str = "INFO"

    anthropic_model_analise: str = "claude-sonnet-4-6"
    anthropic_model_humanizacao: str = "claude-haiku-4-5-20251001"
    voyage_model: str = "voyage-3-large"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Rodar teste e ver passar**

Run: `uv run pytest tests/test_config.py -v`
Expected: 2 tests PASSED.

- [ ] **Step 6: Implementar main.py com /health**

`backend/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="SIACH", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Escrever teste do /health**

`tests/test_api_health.py`:
```python
from fastapi.testclient import TestClient
from backend.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 8: Rodar teste**

Run: `uv run pytest tests/test_api_health.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/ tests/
git commit -m "feat: estrutura básica do backend com Settings e /health"
```

---

## Task 1.3: Modelos SQLAlchemy

**Files:**
- Create: `backend/db.py`
- Create: `backend/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Escrever teste dos modelos**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Rodar teste e ver falhar**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL com ModuleNotFoundError.

- [ ] **Step 3: Implementar db.py**

`backend/db.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db():
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Implementar models.py**

`backend/models.py`:
```python
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class Caso(Base):
    __tablename__ = "caso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idade: Mapped[int]
    renda_anual: Mapped[float] = mapped_column(Float)
    estado_civil: Mapped[str] = mapped_column(String(32))
    dependentes: Mapped[int]
    tempo_emprego_meses: Mapped[int]
    valor_solicitado: Mapped[float] = mapped_column(Float)
    prazo_meses: Mapped[int]
    finalidade: Mapped[str] = mapped_column(String(64))
    score_interno: Mapped[int]
    divida_aberto: Mapped[float] = mapped_column(Float)
    tipo_garantia: Mapped[str] = mapped_column(String(64))

    # Campos sintéticos rurais
    area_propriedade_ha: Mapped[float] = mapped_column(Float)
    var_produtividade_pct: Mapped[float] = mapped_column(Float)
    renegociacoes_recentes: Mapped[int]
    atividade_principal: Mapped[str] = mapped_column(String(32))

    decisao_final: Mapped[str] = mapped_column(String(32))
    inadimpliu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Decisao(Base):
    __tablename__ = "decisao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitacao_id: Mapped[int]
    timestamp: Mapped[datetime] = mapped_column(DateTime)

    dados_solicitante: Mapped[dict] = mapped_column(JSON)
    casos_similares: Mapped[list] = mapped_column(JSON)

    parecer_tecnico: Mapped[str] = mapped_column(String)
    parecer_humanizado: Mapped[str] = mapped_column(String)
    recomendacao: Mapped[str] = mapped_column(String(32))
    confianca: Mapped[float] = mapped_column(Float)

    status_feedback: Mapped[str] = mapped_column(String(16), default="pendente")
    parecer_ajustado: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 5: Rodar testes**

Run: `uv run pytest tests/test_models.py -v`
Expected: 2 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/db.py backend/models.py tests/test_models.py
git commit -m "feat: modelos SQLAlchemy Caso e Decisao"
```

---

## Task 1.4: Schemas Pydantic

**Files:**
- Create: `backend/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Escrever testes**

`tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError
from backend.schemas import SolicitacaoCredito, ParecerTecnico, FeedbackPayload, Recomendacao


def _payload_valido():
    return {
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def test_solicitacao_valida():
    s = SolicitacaoCredito(**_payload_valido())
    assert s.idade == 45


def test_solicitacao_renda_negativa_falha():
    p = _payload_valido() | {"renda_anual": -1}
    with pytest.raises(ValidationError):
        SolicitacaoCredito(**p)


def test_solicitacao_prazo_fora_do_intervalo():
    for prazo in [3, 100]:
        p = _payload_valido() | {"prazo_meses": prazo}
        with pytest.raises(ValidationError):
            SolicitacaoCredito(**p)


def test_parecer_tecnico_aceita_recomendacao_valida():
    pt = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="Casos similares...",
        recomendacoes_acao=["revisar planejamento"],
    )
    assert pt.recomendacao == Recomendacao.APROVADO_COM_RESSALVAS


def test_parecer_tecnico_confianca_fora_do_intervalo():
    with pytest.raises(ValidationError):
        ParecerTecnico(
            recomendacao=Recomendacao.APROVADO,
            confianca=1.5,
            fatores_favoraveis=[],
            fatores_de_risco=[],
            comparacao_historica="x",
            recomendacoes_acao=[],
        )


def test_feedback_aprovado():
    fb = FeedbackPayload(status="aprovado")
    assert fb.parecer_ajustado is None


def test_feedback_ajustado_exige_texto():
    with pytest.raises(ValidationError):
        FeedbackPayload(status="ajustado")  # falta parecer_ajustado
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: FAIL.

- [ ] **Step 3: Implementar schemas.py**

`backend/schemas.py`:
```python
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Recomendacao(str, Enum):
    APROVADO = "aprovado"
    APROVADO_COM_RESSALVAS = "aprovado_com_ressalvas"
    RECUSADO = "recusado"


class AtividadePrincipal(str, Enum):
    AGRICULTURA = "agricultura"
    PECUARIA = "pecuaria"
    MISTA = "mista"


class SolicitacaoCredito(BaseModel):
    idade: int = Field(ge=18, le=100)
    renda_anual: float = Field(gt=0)
    estado_civil: str
    dependentes: int = Field(ge=0)
    tempo_emprego_meses: int = Field(ge=0)
    valor_solicitado: float = Field(gt=0)
    prazo_meses: int = Field(ge=6, le=60)
    finalidade: str
    score_interno: int = Field(ge=0, le=1000)
    divida_aberto: float = Field(ge=0)
    tipo_garantia: str

    area_propriedade_ha: float = Field(gt=0)
    var_produtividade_pct: float
    renegociacoes_recentes: int = Field(ge=0)
    atividade_principal: AtividadePrincipal


class CasoSimilar(BaseModel):
    caso_id: int
    score: float
    narrativa: str
    decisao_final: Recomendacao
    inadimpliu: bool | None = None


class ParecerTecnico(BaseModel):
    recomendacao: Recomendacao
    confianca: float = Field(ge=0.0, le=1.0)
    fatores_favoraveis: list[str]
    fatores_de_risco: list[str]
    comparacao_historica: str
    recomendacoes_acao: list[str]


class RespostaAnalise(BaseModel):
    decisao_id: int
    parecer_tecnico: ParecerTecnico
    parecer_humanizado: str
    casos_similares: list[CasoSimilar]


class FeedbackPayload(BaseModel):
    status: Literal["aprovado", "ajustado", "rejeitado"]
    parecer_ajustado: str | None = None

    @model_validator(mode="after")
    def _exige_texto_quando_ajustado(self):
        if self.status == "ajustado" and not self.parecer_ajustado:
            raise ValueError("parecer_ajustado é obrigatório quando status=ajustado")
        return self
```

- [ ] **Step 4: Rodar testes**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py tests/test_schemas.py
git commit -m "feat: schemas Pydantic (SolicitacaoCredito, ParecerTecnico, FeedbackPayload)"
```

---

## Task 1.5: Carregar SCR/BCB e gerar casos sintéticos calibrados

**Files:**
- Create: `data/load_scrbcb.py`
- Modify: `.gitignore` (já contém `data/scrdata_2025/`)

Os arquivos brutos do SCR já estão em `C:/Users/nevit/code/tcc/data/scrdata_2025/scrdata_2025{01..12}.csv` (12 arquivos, ~100MB cada). Cada arquivo tem ~300k linhas; cada linha é um BUCKET agregado (UF + segmento + cliente + CNAE + porte + modalidade + submodalidade + origem + indexador) com totais (numero_de_operacoes, carteira_ativa, carteira_inadimplencia, etc.).

Estratégia: filtrar pela modalidade "Financiamentos rurais  (ex-financiamentos rurais e agroindustriais)" e gerar até 5 casos individuais sintéticos por bucket, calibrados pelos totais do bucket.

- [x] **Step 1: Implementar `data/load_scrbcb.py`**

```python
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
```

- [x] **Step 2: Rodar e verificar**

Run: `uv run python data/load_scrbcb.py`
Expected: `Salvos 5,000 casos em ...casos_processados.csv` (ou menos se a base de buckets for menor). A taxa de inadimplência empírica deve estar próxima da real do BCB (~2–8% dependendo do filtro).

- [ ] **Step 3: Commit**

```bash
git add data/load_scrbcb.py
git commit -m "feat: loader SCR/BCB com geração de casos sintéticos calibrados"
```

---

## Task 1.6: (vazia, integrada na 1.5)

> Os campos sintéticos rurais (area_propriedade_ha, var_produtividade_pct, renegociacoes_recentes, atividade_principal) agora são gerados dentro do `load_scrbcb.py` da Task 1.5, diretamente em `gerar_casos_de_bucket`. Se no futuro precisarmos gerar para casos vindos do feedback do analista, criamos `data/seed_synthetic.py` na Task 4.2. O teste `tests/test_seed_synthetic.py` mencionado aqui é skippable se `data/seed_synthetic.py` não existir.

---

## Task 1.7: Mapear decisao_final do dataset

**Files:**
- Modify: `data/load_scrbcb.py` (adicionar função `mapear_decisao_final` ao final do arquivo)
- Create: `tests/test_seed_synthetic.py` (importar de `data.load_scrbcb`)

A lógica de mapeamento permanece idêntica à especificada originalmente. Mover a função `mapear_decisao_final` para `data/load_scrbcb.py` (ao invés de `data/seed_synthetic.py`) e ajustar o teste para importar de lá. O teste em si fica igual.

- [ ] **Step 1: Adicionar testes**

Criar `tests/test_seed_synthetic.py`:
```python
import pandas as pd
from data.load_scrbcb import mapear_decisao_final


def test_decisao_final_segue_score_e_inadimpliu():
    df = pd.DataFrame({
        "score_interno": [800, 500, 650, 650],
        "divida_aberto": [1_000, 50_000, 30_000, 30_000],
        "renda_anual": [100_000, 50_000, 100_000, 100_000],
        "inadimpliu":    [False,  True,    False,    True],
    })
    out = mapear_decisao_final(df)
    # score alto e dívida baixa → aprovado
    assert out.iloc[0] == "aprovado"
    # score baixo + dívida alta → recusado
    assert out.iloc[1] == "recusado"
    # caso intermediário sem inadimplência → com_ressalvas
    assert out.iloc[2] == "aprovado_com_ressalvas"
    # caso intermediário que inadimpliu → recusado
    assert out.iloc[3] == "recusado"
```

- [ ] **Step 2: Implementar**

Adicionar ao final de `data/load_scrbcb.py`:
```python
def mapear_decisao_final(df: pd.DataFrame) -> pd.Series:
    """
    Mapeia para `aprovado` / `aprovado_com_ressalvas` / `recusado`
    com base em score_interno, razão dívida/renda e inadimpliu.

    Esta é a decisão original que o analista (humano) tomou no caso
    histórico, NÃO a recomendação do SIACH.
    """
    razao = df["divida_aberto"] / df["renda_anual"]
    score = df["score_interno"]
    inad = df["inadimpliu"].astype(bool)

    decisao = pd.Series(["aprovado_com_ressalvas"] * len(df), index=df.index)
    decisao[(score >= 700) & (razao < 0.20)] = "aprovado"
    decisao[(score < 550) | (razao > 0.40)] = "recusado"
    # Quem inadimpliu e estava no meio termo, retroativamente foi recusado
    decisao[(decisao == "aprovado_com_ressalvas") & inad] = "recusado"
    return decisao
```

- [ ] **Step 3: Rodar teste**

Run: `uv run pytest tests/test_seed_synthetic.py -v`
Expected: 1 test PASSED.

- [ ] **Step 4: Commit**

```bash
git add data/load_scrbcb.py tests/test_seed_synthetic.py
git commit -m "feat: mapear decisao_final a partir de score e dívida (em load_scrbcb)"
```

---

## Task 1.8: Script de seed (CSV → SQLite)

**Files:**
- Create: `backend/seed/load_data.py`
- Create: `tests/test_seed_load.py`
- Create: `scripts/seed.sh`

O CSV de entrada agora é `data/casos_processados.csv` (gerado pelo `load_scrbcb.py` da Task 1.5). Os campos uf, tipo_cliente, cnae_ocupacao, submodalidade já estão presentes no CSV e devem ser passados ao construtor do `Caso`. Não há mais chamada a `gerar_campos_sinteticos` (já feito no loader).

- [ ] **Step 1: Escrever teste**

`tests/test_seed_load.py`:
```python
from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db import Base
from backend.models import Caso
from backend.seed.load_data import carregar_csv_em_sqlite


@pytest.fixture
def csv_minimo(tmp_path: Path) -> Path:
    df = pd.DataFrame([
        {
            "uf": "PR", "tipo_cliente": "PF", "cnae_ocupacao": "Empresário",
            "submodalidade": "Custeio",
            "idade": 35, "renda_anual": 80_000, "estado_civil": "casado",
            "dependentes": 1, "tempo_emprego_meses": 36,
            "valor_solicitado": 20_000, "prazo_meses": 24,
            "finalidade": "custeio_agricola", "score_interno": 700,
            "divida_aberto": 5_000, "tipo_garantia": "fiador",
            "area_propriedade_ha": 50.0, "var_produtividade_pct": -2.0,
            "renegociacoes_recentes": 0, "atividade_principal": "agricultura",
            "inadimpliu": False,
        },
        {
            "uf": "SP", "tipo_cliente": "PJ", "cnae_ocupacao": "Agricultura, pecuária",
            "submodalidade": "Investimento",
            "idade": 60, "renda_anual": 30_000, "estado_civil": "solteiro",
            "dependentes": 0, "tempo_emprego_meses": 12,
            "valor_solicitado": 15_000, "prazo_meses": 36,
            "finalidade": "custeio_agricola", "score_interno": 500,
            "divida_aberto": 12_000, "tipo_garantia": "sem_garantia",
            "area_propriedade_ha": 20.0, "var_produtividade_pct": -12.0,
            "renegociacoes_recentes": 2, "atividade_principal": "mista",
            "inadimpliu": True,
        },
    ])
    p = tmp_path / "in.csv"
    df.to_csv(p, index=False)
    return p


def test_carrega_csv_em_sqlite(csv_minimo, tmp_path):
    db_url = f"sqlite:///{tmp_path/'test.db'}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    n = carregar_csv_em_sqlite(str(csv_minimo), engine)
    assert n == 2

    with Session(engine) as s:
        casos = s.scalars(select(Caso)).all()
        assert len(casos) == 2
        # novos campos presentes
        assert casos[0].uf == "PR"
        assert casos[0].tipo_cliente == "PF"
        # campos rurais preservados
        assert all(c.area_propriedade_ha > 0 for c in casos)
        assert all(c.atividade_principal in {"agricultura", "pecuaria", "mista"} for c in casos)
        # decisao_final mapeada
        assert all(c.decisao_final in {"aprovado", "aprovado_com_ressalvas", "recusado"} for c in casos)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_seed_load.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar**

`backend/seed/load_data.py`:
```python
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
```

- [ ] **Step 4: Rodar testes**

Run: `uv run pytest tests/test_seed_load.py -v`
Expected: PASS.

- [ ] **Step 5: Criar script shell**

`scripts/seed.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

# Gera casos sintéticos e popula SQLite
uv run python data/load_scrbcb.py

uv run python -c "
from backend.db import Base, get_engine
from backend.seed.load_data import carregar_csv_em_sqlite

engine = get_engine()
Base.metadata.create_all(engine)
n = carregar_csv_em_sqlite('data/casos_processados.csv', engine)
print(f'Carregados {n} casos.')
"
```

- [ ] **Step 6: Tornar executável e rodar**

Run:
```bash
chmod +x scripts/seed.sh
./scripts/seed.sh
```
Expected: `Carregados 5000 casos.`

- [ ] **Step 7: Commit**

```bash
git add backend/seed/ tests/test_seed_load.py scripts/seed.sh
git commit -m "feat: script de seed que carrega casos_processados.csv (SCR/BCB) no SQLite"
```

---

# Milestone 2 — Pipeline Determinístico (Semana 2)

## Task 2.1: Template Jinja2 de narrativa

**Files:**
- Create: `backend/prompts/narrativa.j2`
- Create: `backend/services/narrativa.py`
- Create: `tests/test_narrativa.py`

- [ ] **Step 1: Escrever testes**

`tests/test_narrativa.py`:
```python
from backend.schemas import SolicitacaoCredito, AtividadePrincipal
from backend.services.narrativa import gerar_narrativa


def _solicitacao(**kw):
    base = dict(
        idade=45, renda_anual=180_000.0, estado_civil="casado",
        dependentes=2, tempo_emprego_meses=120,
        valor_solicitado=120_000.0, prazo_meses=12,
        finalidade="custeio_agricola", score_interno=580,
        divida_aberto=45_000.0, tipo_garantia="penhor_agricola",
        area_propriedade_ha=80.0, var_produtividade_pct=-15.0,
        renegociacoes_recentes=2, atividade_principal=AtividadePrincipal.MISTA,
    )
    return SolicitacaoCredito(**(base | kw))


def test_narrativa_contem_dados_essenciais():
    n = gerar_narrativa(_solicitacao())
    assert "45 anos" in n
    assert "R$" in n
    assert "80" in n  # área
    assert "mista" in n


def test_narrativa_destaca_queda_significativa():
    n = gerar_narrativa(_solicitacao(var_produtividade_pct=-20.0))
    assert "queda significativa" in n.lower()


def test_narrativa_nao_destaca_queda_pequena():
    n = gerar_narrativa(_solicitacao(var_produtividade_pct=-3.0))
    assert "queda significativa" not in n.lower()


def test_narrativa_eh_deterministica():
    s = _solicitacao()
    n1 = gerar_narrativa(s)
    n2 = gerar_narrativa(s)
    assert n1 == n2


def test_narrativa_aborda_renegociacoes():
    n = gerar_narrativa(_solicitacao(renegociacoes_recentes=3))
    assert "renegoci" in n.lower()


def test_narrativa_sem_renegociacoes_nao_menciona():
    n = gerar_narrativa(_solicitacao(renegociacoes_recentes=0))
    assert "renegociações" not in n.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_narrativa.py -v`
Expected: ImportError.

- [ ] **Step 3: Criar template Jinja2**

`backend/prompts/narrativa.j2`:
```jinja2
{% set queda_significativa = var_produtividade_pct < -10 -%}
{% set tem_renegociacoes = renegociacoes_recentes > 0 -%}
Solicitante de {{ idade }} anos, {{ estado_civil }}, com {{ dependentes }}
{%- if dependentes == 1 %} dependente{% else %} dependentes{% endif %}.
Atividade principal: {{ atividade_principal }}, em propriedade de {{ "%.1f"|format(area_propriedade_ha) }} hectares.
Renda anual de R$ {{ "{:,.2f}".format(renda_anual).replace(',', 'X').replace('.', ',').replace('X', '.') }}.
{% if queda_significativa -%}
Apresenta queda significativa de produtividade ({{ "%.1f"|format(var_produtividade_pct) }}%) em relação ao ciclo anterior.
{%- elif var_produtividade_pct < 0 -%}
Apresenta leve redução de produtividade ({{ "%.1f"|format(var_produtividade_pct) }}%).
{%- else -%}
Produtividade estável ou em crescimento ({{ "%.1f"|format(var_produtividade_pct) }}%).
{% endif %}
{% if tem_renegociacoes -%}
Possui {{ renegociacoes_recentes }}
{%- if renegociacoes_recentes == 1 %} renegociação recente{% else %} renegociações recentes{% endif -%}
.
{% endif -%}
Dívida em aberto de R$ {{ "{:,.2f}".format(divida_aberto).replace(',', 'X').replace('.', ',').replace('X', '.') }}.
Solicita R$ {{ "{:,.2f}".format(valor_solicitado).replace(',', 'X').replace('.', ',').replace('X', '.') }} para {{ finalidade|replace('_', ' ') }},
prazo de {{ prazo_meses }} meses, garantia: {{ tipo_garantia|replace('_', ' ') }}.
Score interno {{ score_interno }}.
Tempo de atividade/emprego formal: {{ tempo_emprego_meses }} meses.
```

- [ ] **Step 4: Implementar serviço**

`backend/services/narrativa.py`:
```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.schemas import SolicitacaoCredito

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("narrativa.j2")


def gerar_narrativa(s: SolicitacaoCredito) -> str:
    """Converte um caso tabular em parágrafo descritivo determinístico."""
    return _template.render(
        idade=s.idade,
        renda_anual=s.renda_anual,
        estado_civil=s.estado_civil,
        dependentes=s.dependentes,
        tempo_emprego_meses=s.tempo_emprego_meses,
        valor_solicitado=s.valor_solicitado,
        prazo_meses=s.prazo_meses,
        finalidade=s.finalidade,
        score_interno=s.score_interno,
        divida_aberto=s.divida_aberto,
        tipo_garantia=s.tipo_garantia,
        area_propriedade_ha=s.area_propriedade_ha,
        var_produtividade_pct=s.var_produtividade_pct,
        renegociacoes_recentes=s.renegociacoes_recentes,
        atividade_principal=s.atividade_principal.value,
    ).strip()
```

- [ ] **Step 5: Rodar testes**

Run: `uv run pytest tests/test_narrativa.py -v`
Expected: 6 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/prompts/narrativa.j2 backend/services/narrativa.py tests/test_narrativa.py
git commit -m "feat: gerador de narrativa textual determinístico (etapa 2)"
```

---

## Task 2.2: Wrapper de embeddings (Voyage + fallback local)

**Files:**
- Create: `backend/services/embeddings.py`
- Create: `tests/test_embeddings.py`

- [ ] **Step 1: Escrever teste**

`tests/test_embeddings.py`:
```python
from unittest.mock import MagicMock, patch
import numpy as np
from backend.services.embeddings import EmbeddingsClient


def test_voyage_chama_client_e_retorna_vetor(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "voyage")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_voyage = MagicMock()
    fake_voyage.Client.return_value.embed.return_value.embeddings = [
        [0.1] * 1024,
        [0.2] * 1024,
    ]
    with patch.dict("sys.modules", {"voyageai": fake_voyage}):
        c = EmbeddingsClient()
        out = c.embed(["texto a", "texto b"])
        assert len(out) == 2
        assert len(out[0]) == 1024


def test_local_usa_sentence_transformers(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_st_class = MagicMock()
    fake_model = MagicMock()
    fake_model.encode.return_value = np.array([[0.0] * 384])
    fake_st_class.return_value = fake_model
    fake_module = MagicMock(SentenceTransformer=fake_st_class)
    with patch.dict("sys.modules", {"sentence_transformers": fake_module}):
        c = EmbeddingsClient()
        out = c.embed(["texto"])
        assert len(out) == 1


def test_dimensao_consistente(monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "voyage")
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    fake_voyage = MagicMock()
    fake_voyage.Client.return_value.embed.return_value.embeddings = [[0.1] * 1024]
    with patch.dict("sys.modules", {"voyageai": fake_voyage}):
        c = EmbeddingsClient()
        assert c.dim == 1024
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_embeddings.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar**

`backend/services/embeddings.py`:
```python
"""
Wrapper sobre Voyage AI ou sentence-transformers.
A escolha é controlada pela env var EMBEDDINGS_PROVIDER (voyage|local).
"""
from __future__ import annotations

from typing import Protocol

from backend.config import get_settings


class EmbeddingsBackend(Protocol):
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class _VoyageBackend:
    def __init__(self, api_key: str, model: str):
        import voyageai
        self._client = voyageai.Client(api_key=api_key)
        self._model = model
        self.dim = 1024  # voyage-3-large

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.embed(texts, model=self._model, input_type="document")
        return list(result.embeddings)


class _LocalBackend:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer("intfloat/multilingual-e5-large")
        self.dim = 1024

    def embed(self, texts: list[str]) -> list[list[float]]:
        # e5 espera prefixo "passage:" para documentos
        prefixed = [f"passage: {t}" for t in texts]
        vecs = self._model.encode(prefixed, convert_to_numpy=True, normalize_embeddings=True)
        return vecs.tolist()


class EmbeddingsClient:
    def __init__(self):
        s = get_settings()
        if s.embeddings_provider == "voyage":
            if not s.voyage_api_key:
                raise RuntimeError("VOYAGE_API_KEY não configurada para EMBEDDINGS_PROVIDER=voyage")
            self._backend: EmbeddingsBackend = _VoyageBackend(s.voyage_api_key, s.voyage_model)
        else:
            self._backend = _LocalBackend()

    @property
    def dim(self) -> int:
        return self._backend.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._backend.embed(texts)
```

- [ ] **Step 4: Rodar testes**

Run: `uv run pytest tests/test_embeddings.py -v`
Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/services/embeddings.py tests/test_embeddings.py
git commit -m "feat: wrapper de embeddings com Voyage e fallback sentence-transformers"
```

---

## Task 2.3: Indexação no Chroma (script + serviço RAG)

**Files:**
- Create: `backend/services/rag.py`
- Modify: `backend/seed/load_data.py` (adicionar `indexar_em_chroma`)
- Create: `tests/test_rag.py`

- [ ] **Step 1: Escrever testes do RAG**

`tests/test_rag.py`:
```python
from unittest.mock import MagicMock
import pytest
from backend.services.rag import RAGService


def test_recupera_k_similares():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["narrativa 1", "narrativa 2"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
            {"decisao_final": "recusado", "inadimpliu": True, "finalidade": "x", "atividade_principal": "agricultura"},
        ]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    casos = rag.recuperar("narrativa de teste", k=2)

    assert len(casos) == 2
    assert casos[0].caso_id == 1
    assert casos[0].decisao_final.value == "aprovado"
    assert casos[1].inadimpliu is True


def test_exclui_id():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [["1", "2"]],
        "documents": [["a", "b"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
            {"decisao_final": "aprovado", "inadimpliu": False, "finalidade": "x", "atividade_principal": "mista"},
        ]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    rag.recuperar("q", k=2, excluir_id=99)

    args, kwargs = fake_chroma.query.call_args
    where = kwargs.get("where")
    assert where == {"id_caso": {"$ne": 99}}


def test_recupera_zero_quando_vazio():
    fake_chroma = MagicMock()
    fake_chroma.query.return_value = {
        "ids": [[]], "documents": [[]], "distances": [[]], "metadatas": [[]],
    }
    fake_emb = MagicMock()
    fake_emb.embed.return_value = [[0.1] * 1024]

    rag = RAGService(collection=fake_chroma, embeddings=fake_emb)
    assert rag.recuperar("x", k=5) == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_rag.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar RAGService**

`backend/services/rag.py`:
```python
"""
Wrapper sobre a collection Chroma. Recupera k casos similares, excluindo
um id se solicitado (anti-leak na avaliação experimental).
"""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from backend.config import get_settings
from backend.schemas import CasoSimilar, Recomendacao
from backend.services.embeddings import EmbeddingsClient

_COLLECTION_NAME = "casos"


def get_collection() -> Collection:
    s = get_settings()
    Path(s.chroma_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=s.chroma_dir)
    return client.get_or_create_collection(_COLLECTION_NAME)


class RAGService:
    def __init__(
        self,
        collection: Collection | None = None,
        embeddings: EmbeddingsClient | None = None,
    ):
        self._coll = collection if collection is not None else get_collection()
        self._emb = embeddings if embeddings is not None else EmbeddingsClient()

    def recuperar(
        self, narrativa: str, k: int = 5, excluir_id: int | None = None,
    ) -> list[CasoSimilar]:
        if not narrativa.strip():
            return []
        query_vec = self._emb.embed([narrativa])[0]
        kwargs = {"query_embeddings": [query_vec], "n_results": k}
        if excluir_id is not None:
            kwargs["where"] = {"id_caso": {"$ne": excluir_id}}
        result = self._coll.query(**kwargs)

        out: list[CasoSimilar] = []
        ids = result["ids"][0]
        docs = result["documents"][0]
        dists = result["distances"][0]
        metas = result["metadatas"][0]
        for i, doc, dist, meta in zip(ids, docs, dists, metas):
            out.append(CasoSimilar(
                caso_id=int(i),
                score=1.0 - float(dist),
                narrativa=doc,
                decisao_final=Recomendacao(meta["decisao_final"]),
                inadimpliu=meta.get("inadimpliu"),
            ))
        return out
```

- [ ] **Step 4: Rodar testes**

Run: `uv run pytest tests/test_rag.py -v`
Expected: 3 tests PASSED.

- [ ] **Step 5: Adicionar indexação ao seed**

Editar `backend/seed/load_data.py`. **Adicionar estas importações no topo do arquivo** (junto com as existentes):

```python
from sqlalchemy import select
from backend.services.embeddings import EmbeddingsClient
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import get_collection
from backend.schemas import SolicitacaoCredito, AtividadePrincipal
```

E **acrescentar ao final do arquivo** as duas novas funções:

```python
def _caso_para_solicitacao(c: Caso) -> SolicitacaoCredito:
    return SolicitacaoCredito(
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
```

- [ ] **Step 6: Atualizar seed.sh**

Substituir conteúdo de `scripts/seed.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

uv run python -c "
from backend.db import Base, get_engine
from backend.seed.load_data import carregar_csv_em_sqlite, indexar_em_chroma

engine = get_engine()
Base.metadata.create_all(engine)
n = carregar_csv_em_sqlite('data/german_credit.csv', engine)
print(f'Carregados {n} casos no SQLite.')
m = indexar_em_chroma(engine)
print(f'Indexados {m} casos no ChromaDB.')
"
```

- [ ] **Step 7: Rodar seed completo**

Run: `./scripts/seed.sh`
Expected: `Carregados 1000 casos no SQLite.` e `Indexados 1000 casos no ChromaDB.`

(Se VOYAGE_API_KEY não estiver disponível, configurar `EMBEDDINGS_PROVIDER=local` no `.env` e rodar de novo — o sentence-transformers baixa o modelo na primeira vez, ~2GB.)

- [ ] **Step 8: Commit**

```bash
git add backend/services/rag.py backend/seed/load_data.py tests/test_rag.py scripts/seed.sh
git commit -m "feat: indexação no ChromaDB e RAGService com anti-leak por id"
```

---

## Task 2.4: Endpoint POST /analise (versão sem LLM ainda)

**Files:**
- Create: `backend/routes/analise.py`
- Modify: `backend/main.py`
- Create: `tests/test_api_analise.py`

- [ ] **Step 1: Escrever teste do endpoint**

`tests/test_api_analise.py`:
```python
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import CasoSimilar, Recomendacao


def _payload():
    return {
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def test_analise_retorna_similares(monkeypatch):
    similares = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="n1",
        decisao_final=Recomendacao.RECUSADO, inadimpliu=True,
    )]
    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = similares

    with patch("backend.routes.analise.RAGService", return_value=fake_rag):
        client = TestClient(app)
        r = client.post("/analise", json=_payload())

    assert r.status_code == 200
    body = r.json()
    assert "casos_similares" in body
    assert body["casos_similares"][0]["caso_id"] == 1
    assert "narrativa" in body  # preview da narrativa gerada


def test_analise_payload_invalido_retorna_422():
    client = TestClient(app)
    r = client.post("/analise", json={"idade": -1})
    assert r.status_code == 422
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_api_analise.py -v`
Expected: 404 (endpoint não existe).

- [ ] **Step 3: Criar router**

`backend/routes/analise.py`:
```python
from fastapi import APIRouter, HTTPException

from backend.schemas import SolicitacaoCredito
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import RAGService

router = APIRouter()


@router.post("/analise")
def analisar(solicitacao: SolicitacaoCredito) -> dict:
    narrativa = gerar_narrativa(solicitacao)
    rag = RAGService()
    similares = rag.recuperar(narrativa, k=5)
    return {
        "narrativa": narrativa,
        "casos_similares": [s.model_dump() for s in similares],
    }
```

- [ ] **Step 4: Montar router no app**

Substituir `backend/main.py`:
```python
from fastapi import FastAPI

from backend.routes import analise

app = FastAPI(title="SIACH", version="0.1.0")
app.include_router(analise.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Rodar testes**

Run: `uv run pytest tests/test_api_analise.py -v`
Expected: 2 tests PASSED.

- [ ] **Step 6: Smoke manual**

Run em um terminal: `uv run uvicorn backend.main:app --reload`
Em outro terminal:
```bash
curl -X POST http://localhost:8000/analise \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "idade": 45, "renda_anual": 180000, "estado_civil": "casado",
  "dependentes": 2, "tempo_emprego_meses": 120,
  "valor_solicitado": 120000, "prazo_meses": 12,
  "finalidade": "custeio_agricola", "score_interno": 580,
  "divida_aberto": 45000, "tipo_garantia": "penhor_agricola",
  "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
  "renegociacoes_recentes": 2, "atividade_principal": "mista"
}
EOF
```
Expected: JSON com `narrativa` e 5 `casos_similares`.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/routes/analise.py tests/test_api_analise.py
git commit -m "feat: POST /analise retorna narrativa + 5 casos similares (sem LLM ainda)"
```

---

# Milestone 3 — Chains LLM (Semana 3)

## Task 3.1: Prompt da análise técnica

**Files:**
- Create: `backend/prompts/analise_system.j2`

- [ ] **Step 1: Criar prompt**

`backend/prompts/analise_system.j2`:
```jinja2
Você é um analista de crédito sênior em uma cooperativa de crédito brasileira,
especializado em crédito rural. Sua tarefa é avaliar uma nova solicitação de
crédito comparando-a com casos historicamente semelhantes e produzir um
parecer técnico estruturado.

Princípios obrigatórios:
- Baseie-se em evidências comparáveis com os casos similares fornecidos.
- Seja conservador quando o histórico mostra padrão recorrente de inadimplência.
- Não invente informações que não estejam nos dados.
- Responda EXCLUSIVAMENTE em JSON válido seguindo o schema indicado.
- O campo `recomendacao` deve ser um destes literais: "aprovado",
  "aprovado_com_ressalvas" ou "recusado".
- O campo `confianca` é um float entre 0.0 e 1.0.

# Caso a avaliar

{{ narrativa_atual }}

# Casos historicamente similares (para comparação)
{% for c in casos_similares %}
## Caso similar #{{ loop.index }} (decisão original: {{ c.decisao_final.value }})
{{ c.narrativa }}
{% endfor %}

# Schema de resposta esperado

```json
{
  "recomendacao": "aprovado | aprovado_com_ressalvas | recusado",
  "confianca": 0.0,
  "fatores_favoraveis": ["..."],
  "fatores_de_risco": ["..."],
  "comparacao_historica": "Síntese de como o caso atual se compara aos similares",
  "recomendacoes_acao": ["..."]
}
```

Responda agora com APENAS o JSON, sem texto fora do bloco JSON.
```

Notar: o prompt **não** inclui o campo `inadimpliu` dos casos similares — para evitar que o LLM "decore" o desfecho. O LLM vê só a `decisao_final` (a decisão original do analista humano).

- [ ] **Step 2: Commit**

```bash
git add backend/prompts/analise_system.j2
git commit -m "feat: prompt template para análise técnica"
```

---

## Task 3.2: AnaliseChain com LangChain

**Files:**
- Create: `backend/services/analise_chain.py`
- Create: `tests/test_analise_chain.py`

- [ ] **Step 1: Escrever testes**

`tests/test_analise_chain.py`:
```python
import json
from unittest.mock import MagicMock, patch
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


def _similares():
    return [
        CasoSimilar(caso_id=1, score=0.9, narrativa="caso A",
                    decisao_final=Recomendacao.APROVADO, inadimpliu=False),
        CasoSimilar(caso_id=2, score=0.85, narrativa="caso B",
                    decisao_final=Recomendacao.RECUSADO, inadimpliu=True),
    ]


def test_chain_parseia_json_valido():
    payload = {
        "recomendacao": "aprovado_com_ressalvas",
        "confianca": 0.7,
        "fatores_favoraveis": ["renda compatível"],
        "fatores_de_risco": ["queda de produtividade"],
        "comparacao_historica": "x",
        "recomendacoes_acao": ["revisar planejamento"],
    }
    fake_resp = MagicMock()
    fake_resp.content = json.dumps(payload)
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    from backend.services.analise_chain import AnaliseChain
    chain = AnaliseChain(llm=fake_llm)

    pt = chain.run(narrativa="narrativa atual", casos_similares=_similares())
    assert isinstance(pt, ParecerTecnico)
    assert pt.recomendacao == Recomendacao.APROVADO_COM_RESSALVAS
    assert pt.confianca == 0.7


def test_chain_extrai_json_de_bloco_markdown():
    payload = {
        "recomendacao": "aprovado",
        "confianca": 0.9,
        "fatores_favoraveis": [],
        "fatores_de_risco": [],
        "comparacao_historica": "x",
        "recomendacoes_acao": [],
    }
    fake_resp = MagicMock()
    fake_resp.content = f"```json\n{json.dumps(payload)}\n```"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    from backend.services.analise_chain import AnaliseChain
    chain = AnaliseChain(llm=fake_llm)
    pt = chain.run(narrativa="x", casos_similares=[])
    assert pt.recomendacao == Recomendacao.APROVADO


def test_chain_falha_apos_max_retries():
    fake_resp = MagicMock()
    fake_resp.content = "isto não é json"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    import pytest
    from backend.services.analise_chain import AnaliseChain, JsonParseFailure
    chain = AnaliseChain(llm=fake_llm, max_retries=2)
    with pytest.raises(JsonParseFailure):
        chain.run(narrativa="x", casos_similares=[])
    assert fake_llm.invoke.call_count == 2  # tentou 2 vezes
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_analise_chain.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar**

`backend/services/analise_chain.py`:
```python
"""
Etapa 4 do pipeline: análise técnica via Claude Sonnet, com saída JSON
validada por Pydantic. Retry simples com prompt-de-correção em falha de parse.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import get_settings
from backend.schemas import CasoSimilar, ParecerTecnico

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("analise_system.j2")

_BLOCO_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_PRIMEIRO_OBJETO = re.compile(r"(\{.*\})", re.DOTALL)


class JsonParseFailure(Exception):
    pass


class AnaliseChain:
    def __init__(self, llm=None, max_retries: int = 2):
        if llm is None:
            s = get_settings()
            llm = ChatAnthropic(
                model=s.anthropic_model_analise,
                api_key=s.anthropic_api_key,
                temperature=0.2,
                max_tokens=1500,
            )
        self._llm = llm
        self._max_retries = max_retries

    def run(self, narrativa: str, casos_similares: list[CasoSimilar]) -> ParecerTecnico:
        prompt = _template.render(narrativa_atual=narrativa, casos_similares=casos_similares)
        last_err: Exception | None = None

        for attempt in range(self._max_retries):
            resp = self._llm.invoke([HumanMessage(content=prompt)])
            content = resp.content if isinstance(resp.content, str) else str(resp.content)
            try:
                return self._parse(content)
            except Exception as e:
                last_err = e
                # Reforça instrução no retry
                prompt = (
                    prompt
                    + "\n\nATENÇÃO: sua resposta anterior não pôde ser interpretada como"
                    + " JSON válido. Responda agora com APENAS o objeto JSON, sem texto"
                    + " antes ou depois, sem blocos markdown."
                )

        raise JsonParseFailure(f"Falha após {self._max_retries} tentativas: {last_err}")

    @staticmethod
    def _parse(content: str) -> ParecerTecnico:
        # 1) tenta bloco markdown ```json ... ```
        if (m := _BLOCO_JSON.search(content)):
            return ParecerTecnico.model_validate_json(m.group(1))
        # 2) tenta primeiro objeto JSON encontrado
        if (m := _PRIMEIRO_OBJETO.search(content)):
            return ParecerTecnico.model_validate_json(m.group(1))
        # 3) tenta o conteúdo inteiro
        return ParecerTecnico.model_validate(json.loads(content))
```

- [ ] **Step 4: Rodar testes**

Run: `uv run pytest tests/test_analise_chain.py -v`
Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/services/analise_chain.py tests/test_analise_chain.py
git commit -m "feat: AnaliseChain com Sonnet + retry de parse JSON"
```

---

## Task 3.3: Prompt e HumanizacaoChain

**Files:**
- Create: `backend/prompts/humanizacao_system.j2`
- Create: `backend/services/humanizacao_chain.py`
- Create: `tests/test_humanizacao_chain.py`

- [ ] **Step 1: Criar prompt**

`backend/prompts/humanizacao_system.j2`:
```jinja2
Você está escrevendo a comunicação final ao solicitante de crédito, em nome
de uma cooperativa. Sua tarefa é transformar um parecer técnico estruturado
em um texto curto, claro e empático.

Princípios obrigatórios:
- 1ª pessoa do plural ("nós, da cooperativa..."), tom respeitoso.
- Evite jargão técnico. Não cite "score interno", "razão dívida/renda",
  "AUC", etc. — explique em linguagem do cotidiano.
- Mantenha a recomendação técnica, mesmo que negativa.
- Inclua até duas recomendações de ação acionáveis.
- 4 a 7 frases. Sem listas, sem negrito.

# Parecer técnico (entrada estruturada)

Recomendação: {{ parecer.recomendacao.value }}
Confiança: {{ "%.2f"|format(parecer.confianca) }}

Fatores favoráveis:
{% for f in parecer.fatores_favoraveis %}- {{ f }}
{% endfor %}
Fatores de risco:
{% for f in parecer.fatores_de_risco %}- {{ f }}
{% endfor %}
Comparação histórica: {{ parecer.comparacao_historica }}

Recomendações de ação:
{% for r in parecer.recomendacoes_acao %}- {{ r }}
{% endfor %}

Solicitante: atividade {{ atividade_principal.value }}.

Escreva agora a mensagem ao solicitante.
```

- [ ] **Step 2: Escrever testes**

`tests/test_humanizacao_chain.py`:
```python
from unittest.mock import MagicMock
from backend.schemas import (
    AtividadePrincipal, ParecerTecnico, Recomendacao,
)


def _parecer():
    return ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="Casos similares mostraram risco moderado.",
        recomendacoes_acao=["revisar planejamento"],
    )


def test_humanizacao_invoca_llm_e_retorna_texto():
    from backend.services.humanizacao_chain import HumanizacaoChain
    fake_resp = MagicMock()
    fake_resp.content = "Sr(a). solicitante, agradecemos sua confiança..."
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    chain = HumanizacaoChain(llm=fake_llm)
    texto = chain.run(parecer=_parecer(), atividade_principal=AtividadePrincipal.MISTA)

    assert "agradecemos" in texto.lower()
    fake_llm.invoke.assert_called_once()


def test_humanizacao_strip():
    from backend.services.humanizacao_chain import HumanizacaoChain
    fake_resp = MagicMock()
    fake_resp.content = "  texto com espaços ao redor  \n"
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_resp

    chain = HumanizacaoChain(llm=fake_llm)
    texto = chain.run(parecer=_parecer(), atividade_principal=AtividadePrincipal.AGRICULTURA)
    assert texto == "texto com espaços ao redor"
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `uv run pytest tests/test_humanizacao_chain.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar**

`backend/services/humanizacao_chain.py`:
```python
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import get_settings
from backend.schemas import AtividadePrincipal, ParecerTecnico

_TEMPLATES_DIR = Path(__file__).parent.parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)
_template = _env.get_template("humanizacao_system.j2")


class HumanizacaoChain:
    def __init__(self, llm=None):
        if llm is None:
            s = get_settings()
            llm = ChatAnthropic(
                model=s.anthropic_model_humanizacao,
                api_key=s.anthropic_api_key,
                temperature=0.5,
                max_tokens=600,
            )
        self._llm = llm

    def run(
        self,
        parecer: ParecerTecnico,
        atividade_principal: AtividadePrincipal,
    ) -> str:
        prompt = _template.render(parecer=parecer, atividade_principal=atividade_principal)
        resp = self._llm.invoke([HumanMessage(content=prompt)])
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return content.strip()
```

- [ ] **Step 5: Rodar testes**

Run: `uv run pytest tests/test_humanizacao_chain.py -v`
Expected: 2 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/prompts/humanizacao_system.j2 backend/services/humanizacao_chain.py tests/test_humanizacao_chain.py
git commit -m "feat: HumanizacaoChain com Haiku para parecer empático"
```

---

## Task 3.4: Integrar chains no /analise + persistência inicial

**Files:**
- Create: `backend/services/persistence.py`
- Modify: `backend/routes/analise.py`
- Create: `tests/test_persistence.py`

- [ ] **Step 1: Escrever teste de persistência**

`tests/test_persistence.py`:
```python
from datetime import datetime, UTC
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.db import Base
from backend.models import Decisao
from backend.schemas import (
    SolicitacaoCredito, ParecerTecnico, CasoSimilar,
    Recomendacao, AtividadePrincipal,
)
from backend.services.persistence import salvar_decisao


def _solicitacao():
    return SolicitacaoCredito(
        idade=45, renda_anual=180_000, estado_civil="casado",
        dependentes=2, tempo_emprego_meses=120,
        valor_solicitado=120_000, prazo_meses=12,
        finalidade="custeio_agricola", score_interno=580,
        divida_aberto=45_000, tipo_garantia="penhor_agricola",
        area_propriedade_ha=80.0, var_produtividade_pct=-15.0,
        renegociacoes_recentes=2, atividade_principal=AtividadePrincipal.MISTA,
    )


def _parecer():
    return ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.72,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="x",
        recomendacoes_acao=["revisar planejamento"],
    )


def test_salvar_decisao_grava_todos_os_campos(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'p.db'}")
    Base.metadata.create_all(engine)

    similares = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    with Session(engine) as s:
        d = salvar_decisao(
            session=s,
            solicitacao_id=42,
            solicitacao=_solicitacao(),
            parecer=_parecer(),
            parecer_humanizado="Olá, Sr(a)...",
            casos_similares=similares,
        )

    with Session(engine) as s:
        loaded = s.scalars(select(Decisao)).first()
        assert loaded.recomendacao == "aprovado_com_ressalvas"
        assert loaded.confianca == 0.72
        assert loaded.dados_solicitante["idade"] == 45
        assert loaded.casos_similares[0]["caso_id"] == 1
        assert loaded.status_feedback == "pendente"
        assert "fatores_favoraveis" in loaded.parecer_tecnico
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_persistence.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar persistence**

`backend/services/persistence.py`:
```python
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from backend.models import Decisao
from backend.schemas import CasoSimilar, ParecerTecnico, SolicitacaoCredito


def salvar_decisao(
    session: Session,
    solicitacao_id: int,
    solicitacao: SolicitacaoCredito,
    parecer: ParecerTecnico,
    parecer_humanizado: str,
    casos_similares: list[CasoSimilar],
) -> Decisao:
    d = Decisao(
        solicitacao_id=solicitacao_id,
        timestamp=datetime.now(UTC),
        dados_solicitante=solicitacao.model_dump(mode="json"),
        casos_similares=[c.model_dump(mode="json") for c in casos_similares],
        parecer_tecnico=parecer.model_dump_json(),
        parecer_humanizado=parecer_humanizado,
        recomendacao=parecer.recomendacao.value,
        confianca=parecer.confianca,
        status_feedback="pendente",
        parecer_ajustado=None,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d
```

- [ ] **Step 4: Atualizar router /analise**

Substituir `backend/routes/analise.py`:
```python
from itertools import count

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import RespostaAnalise, SolicitacaoCredito
from backend.services.analise_chain import AnaliseChain
from backend.services.humanizacao_chain import HumanizacaoChain
from backend.services.narrativa import gerar_narrativa
from backend.services.persistence import salvar_decisao
from backend.services.rag import RAGService

router = APIRouter()

# Contador simples para solicitacao_id (em produção viria do front)
_contador = count(1)


@router.post("/analise", response_model=RespostaAnalise)
def analisar(solicitacao: SolicitacaoCredito, db: Session = Depends(get_db)) -> RespostaAnalise:
    narrativa = gerar_narrativa(solicitacao)
    rag = RAGService()
    similares = rag.recuperar(narrativa, k=5)

    parecer = AnaliseChain().run(narrativa=narrativa, casos_similares=similares)
    humanizado = HumanizacaoChain().run(
        parecer=parecer, atividade_principal=solicitacao.atividade_principal,
    )

    decisao = salvar_decisao(
        session=db,
        solicitacao_id=next(_contador),
        solicitacao=solicitacao,
        parecer=parecer,
        parecer_humanizado=humanizado,
        casos_similares=similares,
    )

    return RespostaAnalise(
        decisao_id=decisao.id,
        parecer_tecnico=parecer,
        parecer_humanizado=humanizado,
        casos_similares=similares,
    )
```

- [ ] **Step 5: Atualizar teste de /analise para mockar chains**

Substituir `tests/test_api_analise.py`:
```python
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.db import Base, get_db
from backend.main import app
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


def _payload():
    return {
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def _override_db(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'t.db'}")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db


def test_analise_e2e_com_mocks(tmp_path_factory):
    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    fake_analise = MagicMock()
    fake_analise.run.return_value = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda"], fatores_de_risco=["queda"],
        comparacao_historica="x", recomendacoes_acao=["rev"],
    )
    fake_humaniz = MagicMock()
    fake_humaniz.run.return_value = "Olá, Sr(a)..."

    app.dependency_overrides[get_db] = _override_db(tmp_path_factory)

    with patch("backend.routes.analise.RAGService", return_value=fake_rag), \
         patch("backend.routes.analise.AnaliseChain", return_value=fake_analise), \
         patch("backend.routes.analise.HumanizacaoChain", return_value=fake_humaniz):
        client = TestClient(app)
        r = client.post("/analise", json=_payload())

    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["parecer_tecnico"]["recomendacao"] == "aprovado_com_ressalvas"
    assert body["parecer_humanizado"].startswith("Olá")
    assert body["decisao_id"] >= 1


def test_analise_payload_invalido_retorna_422():
    client = TestClient(app)
    r = client.post("/analise", json={"idade": -1})
    assert r.status_code == 422
```

- [ ] **Step 6: Rodar testes**

Run: `uv run pytest tests/test_api_analise.py tests/test_persistence.py -v`
Expected: tudo passa.

- [ ] **Step 7: Smoke E2E real**

Garantir que `.env` tem `ANTHROPIC_API_KEY` válida e Chroma populado. Em um terminal:
```bash
uv run uvicorn backend.main:app --reload
```
Em outro terminal, fazer POST em `/analise` com payload do exemplo. Inspecionar resposta:
- `parecer_tecnico` deve ter recomendação coerente
- `parecer_humanizado` deve ser texto fluido em pt-br

- [ ] **Step 8: Gravar 3 respostas de smoke em `tests/golden/`**

```bash
mkdir -p tests/golden
curl -s -X POST http://localhost:8000/analise -H "Content-Type: application/json" \
  -d @data/payload_smoke_1.json > tests/golden/smoke_1.json
# Repetir com 2 outros payloads variando atividade e var_produtividade_pct
```

(Criar `data/payload_smoke_1.json`, `_2.json`, `_3.json` com casos manualmente desenhados.)

- [ ] **Step 9: Commit**

```bash
git add backend/services/persistence.py backend/routes/analise.py \
        tests/test_persistence.py tests/test_api_analise.py \
        tests/golden/ data/payload_smoke_*.json
git commit -m "feat: pipeline E2E /analise com chains LLM e persistência"
```

---

# Milestone 4 — Frontend, Feedback e Aprendizado Contínuo (Semana 4)

## Task 4.1: Endpoint GET /historico

**Files:**
- Create: `backend/routes/historico.py`
- Modify: `backend/main.py`
- Create: `tests/test_api_historico.py`

- [ ] **Step 1: Escrever teste**

`tests/test_api_historico.py`:
```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_api_historico.py -v`
Expected: 404.

- [ ] **Step 3: Implementar router**

`backend/routes/historico.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Decisao

router = APIRouter()


@router.get("/historico")
def listar(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    q = (
        select(Decisao)
        .order_by(desc(Decisao.timestamp))
        .limit(limit).offset(offset)
    )
    decisoes = db.scalars(q).all()
    return [
        {
            "id": d.id,
            "solicitacao_id": d.solicitacao_id,
            "timestamp": d.timestamp.isoformat(),
            "dados_solicitante": d.dados_solicitante,
            "recomendacao": d.recomendacao,
            "confianca": d.confianca,
            "status_feedback": d.status_feedback,
            "parecer_humanizado": d.parecer_humanizado,
        }
        for d in decisoes
    ]
```

- [ ] **Step 4: Montar router**

Em `backend/main.py`, adicionar:
```python
from backend.routes import analise, historico

app.include_router(analise.router)
app.include_router(historico.router)
```

- [ ] **Step 5: Rodar testes**

Run: `uv run pytest tests/test_api_historico.py -v`
Expected: 2 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/historico.py backend/main.py tests/test_api_historico.py
git commit -m "feat: GET /historico com paginação"
```

---

## Task 4.2: Endpoint POST /feedback + aprendizado contínuo

**Files:**
- Create: `backend/routes/feedback.py`
- Modify: `backend/services/persistence.py` (adicionar `aplicar_feedback`)
- Create: `tests/test_api_feedback.py`

- [ ] **Step 1: Escrever teste**

`tests/test_api_feedback.py`:
```python
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Caso, Decisao


def _setup(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'f.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as s:
        d = Decisao(
            solicitacao_id=1, timestamp=datetime.now(UTC),
            dados_solicitante={
                "idade": 40, "renda_anual": 100_000, "estado_civil": "casado",
                "dependentes": 1, "tempo_emprego_meses": 60,
                "valor_solicitado": 30_000, "prazo_meses": 24,
                "finalidade": "custeio_agricola", "score_interno": 700,
                "divida_aberto": 10_000, "tipo_garantia": "fiador",
                "area_propriedade_ha": 50.0, "var_produtividade_pct": -2.0,
                "renegociacoes_recentes": 0, "atividade_principal": "agricultura",
            },
            casos_similares=[],
            parecer_tecnico='{"recomendacao": "aprovado"}',
            parecer_humanizado="x",
            recomendacao="aprovado", confianca=0.85,
            status_feedback="pendente",
        )
        s.add(d); s.commit()
        decisao_id = d.id

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db, SessionLocal, decisao_id


def test_feedback_aprovado_cria_caso_e_indexa(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock(); fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(f"/feedback/{decisao_id}", json={"status": "aprovado"})

    app.dependency_overrides.clear()

    assert r.status_code == 200
    with Session() as s:
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "aprovado"
        casos = s.query(Caso).all()
        assert len(casos) == 1
        assert casos[0].decisao_final == "aprovado"
        assert casos[0].inadimpliu is None  # ainda desconhecido
    fake_coll.add.assert_called_once()


def test_feedback_ajustado_grava_texto(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock(); fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(
            f"/feedback/{decisao_id}",
            json={"status": "ajustado", "parecer_ajustado": "Texto revisado pelo analista."},
        )

    app.dependency_overrides.clear()
    assert r.status_code == 200
    with Session() as s:
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "ajustado"
        assert d.parecer_ajustado == "Texto revisado pelo analista."


def test_feedback_rejeitado_nao_indexa(tmp_path_factory):
    override, Session, decisao_id = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_emb = MagicMock()
    fake_coll = MagicMock()
    with patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):
        client = TestClient(app)
        r = client.post(f"/feedback/{decisao_id}", json={"status": "rejeitado"})

    app.dependency_overrides.clear()
    assert r.status_code == 200
    fake_coll.add.assert_not_called()
    with Session() as s:
        casos = s.query(Caso).all()
        assert len(casos) == 0
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/test_api_feedback.py -v`
Expected: 404.

- [ ] **Step 3: Adicionar `aplicar_feedback` ao persistence**

Editar `backend/services/persistence.py`. **Adicionar estas importações no topo** (junto com as existentes):

```python
from backend.models import Caso
from backend.schemas import (
    AtividadePrincipal, FeedbackPayload, SolicitacaoCredito,
)
from backend.services.embeddings import EmbeddingsClient
from backend.services.narrativa import gerar_narrativa
from backend.services.rag import get_collection
```

E **acrescentar ao final do arquivo** a nova função:

```python
def aplicar_feedback(
    session: Session,
    decisao_id: int,
    payload: FeedbackPayload,
) -> Decisao:
    d = session.get(Decisao, decisao_id)
    if d is None:
        raise ValueError(f"Decisao {decisao_id} não encontrada")

    d.status_feedback = payload.status
    if payload.status == "ajustado":
        d.parecer_ajustado = payload.parecer_ajustado
    session.commit()

    # Aprendizado contínuo: aprovação cria registro em `caso` + indexa no Chroma
    if payload.status == "aprovado":
        s = SolicitacaoCredito(**d.dados_solicitante)
        novo_caso = Caso(
            idade=s.idade, renda_anual=s.renda_anual, estado_civil=s.estado_civil,
            dependentes=s.dependentes, tempo_emprego_meses=s.tempo_emprego_meses,
            valor_solicitado=s.valor_solicitado, prazo_meses=s.prazo_meses,
            finalidade=s.finalidade, score_interno=s.score_interno,
            divida_aberto=s.divida_aberto, tipo_garantia=s.tipo_garantia,
            area_propriedade_ha=s.area_propriedade_ha,
            var_produtividade_pct=s.var_produtividade_pct,
            renegociacoes_recentes=s.renegociacoes_recentes,
            atividade_principal=s.atividade_principal.value,
            decisao_final=d.recomendacao,
            inadimpliu=None,  # ainda desconhecido
        )
        session.add(novo_caso); session.commit(); session.refresh(novo_caso)

        narrativa = gerar_narrativa(s)
        emb = EmbeddingsClient()
        vec = emb.embed([narrativa])[0]
        get_collection().add(
            ids=[str(novo_caso.id)],
            documents=[narrativa],
            embeddings=[vec],
            metadatas=[{
                "id_caso": novo_caso.id,
                "decisao_final": d.recomendacao,
                "inadimpliu": False,
                "finalidade": s.finalidade,
                "atividade_principal": s.atividade_principal.value,
                "area_ha": float(s.area_propriedade_ha),
            }],
        )

    return d
```

- [ ] **Step 4: Implementar router**

`backend/routes/feedback.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import FeedbackPayload
from backend.services.persistence import aplicar_feedback

router = APIRouter()


@router.post("/feedback/{decisao_id}")
def registrar_feedback(
    decisao_id: int,
    payload: FeedbackPayload,
    db: Session = Depends(get_db),
) -> dict:
    try:
        d = aplicar_feedback(db, decisao_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": d.id, "status_feedback": d.status_feedback}
```

- [ ] **Step 5: Montar no main**

Em `backend/main.py`:
```python
from backend.routes import analise, feedback, historico

app.include_router(analise.router)
app.include_router(feedback.router)
app.include_router(historico.router)
```

- [ ] **Step 6: Rodar testes**

Run: `uv run pytest tests/test_api_feedback.py -v`
Expected: 3 tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/feedback.py backend/services/persistence.py \
        backend/main.py tests/test_api_feedback.py
git commit -m "feat: POST /feedback com aprendizado contínuo (re-indexação no Chroma)"
```

---

## Task 4.3: Frontend — formulário de nova análise

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/style.css`
- Create: `frontend/app.js`

- [ ] **Step 1: Criar style.css**

`frontend/style.css`:
```css
:root {
  --brand: #2c5f2d;
  --brand-soft: #97bc62;
  --warn: #d97706;
  --danger: #b91c1c;
}

body {
  background: #f7f8f5;
  color: #1f2937;
}

.navbar-brand {
  font-weight: 700;
  color: var(--brand) !important;
}

.card-siach {
  border-left: 4px solid var(--brand);
  border-radius: 8px;
}

.recomendacao-aprovado { color: #166534; font-weight: 700; }
.recomendacao-aprovado_com_ressalvas { color: var(--warn); font-weight: 700; }
.recomendacao-recusado { color: var(--danger); font-weight: 700; }

.parecer-humanizado {
  background: #ecfdf5;
  border-left: 4px solid var(--brand-soft);
  padding: 1rem;
  font-size: 1.05rem;
  line-height: 1.6;
}

.caso-similar {
  background: #f9fafb;
  border-left: 3px solid #9ca3af;
  padding: .6rem .8rem;
  margin-bottom: .5rem;
  font-size: .9rem;
}
```

- [ ] **Step 2: Criar index.html**

`frontend/index.html`:
```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SIACH — Nova análise</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <nav class="navbar navbar-light bg-white border-bottom mb-4">
    <div class="container">
      <a class="navbar-brand" href="/">SIACH</a>
      <div>
        <a href="/static/index.html" class="btn btn-sm btn-outline-success me-2">Nova análise</a>
        <a href="/static/historico.html" class="btn btn-sm btn-outline-secondary">Histórico</a>
      </div>
    </div>
  </nav>

  <main class="container">
    <h1 class="h3 mb-4">Nova solicitação de crédito</h1>

    <form id="form-analise" class="card card-siach p-4">
      <div class="row g-3">
        <div class="col-md-3"><label class="form-label">Idade</label>
          <input type="number" name="idade" min="18" max="100" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Estado civil</label>
          <select name="estado_civil" required class="form-select">
            <option value="solteiro">Solteiro(a)</option>
            <option value="casado">Casado(a)</option>
            <option value="divorciado">Divorciado(a)</option>
          </select></div>
        <div class="col-md-3"><label class="form-label">Dependentes</label>
          <input type="number" name="dependentes" min="0" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Tempo de atividade (meses)</label>
          <input type="number" name="tempo_emprego_meses" min="0" required class="form-control" /></div>

        <div class="col-md-3"><label class="form-label">Renda anual (R$)</label>
          <input type="number" name="renda_anual" step="0.01" min="0" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Valor solicitado (R$)</label>
          <input type="number" name="valor_solicitado" step="0.01" min="0" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Prazo (meses)</label>
          <input type="number" name="prazo_meses" min="6" max="60" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Score interno</label>
          <input type="number" name="score_interno" min="0" max="1000" required class="form-control" /></div>

        <div class="col-md-3"><label class="form-label">Dívida em aberto (R$)</label>
          <input type="number" name="divida_aberto" step="0.01" min="0" required class="form-control" /></div>
        <div class="col-md-3"><label class="form-label">Finalidade</label>
          <select name="finalidade" required class="form-select">
            <option value="custeio_agricola">Custeio agrícola</option>
            <option value="reformas">Reformas</option>
            <option value="negocio">Negócio</option>
            <option value="outros">Outros</option>
          </select></div>
        <div class="col-md-3"><label class="form-label">Tipo de garantia</label>
          <select name="tipo_garantia" required class="form-select">
            <option value="penhor_agricola">Penhor agrícola</option>
            <option value="fiador">Fiador</option>
            <option value="sem_garantia">Sem garantia</option>
          </select></div>
        <div class="col-md-3"><label class="form-label">Atividade principal</label>
          <select name="atividade_principal" required class="form-select">
            <option value="agricultura">Agricultura</option>
            <option value="pecuaria">Pecuária</option>
            <option value="mista">Mista</option>
          </select></div>

        <div class="col-md-4"><label class="form-label">Área da propriedade (ha)</label>
          <input type="number" name="area_propriedade_ha" step="0.1" min="0.1" required class="form-control" /></div>
        <div class="col-md-4"><label class="form-label">Variação de produtividade (%)</label>
          <input type="number" name="var_produtividade_pct" step="0.1" required class="form-control"
                 placeholder="negativo = queda" /></div>
        <div class="col-md-4"><label class="form-label">Renegociações recentes</label>
          <input type="number" name="renegociacoes_recentes" min="0" required class="form-control" /></div>
      </div>

      <button type="submit" class="btn btn-success mt-4">Analisar solicitação</button>
      <div id="form-error" class="text-danger mt-2"></div>
    </form>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Criar app.js**

`frontend/app.js`:
```javascript
const form = document.getElementById('form-analise');
if (form) {
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    document.getElementById('form-error').textContent = '';
    const data = Object.fromEntries(new FormData(form).entries());
    // Converter números
    const numericos = [
      'idade','dependentes','tempo_emprego_meses','prazo_meses',
      'score_interno','renegociacoes_recentes',
    ];
    const floats = [
      'renda_anual','valor_solicitado','divida_aberto',
      'area_propriedade_ha','var_produtividade_pct',
    ];
    numericos.forEach(k => data[k] = parseInt(data[k], 10));
    floats.forEach(k => data[k] = parseFloat(data[k]));

    const submitBtn = form.querySelector('button[type=submit]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analisando...';

    try {
      const r = await fetch('/analise', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        throw new Error(detail.detail ? JSON.stringify(detail.detail) : `HTTP ${r.status}`);
      }
      const body = await r.json();
      sessionStorage.setItem('siach.last_resultado', JSON.stringify(body));
      window.location.href = '/static/resultado.html';
    } catch (e) {
      document.getElementById('form-error').textContent = String(e);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Analisar solicitação';
    }
  });
}
```

- [ ] **Step 4: Servir arquivos estáticos no FastAPI**

Adicionar ao `backend/main.py` (depois dos `include_router`):
```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

_FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="static")


@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")
```

- [ ] **Step 5: Smoke manual**

Run: `uv run uvicorn backend.main:app --reload`
Abrir `http://localhost:8000` no navegador. Deve abrir o formulário.

- [ ] **Step 6: Commit**

```bash
git add frontend/ backend/main.py
git commit -m "feat: frontend HTML/Bootstrap com formulário de nova análise"
```

---

## Task 4.4: Frontend — página de resultado com feedback

**Files:**
- Create: `frontend/resultado.html`
- Modify: `frontend/app.js`

- [ ] **Step 1: Criar resultado.html**

`frontend/resultado.html`:
```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SIACH — Resultado</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <nav class="navbar navbar-light bg-white border-bottom mb-4">
    <div class="container">
      <a class="navbar-brand" href="/">SIACH</a>
      <div>
        <a href="/static/index.html" class="btn btn-sm btn-outline-success me-2">Nova análise</a>
        <a href="/static/historico.html" class="btn btn-sm btn-outline-secondary">Histórico</a>
      </div>
    </div>
  </nav>

  <main class="container" id="resultado-root">
    <h1 class="h3 mb-4">Resultado da análise</h1>
    <div id="conteudo">Carregando...</div>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Estender app.js**

Adicionar ao final de `frontend/app.js`:
```javascript
const resultadoRoot = document.getElementById('resultado-root');
if (resultadoRoot) {
  const raw = sessionStorage.getItem('siach.last_resultado');
  if (!raw) {
    document.getElementById('conteudo').textContent = 'Nenhum resultado para exibir. Faça uma nova análise.';
  } else {
    const body = JSON.parse(raw);
    document.getElementById('conteudo').innerHTML = renderResultado(body);
    bindFeedbackButtons(body.decisao_id);
  }
}

function renderResultado(body) {
  const pt = body.parecer_tecnico;
  const cls = `recomendacao-${pt.recomendacao}`;
  const similares = body.casos_similares.map(c => `
    <div class="caso-similar">
      <strong>Caso #${c.caso_id}</strong> · decisão original: ${c.decisao_final} · score ${c.score.toFixed(2)}
      <div class="text-muted small mt-1">${escapeHtml(c.narrativa).slice(0, 240)}…</div>
    </div>
  `).join('');

  return `
    <div class="card card-siach p-4 mb-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <span class="${cls}">Recomendação: ${pt.recomendacao.replace(/_/g, ' ')}</span>
        <span class="text-muted">Confiança: ${(pt.confianca * 100).toFixed(0)}%</span>
      </div>
      <div class="parecer-humanizado mb-3">${escapeHtml(body.parecer_humanizado)}</div>

      <h5 class="mt-3">Análise técnica</h5>
      <div class="row">
        <div class="col-md-6">
          <h6>Fatores favoráveis</h6>
          <ul>${pt.fatores_favoraveis.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
        </div>
        <div class="col-md-6">
          <h6>Fatores de risco</h6>
          <ul>${pt.fatores_de_risco.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
        </div>
      </div>
      <h6>Comparação histórica</h6>
      <p>${escapeHtml(pt.comparacao_historica)}</p>
      <h6>Recomendações de ação</h6>
      <ul>${pt.recomendacoes_acao.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
    </div>

    <h5>Casos similares consultados</h5>
    ${similares || '<p class="text-muted">Nenhum caso similar.</p>'}

    <div class="mt-4 p-3 bg-white border rounded">
      <h5>Feedback do analista</h5>
      <p class="text-muted small">Aprovar registra este caso na base e o disponibiliza para futuras análises.</p>
      <div class="d-flex gap-2 flex-wrap">
        <button class="btn btn-success" data-feedback="aprovado">Aprovar</button>
        <button class="btn btn-warning" data-feedback="ajustado">Ajustar parecer</button>
        <button class="btn btn-outline-danger" data-feedback="rejeitado">Rejeitar</button>
      </div>
      <div id="feedback-msg" class="mt-2"></div>
      <textarea id="feedback-ajuste" class="form-control mt-2 d-none" rows="3"
        placeholder="Texto revisado pelo analista..."></textarea>
    </div>
  `;
}

function bindFeedbackButtons(decisaoId) {
  const ajusteBox = document.getElementById('feedback-ajuste');
  document.querySelectorAll('[data-feedback]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const status = btn.dataset.feedback;
      if (status === 'ajustado' && ajusteBox.classList.contains('d-none')) {
        ajusteBox.classList.remove('d-none');
        ajusteBox.focus();
        return;
      }
      const payload = { status };
      if (status === 'ajustado') payload.parecer_ajustado = ajusteBox.value;
      const r = await fetch(`/feedback/${decisaoId}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const msg = document.getElementById('feedback-msg');
      if (r.ok) {
        msg.innerHTML = `<span class="text-success">Feedback registrado.</span>`;
        document.querySelectorAll('[data-feedback]').forEach(b => b.disabled = true);
      } else {
        const detail = await r.json().catch(() => ({}));
        msg.innerHTML = `<span class="text-danger">Erro: ${escapeHtml(JSON.stringify(detail.detail || ''))}</span>`;
      }
    });
  });
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}
```

- [ ] **Step 2.5: Smoke manual**

1. Abrir `http://localhost:8000`, preencher formulário, submeter.
2. Verificar que a página de resultado abre com parecer técnico + humanizado + 5 casos similares.
3. Clicar em "Aprovar". Mensagem de sucesso aparece.
4. Verificar no SQLite (`sqlite3 siach.db "SELECT id, recomendacao, status_feedback FROM decisao;"`) que `status_feedback = aprovado`.
5. Verificar que um novo registro apareceu em `caso` (último id).

- [ ] **Step 3: Commit**

```bash
git add frontend/resultado.html frontend/app.js
git commit -m "feat: página de resultado com parecer + casos similares + feedback"
```

---

## Task 4.5: Frontend — página de histórico

**Files:**
- Create: `frontend/historico.html`
- Modify: `frontend/app.js` (adicionar render do histórico)

- [ ] **Step 1: Criar historico.html**

`frontend/historico.html`:
```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SIACH — Histórico</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <nav class="navbar navbar-light bg-white border-bottom mb-4">
    <div class="container">
      <a class="navbar-brand" href="/">SIACH</a>
      <div>
        <a href="/static/index.html" class="btn btn-sm btn-outline-success me-2">Nova análise</a>
        <a href="/static/historico.html" class="btn btn-sm btn-outline-secondary">Histórico</a>
      </div>
    </div>
  </nav>

  <main class="container" id="historico-root">
    <h1 class="h3 mb-4">Histórico de análises</h1>
    <div id="historico-conteudo">Carregando...</div>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Estender app.js**

Adicionar ao final de `frontend/app.js`:
```javascript
const histRoot = document.getElementById('historico-root');
if (histRoot) {
  fetch('/historico?limit=100').then(r => r.json()).then(items => {
    document.getElementById('historico-conteudo').innerHTML = renderHistorico(items);
  });
}

function renderHistorico(items) {
  if (!items.length) return '<p class="text-muted">Nenhuma análise registrada ainda.</p>';
  return `
    <table class="table table-sm">
      <thead>
        <tr>
          <th>#</th>
          <th>Data</th>
          <th>Atividade</th>
          <th>Valor solicitado</th>
          <th>Recomendação</th>
          <th>Confiança</th>
          <th>Feedback</th>
        </tr>
      </thead>
      <tbody>
        ${items.map(it => `
          <tr>
            <td>${it.id}</td>
            <td>${new Date(it.timestamp).toLocaleString('pt-BR')}</td>
            <td>${escapeHtml(it.dados_solicitante.atividade_principal || '—')}</td>
            <td>R$ ${(it.dados_solicitante.valor_solicitado || 0).toLocaleString('pt-BR')}</td>
            <td><span class="recomendacao-${it.recomendacao}">${it.recomendacao.replace(/_/g, ' ')}</span></td>
            <td>${(it.confianca * 100).toFixed(0)}%</td>
            <td>${escapeHtml(it.status_feedback)}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}
```

- [ ] **Step 3: Smoke manual**

Acessar `http://localhost:8000/static/historico.html`. Deve listar todas as decisões registradas, ordenadas por timestamp desc.

- [ ] **Step 4: Commit**

```bash
git add frontend/historico.html frontend/app.js
git commit -m "feat: página de histórico de análises"
```

---

## Task 4.6: Teste E2E e gate de fallback

**Files:**
- Create: `tests/test_e2e.py`
- Create: `docs/superpowers/specs/2026-04-26-siach-design.md` (atualizar status do gate)

- [ ] **Step 1: Escrever teste E2E**

`tests/test_e2e.py`:
```python
"""
Teste E2E que exercita /analise (com mocks de LLM e RAG), /feedback e /historico.
Verifica que o ciclo completo funciona e que aprovar uma análise indexa um caso.
"""
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Caso, Decisao
from backend.schemas import CasoSimilar, ParecerTecnico, Recomendacao


def _override_db(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'e.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
    return _get_db, SessionLocal


def _payload():
    return {
        "idade": 45, "renda_anual": 180_000, "estado_civil": "casado",
        "dependentes": 2, "tempo_emprego_meses": 120,
        "valor_solicitado": 120_000, "prazo_meses": 12,
        "finalidade": "custeio_agricola", "score_interno": 580,
        "divida_aberto": 45_000, "tipo_garantia": "penhor_agricola",
        "area_propriedade_ha": 80.0, "var_produtividade_pct": -15.0,
        "renegociacoes_recentes": 2, "atividade_principal": "mista",
    }


def test_ciclo_completo(tmp_path_factory):
    override, Session = _override_db(tmp_path_factory)
    app.dependency_overrides[get_db] = override

    fake_rag = MagicMock()
    fake_rag.recuperar.return_value = [CasoSimilar(
        caso_id=1, score=0.9, narrativa="x",
        decisao_final=Recomendacao.APROVADO, inadimpliu=False,
    )]
    fake_analise = MagicMock()
    fake_analise.run.return_value = ParecerTecnico(
        recomendacao=Recomendacao.APROVADO_COM_RESSALVAS,
        confianca=0.7,
        fatores_favoraveis=["renda compatível"],
        fatores_de_risco=["queda de produtividade"],
        comparacao_historica="x",
        recomendacoes_acao=["revisar planejamento"],
    )
    fake_humaniz = MagicMock()
    fake_humaniz.run.return_value = "Olá, Sr(a)..."

    fake_emb = MagicMock(); fake_emb.embed.return_value = [[0.1] * 1024]
    fake_coll = MagicMock()

    client = TestClient(app)

    with patch("backend.routes.analise.RAGService", return_value=fake_rag), \
         patch("backend.routes.analise.AnaliseChain", return_value=fake_analise), \
         patch("backend.routes.analise.HumanizacaoChain", return_value=fake_humaniz), \
         patch("backend.services.persistence.EmbeddingsClient", return_value=fake_emb), \
         patch("backend.services.persistence.get_collection", return_value=fake_coll):

        # 1) POST /analise
        r1 = client.post("/analise", json=_payload())
        assert r1.status_code == 200
        body = r1.json()
        decisao_id = body["decisao_id"]

        # 2) /historico já mostra a análise
        r2 = client.get("/historico")
        assert r2.status_code == 200
        assert any(it["id"] == decisao_id for it in r2.json())

        # 3) POST /feedback aprovado
        r3 = client.post(f"/feedback/{decisao_id}", json={"status": "aprovado"})
        assert r3.status_code == 200

    app.dependency_overrides.clear()

    # 4) Verifica que um novo Caso foi criado e indexado
    with Session() as s:
        casos = s.query(Caso).all()
        assert len(casos) == 1
        assert casos[0].decisao_final == "aprovado_com_ressalvas"
        d = s.get(Decisao, decisao_id)
        assert d.status_feedback == "aprovado"
    fake_coll.add.assert_called_once()
```

- [ ] **Step 2: Rodar todos os testes**

Run: `uv run pytest -v`
Expected: TODOS os testes passam.

- [ ] **Step 3: Smoke real (E2E com Claude e Voyage de verdade)**

Pré-requisitos:
- `.env` com chaves reais
- `./scripts/seed.sh` rodado com sucesso
- Servidor rodando: `uv run uvicorn backend.main:app --reload`

Passos manuais:
1. Abrir 5 casos diferentes no formulário (variar atividade, var_produtividade_pct, score, área)
2. Para cada um:
   - Verificar que parecer técnico tem JSON válido nos 6 campos
   - Verificar que parecer humanizado é texto fluido em pt-br
   - Verificar que cita pelo menos um fator presente no caso
   - Verificar que latência < 12s (alvo do spec é 8s, mas em desenvolvimento aceita-se até 12s)
3. Aprovar uma análise. Confirmar que aparece como caso similar em uma análise subsequente similar.

- [ ] **Step 4: Avaliação do gate de fallback**

Critério explícito do spec (§9.1): "**os pareceres do SIACH são minimamente coerentes nos casos manuais testados na S3?**"

Marcar abaixo:

- [ ] **PASSA** — pareceres coerentes em ≥ 4 dos 5 casos. Continuar com Abordagem B (RAG completo).
- [ ] **FALHA** — pareceres incoerentes em ≥ 2 casos. Iniciar fallback Abordagem A: criar
      novo plano `2026-XX-XX-siach-fallback-knn.md` substituindo etapas 3 e 4 por
      `KNNAnaliseService` que vota pela maioria entre os k vizinhos, mantendo etapas
      5 e 6 intactas.

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: E2E do ciclo completo /analise → /feedback → /historico"
```

---

# Próximos planos (não cobertos aqui)

Após este plano, criar planos separados para:

1. **`2026-XX-XX-siach-validacao-experimental.md`** — implementa `experiments/baseline_kn.py`, `run_evaluation.py`, `metrics.py` e o notebook `analise_resultados.ipynb`. Cobre os Experimentos 1, 2 e 3 do spec (S5–S6).
2. **Escrita da monografia (S7–S8)** — não precisa de plano de implementação; é texto.
