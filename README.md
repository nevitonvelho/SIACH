# SIACH — Sistema Inteligente de Análise de Crédito Humanizada

> **Trabalho de Conclusão de Curso** — Bacharelado em Engenharia de Software, UTFPR Dois Vizinhos
> Autor: Neviton Porfirio Vieira Velho · Orientador: Prof. Dr. Francisco Carlos Souza
> Defesa prevista: 22 a 29 de junho de 2026

## O que é o SIACH

Sistema web que recebe dados de uma solicitação de crédito (com foco em crédito rural brasileiro), recupera casos históricos similares por busca vetorial e usa LLMs para gerar dois pareceres complementares:

1. **Parecer técnico estruturado** (JSON validado): recomendação, confiança, fatores favoráveis/de risco, comparação histórica, recomendações de ação.
2. **Parecer humanizado**: texto curto, em 1ª pessoa do plural, sem jargão técnico, voltado para o solicitante.

A tese central é que separar a análise técnica (auditável) da comunicação humanizada (empática) torna o processo de crédito mais consistente, transparente e respeitoso — sem comprometer o rigor analítico.

## Como funciona — pipeline de 6 etapas

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (HTML + Bootstrap 5 + fetch)                              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ POST /analise
┌────────────────────────────────▼────────────────────────────────────┐
│  FastAPI                                                            │
│                                                                     │
│   1. Coleta ─→ 2. Narrativa ─→ 3. RAG ─→ 4. Análise Técnica         │
│      (Pydantic)  (Jinja2)        (Chroma)  (Claude Sonnet 4.6)      │
│                                                  │                  │
│                            6. Persistência ←─ 5. Humanização        │
│                            (SQLAlchemy)         (Claude Haiku 4.5)  │
└─────────────────────────────────────────────────────────────────────┘
```

| Etapa | Determinístico? | Função |
|---|---|---|
| 1. Coleta | sim (Pydantic) | valida payload (idade, renda, valor, prazo, etc.) |
| 2. Narrativa | sim (Jinja2) | converte campos tabulares em parágrafo descritivo |
| 3. RAG | embeddings + Chroma | recupera 5 casos historicamente similares |
| 4. Análise técnica | LLM (Sonnet 4.6) | gera parecer JSON estruturado com base nos similares |
| 5. Humanização | LLM (Haiku 4.5) | reescreve o parecer em texto empático |
| 6. Persistência | sim (SQLAlchemy) | grava decisão; ao aprovar, re-indexa o caso (aprendizado contínuo) |

## Dataset

**Fonte:** SCR — Sistema de Informações de Crédito do Banco Central do Brasil, dados públicos de 2025 (12 meses, ~278 mil registros de "Financiamentos rurais").

**Estratégia:** o SCR é agregado por *bucket* (UF × segmento × tipo de cliente × CNAE × porte × submodalidade). Como precisamos de casos individuais para o RAG, geramos **5.000 casos sintéticos** cujos atributos categóricos vêm dos buckets reais e cujas taxas de inadimplência respeitam a estatística agregada do BCB (Bernoulli da razão `carteira_inadimplencia / carteira_ativa`).

Resultado: dataset 100% brasileiro, com casos individuais para RAG, calibrado por dados oficiais. Taxa de inadimplência empírica nos sintéticos: **4,98%** (consistente com o benchmark BCB para crédito rural).

Limitação assumida: dados individuais públicos brasileiros de crédito não existem (LGPD + sigilo bancário). A síntese calibrada é a melhor aproximação possível e é academicamente defensável.

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Web | FastAPI + Uvicorn |
| Validação | Pydantic 2 + pydantic-settings |
| Banco | SQLite + SQLAlchemy 2 |
| Vector store | ChromaDB (modo embedded, persistente) |
| Embeddings | Voyage AI (`voyage-3-large`, 1024-dim) com fallback `sentence-transformers/multilingual-e5-large` |
| LLM | Anthropic Claude — Sonnet 4.6 (análise técnica) + Haiku 4.5 (humanização) |
| Orquestração | LangChain (`langchain-anthropic`, `langchain-chroma`) |
| Templates | Jinja2 |
| Frontend | HTML5 + Bootstrap 5.3 (CDN) + JavaScript vanilla |
| Testes | pytest + httpx (TestClient) — 42 testes |
| Lint | ruff |
| Pkg manager | uv |

## Estrutura do repositório

```
tcc/
├── backend/
│   ├── main.py              # FastAPI app + StaticFiles + redirect raiz
│   ├── config.py            # Settings (pydantic-settings)
│   ├── db.py                # SQLAlchemy engine + session
│   ├── models.py            # ORM: Caso, Decisao
│   ├── schemas.py           # Pydantic: SolicitacaoCredito, ParecerTecnico, etc.
│   ├── routes/              # /analise, /feedback, /historico
│   ├── services/            # narrativa, embeddings, rag, chains, persistence
│   ├── prompts/             # narrativa.j2, analise_system.j2, humanizacao_system.j2
│   └── seed/load_data.py    # CSV → SQLite + indexação Chroma
│
├── data/
│   ├── load_scrbcb.py       # Lê SCR/BCB e gera casos sintéticos
│   ├── scrdata_2025/        # 12 CSVs do BCB (gitignore — 1,2 GB)
│   └── casos_processados.csv# 5.000 casos gerados (gitignore)
│
├── frontend/
│   ├── index.html           # Formulário de nova análise
│   ├── resultado.html       # Parecer + casos similares + feedback
│   ├── historico.html       # Tabela de decisões anteriores
│   ├── style.css
│   └── app.js
│
├── tests/                   # 42 testes (unit + integration + e2e)
├── scripts/seed.sh          # Gera casos sintéticos + popula SQLite + indexa Chroma
├── docs/superpowers/
│   ├── specs/2026-04-26-siach-design.md      # Especificação técnica
│   └── plans/2026-04-26-siach-implementation.md # Plano de implementação (22 tasks TDD)
└── pyproject.toml + uv.lock
```

## Como rodar

### Pré-requisitos

- Python 3.12
- [uv](https://github.com/astral-sh/uv) (`pip install uv` ou `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Os 12 CSVs do SCR/BCB 2025 em `data/scrdata_2025/` (já presentes localmente)
- Chave da Anthropic API (`ANTHROPIC_API_KEY`)
- (Opcional) Chave Voyage AI (`VOYAGE_API_KEY`) — caso contrário, usar embeddings locais

