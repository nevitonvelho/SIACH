# Módulo de Avaliação da Qualidade do RAG — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que 5 analistas deem nota 0–10 às mesmas 10 análises do RAG, com link próprio por analista, e ver os resultados num dashboard com export CSV.

**Architecture:** Duas tabelas novas (`estudo_item`, `avaliacao`) criadas no boot via `create_all` (sem migração). As 10 análises são geradas pelo pipeline real através de um endpoint idempotente `POST /estudo/seed` (protegido por token), chamado uma vez após o deploy. Frontend em HTML/JS vanilla + Bootstrap, no padrão das páginas existentes.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest + TestClient, Bootstrap 5.3, JS vanilla. Gerenciado com `uv`.

**Convenções do projeto (já observadas):**
- Testes criam engine SQLite temporário, `Base.metadata.create_all`, e fazem `app.dependency_overrides[get_db] = override`. Usam `TestClient(app)` **sem** `with` (não dispara o lifespan).
- Rodar testes: `uv run pytest <caminho> -v`.
- Frontend: Bootstrap + `/static/style.css`; classes `recomendacao-<valor>`; helper `escapeHtml`.

---

### Task 1: Config — token do estudo

**Files:**
- Modify: `backend/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_config.py`:

```python
def test_estudo_token_default_e_override(monkeypatch):
    from backend.config import Settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.delenv("ESTUDO_TOKEN", raising=False)
    assert Settings().estudo_token == "troque-este-token"
    monkeypatch.setenv("ESTUDO_TOKEN", "segredo123")
    assert Settings().estudo_token == "segredo123"
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `uv run pytest tests/test_config.py::test_estudo_token_default_e_override -v`
Expected: FAIL (`AttributeError`/`ValidationError`: `estudo_token` não existe).

- [ ] **Step 3: Implementar**

Em `backend/config.py`, dentro da classe `Settings`, adicionar o campo (depois de `log_level`):

```python
    estudo_token: str = "troque-este-token"
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/config.py tests/test_config.py
git commit -m "feat(config): adiciona estudo_token (env ESTUDO_TOKEN)"
```

---

### Task 2: Models — `EstudoItem` e `Avaliacao`

**Files:**
- Modify: `backend/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_models.py`:

```python
def test_estudo_item_e_avaliacao(tmp_path):
    from datetime import datetime, UTC
    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker
    from backend.db import Base
    from backend.models import Avaliacao, EstudoItem

    engine = create_engine(f"sqlite:///{tmp_path/'m.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        s.add(EstudoItem(decisao_id=1, ordem=1))
        s.add(Avaliacao(analista="ana", decisao_id=1, nota=8, timestamp=datetime.now(UTC)))
        s.commit()

    # Único composto (analista, decisao_id)
    with Session() as s:
        s.add(Avaliacao(analista="ana", decisao_id=1, nota=3, timestamp=datetime.now(UTC)))
        try:
            s.commit()
            assert False, "esperava IntegrityError"
        except IntegrityError:
            s.rollback()
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `uv run pytest tests/test_models.py::test_estudo_item_e_avaliacao -v`
Expected: FAIL (`ImportError: cannot import name 'EstudoItem'`).

- [ ] **Step 3: Implementar**

Em `backend/models.py`, ajustar o import do topo e adicionar as classes ao final:

```python
from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint,
)
```

```python
class EstudoItem(Base):
    __tablename__ = "estudo_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decisao_id: Mapped[int] = mapped_column(ForeignKey("decisao.id"), unique=True)
    ordem: Mapped[int] = mapped_column(Integer)


class Avaliacao(Base):
    __tablename__ = "avaliacao"
    __table_args__ = (
        UniqueConstraint("analista", "decisao_id", name="uq_analista_decisao"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analista: Mapped[str] = mapped_column(String(64))
    decisao_id: Mapped[int] = mapped_column(ForeignKey("decisao.id"))
    nota: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models.py tests/test_models.py
git commit -m "feat(models): EstudoItem e Avaliacao"
```

---

### Task 3: Schema — `AvaliacaoPayload`

**Files:**
- Modify: `backend/schemas.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_schemas.py`:

```python
def test_avaliacao_payload_valida_nota():
    import pytest
    from pydantic import ValidationError
    from backend.schemas import AvaliacaoPayload

    ok = AvaliacaoPayload(analista="ana", decisao_id=1, nota=10)
    assert ok.nota == 10
    with pytest.raises(ValidationError):
        AvaliacaoPayload(analista="ana", decisao_id=1, nota=11)
    with pytest.raises(ValidationError):
        AvaliacaoPayload(analista="ana", decisao_id=1, nota=-1)
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `uv run pytest tests/test_schemas.py::test_avaliacao_payload_valida_nota -v`
Expected: FAIL (`ImportError: cannot import name 'AvaliacaoPayload'`).

- [ ] **Step 3: Implementar**

Adicionar ao final de `backend/schemas.py`:

```python
class AvaliacaoPayload(BaseModel):
    analista: str = Field(min_length=1, max_length=64)
    decisao_id: int
    nota: int = Field(ge=0, le=10)
```

- [ ] **Step 4: Rodar o teste e ver passar**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py tests/test_schemas.py
git commit -m "feat(schemas): AvaliacaoPayload (nota 0-10)"
```

---

### Task 4: Service — `estudo.py` (10 curadas, seed, upsert, agregação, CSV)

**Files:**
- Create: `backend/services/estudo.py`
- Test: `tests/test_estudo_service.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_estudo_service.py`:

```python
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
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `uv run pytest tests/test_estudo_service.py -v`
Expected: FAIL (`ModuleNotFoundError: backend.services.estudo`).

- [ ] **Step 3: Implementar o service**

Criar `backend/services/estudo.py`:

```python
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
```

- [ ] **Step 4: Rodar os testes e ver passar**

Run: `uv run pytest tests/test_estudo_service.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add backend/services/estudo.py tests/test_estudo_service.py
git commit -m "feat(estudo): service de seed, upsert de notas, agregacao e CSV"
```

---

### Task 5: Routes — `estudo.py` + registro no `main.py`

**Files:**
- Create: `backend/routes/estudo.py`
- Modify: `backend/main.py`
- Test: `tests/test_api_estudo.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_api_estudo.py`:

```python
from datetime import datetime, UTC

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings
from backend.db import Base, get_db
from backend.main import app
from backend.models import Decisao, EstudoItem


def _setup(tmp_path_factory):
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('db')/'a.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        d = Decisao(
            solicitacao_id=1, timestamp=datetime.now(UTC),
            dados_solicitante={"atividade_principal": "agricultura", "valor_solicitado": 1000},
            casos_similares=[], parecer_tecnico='{"recomendacao":"aprovado"}',
            parecer_humanizado="texto", recomendacao="aprovado", confianca=0.8,
            status_feedback="pendente",
        )
        s.add(d); s.commit()
        s.add(EstudoItem(decisao_id=d.id, ordem=1)); s.commit()
        did = d.id

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()
    return _get_db, Session, did


