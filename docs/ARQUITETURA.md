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

`municipios_index.json` é o único catálogo municipal público e é carregado no início junto com `indicadores.json`. O frontend deriva em memória a lista simples de nomes a partir das entradas desse catálogo, preservando o contrato dos consumidores atuais. O agregado `municipios.json` continua existindo somente como staging interno do pipeline, usado como entrada do particionamento, e não faz parte do contrato público. No ciclo PNE 2026–2036, `indicadores.json`, o catálogo do Diagnóstico e `docs/generated/PNE_2026_CONTRACT.md` são projeções do contrato canônico, verificadas por `npm run check:pne-contract`. O slug continua sendo o identificador legível da rota, mas os arquivos municipais são canônicos somente pelo código IBGE: `/data/municipios/<ibge>/...`.

`public/data` é saída publicada e versionada. Snapshots que não podem ser reconstruídos durante um build comum ficam em `data_pipeline/data`. Os cenários aprovados em `data_pipeline/data/planning_scenarios` alimentam o export principal.

O arquivo municipal `diagnostico.json` preserva a URL pública, mas contém
somente `municipal-inequality-v1`. O diagnóstico PNE completo é carregado da
release ativa apontada por `pne2026-diagnostic-v3/current.json`.

## Pipeline

As regras dos ciclos ficam em `data_pipeline/src/pne`, os detalhes em `pne/indicator_details.py` e os exportadores especializados em módulos Python puros. O pipeline não inicializa aplicação web, páginas, layouts ou callbacks. Stagings são isolados por domínio: o particionamento estático usa `data_pipeline/export/static_partitioned`, enquanto os contratos financeiros usam `data_pipeline/export/municipal_finance`. Cada sincronizador só pode remover arquivos pertencentes ao próprio contrato. O fluxo operacional está em [OPERACAO.md](OPERACAO.md).

## Publicação e segurança

O artefato publicável é `dist`. A hospedagem deve servir arquivos estáticos e usar `index.html` como fallback. Credenciais, dumps privados e dados pessoais não podem entrar em `public`, `dist` ou arquivos versionados.
