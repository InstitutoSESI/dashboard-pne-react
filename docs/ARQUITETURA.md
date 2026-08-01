# Arquitetura

## Visão geral

O produto é uma aplicação React entregue como site estático. `src/main.jsx` monta `App.tsx`; a navegação usa hash e parâmetros preservados por `src/app` e `src/hooks`. O Vite gera `dist`, incluindo os ativos de `public`.

```text
navegador
  -> React/Vite
  -> rotas por hash
  -> loaders em src/data e src/hooks
  -> JSONs públicos em /data
```

Não há backend de aplicação em produção. Toda informação disponível no navegador deve ser tratada como pública.

## Camadas

- `src/app`: resolução de rota, limites de carregamento e composição de páginas.
- `src/pages`: páginas de alto nível.
- `src/features`: fluxos de Educação, Diagnóstico e Financiamento.
- `src/components`: componentes compartilhados.
- `src/data`: catálogos, metadados e loaders dos contratos estáticos.
- `src/config`: validação e adaptação da configuração estadual ativa.
- `src/domain`: contratos puros de registro, rota e persistência municipal.
- `src/utils` e `src/hooks`: apresentação, navegação e carregamento.
- `src/styles` e `src/App.css`: tokens e camadas temáticas atuais.

As rotas são resolvidas em `src/app/appRoutes.ts`. O município selecionado é mantido pelo `MunicipalityContext` e sincronizado com a URL quando necessário.

## Mapa atual

| Área | Rota principal | Componente principal | Dados | Gerador | Testes |
| --- | --- | --- | --- | --- | --- |
| Entrada | `#home` | `src/pages/Home.jsx` | `municipios_index.json`, `indicadores.json` | `data_pipeline/scripts/export_static_data.py` | `test:app-routing`, E2E |
| PNE institucional | `#pne-overview`, `#pne-legal-goals` | `PneOverviewPage`, `PneLegalGoalsPage` | catálogos de indicadores, textos e relações legais em `src/data` | `export_static_data.py`, `scripts/generate-diagnostic-catalog.mjs` | `test:unit`, `test:data-sources` |
| Ciclos PNE | `#pne2014`, `#pne2026` | `src/pages/CyclePage.jsx` | `municipios/<ibge>/index.json`, `details.json`, referências estaduais por ciclo | `data_pipeline/src/pne`, `export_static_data.py` | `test:unit`, `test:python` |
| Diagnóstico | `#diagnostico` | `src/pages/Diagnostico.jsx` | release ativa única em `pne2026-diagnostic-v3` | `materialize_pne2026_public_diagnostic_v3.py`, `promote_pne2026_public_diagnostic_v3.py` | `test:diagnostic`, `test:python` |
| Educação | `#educacao` com `secao` | `src/features/education/EducationPage.tsx` | `municipios/<ibge>/index.json`, `educacao/visao-geral-municipal/<ibge>.json` | `export_education_indicators.py`, `materialize_municipal_education_overview.py` | `test:education`, `test:python` |
| Panorama financeiro | `#financeiros-panorama` | `MunicipalFinancePanoramaPage` | `municipios/<ibge>/financeiro.json`, histórico anual da QSE | `generate_municipal_finance.py`, `generate_qse_annual.py` | `test:municipal-finance`, `test:python` |
| Módulos financeiros | `#financeiros`, `#financeiros-*` | `src/pages/FinancialPage.jsx` | contrato municipal, catálogos e metadados de `src/data` | exportadores de Fundeb/PNATE e geradores financeiros | `test:municipal-finance`, `test:data-sources` |

## Contratos de dados

`config/states/rs.json` é a primeira configuração estadual versionada e é
validada em runtime por `src/config/stateConfig.ts` e pelo pipeline em
`data_pipeline/src/state_config.py`. Ela declara o contrato
`state-config-v1`, o estado RS, o prefixo IBGE 43, a cobertura esperada de 497
municípios e o locale `pt-BR`. O frontend continua RS-only: não há configuração
de outro estado nem seletor estadual nesta etapa.

`config/municipalities/rs.json` implementa `municipality-registry-v1` e é a
fonte canônica de código IBGE, nome e slug no pipeline Python. O registro é
validado por `data_pipeline/src/municipality_registry.py` contra a configuração
estadual, preserva a ordem versionada e oferece lookups imutáveis por código e
resolução única por nome. O código IBGE é a chave; nome é apresentação e
compatibilidade temporária; slug é rota pública.