def test_post_avaliacao_e_retomar(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)

    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 7})
    assert r.status_code == 200
    # upsert: re-enviar atualiza
    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 9})
    assert r.status_code == 200

    r = client.get("/avaliacoes/ana")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {str(did): 9}


def test_post_avaliacao_nota_invalida(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    r = client.post("/avaliacoes", json={"analista": "ana", "decisao_id": did, "nota": 11})
    app.dependency_overrides.clear()
    assert r.status_code == 422


def test_resultados_dados_exige_token(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    token = get_settings().estudo_token

    r = client.get("/resultados/dados")  # sem token
    assert r.status_code == 403
    r = client.get(f"/resultados/dados?token={token}")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert body["total_itens"] == 1
    assert body["por_analise"][0]["decisao_id"] == did


def test_estudo_analises_lista(tmp_path_factory):
    override, Session, did = _setup(tmp_path_factory)
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    r = client.get("/estudo/analises")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    itens = r.json()
    assert len(itens) == 1
    assert itens[0]["decisao_id"] == did
    assert itens[0]["parecer_humanizado"] == "texto"
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `uv run pytest tests/test_api_estudo.py -v`
Expected: FAIL (rotas `/avaliacoes`, `/resultados/dados`, `/estudo/analises` retornam 404).

- [ ] **Step 3: Implementar as rotas**

Criar `backend/routes/estudo.py`:

```python
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import get_db
from backend.models import Avaliacao, Decisao, EstudoItem
from backend.schemas import AvaliacaoPayload
from backend.services import estudo as svc

router = APIRouter()
_FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"


def _check_token(token: str) -> None:
    if token != get_settings().estudo_token:
        raise HTTPException(status_code=403, detail="token inválido")


@router.get("/avaliar/{analista}")
def pagina_avaliar(analista: str):
    return FileResponse(str(_FRONTEND_DIR / "avaliar.html"))


@router.get("/resultados")
def pagina_resultados():
    return FileResponse(str(_FRONTEND_DIR / "resultados.html"))


@router.get("/estudo/analises")
def listar_analises(db: Session = Depends(get_db)) -> list[dict]:
    itens = db.scalars(select(EstudoItem).order_by(EstudoItem.ordem)).all()
    out = []
    for item in itens:
        d = db.get(Decisao, item.decisao_id)
        if d is None:
            continue
        out.append({
            "decisao_id": d.id, "ordem": item.ordem,
            "recomendacao": d.recomendacao, "confianca": d.confianca,
            "dados_solicitante": d.dados_solicitante,
            "parecer_humanizado": d.parecer_humanizado,
            "parecer_tecnico": json.loads(d.parecer_tecnico),
            "casos_similares": d.casos_similares,
        })
    return out


@router.get("/avaliacoes/{analista}")
def avaliacoes_do_analista(analista: str, db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Avaliacao).where(Avaliacao.analista == analista)
    ).all()
    return {str(r.decisao_id): r.nota for r in rows}


@router.post("/avaliacoes")
def registrar_avaliacao(
    payload: AvaliacaoPayload, db: Session = Depends(get_db),
) -> dict:
    if db.get(Decisao, payload.decisao_id) is None:
        raise HTTPException(status_code=404, detail="decisao não encontrada")
    av = svc.upsert_avaliacao(db, payload)
    return {"id": av.id, "decisao_id": av.decisao_id, "nota": av.nota}


@router.post("/estudo/seed")
def seed(token: str = Query(""), db: Session = Depends(get_db)) -> dict:
    _check_token(token)
    ids = svc.seed_estudo(db)
    return {"decisao_ids": ids, "total": len(ids)}


@router.get("/resultados/dados")
def resultados_dados(token: str = Query(""), db: Session = Depends(get_db)) -> dict:
    _check_token(token)
    return svc.agregar_resultados(db)


@router.get("/resultados.csv")
def resultados_csv(token: str = Query(""), db: Session = Depends(get_db)) -> Response:
    _check_token(token)
    csv_text = svc.gerar_csv(db)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=avaliacoes.csv"},
    )
```

- [ ] **Step 4: Registrar o router no `main.py`**

Em `backend/main.py`, no bloco de imports trocar:

```python
from backend.routes import analise, feedback, historico
```

por:

```python
from backend.routes import analise, estudo, feedback, historico
```

E logo após `app.include_router(historico.router)` adicionar:

```python
app.include_router(estudo.router)
```

- [ ] **Step 5: Rodar os testes e ver passar**

Run: `uv run pytest tests/test_api_estudo.py -v`
Expected: PASS (4 testes).

- [ ] **Step 6: Rodar a suíte inteira (sem regressões)**

Run: `uv run pytest -q`
Expected: todos os testes passam.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/estudo.py backend/main.py tests/test_api_estudo.py
git commit -m "feat(estudo): rotas de avaliacao, seed, resultados e CSV"
```

---

### Task 6: Frontend — página do analista (`avaliar.html` + `avaliar.js`)

**Files:**
- Create: `frontend/avaliar.html`
- Create: `frontend/avaliar.js`

Não há infra de teste de frontend no projeto; a verificação é manual no navegador (Step final).

- [ ] **Step 1: Criar `frontend/avaliar.html`**

```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SIACH — Avaliação</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
  <style>
    .nota-btn{width:44px;height:44px;border-radius:8px;border:1px solid #cfcfcf;background:#fafafa;font-weight:600}
    .nota-btn.ativa{background:#198754;color:#fff;border-color:#198754}
    .nota-row{display:flex;gap:6px;flex-wrap:wrap}
  </style>
</head>
<body>
  <nav class="navbar navbar-light bg-white border-bottom mb-4">
    <div class="container">
      <span class="navbar-brand">SIACH — Avaliação</span>
      <span class="text-muted" id="analista-label"></span>
    </div>
  </nav>

  <main class="container" id="avaliar-root" style="max-width:760px">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1 class="h4 mb-0" id="progresso">Carregando…</h1>
      <span class="badge bg-secondary" id="contador"></span>
    </div>
    <div id="conteudo"></div>
    <div class="d-flex justify-content-between mt-4">
      <button class="btn btn-outline-secondary" id="btn-anterior">‹ Anterior</button>
      <button class="btn btn-success" id="btn-proxima">Próxima ›</button>
    </div>
    <div id="msg" class="mt-2 small"></div>
  </main>

  <script src="/static/avaliar.js"></script>
</body>
</html>
```

- [ ] **Step 2: Criar `frontend/avaliar.js`**

```javascript
const analista = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
document.getElementById('analista-label').textContent = analista ? `Olá, ${analista}` : '';

let analises = [];
let notas = {};        // { decisao_id: nota }
let idx = 0;

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function carregar() {
  const [a, n] = await Promise.all([
    fetch('/estudo/analises').then(r => r.json()),
    fetch(`/avaliacoes/${encodeURIComponent(analista)}`).then(r => r.json()),
  ]);
  analises = a;
  notas = n;
  if (!analises.length) {
    document.getElementById('conteudo').innerHTML =
      '<p class="text-muted">Nenhuma análise disponível ainda. Volte mais tarde.</p>';
    document.getElementById('progresso').textContent = 'Avaliação';
    return;
  }
  // Retoma na primeira sem nota, se houver
  const primeiraSemNota = analises.findIndex(x => !(String(x.decisao_id) in notas));
  idx = primeiraSemNota >= 0 ? primeiraSemNota : 0;
  render();
}

function render() {
  const item = analises[idx];
  const pt = item.parecer_tecnico;
  const ds = item.dados_solicitante || {};
  document.getElementById('progresso').textContent = `Análise ${idx + 1} de ${analises.length}`;
  const avaliadas = analises.filter(x => String(x.decisao_id) in notas).length;
  document.getElementById('contador').textContent = `${avaliadas}/${analises.length} avaliadas`;

  const notaAtual = notas[String(item.decisao_id)];
  const escala = Array.from({length: 11}, (_, i) =>
    `<button class="nota-btn ${notaAtual === i ? 'ativa' : ''}" data-nota="${i}">${i}</button>`
  ).join('');

  const similares = (item.casos_similares || []).map(c =>
    `<li class="small text-muted">Caso #${c.caso_id} · ${c.decisao_final} · score ${Number(c.score).toFixed(2)}</li>`
  ).join('');

  document.getElementById('conteudo').innerHTML = `
    <div class="card card-siach p-4">
      <div class="d-flex justify-content-between mb-2">
        <span class="recomendacao-${item.recomendacao}">Recomendação: ${String(item.recomendacao).replace(/_/g,' ')}</span>
        <span class="text-muted">Confiança: ${(item.confianca * 100).toFixed(0)}%</span>
      </div>
      <p class="text-muted small mb-2">
        ${escapeHtml(ds.atividade_principal || '')} ·
        R$ ${(ds.valor_solicitado || 0).toLocaleString('pt-BR')} ·
        ${ds.prazo_meses || '—'} meses · score ${ds.score_interno ?? '—'}
      </p>
      <div class="parecer-humanizado mb-3">${escapeHtml(item.parecer_humanizado)}</div>
      <details class="mb-3">
        <summary>Detalhes técnicos e casos similares</summary>
        <h6 class="mt-2">Fatores favoráveis</h6>
        <ul>${(pt.fatores_favoraveis||[]).map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul>
        <h6>Fatores de risco</h6>
        <ul>${(pt.fatores_de_risco||[]).map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul>
        <h6>Casos similares</h6>
        <ul>${similares || '<li class="small text-muted">—</li>'}</ul>
      </details>
      <label class="form-label fw-bold text-success">Sua nota para esta análise (0–10):</label>
      <div class="nota-row" id="nota-row">${escala}</div>
    </div>
  `;

  document.querySelectorAll('#nota-row .nota-btn').forEach(btn => {
    btn.addEventListener('click', () => salvarNota(item.decisao_id, parseInt(btn.dataset.nota, 10)));
  });

  document.getElementById('btn-anterior').disabled = idx === 0;
  document.getElementById('btn-proxima').disabled = idx >= analises.length - 1;
}

async function salvarNota(decisaoId, nota) {
  const msg = document.getElementById('msg');
  try {
    const r = await fetch('/avaliacoes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ analista, decisao_id: decisaoId, nota }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    notas[String(decisaoId)] = nota;
    msg.innerHTML = '<span class="text-success">Nota salva.</span>';
    render();
    // Avança automaticamente se não for a última
    if (idx < analises.length - 1) { setTimeout(() => { idx++; render(); }, 250); }
    else { msg.innerHTML = '<span class="text-success">Obrigado! Você avaliou todas as análises. 🎉</span>'; }
  } catch (e) {
    msg.innerHTML = `<span class="text-danger">Erro ao salvar: ${escapeHtml(String(e))}</span>`;
  }
}

document.getElementById('btn-anterior').addEventListener('click', () => { if (idx > 0) { idx--; render(); } });
document.getElementById('btn-proxima').addEventListener('click', () => { if (idx < analises.length - 1) { idx++; render(); } });

carregar();
```

- [ ] **Step 3: Verificação manual (local)**

Pré-requisito: ter ao menos 1 item de estudo no banco local. Se o `siach.db` local não tiver, rode o seed local primeiro:

```bash
uv run python -c "from backend.db import Base,get_engine;from backend.services.estudo import seed_estudo;from backend.db import get_session_factory;Base.metadata.create_all(get_engine());s=get_session_factory()();seed_estudo(s);s.close()"
```

Subir o app e abrir a página:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

No navegador: `http://localhost:8000/avaliar/analista-1`
Esperado: wizard carrega, mostra "Análise 1 de N", clicar numa nota salva (aparece "Nota salva.") e avança; recarregar a página retoma as notas já dadas.

- [ ] **Step 4: Commit**

```bash
git add frontend/avaliar.html frontend/avaliar.js
git commit -m "feat(frontend): pagina do analista (wizard de avaliacao 0-10)"
```

---

### Task 7: Frontend — dashboard de resultados (`resultados.html` + `resultados.js`)

**Files:**
- Create: `frontend/resultados.html`
- Create: `frontend/resultados.js`

- [ ] **Step 1: Criar `frontend/resultados.html`**

```html
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SIACH — Resultados do Estudo</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <nav class="navbar navbar-light bg-white border-bottom mb-4">
    <div class="container">
      <span class="navbar-brand">SIACH — Resultados do Estudo</span>
      <a href="#" id="link-csv" class="btn btn-sm btn-outline-success">Exportar CSV</a>
    </div>
  </nav>
  <main class="container" id="resultados-root">
    <div id="conteudo">Carregando…</div>
  </main>
  <script src="/static/resultados.js"></script>
</body>
</html>
```

- [ ] **Step 2: Criar `frontend/resultados.js`**

```javascript
const token = new URLSearchParams(location.search).get('token') || '';
document.getElementById('link-csv').href = `/resultados.csv?token=${encodeURIComponent(token)}`;

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function carregar() {
  const r = await fetch(`/resultados/dados?token=${encodeURIComponent(token)}`);
  const cont = document.getElementById('conteudo');
  if (r.status === 403) { cont.innerHTML = '<p class="text-danger">Token inválido. Use /resultados?token=SEU_TOKEN</p>'; return; }
  const d = await r.json();

  const linhasAnalise = d.por_analise.map(p => `
    <tr>
      <td>${p.ordem}</td>
      <td>${p.decisao_id}</td>
      <td><span class="recomendacao-${p.recomendacao}">${String(p.recomendacao).replace(/_/g,' ')}</span></td>
      <td><strong>${p.media ?? '—'}</strong></td>
      <td>${p.n_notas}</td>
    </tr>`).join('');

  const linhasAnalista = d.por_analista.map(p => `
    <tr>
      <td>${escapeHtml(p.analista)}</td>
      <td><strong>${p.media ?? '—'}</strong></td>
      <td>${p.avaliadas}</td>
      <td>${p.faltam}</td>
    </tr>`).join('');

  cont.innerHTML = `
    <h2 class="h5">Por análise (${d.total_itens})</h2>
    <table class="table table-sm">
      <thead><tr><th>Ordem</th><th>Decisão</th><th>Recomendação</th><th>Nota média</th><th>Nº notas</th></tr></thead>
      <tbody>${linhasAnalise || '<tr><td colspan="5" class="text-muted">Sem itens.</td></tr>'}</tbody>
    </table>
    <h2 class="h5 mt-4">Por analista</h2>
    <table class="table table-sm">
      <thead><tr><th>Analista</th><th>Nota média</th><th>Avaliadas</th><th>Faltam</th></tr></thead>
      <tbody>${linhasAnalista || '<tr><td colspan="4" class="text-muted">Nenhuma avaliação ainda.</td></tr>'}</tbody>
    </table>
  `;
}

carregar();
```

- [ ] **Step 3: Verificação manual (local)**

Com o app rodando (Task 6, Step 3) e ao menos uma nota registrada, abrir:
`http://localhost:8000/resultados?token=troque-este-token`
Esperado: tabelas "Por análise" e "Por analista" com as médias; botão "Exportar CSV" baixa `avaliacoes.csv`. Sem token → mensagem de token inválido.

- [ ] **Step 4: Commit**

```bash
git add frontend/resultados.html frontend/resultados.js
git commit -m "feat(frontend): dashboard de resultados + export CSV"
```

---

### Task 8: Deploy e seed em produção

**Files:** nenhum arquivo de código (passos operacionais no Railway).

- [ ] **Step 1: Push (dispara o deploy)**

```bash
git push origin main
```

- [ ] **Step 2: Definir a variável de ambiente no Railway**

Na aba **Variables** do serviço SIACH, adicionar:
`ESTUDO_TOKEN=<um segredo forte que você escolher>`
Aplicar/redeploy.

- [ ] **Step 3: Gerar as 10 análises em produção (uma vez)**

Após o deploy ficar "Active", chamar o seed (substitua a URL e o token):

```bash
curl -X POST "https://siach-production.up.railway.app/estudo/seed?token=SEU_TOKEN"
```

Esperado: JSON `{"decisao_ids":[...],"total":10}`. Chamar de novo é seguro (idempotente, continua 10).

- [ ] **Step 4: Verificar em produção**

- `https://siach-production.up.railway.app/avaliar/analista-1` → wizard com 10 análises.
- `https://siach-production.up.railway.app/resultados?token=SEU_TOKEN` → dashboard.

- [ ] **Step 5: Distribuir os links**

Enviar um link por analista:
`/avaliar/analista-1` … `/avaliar/analista-5` (ou os nomes que preferir — o slug é livre).

---

## Notas finais

- **Persistência:** tudo grava no volume (`/data/siach.db`), então as notas sobrevivem a redeploys. As 2 tabelas novas são criadas pelo `create_all` no boot.
- **Segurança:** `/avaliar/{slug}` é aberto (qualquer um com o link avalia); `seed`, `resultados` e `resultados.csv` exigem `ESTUDO_TOKEN`.
- **Slugs livres:** se um analista abrir `/avaliar/joao`, as notas dele ficam sob "joao" no dashboard automaticamente.
