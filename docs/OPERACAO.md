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

Internamente, o código IBGE identifica o município; o nome é texto de
apresentação e compatibilidade temporária dos agregados por nome, e o slug é o
valor canônico de URL. O particionamento resolve nomes de forma única contra o
registro e nunca deriva código ou slug do nome. Fundeb e PNATE fornecem dados,
mas não identidade. A persistência do navegador usa
`dashboard-context-v2`, com estado e código municipal. Valores antigos baseados
em nome são migrados uma única vez quando há correspondência inequívoca. Não há
seletor de estado, configuração de Alagoas nem caminhos públicos de dados por
estado; fontes e fórmulas multiestado dependem da Etapa 4B2, e o suporte de
produto e publicação por estado depende da Etapa 4C.

Os comandos centrais aceitam `--state RS`; `rs` é normalizado para `RS`. Um
estado sem `config/states/<uf>.json`, como `AL` nesta etapa, falha antes de
exportação, particionamento, sincronização ou escrita, sem fallback para RS.

## Atualização completa

```powershell
npm run update:data
```

O comando executa, nesta ordem:

1. exportação dos agregados;
2. particionamento em `data_pipeline/export/static_partitioned`;
3. atualização dos documentos de Educação;
4. incorporação do recorte municipal de desigualdade em `details.json` no staging;
5. sincronização atômica do conjunto estático administrado;
6. validação dos detalhes;
7. build da aplicação.

Somente arquivos alterados são copiados. Educação, Financeiro, QSE e a
publicação do diagnóstico PNE têm autoridades próprias e não são removidos pela
sincronização estática.

Comandos úteis:

```powershell
# Atualiza os dados sem recompilar a aplicação
npm run update:data:skip-build

# Atualiza somente Educação e o recorte de desigualdade derivado dela
npm run update:education-data

# Mostra as etapas e tempos sem executar
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --dry-run --profile

# Explicita o estado ativo sem alterar o caminho público atual
uv run --project data_pipeline --frozen python data_pipeline/scripts/update_static_data.py --state RS --dry-run

# Validação rápida do código da aplicação
npm run check:fast
```

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
- staging temporário do diagnóstico PNE: `data_pipeline/.staging`.

Esses diretórios não são fontes analíticas. Podem ser regenerados pelos
respectivos comandos e não devem ser usados como entrada permanente.

## Validação para entrega

```powershell
npm run check:fast
npm run python:lock:check
npm run check:python-deps
npm run test:unit
npm run test:education
npm run test:municipality-identity
npm run test:python
npm run build
```

Use testes focados durante o desenvolvimento. Execute a suíte completa ao
preparar uma entrega ou após mudanças transversais no pipeline.

## Diagnóstico de falhas

- falha antes da sincronização: `public/data` permanece com o conjunto anterior;
- falha na materialização PNE: o staging incompleto não é publicado;
- falha na promoção PNE antes do ponteiro: a release ativa permanece válida;
- falha depois da ativação: `current.json` continua apontando para uma release
  validada; a próxima execução reaplica a limpeza de inativas.
