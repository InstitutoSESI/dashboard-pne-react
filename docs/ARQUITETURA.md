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

### Perfil estadual de build

`PLATFORM_STATE` seleciona um manifesto em `config/publications`. O manifesto
aponta explicitamente a configuração estadual, o registro municipal e uma única
raiz de dados versionada. Antes do build completo ou do
servidor de desenvolvimento, a fronteira de publicação exige igualdade entre
UF, prefixo IBGE, contagem, ordem, nomes, slugs, paths e conjunto de diretórios
municipais. Qualquer divergência falha fechada.

O build desativa a cópia genérica de `public`: ativos compartilhados são
copiados sem a subárvore `data`, e somente os dados do perfil validado ocupam
`dist/data`. No desenvolvimento, um middleware intercepta todo caminho `/data`
e nunca deixa uma ausência cair na publicação de outra UF. O build app-only
continua sem copiar dado público. RS é o padrão compatível e a publicação
analítica completa. AL é uma publicação `identity-only`, com raiz própria e
indisponibilidade analítica explícita; não existe fallback de AL para RS.

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
municípios e o locale `pt-BR`. `config/publications/rs.json` declara o contrato
`state-publication-v3` e aponta a publicação RS para `public/data`, com analytics
completo. O manifesto AL usa o mesmo schema, aponta para `config/states/al.json`,
`config/municipalities/al.json` e `state-publications/al/data`, e declara
`analyticsStatus=identity-only`. O frontend recebe ambos os contratos validados
pelo build; módulos analíticos só são carregados quando o perfil os declara
disponíveis.

O `state-publication-v3` acrescenta o status `partial` e o campo
`enabledProducts`. Uma publicação `partial` exige mensagem de indisponibilidade e
uma lista não vazia de produtos entre `pne`, `educacao` e `financiamento`; os
produtos ausentes continuam navegáveis por URL, mas rendem um aviso explícito de
indisponibilidade em vez de dado. `complete` e `identity-only` exigem
`enabledProducts: null`, e declarar todos os produtos em `partial` é recusado —
isso é `complete`. O vocabulário é replicado em `src/config/analyticsProducts.ts`,
`scripts/lib/state-build-profile.mjs` e
`data_pipeline/src/state_publication.py`, com paridade verificada em
`scripts/checks/multistate-hosting.test.mjs`.

A raiz pública deixou de ser uma constante: `resolve_public_data_dir(state_code)`
em `data_pipeline/src/state_publication.py` lê o manifesto da UF, de modo que RS
resolve `public/data` e AL resolve `state-publications/al/data`. Não há fallback:
uma UF sem manifesto falha antes de escrever.

`config/municipalities/rs.json` implementa `municipality-registry-v1` e é a
fonte canônica de código IBGE, nome e slug no pipeline Python. O registro é
validado por `data_pipeline/src/municipality_registry.py` contra a configuração
estadual, preserva a ordem versionada e oferece lookups imutáveis por código e
resolução única por nome. O código IBGE é a chave; nome é apresentação e
compatibilidade temporária; slug é rota pública.

`municipios_index.json` continua sendo o único catálogo municipal público. Em
uma publicação analítica completa ele é carregado junto com `indicadores.json`;
em uma publicação `identity-only`, somente o catálogo é solicitado.
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

A regionalização foi removida da plataforma: o exportador não possui mais
agregação regional e os artefatos legados `educacao/regioes/*.json` foram
excluídos do repositório. As subárvores
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

Esta fundação separa produto hospedável de cobertura analítica. Somente o RS tem
suporte analítico completo; `rs` é normalizado para `RS`. AL pode ser servido e
empacotado como produto somente de identidade, sem expor qualquer JSON analítico
do RS. A fonte oficial de identidade de AL foi incorporada em
`data_pipeline/data/municipality_registry_sources/al`, com o corpo integral da
rota de municípios por UF da API de Localidades do IBGE, hashes de transporte,
resposta e snapshot, cobertura de 102 municípios e manifesto de proveniência.
Sua projeção `municipality-registry-v1` e o `state-config-v1` correspondente
ficam em `config/states/al.json` e `config/municipalities/al.json`; o parser lê
tokens numéricos como texto desde a desserialização e os códigos canônicos
permanecem strings de sete dígitos.

A publicação AL contém exatamente um manifesto, o índice dos 102 municípios e
um índice por código IBGE, todos com analytics `unavailable`. O materializador
gera em staging, valida o conjunto integral e promove com escrita atômica,
preservação de arquivos idênticos e rollback. A ausência intencional de
`config/states/al.json` e `config/municipalities/al.json` mantém o pipeline
analítico fail-closed. Promover AL para esses diretórios exige primeiro validar
fontes, metodologias, dados analíticos e contratos de compatibilidade próprios.
Nomes físicos de fontes, inclusive tabelas com sufixo `_rs`, podem continuar
específicos do RS sem definir a identidade ou o universo. Esta incorporação não
regenerou os outputs públicos atuais; Educação Indígena e integrações SIDRA,
domínios PNE e Financeiro permanecem para etapas posteriores.

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

