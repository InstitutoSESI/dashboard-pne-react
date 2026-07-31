# Pipeline e operação

## Preparação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline\requirements.txt
Copy-Item data_pipeline\.env.example data_pipeline\.env
```

Preencha apenas `data_pipeline/.env`, ignorado pelo Git. O acesso PostgreSQL/Supabase fica em `data_pipeline/src/data/repository.py`. Caminhos externos compartilhados ficam centralizados em `data_pipeline/src/config.py`: `SESI_DB_DIR` localiza os snapshots de origem e `POPULATION_PROJECTION_SOURCE_PATH` pode apontar para o workbook oficial de projeção populacional quando ele não estiver sob `SESI_DB_DIR`.

## Atualização principal

`npm run update:data` executa:

1. `export_static_data.py --include-derived`;
2. `partition_static_data.py`;
3. sincronização para `public/data`;
4. `refresh_municipal_inequality_pilot.py`;
5. `export_education_indicators.py`;
6. `validate_static_details.py`;
7. `npm run build`.

O comando bloqueia atualização com alterações fora de `public/data`. Use `--dry-run`, `--validate-only`, `--skip-export`, `--skip-partition`, `--skip-education`, `--skip-build` e `--profile` conforme a ajuda. `--education-only` regenera somente Educação, valida e, salvo `--skip-build`, recompila.

## Fluxos especializados

- `npm run update:education-data`: chama o orquestrador com `--education-only`.
- `npm run update:indigenous-coverage`: valida os metadados oficiais do SIDRA 9970, baixa e armazena a resposta bruta do Censo Demográfico 2022, materializa as idades simples e faixas populacionais no banco e regenera os contratos municipais de Educação. É uma atualização explícita; o build não consulta o IBGE.
- `generate_municipal_finance.py`: atualiza os contratos financeiros canônicos por código IBGE.
- `generate_qse_annual.py`: atualiza as séries anuais da QSE.
- `materialize_municipal_education_overview.py`: materializa a visão geral educacional por código IBGE.
- `sync_censo_escolar_microdata.py`: audita os microdados completos já disponíveis ou, com `--download`, adquire e promove fontes oficiais do Censo Escolar com staging e SHA-256.
- `build_censo_escolar_panel.py`: gera o painel municipal compacto em staging e somente promove painel/manifesto e relatórios após as validações. O painel completo usa `data_pipeline/data/censo_escolar_panel`; relatórios ficam em `data_pipeline/export/censo_escolar_panel`. A execução oficial exige 496 municípios em 2007--2012, 497 em 2013--2025 e reconciliação estrita de 497 x 12 x 7. Execuções parciais exigem `--output-dir` e recebem nome com o intervalo; `--skip-reconciliation` substitui os relatórios anteriores por um marcador explícito de reconciliação não executada.
- `materialize_special_education.py`: gera deterministicamente e promove de forma atômica o contrato isolado `special-education-v1`.
- `validate_special_education.py`: valida fonte, 497 contratos, recortes, estados, ausência de extremos e reconciliação da Educação Especial de 2025.
- `materialize_pne2026_public_diagnostic_v2.py`: produtor legado preservado somente para auditoria histórica e rollback frio de builds anteriores; não integra o fluxo V3 e não deve receber novos indicadores ou correções.
- `sync_pne_goal_11b_census.py`: baixa e valida os metadados e componentes
  municipais da tabela IBGE/SIDRA 10061, combina o snapshot local de 15–17 e
  grava a fonte versionada de 2022. Use `--apply`; sem essa opção, o comando é
  somente auditoria.
- `materialize_pne2026_public_diagnostic_v3.py`: gera staging determinístico
  para os 497 municípios; a geração não altera `public/data`.
- `sync_pne_munic_2021.py`, `sync_pne_capes_2024.py` e
  `sync_pne_quality_offer.py`: incorporam, de forma isolada, os snapshots
  oficiais da macro-rodada MUNIC/CAPES/CPC/Enade. Aceitam arquivos locais para
  reexecução offline; o build e o frontend consomem apenas os snapshots
  normalizados.
- `audit_pne_director_selection.py` e `audit_pne_inec_connectivity.py`:
  registram as barreiras das fontes bloqueadas sem criar resultado municipal.
- `promote_pne2026_public_diagnostic_v3.py`: valida e publica releases V3 imutáveis, ativa `current.json` atomicamente e permite rollback de dados por `--activate-release <hash>` sem copiar payloads. Não cria manifesto raiz nem consulta V2.
- `refresh_municipal_decision_summary.py`: atualiza a síntese decisória.
- `sync_eja_integrada_from_sinopse.py` e `sync_ept_nivel_medio_from_sinopse.py`: importam edições oficiais da Sinopse.
- `npm run generate:pne-contract-artifacts`: recompõe o catálogo do Diagnóstico, a projeção PNE de `public/data/indicadores.json` e a documentação gerada de metas, prazos, fórmulas e fontes.

Downloads intermediários ficam em `data_pipeline/cache`; saídas intermediárias, em `data_pipeline/export`. Ambos são ignorados.

## Operação do Diagnóstico PNE V3

O build atual usa exclusivamente `public/data/pne2026-diagnostic-v3/current.json`
e o release imutável apontado. Não existe seleção por variável VITE, modo
`dual` ou fallback V2. Erros de ponteiro, manifesto, hashes ou município
interrompem a carga sem dados parciais.

Versão, hash, cardinalidades, metas, prazos, fórmulas e fontes do contrato ativo
ficam na [documentação gerada do PNE](generated/PNE_2026_CONTRACT.md), validada
por `npm run check:pne-contract`. A política editorial ativa é a 1.7.0
(`c330fb98c727dbb461b809a5f178f92ac73661ee3fe4e9c73cfb9b38ea9f1d3b`).
O schema municipal é `pne2026-public-diagnostic-v4`. As cardinalidades e os
modos de relação não são duplicados neste documento: o gate confere esses dados
diretamente no contrato e na documentação gerada. Cada relação materializada
aparece como `available`, `unavailable`, `not_applicable` ou `suppressed`.

No ciclo, somente relações `progress` ou `tracking` com estado `available` e
referência resolvida geram cards. Relações comparáveis em estado negativo
entram em “Sem comparação no período”; relações complementares nunca são
contadas como indicadores comparáveis. A política editorial define tema e
ordem dos menus, enquanto o contrato define identidade, modo e referência.

O ponteiro `current.json` deve ser servido com revalidação ou `no-cache`. O
loader sempre o solicita com `cache: no-store`; manifesto e payloads usam
caminhos imutáveis por `releaseId`, e o cache em memória municipal usa a chave
`releaseId + IBGE`.
As fórmulas de expansão usam base fixa em 2025 e só publicam valor com
observação posterior.

Macro-rodada reproduzível de fontes:

```powershell
python data_pipeline/scripts/sync_pne_munic_2021.py `
  --source-2021 <Base_MUNIC_2021.xlsx> `
  --source-2024 <Base_MUNIC_2024.xlsx>

