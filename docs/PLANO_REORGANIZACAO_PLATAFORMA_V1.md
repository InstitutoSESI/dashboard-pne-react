# Plano de Reorganização da Plataforma — v1 (2026-08-24)

Plano operacional para: (1) remover totalmente o Caderno de Hipóteses; (2) criar o menu **Relatórios**; (3) criar o menu **Análise Regional** e deixar a plataforma pronta para o **Vocações da Região**.

Protocolo de execução: **Opus 5 orquestra** fase a fase, **delega a aplicação ao Codex 5.6 (sol, xhigh)**, e após cada aplicação **Opus e Codex debatem** a correção da implementação contra os gates da fase. Ao final de todas as fases, **Fable revisa o conjunto**. Ver §Protocolo no fim.

---

## 0. Estado atual (fatos levantados, base do plano)

### Navegação
- Hash-based, sem router de biblioteca. Registro de uma página exige tocar **7 arquivos**: `src/types/app.ts` (`AppPageKey`), `src/app/appRoutes.ts` (`HASH_PAGE_MAP`), `src/config/analyticsProducts.ts` (`PAGE_PRODUCTS`), `src/app/AppPageRouter.tsx` (lazy + branch), `src/components/Header.jsx` (`ALL_NAV_BLOCKS`), `src/components/icons/NavGlyphIcon.tsx`, `src/components/ContextBar.jsx` (`PAGE_CRUMBS`).
- Grupos atuais da sidebar: **PNE** (8 itens, "Cenários da educação" condicional ao manifesto do foresight), **Indicadores educacionais** (1 rota `#educacao` com `?secao=`, 10 seções), **Financiamento** (6 páginas), + itens raiz **Home** e **Relatório Técnico Municipal**.
- O agrupamento visual (`ALL_NAV_BLOCKS`) é acoplado 1:1 ao produto analítico (`pne`/`educacao`/`financiamento`), que controla visibilidade por publicação. Os novos menus misturam produtos, então **desacoplar grupo visual de produto** é pré-requisito.
- Município selecionado: `MunicipalityContext` global; páginas recebem `municipalityId` por prop via `AppPageRouter`; espelhamento `?municipio=<slug>` é opt-in por página no router.

### Invariantes duros (checks que congelam comportamento)
- `scripts/checks/app-routing-test.mjs`: ~40 `ROUTE_CASES` congelados (todo alias atual precisa continuar resolvendo; renomear rota exige manter o nome antigo como alias); fallback `home`; `ANALYTICS_PRODUCTS === ['pne','educacao','financiamento']` exatamente; asserções nominais página→produto; módulos de rota puros (sem React/window).
- `scripts/checks/ui-architecture-test.mjs`: ordem de imports CSS congelada em `App.tsx`/`main.jsx`; orçamento de bytes de CSS (total 1.425.000); todo `.css` em `src/styles/` precisa de importador; `src/app/**` é TS estrito (sem `any`, sem `@ts-nocheck`).
- `scripts/checks/foresight-educacao-navigation.test.mjs`: regex sobre o texto-fonte de `Header.jsx`, `AppPageRouter.tsx`, `ContextBar.jsx` (literais `withForesightItem`, `target: 'cenarios-da-educacao'`, breadcrumb exato). Qualquer mudança de menu no foresight muda este teste junto, deliberadamente.
- Regra arquitetural: a plataforma nunca lê a camada de pesquisa (`C:\Users\rnbirck\PROJETOS\SESI\PNE`) em runtime — só geradores `.mjs` determinísticos que projetam artefato público com manifesto + hash + validação fail-closed.

### Caderno (a remover)
- Feature: `src/features/caderno/` (12 arquivos), `src/hooks/useMunicipioCaderno.ts`, `src/domain/cadernoFrontsStorage.ts`, `src/styles/caderno-page.css`, `src/data/pne2026FederalGuidance.js` (órfão fora, 100% do caderno).
- Scripts: `scripts/generate-pne-caderno.mjs`, `scripts/checks/caderno-federal-guidance.test.mjs`, `caderno-signal-language.test.mjs`, `pne2026-caderno-loader.test.mjs`.
- Dados: `public/data/pne2026-caderno/` (1,5 MB). Docs: `docs/CADERNO_*.md` (5 arquivos).
- **Acoplamento crítico**: `src/features/matriz/matrizVocabulary.ts:1` importa `resolveSignalReading` de `../caderno/cadernoSignalLanguage.js` (usado nas linhas 205 e 239, produção da Matriz). Compatibilidade estrutural `MatrizSignal`↔`CadernoSignal`. Deletar sem portar quebra a Matriz.

