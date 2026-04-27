---
title: SIACH — Design de Implementação
author: Neviton Porfirio Vieira Velho
advisor: Prof. Dr. Francisco Carlos Souza
institution: UTFPR Dois Vizinhos — Bacharelado em Engenharia de Software
date: 2026-04-26
defense-window: 22 a 29 de junho de 2026
status: aprovado
---

# Sistema Inteligente de Análise de Crédito Humanizada (SIACH)

## 1. Resumo executivo

O SIACH é um sistema web que recebe dados de um solicitante de crédito, recupera casos
históricos similares por meio de embeddings de narrativas textuais, gera um parecer
técnico estruturado por LLM e produz uma explicação humanizada acessível. Este
documento descreve o design técnico que será implementado em 8 semanas como TCC.

A arquitetura adotada é a **Abordagem B** discutida em brainstorming: pipeline RAG
completo com LangChain + ChromaDB + Claude. Uma mitigação de risco está prevista
na semana 4, ponto em que se reavalia se o pipeline RAG está produzindo pareceres
coerentes; caso contrário, fallback para k-NN tabular sem LLM.

A contribuição central do trabalho é a separação entre parecer técnico (estruturado,
auditável) e parecer humanizado (texto livre, empático), validados experimentalmente
contra baselines tabulares clássicos e por avaliação automatizada de qualidade.

## 2. Contexto e motivação

O artigo do TCC propõe o SIACH como resposta a três limitações do processo
tradicional de análise de crédito: pouca padronização, baixa clareza nas
justificativas e comunicação limitada com o solicitante. Este documento operacionaliza
aquela proposta em um sistema construível no prazo de 2 meses.

Decisões que diferem do artigo, com justificativa:

- **LangFlow não será usado.** O artigo cita LangFlow como keyword, mas em prazo de
  2 meses, e considerando que o autor está em primeiro contato com LLMs, a camada
  visual do LangFlow adiciona complexidade sem ganho proporcional. LangChain
  (programático) é mantido. A justificativa entra no capítulo de Implementação.
- **Embeddings sobre narrativa textual em vez de números tabulares.** Embedar
  features tabulares diretamente é academicamente fraco. A solução é gerar uma
  narrativa textual determinística por template Jinja2 e embedar a narrativa.
  Esta abordagem é consistente com a literatura da família TabLLM.

## 3. Arquitetura geral

```
┌──────────────────────────────────────────────────────────────────┐
│  Apresentação                                                    │
│        Frontend Web — HTML + Bootstrap 5 + fetch                 │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
┌──────────────────────────────────────────────────────────────────┐
│  API                                                             │
│        FastAPI — /analise · /historico · /feedback               │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
┌──────────────────────────────────────────────────────────────────┐
│  Pipeline (orquestrado por LangChain)                            │
│                                                                  │
│   1. Coleta ─→ 2. Narrativa ─→ 3. RAG ─→ 4. Análise Técnica      │
│                                                  │               │
│                         6. Persistência ←─── 5. Humanização      │
└────────────────────┬───────────────────────┬─────────────────────┘
                     │                       │
┌──────────────────────────────────────────────────────────────────┐
│  Persistência e serviços externos                                │
│   SQLite (decisões + feedback)                                   │
│   ChromaDB (embeddings das narrativas históricas)                │
│   Anthropic Claude (LLM análise + humanização)                   │
│   Voyage AI (embeddings)                                         │
└──────────────────────────────────────────────────────────────────┘
```

Setas sólidas representam o fluxo principal de uma análise. Etapas 1, 2 e 6 são
determinísticas (sem chamada de LLM). Etapas 3, 4 e 5 envolvem LangChain e/ou
chamadas a serviços externos.

O ciclo de aprendizado contínuo opera no nível da etapa 6: quando um analista
aprova um parecer através do endpoint `/feedback`, o caso é inserido na tabela
`caso` e re-indexado no Chroma, ficando disponível para futuras análises.

## 4. Modelo de dados

