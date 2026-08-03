# Painel PNE

Aplicação web estática para leitura municipal de indicadores educacionais, metas dos ciclos do PNE, diagnóstico e financiamento da educação. O frontend usa React, TypeScript e Vite; os JSONs servidos em produção ficam em `public/data` e são mantidos pelo pipeline Python do repositório.

## Ambiente local

Requisitos: Node.js compatível com Vite 8, npm, Python 3.11 a 3.13 e
[`uv`](https://docs.astral.sh/uv/). No Windows, instale o executável oficial e
prepare o ambiente reproduzível do pipeline:

```powershell
winget install --id=astral-sh.uv -e
uv --version
npm ci
npm run python:sync
npm run python:lock:check
npm run test:python
npm run dev
```

`data_pipeline/pyproject.toml` declara somente as dependências diretas;
`data_pipeline/uv.lock` fixa toda a resolução. Não instale pacotes avulsos para
contornar imports: qualquer atualização deve ser uma mudança própria do
contrato e do lock. O antigo `requirements.txt` foi aposentado. Quando uma
integração exigir esse formato, exporte-o sob demanda para o diretório ignorado
`exports`, sem versioná-lo:

```powershell
uv export --project data_pipeline --frozen --format requirements.txt `
  --output-file exports/python-requirements.txt
```

O servidor local usa `http://127.0.0.1:5173` por padrão. O frontend não precisa de credenciais para consumir os dados já versionados.

## Comandos principais

```powershell
npm run typecheck
npm run lint
npm run check:fast
npm run python:lock:check
npm run check:python-deps
npm run test:pipeline-state-config
npm run test:pipeline-profiling
npm run build
npm run test:unit
npm run test:education
npm run test:app-routing
npm run test:municipality-identity
npm run test:data-sources
npm run test:ui-architecture
npm run test:python
npm run validate:details
npm run check:hygiene
```

Os testes E2E esperam uma aplicação ativa. Execute `npm run dev -- --host 127.0.0.1 --port 5173` em um terminal e `npm run test:e2e` em outro. Defina `BASE_URL` para testar outro endereço.

`npm run test:python` usa o `pytest` como coletor único para toda a suíte Python
e o executa no ambiente congelado pelo uv.

## Dados estáticos

`config/states/rs.json` contém os metadados estaduais e
`config/municipalities/rs.json` contém o registro municipal canônico do
pipeline. Nesta etapa a plataforma continua operando exclusivamente com o Rio
Grande do Sul: o código IBGE é a identidade, o nome é apresentação e
compatibilidade temporária de agregados internos, e o slug permanece reservado
às URLs. `public/data/municipios_index.json` conserva schema e caminho, mas é
uma projeção publicada do registro, nunca a entrada do universo no pipeline.

Na Educação, a exportação geral, a Visão Geral Municipal, a Educação Superior e
a Educação Especial recebem `--state` e usam essa configuração com o registro
municipal. Somente `RS` está configurado; `AL` falha antes de banco, fonte ou
escrita. Os 182 slugs históricos que divergem do slug canônico são projetados
pela compatibilidade versionada em
`config/compatibility/education-municipality-routes/rs.json`; ela não define
identidade e a geração não lê o índice público anterior. Essa parametrização não
regenerou `public/data`: schemas, paths e dados publicados do RS permanecem os
mesmos.

`public/data` é parte do produto e deve continuar versionado. Desenvolvimento
visual e validação leve da aplicação usam somente o build app-only:

```powershell
npm run dev
npm run check:fast
npm run build:app
```

`build:app` não copia `public/data`; `check:fast` continua executando typecheck,
lint e esse build leve. A atualização e validação de dados não constroem mais a
aplicação. Para atualizar somente Educação, configure `SESI_DB_DIR` para o
projeto que fornece `utils_educacao`:

```powershell
npm run update:data
npm run update:education-data
npm run update:education-data:fingerprint-shadow
npm run update:education-data:incremental
npm run update:data:education-incremental
```

O primeiro comando exporta, particiona, atualiza Educação, incorpora o documento
municipal de desigualdade em `details.json`, sincroniza `public/data` e valida os
detalhes. O segundo atualiza somente Educação, materializa a desigualdade
derivada e valida. `update:data:skip-build` permanece aceito como alias histórico
do fluxo padrão sem build.

`npm run update:education-data:fingerprint-shadow` executa a mesma Educação
integral e apenas reporta se a tarefa `education.core.rs` poderia ser pulada;
nenhum skip é ativado. `update:education-data:incremental` torna o skip opt-in
somente no fluxo `education-only`; `update:data:education-incremental` mantém os
demais domínios integrais e torna incremental apenas a etapa educacional.
Qualquer incerteza executa a publicação transacional completa. Em hit, o
orquestrador ainda executa desigualdade, sync quando pertencente ao fluxo,
validação e build quando explicitamente solicitado.

O perfil de planejamento é opt-in e não executa subprocessos, banco, staging,
sincronização ou build:

```powershell
npm run update:data -- --state RS --dry-run --profile
```

Uma execução real pode ser perfilada com `npm run update:data -- --state RS
--profile`. Ela gera `profile.json` e `summary.json` em
`data_pipeline/export/profiles/<run-id>/`, diretório ignorado pelo Git. O perfil
mede tanto o fluxo integral quanto o hit incremental. Neste último, registra
`actuallySkipped=1`, zero staging, municípios, arquivos e bytes renderizados.
O build só aparece no perfil quando `--build` é solicitado.

O build completo continua explícito e inclui toda a árvore `public`, portanto
também `public/data`:

```powershell
npm run build
npm run update:data:and-build
npm run update:education-data:and-build
```

Os dois comandos `and-build` executam o build completo somente depois de todas
as respectivas etapas de dados e da validação passarem. Dados promovidos e o
conteúdo de `dist` são responsabilidades separadas. `npm run preview` apenas
serve um `dist` já existente; execute antes `npm run build` quando quiser validar
o pacote completo de release. O deploy continua responsável por executar o
build completo quando necessário. Este desacoplamento não alterou fórmula,
schema, metodologia nem dado publicado.

Para validar um indicador sem publicar dados:

```powershell
npm run verify:indicator -- --cycle pne_2026_2036 --indicator creche --municipio "São Leopoldo"
```

Credenciais ficam em `data_pipeline/.env`, criado a partir de `data_pipeline/.env.example`. Nunca inclua segredos em `public/data`.

## Estrutura

- `src`: aplicação React, rotas, componentes, features, modelos e estilos.
- `config/states`: configurações estaduais versionadas; somente o RS está ativo.
- `config/municipalities`: identidade municipal canônica versionada por estado.
- `public/data`: dados públicos servidos diretamente ao navegador.
- `data_pipeline/src`: cálculo, acesso às fontes e contratos de dados.
- `data_pipeline/src/pne`: regras puras dos ciclos do PNE, sem framework web.
- `data_pipeline/scripts`: atualização, materialização e validação permanentes.
- `data_pipeline/data`: snapshots e contratos-fonte necessários para regeneração.
- `data_pipeline/tests`: testes de domínio e do pipeline.
- `scripts/checks`: testes e verificações permanentes do frontend e do repositório.

Saídas de build, caches, relatórios, screenshots, logs e arquivos de inspeção local não são versionados.

## Documentação canônica

- [Produto](PRODUCT.md)
- [Arquitetura](docs/ARQUITETURA.md)
- [Design](docs/DESIGN.md)
- [Pipeline e operação](docs/OPERACAO.md)
- [Metodologia](docs/METODOLOGIA.md)

## Publicação

Execute `npm run build` e publique `dist` em hospedagem estática com fallback para `index.html`. A aplicação usa navegação por hash e carrega os JSONs por caminhos absolutos sob `/data`.
