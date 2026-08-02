# Pipeline e operação

## Preparação

```powershell
winget install --id=astral-sh.uv -e
uv --version
npm ci
npm run python:sync
npm run python:lock:check
npm run test:python
```

O intervalo suportado é Python 3.11 a 3.13. `data_pipeline/pyproject.toml`
declara as dependências diretas de runtime e mantém `pytest` somente no grupo
`test`; `data_pipeline/uv.lock` fixa a resolução completa usada pelos comandos.
Não instale pacotes avulsos para corrigir imports. Atualizações de dependências
devem ocorrer em mudança própria, com regeneração e validação explícitas do
lock. O antigo `data_pipeline/requirements.txt` foi aposentado.

Para uma integração pontual com pip, gere uma exportação descartável em um
diretório ignorado e não a versione:

```powershell
uv export --project data_pipeline --frozen --format requirements.txt `
  --output-file exports/python-requirements.txt
```

Uma segunda sincronização sem mudanças reutiliza o ambiente local em
`data_pipeline/.venv`. O uv reduz o custo de preparação do ambiente, mas não
substitui a futura otimização incremental da materialização dos dados.

As fontes reproduzíveis e os insumos de regeneração permanecem em
`data_pipeline/data`. Os artefatos públicos são gerados pelo pipeline e não
devem ser editados manualmente.

## Configuração estadual e identidade municipal

`config/states/rs.json` é a configuração estadual ativa e versionada. Frontend
e pipeline validam o mesmo contrato `state-config-v1`. A identidade municipal
canônica do pipeline fica separada em `config/municipalities/rs.json`, no
contrato `municipality-registry-v1`; `public/data/municipios_index.json` é uma
projeção publicada desse registro e não pode ser usado como fonte do universo.

Internamente, o código IBGE textual identifica o município; o nome é texto de
apresentação e compatibilidade temporária dos agregados por nome, e o slug é o
valor canônico de URL. A exportação geral, a Visão Geral Municipal, a Educação
Superior e a Educação Especial usam `StateConfig` e `MunicipalityRegistry`;
os 182 slugs educacionais históricos diferentes do canônico são compatibilidade
explícita de publicação em
`config/compatibility/education-municipality-routes/rs.json`. Esse arquivo não é
cadastro: contém apenas overrides por código IBGE. O índice geral e a Educação
Especial usam o resolvedor; a Visão Geral usa o slug canônico e Superior não
publica slug. Nenhum materializador lê o índice educacional anterior para gerar
as rotas. Índices educacionais publicados são saídas derivadas, não fontes de
identidade.
O particionamento resolve nomes de forma única contra o registro e nunca deriva
código ou slug do nome. Fundeb e PNATE fornecem dados, mas não identidade. A
persistência do navegador usa
`dashboard-context-v2`, com estado e código municipal. Valores antigos baseados
em nome são migrados uma única vez quando há correspondência inequívoca. Não há
seletor de estado, configuração de Alagoas nem caminhos públicos de dados por
estado. Educação Indígena e SIDRA, PNE e Financeiro permanecem para etapas
posteriores, e o suporte de produto e publicação por estado depende de trabalho
futuro. Nomes físicos de fontes podem continuar específicos do RS.

Os comandos centrais aceitam `--state RS`; `rs` é normalizado para `RS`. Um
estado sem `config/states/<uf>.json`, como `AL` nesta etapa, falha antes de
exportação, particionamento, sincronização ou escrita, sem fallback para RS.
Ausência e zero continuam distintos nos contratos educacionais. A
parametrização estadual não executou atualização real nem regenerou os outputs
públicos existentes do RS.

## Atualização de dados

```powershell
npm run update:data
```

O comando executa, nesta ordem:

1. exportação dos agregados;
2. particionamento em `data_pipeline/export/static_partitioned`;
3. geração integral da Educação em staging, validação fail-closed e promoção
   transacional;
4. incorporação do recorte municipal de desigualdade em `details.json` no staging;
5. sincronização atômica do conjunto estático administrado;
6. validação dos detalhes.

O fluxo termina após a validação e não executa build por padrão. Geração,
promoção dos dados versionados e materialização de `dist` são responsabilidades
separadas. Nenhuma fórmula, schema, metodologia ou publicação analítica foi
alterada por esse desacoplamento.

Somente arquivos alterados são copiados. Educação, Financeiro, QSE e a
publicação do diagnóstico PNE têm autoridades próprias e não são removidos pela
sincronização estática.

O passo educacional administra somente `educacao/index.json`,
`educacao/municipios_index.json` e os 497
`educacao/municipios/<IBGE>.json`. Ele preserva `regioes`, `educacao-especial`,
`superior`, `visao-geral-municipal`, `siope` e qualquer arquivo fora da
allowlist. Um erro educacional retorna código não zero e interrompe o
orquestrador antes da desigualdade, validação e de qualquer build explicitamente
solicitado.

Comandos úteis:

```powershell
# Atualiza e valida os dados, sem build
npm run update:data

