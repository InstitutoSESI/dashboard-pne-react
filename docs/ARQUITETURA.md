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
| Educação | `#educacao` com `secao` | `src/features/education/EducationPage.tsx` | `municipios/<ibge>/index.json`, `educacao/visao-geral-municipal/<ibge>.json` | `export_education_indicators.py`, `materialize_municipal_education_overview.py` | `test:education`, `test:pipeline-education-state`, `test:python` |
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

Na camada Python de Educação, a exportação geral, a Visão Geral Municipal, a
Educação Superior e a Educação Especial carregam `StateConfig` e
`MunicipalityRegistry` antes de banco, fonte ou staging. Seus entrypoints usam
`--state`, filtram pelo código estadual ou pelo conjunto exato de códigos do
registro e preservam o código IBGE como texto e identidade. Nome e slug canônico
vêm do registro; a compatibilidade de publicação dos 182 slugs educacionais
históricos fica separada em
`config/compatibility/education-municipality-routes/rs.json`. O resolvedor de
domínio aplica esses overrides somente ao índice educacional geral e à Educação
Especial; a Visão Geral continua canônica e Superior não publica slug. A ordem
histórica do índice também é projetada deterministicamente, sem ler o arquivo
público anterior. Índices e manifestos públicos são somente saídas derivadas.
Ausência, zero observado, `derived_zero`, indisponibilidade e não aplicabilidade
continuam estados distintos conforme cada contrato.

A publicação da Educação principal é transacional e fail-closed. O exportador
`data_pipeline/scripts/export_education_indicators.py` não conhece o caminho
físico de `public/data`: ele recebe exclusivamente o diretório `output` de um
run isolado em `data_pipeline/.staging/education/<run-id>`. Depois de consultar
e calcular o lote integral, materializa nesse staging a allowlist ativa:

- `educacao/index.json`;
- `educacao/municipios_index.json`;
- `educacao/municipios/<IBGE>.json`, exatamente um para cada código textual do
  `MunicipalityRegistry`.

Os arquivos `educacao/regioes/*.json` são artefatos legados do mesmo exportador,
mas o fluxo padrão não os gera nem os administra. As subárvores
`educacao-especial`, `superior`, `visao-geral-municipal` e `siope` pertencem a
outros domínios e ficam fora da allowlist. Os 182 slugs históricos não são
aliases físicos: continuam campos do índice derivados da configuração de
compatibilidade versionada.

Antes da promoção, o publicador exige o conjunto exato de arquivos, JSON
estrito sem `NaN`/`Infinity`, schemas conhecidos, identidade e nome canônicos,
mesma data do manifesto, índice compatível e conjunto exato de slugs. Falha de
qualquer município, serialização, escrita ou validação rejeita o lote inteiro.
Como `public/data/educacao` compartilha a raiz com outros domínios, a promoção é
arquivo a arquivo: os arquivos alterados usam substituição atômica, os alvos
anteriores e os órfãos administrados recebem backup, e um journal restaura o
estado anterior em ordem reversa se ocorrer exceção. Arquivos byte a byte
idênticos não são substituídos e preservam o `mtime`; órfãos dentro do padrão
municipal administrado só são removidos depois da validação integral.

Esta fundação ainda não constitui suporte real a múltiplos estados. Somente o
RS está configurado; `rs` é normalizado para `RS`, enquanto `AL` falha antes de
efeitos colaterais e não possui configuração nem publicação. Nomes físicos de
fontes, inclusive tabelas com sufixo `_rs`, podem continuar específicos do RS
sem definir a identidade ou o universo. A parametrização não regenerou os
outputs públicos atuais. Educação Indígena e integrações SIDRA, domínios PNE e
Financeiro permanecem para etapas posteriores, assim como seleção e publicação
de produto por estado.

`public/data` é saída publicada e versionada. Snapshots que não podem ser reconstruídos durante um build comum ficam em `data_pipeline/data`. Os cenários aprovados em `data_pipeline/data/planning_scenarios` alimentam o export principal.

Os contratos municipais estáticos administrados pelo particionamento são
`municipios/<IBGE>/index.json` e `municipios/<IBGE>/details.json`. O segundo
contém os detalhes dos indicadores e conteúdos municipais compartilhados em
`_shared`; o piloto `municipal-inequality-v1` fica em
`_shared.municipal_inequality`. O antigo `diagnostico.json` municipal foi
aposentado. O Diagnóstico PNE completo permanece separado e é carregado da
release ativa apontada por `pne2026-diagnostic-v3/current.json`.