### Regional (a construir)
- **Não existe região no repositório.** A regionalização anterior foi removida no commit `207de681a` (2026-08-08): 10 artefatos `public/data/educacao/regioes/*.json` (recorte `regiao_senai`, base FIERGS, RS-only) + `exportar_regioes()` em `data_pipeline/scripts/export_education_indicators.py` (−228 linhas) + coluna `regiao_senai` da query de municípios. Tudo recuperável via `git show 207de681a^:...`; a coluna provavelmente segue no banco `SESI\DB`.
- Metodologia de agregação legada (preservada nos `avisos` dos artefatos removidos): contagens somam; percentuais recalculados dos totais somados; IDEB/SAEB por média simples; INSE ponderado por `qtd_alunos_inse`.
- Dados municipais prontos para agregação: chave IBGE7 universal, séries anuais completas, matrículas em contagem absoluta com 17 recortes, 497/497 municípios em `municipios/`, `educacao/`, `pne2026-diagnostic-v3/`.
- Foresight: UI (`ForesightEducacaoPage` + 3 subcomponentes) é 100% declarativa e reaproveitável; o acoplamento municipal está no loader/manifesto/contrato (IBGE7 validado em três pontos). Publicados: só NSR (4313375) e São Leopoldo (4318705), fonte `v0.4.0-rc4`.

---

## 1. Decisões de produto (fixadas neste plano)

| # | Decisão | Escolha | Racional |
|---|---|---|---|
| D1 | Recorte regional | Mapa município→região derivado do recorte industrial já usado internamente (`regiao_senai`, 10 regiões no RS). **Nome público: apenas "Região" / "Região de <nome>"** — a palavra "FIERGS" (e "senai" como recorte) nunca aparece em UI, artefato público, rota ou breadcrumb. | Pedido explícito do usuário; dado já existiu e é recuperável. |
| D2 | Escopo territorial | **Análise regional é RS-only nesta versão.** O mapa vive em `config/regions/rs.json`; nenhum arquivo é criado para outras UFs e nenhum trabalho de generalização é feito além do gate natural: UF ativa sem arquivo de regiões ⇒ menu Análise Regional oculto (fail-closed). AL e demais estados seguem exatamente como hoje. | Decisão do usuário (2026-08-24). O gate por ausência de config já evita regressão na hospedagem multiestado sem custo extra — mesma objeção que motivou a remoção em `207de681a`. |
| D3 | Eixo de seleção | **Não** há seletor de região. A região é **derivada do município selecionado** ("a região à qual o município pertence"). Rota continua `?municipio=<slug>`. | Pedido explícito; evita segundo eixo no `MunicipalityContext`/`ContextBar`. |
| D4 | Produto analítico das páginas regionais | `educacao`. `ANALYTICS_PRODUCTS` **não muda** (contrato congelado no check). Revisitar só se surgir necessidade de gate de publicação próprio. | Menor mudança de contrato; dados-fonte são majoritariamente do produto educação. |
| D5 | Grupos de menu vs. produto | Grupo visual passa a ser **independente** do produto. Visibilidade decidida **por item** (produto do item), não por bloco. | Relatórios mistura `pne`+`educacao`; Análise Regional idem. |
| D6 | Destino dos Cenários municipais | Fase 5 move o item "Cenários da educação" para o grupo Análise Regional (conteúdo municipal inalterado, NSR+SL). Quando o artefato regional "Vocações da Região" for publicado (camada de pesquisa), o item municipal é substituído/aposentado — decisão formal registrada na ocasião. | O usuário definiu que os cenários "vão virar" Vocações da Região; o conteúdo regional ainda não existe. |
| D7 | Compatibilidade de rotas | Nenhum hash existente morre, **exceto** os do caderno (`#caderno`, `#caderno-de-hipoteses`), que passam a cair no fallback `home` — e os `ROUTE_CASES` correspondentes são removidos do teste (única exceção à regra de congelamento, pois a página deixa de existir). | Remoção total pedida. |
| D8 | Aliases novos | Novos itens de Relatórios que apontem para páginas existentes reutilizam as rotas existentes (ex.: Panorama = `educacao?secao=panorama`). Rotas novas: `#analise-regional` e (futura) `#vocacoes-da-regiao`. | Não duplicar páginas. |