### 4.1 Tabelas SQLite

**`caso`** (base histórica para RAG, populada pelo seed inicial e pelo loop de feedback)

| Campo | Tipo | Origem | Notas |
|---|---|---|---|
| `id` | INTEGER PK | seed/feedback | |
| `idade` | INTEGER | German Credit | |
| `renda_anual` | REAL | German Credit | em R$ |
| `estado_civil` | TEXT | German Credit | |
| `dependentes` | INTEGER | German Credit | |
| `tempo_emprego_meses` | INTEGER | German Credit | |
| `valor_solicitado` | REAL | German Credit | |
| `prazo_meses` | INTEGER | German Credit | |
| `finalidade` | TEXT | German Credit | mapeada para `custeio_agricola` quando aplicável |
| `score_interno` | INTEGER | German Credit | |
| `divida_aberto` | REAL | German Credit | |
| `tipo_garantia` | TEXT | German Credit | |
| `area_propriedade_ha` | REAL | sintético | regras + ruído gaussiano |
| `var_produtividade_pct` | REAL | sintético | variação ano-a-ano, pode ser negativa |
| `renegociacoes_recentes` | INTEGER | sintético | distribuição de Poisson |
| `atividade_principal` | TEXT | sintético | `agricultura`, `pecuaria`, `mista` |
| `decisao_final` | TEXT | German Credit + mapeamento | `aprovado`, `aprovado_com_ressalvas`, `recusado` |
| `inadimpliu` | BOOLEAN | German Credit (label) | usado **apenas** na avaliação experimental, nunca no prompt |

**`decisao`** (gerada pelo SIACH em runtime)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `solicitacao_id` | INTEGER | id externo da solicitação |
| `timestamp` | DATETIME | |
| `dados_solicitante` | JSON | snapshot completo da entrada |
| `casos_similares` | JSON | lista `[{caso_id, score}]` recuperados |
| `parecer_tecnico` | TEXT | JSON serializado da saída da etapa 4 |
| `parecer_humanizado` | TEXT | saída da etapa 5 |
| `recomendacao` | TEXT | `aprovado` / `aprovado_com_ressalvas` / `recusado` |
| `confianca` | REAL | 0-1 |
| `status_feedback` | TEXT | `pendente` / `aprovado` / `ajustado` / `rejeitado` |
| `parecer_ajustado` | TEXT | preenchido quando o analista ajusta |

### 4.2 ChromaDB — collection `casos`

- `id` = `caso.id`
- `document` = narrativa textual gerada pela etapa 2
- `embedding` = vetor 1024-dim (Voyage `voyage-3-large`)
- `metadata` = `{decisao_final, inadimpliu, finalidade, atividade_principal, area_ha}`

A collection é populada inicialmente pelo script de seed e atualizada pelo loop
de feedback. `inadimpliu` é gravado em metadata mas **nunca** entra no prompt do
LLM — serve só para análises post-hoc.

### 4.3 Estratégia de geração de narrativa

