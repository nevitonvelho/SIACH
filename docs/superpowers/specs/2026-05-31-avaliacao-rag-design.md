# Módulo de Avaliação da Qualidade do RAG (Estudo do TCC)

**Data:** 2026-05-31
**Autor:** Neviton Velho
**Status:** Aprovado (aguardando revisão do spec)

## Objetivo

Permitir que **5 analistas** avaliem a qualidade das análises geradas pelo
RAG do SIACH, atribuindo uma **nota de 0 a 10** para **as mesmas 10 análises**.
Os resultados alimentam a avaliação de qualidade do sistema no artigo do TCC.

Métrica central: nota média por análise e por analista, além de concordância
entre analistas (possível porque todos avaliam o mesmo conjunto).

## Decisões de design (confirmadas)

| Decisão | Escolha |
|---|---|
| Conjunto avaliado | As **mesmas 10** análises para todos os 5 analistas (50 avaliações) |
| Acesso | **Link único por analista** (`/avaliar/{slug}`), sem login |
| Nota | **Uma nota geral 0–10** por análise (sem comentário) |
| Resultados | **Dashboard** (`/resultados`) + **export CSV** |
| Origem das 10 | **Curadas** (10 solicitações variadas) rodadas pelo pipeline real |
| Layout da avaliação | **Wizard** — uma análise por vez, com Anterior/Próxima |
| Slugs dos analistas | `analista-1` … `analista-5` (slug livre; renomeável) |
| Proteção do dashboard/seed | Token simples via env var `ESTUDO_TOKEN` |

## Modelo de dados

Duas tabelas novas. Ambas criadas por `Base.metadata.create_all()` no boot
(já existente no `lifespan`), **sem migração** da tabela `decisao`.

### `estudo_item`
Define quais decisões compõem o estudo e em que ordem.
- `id` (PK)
- `decisao_id` (FK → `decisao.id`, único)
- `ordem` (int, 1..10)

### `avaliacao`
Uma nota de um analista para uma análise.
- `id` (PK)
- `analista` (str, slug do analista)
- `decisao_id` (FK → `decisao.id`)
- `nota` (int, 0–10)
- `timestamp` (datetime UTC)
- **Único composto `(analista, decisao_id)`** → re-avaliar faz *upsert*.

## Geração das 10 análises (seed do estudo)

`services/estudo.py` contém uma lista curada de **10 `SolicitacaoCredito`**
variadas (agricultura/pecuária/mista; valores, scores e prazos diversos;
cobrindo aprovado / aprovado com ressalvas / recusado).

`POST /estudo/seed` (idempotente, exige token):
1. Se já existem 10 itens em `estudo_item`, retorna o conjunto atual (não duplica).
2. Senão, para cada solicitação curada: roda o pipeline real
   (`gerar_narrativa` → `RAGService.recuperar` → `AnaliseChain` →
   `HumanizacaoChain` → `salvar_decisao`) e insere a `decisao` resultante em
   `estudo_item` com a ordem.

Executado **uma vez** após o deploy (chamada manual ao endpoint), gravando
direto no volume de produção. Não roda no boot para não bloquear o health
check com 10 chamadas ao Claude.

## Rotas (backend — `routes/estudo.py`)

| Método | Rota | Descrição | Proteção |
|---|---|---|---|
| GET | `/avaliar/{analista}` | Serve a página do analista (HTML) | não |
| GET | `/estudo/analises` | As 10 análises do estudo (dados p/ exibir) | não |
| GET | `/avaliacoes/{analista}` | Notas já dadas por este analista (retomar) | não |
| POST | `/avaliacoes` | Upsert de uma nota `{analista, decisao_id, nota}` | não |
| POST | `/estudo/seed` | Gera as 10 análises (idempotente) | token |
| GET | `/resultados` | Dashboard (HTML) | token (via query) |
| GET | `/resultados/dados` | Agregados (média/análise, média/analista) | token |
| GET | `/resultados.csv` | Export CSV das avaliações | token |

Schemas novos em `schemas.py`: `AvaliacaoPayload` (`analista: str`,
`decisao_id: int`, `nota: int` com `ge=0, le=10`).

## Frontend

Padrão atual (HTML + JS vanilla + `style.css`), visual caprichado e coerente
com as páginas existentes.

### `avaliar.html` (+ lógica em `app.js` ou arquivo próprio)
- Lê o slug do analista da URL (`/avaliar/{slug}`).
- Ao carregar: busca `GET /estudo/analises` e `GET /avaliacoes/{analista}`
  (para retomar).
- **Wizard:** "Análise X de 10", resumo do solicitante, parecer humanizado,
  parecer técnico (fatores favoráveis / de risco, recomendação, confiança),
  casos similares (expansível), e a **régua 0–10** (botões 0..10).
- **Autosave**: clicar numa nota dispara `POST /avaliacoes`; navegação por
  Anterior/Próxima.
- Indicador de progresso; tela final "Obrigado! 10/10 avaliadas."

### `resultados.html`
- Exige token (`/resultados?token=...`).
- Tabela: por análise (id, recomendação, **nota média**, nº de notas) e por
  analista (slug, **nota média**, quantas das 10 faltam).
- Botão **Exportar CSV**.

## Tratamento de erros / bordas

- `nota` fora de 0–10 → 422 (validação Pydantic).
- `decisao_id` inexistente no `POST /avaliacoes` → 404.
- Slug de analista é livre: a página funciona para qualquer slug; o dashboard
  exibe quem efetivamente enviou notas.
- Token ausente/errado em rotas protegidas → 403.
- Re-clicar numa nota diferente atualiza (upsert pelo único composto).

## Arquivos afetados

**Backend**
- `backend/models.py` — `EstudoItem`, `Avaliacao`.
- `backend/schemas.py` — `AvaliacaoPayload`.
- `backend/services/estudo.py` — 10 solicitações curadas; seed; agregação; CSV.
- `backend/routes/estudo.py` — rotas acima.
- `backend/main.py` — registrar o router; servir as páginas.
- `backend/config.py` — `estudo_token: str` (env `ESTUDO_TOKEN`).

**Frontend**
- `frontend/avaliar.html`, `frontend/resultados.html`, JS/CSS de apoio.

**Produção (Railway)**
- Nova variável `ESTUDO_TOKEN`.
- Após o deploy: chamar `POST /estudo/seed?token=...` uma vez.

## Fora de escopo (YAGNI)

- Login/autenticação real de analistas.
- Comentários/justificativas nas notas.
- Conjuntos diferentes por analista.
- Notas por dimensão (apenas nota geral).
- Edição das 10 solicitações pela UI (são definidas em código).

## Critérios de sucesso

1. `POST /estudo/seed` cria exatamente 10 análises reais, idempotente.
2. Cada um dos 5 links abre o wizard e salva as notas (retoma ao reabrir).
3. `/resultados` mostra média por análise e por analista e exporta CSV.
4. Tudo persiste no volume de produção entre deploys.