No detalhe de Internet do ano de referência da infraestrutura escolar,
`publica` é o subtotal de `federal + estadual + municipal`, e `privada`
completa o total. A coexistência do subtotal com sua decomposição é aceita
somente quando `series_total.valor` e `series_components.numerador` também
reconciliam com `publica + privada`. O padrão misto de `temporarios` permanece
uma compatibilidade histórica separada, sinalizada por warning.

## Pipeline

As regras dos ciclos ficam em `data_pipeline/src/pne`, os detalhes em `pne/indicator_details.py` e os exportadores especializados em módulos Python puros. O pipeline não inicializa aplicação web, páginas, layouts ou callbacks. Stagings são isolados por domínio: o particionamento estático usa `data_pipeline/export/static_partitioned`, os contratos financeiros usam `data_pipeline/export/municipal_finance` e a Educação principal usa runs efêmeros em `data_pipeline/.staging/education`. Cada sincronizador só pode remover arquivos pertencentes ao próprio contrato. O fluxo operacional está em [OPERACAO.md](OPERACAO.md).

Geração, validação e promoção de dados são independentes da geração do bundle.
`update_static_data.py` termina após validar por padrão e só chama o build
completo quando recebe `--build`. O build permanece uma etapa posterior à
validação, de modo que falhas de exportação, Educação, materialização,
sincronização ou validação não o alcançam. `--skip-build` é somente um alias
histórico do novo padrão sem build. Essa separação não altera os contratos,
schemas, fórmulas, dados ou a publicação transacional da Educação.

O ambiente Python do pipeline também tem contrato único: as dependências
diretas ficam em `data_pipeline/pyproject.toml` e a resolução reproduzível em
`data_pipeline/uv.lock`. Os comandos operacionais do `package.json` executam
Python por `uv run --project data_pipeline`; a pesquisa usa o mesmo ambiente,
mas permanece fora do pipeline automático.

### Perfil de desempenho do pipeline

`data_pipeline/src/pipeline_profiling.py` fornece a instrumentação opt-in comum.
Uma `ProfileSession` identifica o run, estado, comando, processo, parâmetros
sanitizados e ambiente mínimo. `ProfileEvent` registra hierarquia, categoria,
status, timestamps UTC e duração monotônica por `perf_counter_ns`; counters
finitos carregam linhas, colunas, arquivos, bytes e resultados funcionais sem
misturá-los com a duração. As categorias versionadas são `orchestration`,
`subprocess`, `query`, `compute`, `serialization`, `read`, `write`,
`validation`, `promotion`, `cache` e `build`.

O orquestrador cria um evento de subprocesso e propaga somente IDs controlados,
estado, diretório e parâmetros sanitizados. Cada processo Python escreve um
fragmento atômico próprio; o pai valida os schemas, IDs e relações e consolida
os fragmentos deterministicamente em `profile.json` e `summary.json`. Não há
arquivo global escrito concorrentemente. Operações repetidas de cache e de
arquivo são agregadas para não criar eventos por município, linha ou célula.

Os relatórios ficam em `data_pipeline/export/profiles/<run-id>/`, fora de
`public/data` e ignorados pelo Git. Eles não incluem dataset analítico, SQL com
valores vinculados, credenciais, ambiente completo ou paths pessoais
desnecessários. O profile mede o pipeline atual e orienta as Etapas 5D2–5D5;
não cria fingerprint, cache persistente, changed-only ou qualquer execução
incremental. Sem `--profile`, não há sessão, timers internos, serialização,
fragmentos ou diretório de relatório.

## Publicação e segurança

O artefato publicável é `dist`. `npm run build` continua sendo o build completo:
o Vite usa `copyPublicDir` e inclui `public/data`. O modo `app-only`, exposto por
`npm run build:app`, desativa essa cópia e grava em `dist/app-only`; ele também é
usado por `check:fast` para validação leve. `npm run preview` serve o `dist`
existente e, para validar uma release, pressupõe um build completo atual. A
hospedagem e o deploy continuam responsáveis por produzir e servir o pacote
completo, com `index.html` como fallback. Dados já promovidos em `public/data` e
o conteúdo materializado em `dist` têm ciclos operacionais separados.
Credenciais, dumps privados e dados pessoais não podem entrar em `public`,
`dist` ou arquivos versionados.

A Etapa 5B2 alterou somente o mecanismo de geração e publicação da Educação
principal. Nenhuma fonte real foi consultada e nenhum arquivo público foi
regenerado ou promovido durante sua implementação e validação.
