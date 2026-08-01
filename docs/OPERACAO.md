# Pipeline e operação

## Preparação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline\requirements.txt
npm ci
```

As fontes reproduzíveis e os insumos de regeneração permanecem em
`data_pipeline/data`. Os artefatos públicos são gerados pelo pipeline e não
devem ser editados manualmente.

## Atualização completa

```powershell
npm run update:data
```

O comando executa, nesta ordem:

1. exportação dos agregados;
2. particionamento em `data_pipeline/export/static_partitioned`;
3. atualização dos documentos de Educação;
4. materialização do recorte municipal de desigualdade no staging;
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
python data_pipeline/scripts/update_static_data.py --dry-run --profile

# Validação rápida do código da aplicação
npm run check:fast
```

## Artefato municipal de desigualdade

`public/data/municipios/<IBGE>/diagnostico.json` é mantido como URL estável,
mas contém somente o contrato `municipal-inequality-v1`, que é o único conteúdo
desse arquivo consumido pela aplicação atual. A geração é feita por:

```powershell
python data_pipeline/scripts/materialize_municipal_inequality.py `
  --output-root data_pipeline/export/static_partitioned/municipios
```

O materializador lê os documentos educacionais atuais, aplica supressão de
células pequenas e grava apenas quando o conteúdo mudou.

## Publicação do diagnóstico PNE

A aplicação resolve exclusivamente:

1. `public/data/pne2026-diagnostic-v3/current.json`;
2. o manifesto apontado em `releases/<hash>/manifest.json`;
3. `releases/<hash>/municipios/<IBGE>.json`.

O nome do diretório público é preservado por estabilidade de URL. Dentro dele
deve existir somente a release apontada por `current.json`.

Geração e validação:

```powershell
python data_pipeline/scripts/materialize_pne2026_public_diagnostic_v3.py `
  --output-dir data_pipeline/.staging/pne-diagnostic-current

python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir data_pipeline/.staging/pne-diagnostic-current `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

Publicação:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir data_pipeline/.staging/pne-diagnostic-current `
  --destination-dir public/data/pne2026-diagnostic-v3
```

A ativação de `current.json` é atômica. Depois dela, o promotor apaga releases
inativas automaticamente. Para apenas conferir ou aplicar essa invariável:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
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
npm run test:unit
npm run test:education
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