Cada caso é convertido em um parágrafo descritivo por um template Jinja2
determinístico. Frases condicionais destacam sinais (ex.: queda de produtividade
maior que 10% — `var_produtividade_pct < -10` — vira "queda significativa de
produtividade"). Determinismo é importante para reprodutibilidade do experimento.

Exemplo de saída do template para um caso:

> "Produtor rural de 45 anos, atividade mista (soja + bovino), área de 80ha,
> renda anual R$180.000. Apresenta queda de produtividade de 15% e 22% nas
> duas últimas safras. Possui 2 renegociações recentes e dívida em aberto de
> R$45.000. Solicita R$120.000 em custeio agrícola, prazo 12 meses, com
> garantia de penhor agrícola. Score interno 580."

## 5. Pipeline detalhado

### 5.1 Etapa 1 — Coleta e Validação (FastAPI + Pydantic)

- **Entrada:** POST /analise com JSON do formulário.
- **Saída:** instância de `SolicitacaoCredito` (Pydantic v2).
- **Comportamento:** validação de tipos e regras de negócio simples
  (renda > 0, área > 0, prazo dentro de 6 a 60 meses). Erros retornam 422 com
  mensagem clara. Não chama LLM.

### 5.2 Etapa 2 — Geração de Narrativa (Jinja2)

- **Entrada:** `SolicitacaoCredito`.
- **Saída:** string `narrativa`.
- **Comportamento:** template `prompts/narrativa.j2` com placeholders e
  condicionais. Função pura, sem efeitos colaterais.

### 5.3 Etapa 3 — RAG (LangChain + Chroma)

- **Entrada:** `narrativa`.
- **Saída:** lista de até 5 casos similares (`narrativa`, `decisao_final`,
  `score_similaridade`, metadata).
- **Comportamento:**
  1. Embed da narrativa via Voyage `voyage-3-large`.
  2. `chroma.similarity_search_with_score(query_embedding, k=5)` opcionalmente
     filtrando por metadata (`finalidade`, `atividade_principal`).
  3. Durante a avaliação experimental, o id do caso atual é excluído da query
     para evitar data leak.

### 5.4 Etapa 4 — Análise Técnica (LangChain LCEL + Sonnet 4.6)

- **Entrada:** `narrativa` + 5 casos similares.
- **Saída:** `ParecerTecnico` (Pydantic) validado por `PydanticOutputParser`:
  ```json
  {
    "recomendacao": "aprovado_com_ressalvas",
    "confianca": 0.72,
    "fatores_favoraveis": [...],
    "fatores_de_risco": [...],
    "comparacao_historica": "...",
    "recomendacoes_acao": [...]
  }
  ```
- **Comportamento:** prompt system contextualiza o LLM como analista de crédito
  sênior; few-shot inclui os casos similares com decisão real e desfecho. O LLM
  **não** vê o `inadimpliu` do caso atual.

### 5.5 Etapa 5 — Humanização (LangChain + Haiku 4.5)

- **Entrada:** `ParecerTecnico` (estruturado) + dados-chave do solicitante.
- **Saída:** texto livre em primeira pessoa do plural, empático, sem jargão.
- **Comportamento:** prompt separado da etapa 4 para impedir que a humanização
  "amoleça" a recomendação técnica. Usa Haiku para reduzir custo e latência.

### 5.6 Etapa 6 — Persistência e Aprendizado Contínuo

- **Entrada:** parecer técnico + parecer humanizado + dados + casos consultados.
- **Saída:** registro em `decisao` com `status_feedback = pendente`.
- **Loop de feedback (fora do fluxo síncrono da análise):**
  1. Analista revisa parecer no frontend e escolhe aprovar / ajustar / rejeitar.
  2. POST /feedback atualiza `decisao`.
  3. Em caso de aprovação, um novo registro é inserido em `caso` (sem
     `inadimpliu`, ainda desconhecido) e re-indexado no Chroma.

## 6. Stack tecnológico

### 6.1 Backend

| Categoria | Pacote | Versão alvo |
|---|---|---|
| Runtime | Python | 3.12.x |
| Web | fastapi | 0.115+ |
| Web | uvicorn[standard] | 0.32+ |
| Validação | pydantic | 2.x |
| Settings | pydantic-settings | 2.x |
| Banco | sqlalchemy | 2.x |
| RAG | langchain | 0.3+ |
| RAG | langchain-anthropic | 0.3+ |
| RAG | langchain-chroma | 0.2+ |
| Vector | chromadb | 0.5+ |
| LLM | anthropic | 0.40+ |
| Embeddings | voyageai | 0.3+ |
| Templates | jinja2 | 3.x |
| Dados | pandas | 2.x |
| Test | pytest, pytest-asyncio | — |
| Lint | ruff | 0.7+ |
| Pkg manager | uv | latest |

### 6.2 Frontend

- HTML5 + CSS + Bootstrap 5.3 (CDN)
- JavaScript vanilla com `fetch()`
- Servido pelo FastAPI via `StaticFiles`
- 3 páginas: nova análise, resultado, histórico

### 6.3 LLM e embeddings

- **Análise técnica:** `claude-sonnet-4-6` (mais ponderado, saída estruturada).
- **Humanização:** `claude-haiku-4-5-20251001` (rápido, barato).
- **Embeddings:** Voyage `voyage-3-large` (1024-dim).
- **Fallback de embeddings:** sentence-transformers `multilingual-e5-large`,
  ativado por flag de ambiente caso a Voyage esteja instável.

Custo total estimado da validação experimental (200 casos × 2 chamadas LLM
+ 1.000 embeddings) é inferior a US$ 5,00.

## 7. Estrutura de diretórios

```
tcc/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── docs/
│   └── superpowers/specs/
├── data/
│   ├── german_credit.csv
│   ├── seed_synthetic.py
│   └── casos_processados.csv
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── analise.py
│   │   ├── feedback.py
│   │   └── historico.py
│   ├── services/
│   │   ├── narrativa.py
│   │   ├── rag.py
│   │   ├── analise_chain.py
│   │   ├── humanizacao_chain.py
│   │   └── persistence.py
│   ├── prompts/
│   │   ├── narrativa.j2
│   │   ├── analise_system.j2
│   │   └── humanizacao_system.j2
│   └── seed/
│       └── load_data.py
├── frontend/
│   ├── index.html
│   ├── resultado.html
│   ├── historico.html
│   ├── style.css
│   └── app.js
├── experiments/
│   ├── baseline_kn.py
│   ├── run_evaluation.py
│   ├── metrics.py
│   └── notebooks/
│       └── analise_resultados.ipynb
├── tests/
│   ├── conftest.py
│   ├── test_narrativa.py
│   ├── test_rag.py
│   ├── test_chains.py
│   └── test_api.py
└── scripts/
    ├── seed.sh
    └── dev.sh
```

## 8. Validação experimental

### 8.1 Divisão dos dados

- 700 casos (70%) → indexados no Chroma como base histórica.
- 200 casos (20%) → conjunto de teste, rodam pelo SIACH como solicitações novas.
- 100 casos (10%) → conjunto de validação automática.

Durante a análise de um caso de teste, o próprio caso é excluído da query
ao Chroma (anti-leak).

### 8.2 Experimento 1 — Acurácia preditiva contra baselines

Comparação entre quatro modelos no mesmo conjunto de 200 casos:

| Modelo | Descrição |
|---|---|
| Regra fixa | `score_interno > 600 AND divida_aberto / renda_anual < 0.30` |
| k-NN tabular | k=5 sobre features numéricas, voting majoritário |
| Regressão logística | sklearn, todas as features tabulares |
| **SIACH completo** | RAG + LangChain + Sonnet |

Métricas: acurácia, precision/recall/F1 macro e por classe, AUC-ROC, matriz
de confusão.

**Hipótese H1:** SIACH ≥ baselines em F1 macro, especialmente na classe
inadimplente. Caso H1 não se confirme, a contribuição do trabalho recai sobre
o experimento 3 (humanização).

### 8.3 Experimento 2 — Ablation (escopo reduzido)

Três variantes do SIACH avaliadas no mesmo conjunto de teste:

| Variante | O que muda |
|---|---|
| SIACH-zero | LLM zero-shot, sem casos similares no prompt |
| SIACH-tab | Features tabulares no prompt em vez de narrativa |
| SIACH-completo | Configuração principal: narrativa + RAG + k=5 |

Saída: gráfico de barras comparando F1 das três variantes.

### 8.4 Experimento 3 — Qualidade dos pareceres humanizados

Apenas o protocolo automatizado (LLM-as-a-judge), sem avaliação humana.

- Juiz: `claude-opus-4-7` (independente dos modelos do pipeline).
- Pareamento cego: parecer-humanizado (etapa 5) vs. parecer-baseline (parecer
  técnico da etapa 4 renderizado em texto corrido a partir do JSON, sem a
  passagem pela etapa 5 de humanização).
- Dimensões em escala 1-5: clareza, empatia, ausência de jargão, cobertura
  dos fatores-chave, acionabilidade.
- Subset: 50 casos pareados.

**Hipótese H2:** SIACH-humanizado > parecer-baseline nas 5 dimensões. Esta é
a contribuição central do trabalho.

### 8.5 Métricas operacionais

- Latência média end-to-end. Alvo: < 8 s.
- Custo por análise. Alvo: < US$ 0,02.
- Taxa de validação JSON da etapa 4. Alvo: ≥ 98%.
- Variância da recomendação em 3 execuções repetidas (temperature baixa,
  seed fixo onde possível).

## 9. Cronograma

| Semana | Janela | Foco | Entregável |
|---|---|---|---|
| S1 | 28/abr - 04/mai | Setup + dados | 1.000 casos no SQLite, /health responde |
| S2 | 05 - 11/mai | Pipeline determinístico (etapas 1-3) | /analise retorna 5 similares |
| S3 | 12 - 18/mai | Chains LLM (etapas 4-5) | /analise retorna parecer técnico + humanizado |
| **S4** | 19 - 25/mai | **Frontend + persistência + GATE de fallback** | E2E rodando + decisão arquitetural confirmada |
| S5 | 26/mai - 01/jun | Validação · Experimento 1 | Tabela comparativa de 4 modelos |
| S6 | 02 - 08/jun | Validação · Experimentos 2 e 3 | Notebook com todos os gráficos |
| S7 | 09 - 15/jun | Escrita da monografia | Draft completo enviado ao orientador |
| S8 | 16 - 22/jun | Polimento + slides + ensaio | Defesa pronta |

Defesa prevista: 22 a 29 de junho de 2026.

### 9.1 Gate de fallback (S4)

Critério explícito de avaliação na semana 4: **os pareceres do SIACH são
minimamente coerentes nos casos manuais testados na S3?**

- **Sim** → segue Abordagem B no resto do cronograma.
- **Não** → fallback para Abordagem A: substituir etapas 3 e 4 por k-NN
  tabular sem LLM, mantendo as etapas 5 (humanização) e 6 (persistência).
  Cronograma das semanas 5-8 não é afetado.

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Quebra de API do LangChain | Versões pinadas no `pyproject.toml` |
| Voyage instável ou indisponível | Flag de ambiente para fallback sentence-transformers |
| Pipeline RAG produz pareceres incoerentes | Gate explícito na S4 com fallback Abordagem A |
| Demora de revisão pelo orientador | Enviar draft parcial ao final da S6 |
| Resultado contraintuitivo no Exp. 1 | Trabalho ainda se sustenta no Exp. 3 (humanização) |
| Saída JSON inválida frequente da etapa 4 | `PydanticOutputParser` + retry com prompt-de-correção |

## 11. Critérios de sucesso

O TCC é considerado bem-sucedido se, ao final da S8:

1. O sistema E2E está funcional e demonstrável ao vivo na banca.
2. As três tabelas/gráficos dos Experimentos 1, 2 e 3 estão produzidos.
3. A monografia está completa, com capítulo de Resultados que discute as
   hipóteses H1 e H2.
4. Os custos operacionais ficam abaixo do alvo (US$ 0,02/análise).
5. A reprodutibilidade está documentada (seeds, versões, comandos de seed
   e avaliação no README).

## 12. Fora de escopo

Itens explicitamente **não** incluídos neste TCC, podendo aparecer em
"trabalhos futuros":

- Autenticação de usuários e perfis de acesso.
- Multi-tenancy (vários analistas/instituições simultaneamente).
- Avaliação humana com voluntários externos.
- Deploy em produção (Docker, cloud, observabilidade).
- LangFlow ou outras ferramentas visuais de orquestração.
- Suporte multi-idioma (todo conteúdo em português).
- Integração com bureaus de crédito reais (SPC, Serasa).