# Atualiza e valida somente Educação e o recorte de desigualdade derivado dela
npm run update:education-data

# Alias histórico do fluxo padrão sem build
npm run update:data:skip-build

# Atualiza, valida e só então executa o build completo
npm run update:data:and-build

# Atualiza Educação, valida e só então executa o build completo
npm run update:education-data:and-build

# Mostra as etapas e tempos sem executar
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --dry-run --profile

# Explicita o estado ativo sem alterar o caminho público atual
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --state RS --dry-run

# Confere somente o plano educacional e a propagação do estado, sem executar
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --state RS --education-only --dry-run

# Inclui o build completo somente no plano, depois da validação
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --state RS --dry-run --build

# Mostra a CLI educacional sem banco, staging ou escrita
uv run --project data_pipeline --frozen python data_pipeline/scripts/export_education_indicators.py --help

# Valida estado, registro, slugs e o plano sem banco, staging ou escrita
uv run --project data_pipeline --frozen python data_pipeline/scripts/export_education_indicators.py --state rs --dry-run

# Gera e valida o lote integral sem promover; preserva o staging para inspeção
# (este comando acessa as fontes e não foi executado na Etapa 5B2)
uv run --project data_pipeline --frozen python data_pipeline/scripts/export_education_indicators.py --state RS --no-promote

# Valida a parametrização dos quatro domínios educacionais
npm run test:pipeline-education-state

# Valida staging, fail-closed, no-op, promoção, rollback e orquestração
npm run test:pipeline-education-publication

# Validação rápida do código da aplicação
npm run check:fast
```

`--build` e `--skip-build` são mutuamente exclusivos. A segunda opção permanece
aceita somente por compatibilidade e equivale ao padrão sem build.
`--validate-only` nunca constrói a aplicação e não pode ser combinado com
`--build`. Em dry-run, o build aparece no plano apenas quando foi solicitado;
nenhum dry-run cria staging, consulta banco, acessa rede, escreve dados ou
executa Vite.

## Build da aplicação, preview e deploy

Desenvolvimento visual e validação leve usam:

```powershell
npm run dev
npm run check:fast
npm run build:app
```

`build:app` usa o modo `app-only`, grava em `dist/app-only` e não copia
`public/data`. `check:fast` continua composto por typecheck, lint e esse build
leve.

O pacote de release completo é uma ação explícita:

```powershell
npm run build
```

Esse comando preserva a semântica atual do Vite, inclusive `copyPublicDir`, e
copia toda a árvore `public`, incluindo `public/data`, para `dist`. `npm run
preview` não atualiza dados nem constrói o pacote: ele serve o `dist` existente.
Para validar uma release localmente, gere antes um build completo atual. O
deploy continua responsável por executar `npm run build` quando necessário;
paths, base, assets e hospedagem não mudaram.

## Conteúdo municipal compartilhado

`public/data/municipios/<IBGE>/details.json` contém detalhes dos indicadores e
conteúdos compartilhados sob `_shared`. O piloto de desigualdade usa o contrato
completo `municipal-inequality-v1` em `_shared.municipal_inequality`. O antigo
`public/data/municipios/<IBGE>/diagnostico.json` foi aposentado; isso não altera
a publicação do Diagnóstico PNE completo em `pne2026-diagnostic-v3`.

A geração após a atualização de Educação é feita por:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/scripts/materialize_municipal_inequality.py `
  --output-root data_pipeline/export/static_partitioned/municipios