---

## 2. Arquitetura-alvo dos menus

```
Home
Relatórios                        (grupo novo)
├─ Diagnóstico Municipal          → diagnostico            (produto pne)
├─ Matriz de Prioridades          → matriz-prioridades     (produto pne)
├─ Panorama Educacional           → educacao?secao=panorama (produto educacao)
└─ Relatório Técnico Municipal    → relatorio-tecnico-municipal (produto educacao)
Análise Regional                  (grupo novo; RS-only — oculto para UF sem config/regions)
├─ Panorama da Região             → analise-regional       (produto educacao; NOVA página)
└─ Cenários da educação           → cenarios-educacao      (municipal, condicional ao manifesto;
                                     vira "Vocações da Região" quando o artefato regional existir)
PNE
├─ O que é o PNE / Metas legais / PNE 2014–2024 / PNE 2026–2036   (inalterados)
Indicadores educacionais          (inalterado, seções da rota #educacao)
Financiamento                     (inalterado)
```

Observações:
- "Diagnóstico Municipal", "Matriz" e "Relatório Técnico" **saem** dos lugares atuais (grupo PNE / raiz) e entram em Relatórios. Produto de cada página **não muda** (asserções do check intactas).
- O item "Panorama educacional" some da lista de seções do grupo Indicadores educacionais **ou** permanece nos dois lugares — recomendação: permanece nos dois (custo zero, remove-se depois se redundante). Codex implementa "nos dois"; debate Opus×Codex pode reverter.

---

## 3. Fases

Cada fase termina com **gates** (comandos que devem passar) e com o **debate Opus×Codex** (roteiro em §Protocolo). Uma fase só abre quando a anterior fecha. Commits: um por fase, mensagem indicada.

### Fase 0 — Preparação (Opus, sem Codex)
1. Criar branch `reorg/menus-e-regional` a partir de `main` limpo (há mudanças não commitadas no working tree — **commitar ou stashear antes**, decisão do usuário se houver algo em andamento).
2. Rodar baseline e registrar resultado: `npm run check:fast`, `npm run test:app-routing`, `npm run test:ui-architecture`, `npm run test:matriz`, `npm run test:foresight`, `npm run test:caderno`. Tudo que já falhar antes do trabalho é anotado e excluído do escopo.
3. Gate: baseline registrado em `.tmp/reorg/baseline.md`.

### Fase 1 — Porte do módulo de linguagem de sinais para a Matriz
**Objetivo:** eliminar a dependência Matriz→Caderno antes de qualquer deleção.
1. Criar `src/features/matriz/matrizSignalLanguage.ts` com o conteúdo de `src/features/caderno/cadernoSignalLanguage.ts` (432 l.): `resolveSignalReading`, `MEASURE_LABEL`, `formatSignalValue`, `dimensionQualifier`, tipo de leitura.
2. Reescrever a assinatura para os tipos da matriz (`MatrizSignal`/`MatrizMonitoringSignal` de `src/features/matriz/matrizTypes.ts`), conferindo campo a campo (`measureId`, `unit`, `valueRaw`, `direction`, `dimensions`, `period`, `caution`). Atenção: `matrizVocabulary.ts:200-202,236` sintetiza `direction/observability/stance` ao adaptar `cause.proof` — manter o comportamento byte-idêntico das leituras renderizadas.
3. Apontar `src/features/matriz/matrizVocabulary.ts:1` para o novo módulo. Nenhum import de `../caderno/` pode restar em `src/features/matriz/`.
4. Gates: `npm run typecheck`, `npm run test:matriz`, `npm run check:fast`. Critério de debate: as leituras da Matriz renderizadas para 4313375 são idênticas antes/depois (comparação de texto).
5. Commit: `Portar linguagem de sinais do caderno para a matriz`.

### Fase 2 — Remoção total do Caderno de Hipóteses
**Deletar inteiros:** `src/features/caderno/`; `src/hooks/useMunicipioCaderno.ts`; `src/domain/cadernoFrontsStorage.ts`; `src/styles/caderno-page.css`; `src/data/pne2026FederalGuidance.js`; `scripts/generate-pne-caderno.mjs`; `scripts/checks/caderno-federal-guidance.test.mjs`; `scripts/checks/caderno-signal-language.test.mjs`; `scripts/checks/pne2026-caderno-loader.test.mjs`; `public/data/pne2026-caderno/`; `docs/CADERNO_HIPOTESES.md`, `docs/CADERNO_BALANCO_E_ROTA.md`, `docs/CADERNO_ESTADO_ATUAL.md`, `docs/CADERNO_FASE1_POC.md`, `docs/CADERNO_VALIDACAO_AMOSTRA.md`.

