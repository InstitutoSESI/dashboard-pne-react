# Pipeline e operação

## Preparação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r data_pipeline\requirements.txt
Copy-Item data_pipeline\.env.example data_pipeline\.env
```

Preencha apenas `data_pipeline/.env`, ignorado pelo Git. O acesso PostgreSQL/Supabase fica em `data_pipeline/src/data/repository.py`. Caminhos externos compartilhados, inclusive `SESI_DB_DIR`, ficam centralizados em `data_pipeline/src/config.py`.

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
- `generate_municipal_finance.py`: atualiza os contratos financeiros canônicos por código IBGE.
- `generate_qse_annual.py`: atualiza as séries anuais da QSE.
- `materialize_municipal_education_overview.py`: materializa a visão geral educacional por código IBGE.
- `materialize_pne2026_public_diagnostic_v2.py`: materializa o diagnóstico público.
- `refresh_municipal_decision_summary.py`: atualiza a síntese decisória.
- `sync_eja_integrada_from_sinopse.py` e `sync_ept_nivel_medio_from_sinopse.py`: importam edições oficiais da Sinopse.
- `npm run generate:diagnostic-catalog`: recompõe o catálogo do diagnóstico.

Downloads intermediários ficam em `data_pipeline/cache`; saídas intermediárias, em `data_pipeline/export`. Ambos são ignorados.

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
npm run test:ui-architecture
npm run test:python
npm run validate:details
npm run check:hygiene
```

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
