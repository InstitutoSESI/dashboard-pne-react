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
contrato `municipality-registry-v1`; `config/publications/rs.json` liga a UF à
raiz versionada `public/data` pelo contrato `state-publication-v3`.
`public/data/municipios_index.json` é uma projeção publicada do registro e não
pode ser usado como fonte do universo.

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
seletor de estado dentro de uma publicação: cada hospedagem fixa uma UF no
build. PNE, Educação e Financeiro estão disponíveis no RS e permanecem
explicitamente indisponíveis no produto AL. Nomes físicos de fontes podem
continuar específicos do RS.

Os comandos do pipeline analítico aceitam `--state RS`; o frontend e o
empacotamento usam `PLATFORM_STATE`. `rs` é normalizado para `RS`. O manifesto
de produto resolve seus próprios paths de configuração, registro e dados. Uma
UF sem manifesto falha antes de servir ou copiar dados, sem fallback para RS. A
validação de publicação também recusa
contagem, ordem, código, nome, slug, path ou diretório municipal divergente.
Ausência e zero continuam distintos nos contratos educacionais. A mudança não
executou atualização real nem regenerou os outputs públicos existentes do RS.

### Publicação de identidade de Alagoas

O snapshot oficial da API de Localidades do IBGE está em
`data_pipeline/data/municipality_registry_sources/al/raw`, acompanhado do
manifesto com endpoint, instante de aquisição, codificação HTTP, hashes e
cobertura. A normalização usa `json.loads(..., parse_int=str,
parse_float=str)`: todo token numérico chega como texto e o código IBGE nunca
passa por conversão numérica. O resultado fica em
`config/municipalities/al.json`, junto à configuração estadual ativa em
`config/states/al.json`. O manifesto de produto `config/publications/al.json` usa
esses contratos e publica a raiz isolada `state-publications/al/data`, mantendo
`analyticsStatus=partial` com `enabledProducts=["educacao"]`; PNE e
Financiamento permanecem indisponíveis.

Valide snapshot, hashes, cobertura, hierarquia estadual, slugs e projeção exata
com:

```powershell
npm run test:al-municipality-registry
npm run test:identity-publication
npm run test:state-publication
npm run test:multistate-hosting
```

Esse comando é local e não acessa a rede. Uma atualização da fonte é uma tarefa
`SOURCE_REFRESH`: exige autorização explícita de rede, novo snapshot integral,
manifesto reconciliado e validação antes de substituir o candidato. Não copie o
candidato para `config/states` ou `config/municipalities` isoladamente. Essa
ativação analítica só pode ocorrer junto aos contratos e dados de AL validados
como um lote completo.

Para desenvolvimento e release dos dois produtos:

```powershell
npm run dev:rs
npm run dev:al
npm run build:rs
npm run build:al
```

No Cloudflare Pages, use dois projetos sobre o mesmo repositório. O RS executa
`npm run build:cloudflare:rs`, o AL executa
`npm run build:cloudflare:al`, e ambos publicam `dist`. Os comandos fixam a UF
sem depender de sintaxe de variável de ambiente do shell. Veja
`docs/HOSPEDAGEM_MULTIESTADO.md`. Aquisição, banco e atualização de dados não
fazem parte do build da hospedagem.

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
`educacao/municipios/<IBGE>.json`. Ele preserva `educacao-especial`,
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

# Mede elegibilidade shadow e ainda executa a Educação integralmente
npm run update:education-data:fingerprint-shadow

# Reutiliza somente Educação quando o hit forte for comprovado
npm run update:education-data:incremental

# Pipeline geral com apenas a etapa de Educação incremental
npm run update:data:education-incremental

# Alias histórico do fluxo padrão sem build
npm run update:data:skip-build

# Atualiza, valida e só então executa o build completo
npm run update:data:and-build

# Atualiza Educação, valida e só então executa o build completo
npm run update:education-data:and-build

# Gera o perfil de planejamento sem executar efeitos
npm run update:data -- --state RS --dry-run --profile

# Gera o perfil de uma atualização real (documentado; não é smoke test)
npm run update:data -- --state RS --profile

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

# Valida os 51 cenários shadow e os casos adicionais de skip real
npm run test:pipeline-education-fingerprint