**Editar:**
| Arquivo | O quê |
|---|---|
| `src/types/app.ts:10` | remover `'caderno'` de `AppPageKey` (fazer primeiro; o typecheck aponta o resto) |
| `src/app/appRoutes.ts:12-13` | remover `caderno` e `cadernodehipoteses` do `HASH_PAGE_MAP` |
| `src/app/AppPageRouter.tsx:33,389-398` | remover lazy import e branch |
| `src/config/analyticsProducts.ts:31` | remover `caderno: 'pne'` |
| `src/components/Header.jsx:42,88` | remover item do bloco PNE e a chave do `Set` `PNE_PAGES` |
| `src/components/ContextBar.jsx:9` | remover breadcrumb |
| `src/components/icons/NavGlyphIcon.tsx:17,42,71-72` | remover chave de glifo, entrada `caderno: NotebookPen` e o import `NotebookPen` (que fica órfão **neste arquivo**; `DiagnosticPanel.jsx` importa o dele próprio) |
| `package.json:36,40` | remover scripts `test:caderno` e `generate:pne-caderno` |
| `scripts/checks/app-routing-test.mjs:103-105,297,332` | remover os 3 `ROUTE_CASES` do caderno e as 2 asserções (`resolvePageProduct`, `isPageNavigable`) |

**Não tocar:** `src/styles/financial-pages.css:5929` e `institutional-refresh.css:6` usam "caderno" como metáfora editorial — falso positivo. Docs da matriz/foresight que citam o caderno historicamente (`docs/MATRIZ_DE_PRIORIDADES.md` etc.) recebem apenas uma nota "caderno removido em 2026-08-24" onde citarem `npm run test:caderno` como check vigente (`docs/FORESIGHT_EDUCACAO_INTEGRACAO_PLATAFORMA_V0_4_0_RC4.md:209,397`).

**Verificações finais da fase:** `grep -ri "caderno" src/ scripts/ package.json` retorna zero fora dos dois falsos positivos de CSS; `#caderno` no navegador cai em `home`.
**Gates:** `npm run check:fast`, `npm run test:app-routing`, `npm run test:matriz`, `npm run test:ui-architecture`, `npm run test:foresight`.
**Commit:** `Remover o caderno de hipoteses da plataforma`.

### Fase 3 — Registro único de navegação (fundação dos menus novos)
**Objetivo:** uma única fonte de verdade para páginas e grupos, para que mover itens deixe de exigir 7 edições coordenadas.
1. Criar `src/app/navigationRegistry.ts` (TS estrito — `src/app/**` não admite `any`): para cada página, `{ key: AppPageKey, label, hash canônico, aliases, product, group, glyph, crumb, target }`; e a lista ordenada de grupos `{ id, label, icon, itemKeys }`. Grupos **não** têm produto (D5); a visibilidade é por item via `PAGE_PRODUCTS`.
2. `appRoutes.ts` passa a derivar `HASH_PAGE_MAP` do registro (mantendo o objeto exportado com a mesma forma — os módulos de rota precisam continuar puros e o teste compila só eles: **o registro não pode importar React, ícones ou CSS**; ícones/glifos ficam referenciados por nome, resolvidos no `Header`).
3. `Header.jsx` e `ContextBar.jsx` passam a consumir o registro (podem continuar `.jsx`; só a fonte muda). `PAGE_CRUMBS` derivado — e corrigir os dois gaps existentes: `pne-overview` e `relatorio-tecnico-municipal` sem breadcrumb hoje.
4. A lógica condicional do foresight (`withForesightItem`) permanece — o registro marca o item como `conditional: 'foresight'` e o Header aplica o gate. Ajustar `scripts/checks/foresight-educacao-navigation.test.mjs` **junto** se algum literal vigiado mudar de forma (mudança de teste sempre explicitada no debate).
5. **Nenhuma mudança visível nesta fase**: mesma sidebar, mesmas rotas, mesmos crumbs (exceto os 2 corrigidos). É um refactor de fundação.
**Gates:** todos os da Fase 2 + diff visual da sidebar (screenshot antes/depois idêntico a menos dos crumbs corrigidos).
**Commit:** `Introduzir registro unico de navegacao`.