```

O materializador lê os documentos educacionais atuais, aplica supressão de
células pequenas, preserva os demais campos de `details.json` — inclusive
`_shared.privadas_conveniadas` — e grava apenas quando o conteúdo semântico
mudou. O particionamento e a sincronização administram somente `index.json` e
`details.json` em cada diretório municipal.

## Publicação do diagnóstico PNE

A aplicação resolve exclusivamente:

1. `public/data/pne2026-diagnostic-v3/current.json`;
2. o manifesto apontado em `releases/<hash>/manifest.json`;
3. `releases/<hash>/municipios/<IBGE>.json`.

O nome do diretório público é preservado por estabilidade de URL. Dentro dele
deve existir somente a release apontada por `current.json`.

Geração e validação:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/scripts/materialize_pne2026_public_diagnostic_v3.py `
  --output-dir data_pipeline/.staging/pne-diagnostic-current

uv run --project data_pipeline --frozen python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir data_pipeline/.staging/pne-diagnostic-current `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

Publicação:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir data_pipeline/.staging/pne-diagnostic-current `
  --destination-dir public/data/pne2026-diagnostic-v3
```

A ativação de `current.json` é atômica. Depois dela, o promotor apaga releases
inativas automaticamente. Para apenas conferir ou aplicar essa invariável:

```powershell
uv run --project data_pipeline --frozen python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --prune-inactive `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

## Staging por domínio

- estáticos gerais: `data_pipeline/export/static_partitioned`;
- financeiro municipal: `data_pipeline/export/municipal_finance`;
- Educação principal: `data_pipeline/.staging/education/<run-id>/output`;
- staging temporário do diagnóstico PNE: `data_pipeline/.staging`.

Esses diretórios não são fontes analíticas. Podem ser regenerados pelos
respectivos comandos e não devem ser usados como entrada permanente.

### Publicação transacional da Educação principal

O entrypoint valida `StateConfig`, `MunicipalityRegistry` e a compatibilidade
dos 182 slugs antes de criar o staging. `RS` e `rs` selecionam a mesma
configuração; um estado não configurado, como `AL`, falha antes de banco,
staging ou escrita. `--help` e `--dry-run` também não criam staging nem acessam
fontes.

O run materializa primeiro todos os documentos e acumula o relatório completo
de falhas municipais. Qualquer falha impede os índices e a promoção. A árvore
prospectiva só é aceita quando contém exatamente os 499 arquivos administrados,
com 497 códigos IBGE textuais, nomes canônicos, schemas válidos, valores JSON
finitos e índices coerentes. Lotes parciais por `--limit` ou `--municipios` são
reconhecidos pela CLI, mas recusados antes do primeiro efeito.

Na promoção, arquivos idênticos são classificados como `preserved` e mantêm
bytes e `mtime`. Os demais são reportados como `created`, `updated` ou
`removed`. Somente órfãos que correspondam ao padrão administrado
`municipios/<IBGE>.json` podem ser removidos, e apenas depois da validação
integral. Backups e temporários ficam vinculados ao run; uma falha intermediária
restaura, em ordem reversa, cada alvo já alterado. Em sucesso, staging e backups
são removidos. Em falha de rollback de sistema operacional, o run com backup é
preservado e o processo retorna erro para intervenção; `--no-promote` também
preserva explicitamente um staging já validado.

O baseline de auditoria da Etapa 5B2 fica somente no diretório ignorado
`data_pipeline/export/debug`. A etapa não executou `update:data`,
`update:education-data`, consulta a banco, regeneração nem promoção de dados
reais.

## Validação para entrega

```powershell
npm run check:fast
npm run python:lock:check
npm run check:python-deps
npm run test:unit
npm run test:education
npm run test:municipality-identity
npm run test:pipeline-education-state
npm run test:python
npm run build
```

Use testes focados durante o desenvolvimento. Execute a suíte completa ao
preparar uma entrega ou após mudanças transversais no pipeline.

## Diagnóstico de falhas

- falha antes da sincronização: `public/data` permanece com o conjunto anterior;
- falha na geração ou validação da Educação: nenhum arquivo público educacional
  é criado, alterado ou removido;
- falha durante a promoção da Educação: o journal restaura integralmente o lote
  anterior e o processo retorna código não zero;
- falha na materialização PNE: o staging incompleto não é publicado;
- falha na promoção PNE antes do ponteiro: a release ativa permanece válida;
- falha depois da ativação: `current.json` continua apontando para uma release
  validada; a próxima execução reaplica a limpeza de inativas.