### Fingerprint shadow e skip opt-in da Educação principal (5D2A/5D2B)

A tarefa piloto tem identidade estável `education.core.rs`, estado explícito
`RS`, schema `education-task-fingerprint-v1` e algoritmo tabular
`education-source-digest-v1`. O modo shadow recebe o registro municipal e as 18
relações efetivamente entregues ao materializador. Cada DataFrame já carregado
produz um digest sensível a valores, nulls, colunas, dtypes e multiplicidade de
linhas, mas independente da ordem não semântica das linhas. Os campos
operacionais `DATA_EXPORTACAO`, `data_carga`, `updated_at`, `generated_at`,
`runId` e paths de staging ficam fora da identidade; sua produção pública não
foi alterada. Valores float continuam participando após o cânone versionado
`round-float-to-12-decimal-places-v1`, que elimina apenas os últimos bits
instáveis de agregações PostgreSQL em precisão muito superior à publicação.

O `inputFingerprint` combina os 19 digests tabulares, estado, registro dos 497
municípios, compatibilidade dos 182 slugs, definição dos blocos, contrato de
infraestrutura escolar, materialização, publicação transacional, profiling,
repositório de dados, identificadores das relações/queries, adaptador
`utils_educacao`, `uv.lock` e versões de Python, pandas e numpy. A allowlist usa
caminhos explícitos relativos ao repositório. O adaptador externo é resolvido a
partir do módulo efetivamente importado e participa por identificador lógico,
nome do módulo, versão quando declarada, tamanho e SHA-256 do arquivo `.py`,
nunca por seu path local. Módulo ausente, não verificável ou com mais de um
candidato importável produz miss seguro.

Após uma promoção ou no-op confirmado, o piloto calcula o manifesto forte dos
499 outputs administrados: `index.json`, `municipios_index.json` e os 497
`municipios/<IBGE>.json`. Cada entrada guarda path relativo, tamanho e SHA-256;
o conjunto completo recebe um SHA-256 agregado. Subárvores de outros domínios
não entram no manifesto. O estado local é escrito atomicamente somente depois
da confirmação dos outputs finais em
`data_pipeline/export/task-state/RS/education-core.json`, fora de dados,
staging e profiles e sob uma raiz ignorada pelo Git. Arquivo ausente ou
corrompido é sempre miss seguro e nunca serve como fonte de dados.

`wouldSkip=true` exige task state válido, mesmo `inputFingerprint` e paridade
forte dos outputs públicos. Os motivos incluem `first_run`, `manifest_missing`,
`manifest_invalid`, `input_changed`, `contract_changed`, `output_missing`,
`output_changed`, `output_extra`, `state_mismatch`, `algorithm_changed` e
`eligible`. Erro ou incerteza produz `wouldSkip=false`. A flag shadow continua
executando consultas, materialização, staging, validações e promoção/no-op mesmo
quando elegível. A flag incremental, explicitamente opt-in, calcula a decisão
antes de chamar a camada transacional e retorna `reused=true` somente para
`eligible`; nesse caminho não cria staging, não materializa, não valida staging,
não promove, não cria backup/rollback e não regrava o task state. Todo miss usa
o fluxo 5B2 integral e só substitui o state depois da publicação confirmada.

O task state e os profiles não armazenam credenciais, URL de conexão, ambiente
completo, paths pessoais ou valores analíticos municipais. Profiling mede
tempo e volume de operações; fingerprint identifica entradas e integridade de
outputs. São contratos complementares, não equivalentes.

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
desnecessários. O profile mede o pipeline atual, inclusive a decisão incremental
da Educação; ele não autoriza o hit nem funciona como cache. Em hit real, os
counters registram `fingerprintHit=1`, `wouldSkip=1`, `actuallySkipped=1` e zero
staging/materialização/renderização. Sem `--profile`, não há sessão, timers
internos, serialização, fragmentos ou diretório de relatório.

## Publicação e segurança

O artefato publicável é `dist`. `npm run build` continua sendo o build completo:
o Vite desativa `copyPublicDir`, copia os ativos compartilhados sem a subárvore
`data` e materializa em `dist/data` somente a publicação estadual validada. O
modo `app-only`, exposto por `npm run build:app`, omite todos os ativos públicos
e grava em `dist/app-only`; ele também é usado por `check:fast` para validação
leve. `npm run preview` serve o `dist` existente e, para validar uma release,
pressupõe um build completo atual. A hospedagem e o deploy continuam
responsáveis por produzir e servir o pacote completo, com `index.html` como
fallback. Dados já promovidos na raiz declarada e o conteúdo materializado em
`dist` têm ciclos operacionais separados. Credenciais, dumps privados e dados
pessoais não podem entrar em `public`, `dist` ou arquivos versionados.

A Etapa 5B2 alterou somente o mecanismo de geração e publicação da Educação
principal. Nenhuma fonte real foi consultada e nenhum arquivo público foi
regenerado ou promovido durante sua implementação e validação.