### Fase 4 — Menu Relatórios
1. No registro: criar grupo `relatorios` ("Relatórios", ícone `FileText` ou similar) com, na ordem: `diagnostico` (label "Diagnóstico Municipal"), `matriz-prioridades`, item-link "Panorama Educacional" → `educacao?secao=panorama` (é um item de navegação com query, como os itens de seção do grupo educação já fazem), `relatorio-tecnico-municipal`.
2. Remover `diagnostico` e `matriz-prioridades` do grupo PNE; remover `relatorio-tecnico-municipal` da raiz. Grupo PNE fica: overview, metas legais, pne2014, pne2026, cenários (condicional — até a Fase 6).
3. Rotas e produtos **inalterados** (D7/D8). `ROUTE_CASES` intactos. Breadcrumbs atualizados para refletir o novo agrupamento (ex.: `diagnostico: 'Relatórios / Diagnóstico Municipal'`) — decisão de texto no debate.
4. Acordeão: `getOwnerGroup`/`PNE_PAGES`/`FINANCIAL_PAGES` derivados do registro para que o grupo certo abra com a página ativa (incluindo o caso `educacao?secao=panorama` ativo ⇒ abrir Relatórios ou Indicadores? **Regra: abre o grupo pelo qual se navegou; fallback = Indicadores** — implementar o fallback simples primeiro, sofisticar só se incomodar).
**Gates:** suíte da Fase 3 + navegação manual (browser) pelos 4 itens com município selecionado.
**Commit:** `Criar menu Relatorios`.

### Fase 5 — Fundação regional de dados + Menu Análise Regional
**5a. Mapa de regiões (config):**
1. Recuperar o recorte: `git show 207de681a^:public/data/educacao/regioes/<slug>.json` (10 arquivos) fornece `municipios_incluidos` por região — ou, preferencialmente, reexportar `regiao_senai` do banco `SESI\DB` (fora deste repo; se indisponível na sessão, usar o git como fonte e registrar a proveniência).
2. Criar `config/regions/rs.json`: `{ schemaVersion, stateCode: 'RS', regions: [{ slug, name, municipalityIbgeCodes: [...] }] }`, com validação: os 497 municípios de `config/municipalities/rs.json` particionados sem sobra/duplicata (script de check novo `scripts/checks/regions-config-test.mjs`).
3. Guarda de linguagem: nem `fiergs` nem `senai` aparecem em nomes públicos de região, slugs, artefatos ou UI (asserção no check novo).

**5b. Agregador e artefato regional:**
1. Reimplementar a exportação regional em `data_pipeline/scripts/export_education_indicators.py` (base: `git show 207de681a^` da função `exportar_regioes()` e agregadores), lendo o mapa de `config/regions/rs.json` (não mais da coluna do banco) e **rodando apenas para RS** (nenhum caminho de código para outras UFs), publicando `public/data/regioes/<slug>.json` + `public/data/regioes/manifest.json` no padrão da casa (manifesto com `contentHash`/`contentVersion`, escrita atômica, allowlist transacional e fingerprint — **corrigindo a dívida do legado, que ficava fora de ambos**).
2. Conteúdo do artefato por região (v1): identidade (`slug`, `name`, `municipalityIbgeCodes`, `totalMunicipios`), **indicadores PNE principais** (subconjunto acordado no debate — partir dos 49 do ciclo 2026 e selecionar os agregáveis com denominador válido) e **bloco de matrículas** (totais e principais recortes, somas diretas das contagens de `public/data/educacao/municipios/*.json`), com séries anuais.
3. Regras de agregação (herdar metodologia legada, endurecida): contagens somam; percentuais recalculados de numerador/denominador somados (nunca média de percentuais); indicadores sem denominador natural (IDEB/SAEB) **fora da v1** (média simples é frágil — entra depois com método defensável); propagar `null` ≠ zero ≠ indisponível conforme contrato da plataforma; supressão de célula pequena onde o dado municipal já suprime.
4. Loader novo `src/data/regionalData.ts` (ou `src/features/regional/regionalLoader.ts`) com validação de manifesto/hash no padrão foresight, + teste `scripts/checks/regional-loader.test.mjs`.