python data_pipeline/scripts/sync_pne_capes_2024.py `
  --programs-file <programas_2024.csv> `
  --programs-metadata-file <metadados_programas.pdf> `
  --students-file <discentes_2024.csv> `
  --students-metadata-file <metadados_discentes.pdf>

python data_pipeline/scripts/sync_pne_quality_offer.py `
  --cpc-file <CPC_2023.xlsx> `
  --enade-file <Enade_Licenciaturas_2025.xlsx> `
  --igc-file <IGC_2023.xlsx>

python data_pipeline/scripts/materialize_pne2026_public_diagnostic_v3.py `
  --output-dir <staging-fora-de-public-data>
```

Consulte `docs/PNE_MACRO_RODADA_FONTES_2026.md` para fórmulas, hashes,
cobertura, bloqueios e auditoria da promoção.

Rodada reproduzível da Meta 11.b:

```powershell
python data_pipeline/scripts/sync_pne_goal_11b_census.py `
  --apply `
  --reference-date 2026-07-28

python data_pipeline/scripts/materialize_pne2026_public_diagnostic_v3.py `
  --output-dir C:\tmp\pne-diagnostic-v3-staging-11b-full-a

python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir C:\tmp\pne-diagnostic-v3-staging-11b-full-a `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

Rollback entre releases V3:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --activate-release <hash> `
  --destination-dir public/data/pne2026-diagnostic-v3
```

Rollback da aplicação exige republicar um build anterior. Os arquivos V2
permanecem temporariamente apenas para essa janela operacional e auditoria
histórica. Consulte `docs/PNE_DIAGNOSTIC_V3_PROMOTION.md` para os critérios de
remoção física. `--activate-release` isolado só é válido entre releases com o
mesmo contrato; voltar para a release 1.2.0 exige republicação coordenada do
build 1.2.0 correspondente.

## Validação

```powershell
npm ci
npm run typecheck
npm run lint
npm run build
npm run test:unit
npm run test:education
npm run test:app-routing
npm run test:data-sources
npm run check:pne-contract
npm run test:ui-architecture
npm run test:python
npm run validate:details
npm run check:hygiene
```

### Rodada consolidada de indicadores municipais do PNE

Os procedimentos, fontes, variáveis de ambiente, gates metodológicos e comandos de promoção das relações 3.a, 11.d, 14.a, 14.b, 14.d e 15.b estão documentados em `docs/PNE_EXPANSAO_INDICADORES_MUNICIPAIS_2026.md`.

Com o servidor local ativo, execute `npm run test:e2e`.

## Matriz de jornadas permanentes

| Jornada atual | Proteção permanente |
| --- | --- |
| selecionar e trocar município | `test:e2e` em desktop e celular |
| navegação por hash e contexto da URL | `test:app-routing` e `test:e2e` |
| lazy loading dos dois ciclos do PNE | `test:e2e` e `test:pne-cycle` |
| Educação e visão geral municipal | `test:education`, testes Python do contrato e `test:e2e` |
| Financeiro, Fundeb, PNATE, VAAR e QSE | `test:municipal-finance`, testes de fontes e `test:e2e` |
| Diagnóstico municipal | `test:diagnostic`, testes de contrato e `test:e2e` |
| menu, foco, hover e overflow em 390×844 | `test:e2e` |
| vazio, carregando e erro | roteamento e testes de componentes |
| impressão aplicável | componentes e CSS de impressão preservados; cobertura Chromium serve apenas como auditoria |

## Política de arquivos

Versione código, configurações, testes permanentes, os seis documentos canônicos, `public/data` e fontes não regeneráveis de `data_pipeline/data`. Não versione caches, logs, screenshots, relatórios, planilhas geradas, resultados Playwright ou builds.
