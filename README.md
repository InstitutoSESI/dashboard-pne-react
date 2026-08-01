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
npm run build
npm run test:unit
npm run test:education
npm run test:app-routing
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

`public/data` é parte do produto e deve continuar versionado. O fluxo principal é:

```powershell
npm run update:data
```

Ele exporta e particiona os dados, atualiza Educação, incorpora o documento
municipal de desigualdade em `details.json`, sincroniza `public/data`, valida os
detalhes e executa o build. Para omitir apenas o build:

```powershell
npm run update:data:skip-build
```

Para validar rapidamente somente o código da aplicação, sem copiar a árvore
versionada de dados para `dist`, execute `npm run check:fast` ou apenas
`npm run build:app`. A publicação continua exigindo `npm run build`.

Para validar um indicador sem publicar dados:

```powershell
npm run verify:indicator -- --cycle pne_2026_2036 --indicator creche --municipio "São Leopoldo"
```

Para regenerar somente `public/data/educacao`, defina `SESI_DB_DIR` para o projeto que fornece `utils_educacao` e execute:

```powershell
npm run update:education-data
```

Credenciais ficam em `data_pipeline/.env`, criado a partir de `data_pipeline/.env.example`. Nunca inclua segredos em `public/data`.

## Estrutura

- `src`: aplicação React, rotas, componentes, features, modelos e estilos.
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