**5c. Página e menu:**
1. Nova página `analise-regional` ("Panorama da Região"): recebe `municipalityId`, resolve a região via mapa, carrega o artefato regional e apresenta: cabeçalho "Região <nome>" + lista de municípios da região (com destaque ao selecionado), indicadores PNE regionais e bloco de matrículas. Sem seletor próprio (D3).
2. Registro: grupo `analise-regional` ("Análise Regional") com "Panorama da Região" e o item condicional "Cenários da educação" **movido do grupo PNE para cá** (conteúdo municipal inalterado; gate do manifesto inalterado; atualizar `foresight-educacao-navigation.test.mjs` em conjunto). Rota nova `#analise-regional` (+ alias `#regiao`), produto `educacao` (D4), 7 pontos de registro via o registro único.
3. Grupo oculto quando a UF ativa não tem `config/regions/<uf>.json` (D2) — na prática, visível só em RS; a hospedagem de AL não muda em nada.
4. Novos `ROUTE_CASES` no `app-routing-test.mjs` para `#analise-regional` e alias.
**Gates:** suíte completa + `regions-config-test` + `regional-loader.test` + navegação manual: selecionar NSR ⇒ ver a região correta com indicadores coerentes (spot-check de 3 valores contra soma manual dos municípios).
**Commits:** `Criar mapa e artefato regional` e `Criar menu Analise Regional`.

### Fase 6 — Preparar o Vocações da Região (plataforma pronta, conteúdo pendente)
**Objetivo:** deixar o slot regional do foresight pronto para receber o artefato quando a camada de pesquisa (`SESI\PNE`) o produzir. **Nenhum conteúdo é inventado**: fail-closed até publicação real.
1. Generalizar o escopo de publicação do foresight: hoje o loader/manifesto validam IBGE7 em três pontos. Criar família de artefato paralela `public/data/vocacoes-regiao/` com manifesto próprio (`scopeType: 'region'`, chave = slug da região) e um loader irmão (`vocacoesRegiaoLoader`) reutilizando os validadores estritos do foresight (linguagem pública, hash, contrato) com a identidade regional no lugar da municipal. **Não** mexer no pipeline municipal existente (NSR/SL continuam íntegros).
2. Rota `#vocacoes-da-regiao` + página `vocacoes-regiao` reutilizando os componentes declarativos (`ForesightObservedSeries`, `ForesightScenarioComparison`, `ForesightScenarioTabs`) — a UI já é 100% orientada a `document.*`.
3. Item de menu condicional no grupo Análise Regional: `isVocacoesPublished(manifest, regionSlug)`; enquanto nenhum artefato existir, o item não aparece (mesmo padrão do foresight municipal). Manifesto vazio válido publicado desde já.
4. Esqueleto do gerador `scripts/generate-vocacoes-regiao.mjs` no padrão do gerador municipal (fonte canônica em `SESI\PNE\foresight`, contrato regional a ser definido lá), com `--check` e fail-closed. O contrato de origem regional é trabalho da camada de pesquisa — fora deste plano; o gerador falha fechado até ele existir.
5. Registrar no plano de pesquisa (memória/nota): próxima rodada em `SESI\PNE` = definir contrato "vocacoes-regiao v0.1" (transposição municipal→regional; a metodologia-mãe Vocações era regional, o caminho é conhecido).
6. Decisão D6 fica armada: quando o primeiro artefato regional for publicado, debate formal decide a aposentadoria/substituição dos Cenários municipais.
**Gates:** suíte completa + `#vocacoes-da-regiao` sem artefato ⇒ redireciona/oculta fail-closed sem erro de console.
**Commit:** `Preparar slot Vocacoes da Regiao`.

### Fase 7 — Revisão final (Fable)
1. Suíte integral: `npm run check:fast`, `test:app-routing`, `test:ui-architecture`, `test:matriz`, `test:foresight`, `test:foresight:e2e`, checks novos (`regions-config`, `regional-loader`), e2e da plataforma se existir no `package.json`.
2. Revisão de código do diff completo da branch (correção, aderência aos invariantes, linguagem pública sem tokens internos, sem resíduo de "caderno"/"fiergs").
3. Navegação manual completa (browser): todos os menus, 3 municípios do RS (NSR, São Leopoldo, um fora do piloto), e a hospedagem AL para confirmar que o menu Análise Regional não aparece e nada regrediu.
4. Atualização de docs (`docs/ARQUITETURA.md` — seção de regionalização reescrita: por que voltou e como difere do legado; `PRODUCT.md` se houver) e das memórias do projeto.
5. Merge em `main` só após aprovação do usuário.