`municipios_index.json` continua sendo o único catálogo municipal público e é
carregado pelo frontend junto com `indicadores.json`, sem terceira requisição.
Ele agora é uma projeção publicada do registro canônico, com o mesmo schema,
ordem e caminho existentes. Na fronteira de carregamento, o payload bruto em português
`MunicipalityIndexEntryPayload` é validado e convertido para a única coleção
canônica `MunicipalityRef[]`. O código IBGE (`ibgeCode`) é a identidade interna,
`name` serve somente à apresentação e `slug` somente às URLs. O registro mantém
a ordem pública, valida quantidade, prefixo, unicidade, path e indexa os
municípios por código. A resolução por nome existe apenas para migração do
armazenamento antigo e compatibilidade histórica de URL, sempre exigindo uma
correspondência única.

O agregado `municipios.json` continua existindo somente como staging interno do
pipeline, usado como entrada transitória do particionamento e indexado por nome.
Cada nome precisa resolver de forma única contra o registro; ele não cria código
nem slug. Fundeb e PNATE permanecem fontes de dados e de cobertura, mas não
definem existência, nome ou código municipal. No ciclo PNE 2026–2036,
`indicadores.json`, o catálogo do Diagnóstico e
`docs/generated/PNE_2026_CONTRACT.md` são projeções do contrato canônico,
verificadas por `npm run check:pne-contract`. O slug continua sendo o
identificador legível da rota, mas os arquivos municipais são canônicos somente
pelo código IBGE: `/data/municipios/<ibge>/...`.

O `MunicipalityContext` persiste `selectedMunicipalityId` no contrato JSON
versionado `dashboard-context-v2`, que inclui `stateCode` e `municipalityId`.
A chave antiga baseada somente no nome é lida uma vez para migração, convertida
por correspondência única e removida; ela nunca volta a ser escrita. Rotas com
`municipio` aceitam slug, código IBGE ou nome legado e, quando válidas, são
normalizadas para o slug sem mudar a identidade interna.

Esta fundação ainda não constitui suporte real a múltiplos estados. Os scripts
centrais aceitam `--state RS` e falham antes de escrever quando a configuração
solicitada não existe. Fontes, fórmulas e agregados ainda específicos do RS,
Alagoas, seleção e publicação por estado dependem das Etapas 4B2 e 4C.

`public/data` é saída publicada e versionada. Snapshots que não podem ser reconstruídos durante um build comum ficam em `data_pipeline/data`. Os cenários aprovados em `data_pipeline/data/planning_scenarios` alimentam o export principal.

Os contratos municipais estáticos administrados pelo particionamento são
`municipios/<IBGE>/index.json` e `municipios/<IBGE>/details.json`. O segundo
contém os detalhes dos indicadores e conteúdos municipais compartilhados em
`_shared`; o piloto `municipal-inequality-v1` fica em
`_shared.municipal_inequality`. O antigo `diagnostico.json` municipal foi
aposentado. O Diagnóstico PNE completo permanece separado e é carregado da
release ativa apontada por `pne2026-diagnostic-v3/current.json`.

## Pipeline

As regras dos ciclos ficam em `data_pipeline/src/pne`, os detalhes em `pne/indicator_details.py` e os exportadores especializados em módulos Python puros. O pipeline não inicializa aplicação web, páginas, layouts ou callbacks. Stagings são isolados por domínio: o particionamento estático usa `data_pipeline/export/static_partitioned`, enquanto os contratos financeiros usam `data_pipeline/export/municipal_finance`. Cada sincronizador só pode remover arquivos pertencentes ao próprio contrato. O fluxo operacional está em [OPERACAO.md](OPERACAO.md).

O ambiente Python do pipeline também tem contrato único: as dependências
diretas ficam em `data_pipeline/pyproject.toml` e a resolução reproduzível em
`data_pipeline/uv.lock`. Os comandos operacionais do `package.json` executam
Python por `uv run --project data_pipeline`; a pesquisa usa o mesmo ambiente,
mas permanece fora do pipeline automático.

## Publicação e segurança

O artefato publicável é `dist`. A hospedagem deve servir arquivos estáticos e usar `index.html` como fallback. Credenciais, dumps privados e dados pessoais não podem entrar em `public`, `dist` ou arquivos versionados.