### Setup

```bash
# 1. Instalar dependências (cria .venv automaticamente)
uv sync

# 2. Copiar template de configuração
cp .env.example .env
# Editar .env com suas chaves

# 3. Carregar SQLite + indexar Chroma (~2-5 min com Voyage; ~10 min na 1ª vez com local)
./scripts/seed.sh
```

### Servir

```bash
uv run uvicorn backend.main:app --reload
```

Abrir <http://localhost:8000> no navegador.

### Rodar testes

```bash
uv run pytest -v          # 42 testes
uv run ruff check .       # Lint
```

## Status atual

✅ **Sistema E2E funcional** — todas as 22 tasks do plano de implementação completas, 42 testes passando.

⏳ **Pendente:**
1. Smoke real com chaves de API (não foi feito automaticamente)
2. Avaliação manual do **gate de fallback (S4 do cronograma)**: pareceres reais são coerentes? → segue Abordagem B (RAG+LLM); se não → fallback Abordagem A (k-NN puro)
3. **Validação experimental** (S5–S6): baselines, métricas (acurácia, F1, AUC-ROC, ablation, LLM-as-a-judge)
4. **Escrita da monografia** (S7–S8)

## Cronograma

| Semana | Janela | Status | Foco |
|---|---|---|---|
| S1 | 28/abr–04/mai | ✅ feito | Setup + dataset SCR/BCB |
| S2 | 05–11/mai | ✅ feito | Pipeline determinístico (etapas 1-3) |
| S3 | 12–18/mai | ✅ feito | Chains LLM (etapas 4-5) |
| S4 | 19–25/mai | ✅ feito (gate pendente) | Frontend + persistência + decisão de gate |
| S5 | 26/mai–01/jun | ⏳ próximo plano | Experimento 1: acurácia vs baselines |
| S6 | 02–08/jun | ⏳ | Experimento 2 (ablation) + Experimento 3 (LLM-as-a-judge) |
| S7 | 09–15/jun | ⏳ | Escrita da monografia |
| S8 | 16–22/jun | ⏳ | Polimento + slides + ensaio |

## Documentação

- **Artigo do TCC:** `Artigo_TCC Neviton.pdf`
- **Spec de design:** [`docs/superpowers/specs/2026-04-26-siach-design.md`](docs/superpowers/specs/2026-04-26-siach-design.md)
- **Plano de implementação (22 tasks TDD):** [`docs/superpowers/plans/2026-04-26-siach-implementation.md`](docs/superpowers/plans/2026-04-26-siach-implementation.md)

## Decisões arquiteturais relevantes

1. **Embeddings sobre narrativa textual, não sobre features tabulares.** Cada caso é primeiro convertido em parágrafo descritivo determinístico (Jinja2) e só então embedado. Mais rico semanticamente que embedar números diretamente; alinhado à literatura de TabLLM.
2. **Duas chains LLM separadas (técnica + humanizada).** Impede que a humanização "amoleça" a recomendação técnica. A técnica é JSON auditável; a humanizada é texto livre.
3. **Anti-leak no RAG.** Durante avaliação experimental, o caso de teste é excluído por id da consulta ao Chroma para não recuperar a si mesmo.
4. **`inadimpliu` nunca entra no prompt do LLM.** Está nos dados históricos para validação experimental, mas o LLM só vê `decisao_final` (a decisão original do analista humano), evitando data leak no aprendizado.
5. **Gate de fallback explícito na semana 4.** Se o RAG completo (Abordagem B) não produzir pareceres coerentes, fallback para k-NN tabular puro (Abordagem A) sem perda de cronograma.

## Licença

Trabalho acadêmico — UTFPR, 2026.