---

## 4. Protocolo de orquestração (Opus 5 × Codex 5.6 × Fable)

**Papéis:** Opus 5 = orquestrador (prepara ordem de trabalho, avalia, debate, decide gate); Codex 5.6 sol xhigh = executor (aplica a mudança); Fable = revisor final (Fase 7).

**Por fase:**
1. **Ordem de trabalho (Opus):** Opus escreve em `.tmp/reorg/fase-<n>-ordem.md` a instrução autocontida para o Codex: objetivo, lista exata de arquivos (deste plano), invariantes que não podem quebrar, gates, e o que **não** fazer. Uma fase grande (5) é fatiada em 5a/5b/5c — **uma chamada de codex-rescue por fatia** (regra do runtime: um agente = uma chamada; `--write` obrigatório para escrever; sem `--cd`; o job pode morrer calado — Opus confere sempre o resultado no filesystem, nunca assume).
2. **Aplicação (Codex):** Codex aplica e escreve um relatório curto em `.tmp/reorg/fase-<n>-relatorio.md`: o que mudou, o que divergiu do plano e por quê, resultado dos gates que rodou.
3. **Debate (Opus × Codex):** Opus roda os gates ele mesmo (não confia no relato), lê o diff, e confronta o Codex com objeções concretas (mínimo: 1 rodada; máximo: 3): invariantes tocados? teste alterado junto com comportamento e justificado? divergência do plano defensável? Codex responde/corrige na mesma sessão de rescue quando possível, ou em nova chamada com contexto do relatório. Impasse após 3 rodadas ⇒ Opus registra a divergência em `.tmp/reorg/fase-<n>-pendencia.md` e escala para Fable/usuário em vez de forçar.
4. **Fechamento (Opus):** gates verdes + debate resolvido ⇒ commit da fase (mensagens acima, com `Co-Authored-By`), atualização de `.tmp/reorg/progresso.md` (fase, commit hash, pendências).
5. **Regra de ouro:** nenhum teste é enfraquecido silenciosamente. Toda mudança em `scripts/checks/*` aparece nomeada no relatório e no debate, com justificativa vinculada a uma decisão (D1–D8) deste plano.

**Fable (final):** revisão da Fase 7 sobre a branch inteira; achados voltam como ordens de correção via o mesmo protocolo.

---

## 5. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Porte da linguagem de sinais muda leituras da Matriz | Fase 1 isolada com comparação byte a byte das leituras renderizadas antes de qualquer deleção |
| Testes de navegação do foresight (regex sobre fonte) quebram nas fases 3–5 | Mudanças de teste sempre pareadas com a mudança de código, nomeadas no debate |
| Registro de navegação vaza impureza para os módulos de rota (React/ícones) e quebra a compilação isolada do `app-routing-test` | Registro sem imports de UI; glifos por nome; gate da Fase 3 inclui o teste |
| Agregação regional produz número errado (percentual como média, denominador ausente) | Regra explícita 5b.3; IDEB/SAEB fora da v1; spot-check manual de 3 valores no gate |
| Recorte regional vaza o nome institucional | Asserção anti-`fiergs`/`senai` no check de regiões + revisão de linguagem na Fase 7 |
| Codex morre calado ou aplica parcialmente | Opus verifica filesystem e roda gates ele mesmo após cada chamada |
| CSS de páginas novas estoura o orçamento do `ui-architecture-test` | Página regional reutiliza estilos existentes; se precisar de CSS novo, subir o baseline deliberadamente com justificativa (regra do próprio teste) |

---

## 6. Fora de escopo deste plano
- Conteúdo do Vocações da Região (contrato v0.1, cenários regionais) — camada de pesquisa `SESI\PNE`, rodada futura.
- Aposentadoria dos Cenários municipais (armada em D6, decidida quando o regional existir).
- IDEB/SAEB regional (fora da v1 do artefato regional).
- **Análise regional para qualquer UF além do RS** (D2): sem config de regiões, sem exportação, sem menu para AL/os demais estados. Quando (e se) outra UF ganhar recorte regional, o custo será criar `config/regions/<uf>.json` e rodar a exportação — a arquitetura já acomoda, mas isso é decisão futura, não trabalho deste plano.