# Validação rápida do código da aplicação
npm run check:fast
```

`--build` e `--skip-build` são mutuamente exclusivos. A segunda opção permanece
aceita somente por compatibilidade e equivale ao padrão sem build.
`--validate-only` nunca constrói a aplicação e não pode ser combinado com
`--build`. Em dry-run, o build aparece no plano apenas quando foi solicitado;
nenhum dry-run cria staging, consulta banco, acessa rede, escreve dados ou
executa Vite.

## Perfil reproduzível

`--profile` é opcional. Sem a flag, a execução mantém o fluxo normal e não cria
diretório, evento, fragmento ou JSON de perfil. `--profile-output <diretório>`
só pode ser usado com `--profile` e aceita apenas um subdiretório dedicado de
`data_pipeline/export/profiles` ou do diretório temporário do sistema; raízes
amplas, `public/data`, `data_pipeline/data` e staging são recusados.

Perfil de planejamento, seguro para inspeção sem efeitos:

```powershell
npm run update:data -- --state RS --dry-run --profile
```

Perfil real, apenas para uma operação de dados autorizada:

```powershell
npm run update:data -- --state RS --profile
```

O diretório padrão é `data_pipeline/export/profiles/<run-id>/` e contém:

- `profile.json`, schema `pipeline-profile-v1`, com sessão, processos e eventos;
- `summary.json`, schema `pipeline-profile-summary-v1`, com agregados por
  categoria e counters totais;
- `fragments/<child-run-id>.json`, arquivos intermediários atômicos dos
  subprocessos, consolidados pelo processo pai.

As categorias distinguem orquestração, subprocesso, consulta, cálculo,
serialização, leitura, escrita, validação, promoção, cache e build. Queries usam
identificadores estáveis e registram duração, linhas e colunas sem `COUNT`
adicional nem exposição dos parâmetros. Arquivos distinguem bytes renderizados,
lidos, comparados, escritos e promovidos. Educação e loops municipais publicam
agregados, não um evento por município.

A correlação usa variáveis de ambiente próprias do perfil, não o ambiente
completo. Credenciais, URLs autenticadas, conteúdo analítico e paths pessoais
são omitidos ou sanitizados. Os relatórios são determinísticos para o mesmo
conteúdo, usam JSON UTF-8 finito e ficam ignorados pelo Git. Uma falha de
subprocesso permanece visível com status `error`; falha ao gravar o relatório é
informada ao final e não pode causar publicação analítica parcial.

O perfil não acelera o pipeline e não equivale a execução incremental. Seus
dados orientarão as Etapas 5D2–5D5. O build continua separado: só é medido quando
`--build` é solicitado explicitamente e continua depois da validação.

Validação dedicada:

```powershell
npm run test:pipeline-profiling
```

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
npm run build:rs
npm run build:al
```

Esse comando desativa a cópia genérica do Vite, valida o perfil selecionado,
copia os ativos compartilhados sem `public/data` e materializa em `dist/data`
somente a raiz declarada em `config/publications/<uf>.json`. `npm run preview`
não atualiza dados nem constrói o pacote: ele serve o `dist` existente. Para
validar uma release localmente, gere antes um build completo atual. O deploy
continua responsável por executar `npm run build` quando necessário; os paths
públicos sob `/data`, base, assets e hospedagem permanecem compatíveis.

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
- identidade estadual: `data_pipeline/.staging/identity-publication`;
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

### Fingerprint shadow 5D2A e skip opt-in 5D2B

O comando operacional explícito é:

```powershell
npm run update:education-data:fingerprint-shadow
npm run update:education-data:incremental
npm run update:data:education-incremental
```

Shadow propaga `--education-fingerprint-shadow` ao orquestrador e
`--fingerprint-shadow` ao exportador. Incremental propaga
`--education-fingerprint-skip` e `--fingerprint-skip`. Sem essas flags, nenhum
digest novo é calculado e nenhum task state é lido ou escrito. `--help` não cria
diretório; em `--dry-run`, a CLI apenas informa o modo, sem banco ou digest
tabular. Lotes parciais continuam recusados e `AL` falha antes do primeiro
efeito. `--no-promote` permanece disponível para shadow, mas é incompatível com
skip porque não representa publicação final reutilizável.

O contrato usa `taskId=education.core.rs`, estado `RS`, schema
`education-task-fingerprint-v1`, algoritmo de fontes
`education-source-digest-v1` e algoritmo de input
`education-input-fingerprint-v1`. Os source digests cobrem os 19 DataFrames
reais: a tabela municipal, 15 views PostgreSQL e três tabelas PostgreSQL
alimentadas por snapshots locais de Educação/População Indígena. Transformações
em memória, como os contratos municipais de infraestrutura escolar e os blocos
de apresentação, são cobertas pela allowlist de código e contrato. O
`utils_educacao` efetivamente importado é resolvido antes do digest; seu arquivo
`.py` participa por SHA-256 e versão explícita quando disponível. Path pessoal,
conteúdo do módulo, `SESI_DB_DIR`, credenciais e URL não são serializados.
Ausência, origem não verificável ou import ambíguo força execução integral.

O digest tabular trata as linhas como multiconjunto: reordená-las não muda a
identidade, mas valor, null, coluna, ordem contratual de colunas, dtype ou
multiplicidade mudam. Ausências seguem a política única
`pandas-isna-single-null-v1`; booleano não equivale a inteiro e código IBGE
textual não equivale a número. `DATA_EXPORTACAO`, `data_carga`, `updated_at`,
`generated_at`, run IDs e paths de staging são operacionais e não entram no
`inputFingerprint`. Floats permanecem analíticos e participantes, com cânone
`round-float-to-12-decimal-places-v1`: a regra remove somente ruído de
representação abaixo de 12 casas decimais observado em agregações PostgreSQL,
seis casas além da maior precisão publicada; mudança acima desse limiar
invalida o digest.

O task state local fica em
`data_pipeline/export/task-state/RS/education-core.json`. A escrita usa arquivo
temporário, `fsync` e substituição atômica. O arquivo não é versionado, não é
compartilhado entre estados e nunca é usado como fonte analítica. Ele contém
somente digests, metadados de schema/versão/contagem e o manifesto forte dos
499 outputs administrados. Não contém credenciais, ambiente completo, URL de
conexão, path pessoal nem valores municipais analíticos.

A decisão exige manifesto anterior válido, mesmo `inputFingerprint` e os 499
outputs atuais com mesmo tamanho/SHA-256/conjunto. `wouldSkip=false` registra
motivos como `first_run`, `manifest_missing`, `manifest_invalid`,
`input_changed`, `contract_changed`, `output_missing`, `output_changed`,
`output_extra`, `state_mismatch` ou `algorithm_changed`; `eligible` é o único
hit. Em qualquer caso, shadow continua consultando, materializando, validando e
promovendo. No modo incremental, a decisão ocorre antes da criação do staging:
um hit retorna `reused=true`, não chama a camada transacional e preserva bytes e
mtimes dos 499 outputs e do task state. Um miss executa integralmente staging,
materialização, validação e promoção/no-op. O state novo só é gravado depois da
publicação confirmada; falha nunca substitui o anterior.

Quando `--profile` também está ativo, os eventos agregados
`education.fingerprint.sources`, `.contracts`, `.input`, `.output_integrity`,
`.shadow_decision`, `.skip_decision` e `.state_write` medem tempo, linhas,
colunas, bytes e a decisão, sem eventos por linha ou município. Hit real registra
`fingerprintHit=1`, `wouldSkip=1`, `actuallySkipped=1`, `stagingCreated=0`, zero
municípios, arquivos e bytes renderizados. Shadow nunca registra
`actuallySkipped=1`; sem flags não existe evento de fingerprint. Profiling
responde quanto o fluxo custou; fingerprint responde se entradas e outputs são
idênticos.

Mesmo com Educação reutilizada, o orquestrador continua desigualdade, sync
quando pertencente ao pipeline geral, `validate:details` e build apenas quando
explicitamente solicitado. Falha posterior continua sendo erro. O resumo usa
`reused=true` para hit e `publicationNoop=true` para uma publicação integral que
não precisou trocar bytes; os resultados não são equivalentes.

Validação dedicada:

```powershell
npm run test:pipeline-education-fingerprint
```

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
