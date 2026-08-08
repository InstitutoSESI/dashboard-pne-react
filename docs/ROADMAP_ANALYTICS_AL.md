# Roadmap técnico — Analytics de Alagoas

Gerado em 2026-08-07 a partir de auditoria completa do pipeline. Objetivo: levar a
publicação de AL de `identity-only` até `complete`, com o mesmo esqueleto de
visualizações do RS.

## 0. Descoberta estrutural

O pipeline analítico **não lê os microdados nacionais do SESI/DB diretamente.
Ele lê um banco Postgres local chamado `sesi`**, populado pelo projeto externo
`C:\Users\rnbirck\PROJETOS\SESI\DB`, cujos ETLs são todos fixados em RS.

- `data_pipeline/src/data/repository.py:27` — `DEFAULT_DATA_BACKEND = "postgres_local"`
- `data_pipeline/src/data/repository.py:45-285` — `DATASET_SPECS` mapeia ~40 datasets para tabelas do banco
- `data_pipeline/scripts/export_education_indicators.py:838-842` — usa `get_engine("sesi")` do projeto SESI/DB
- Os 58 arquivos em `data_pipeline/queries/*.sql` **não têm filtro de UF** — o recorte
  do RS é implícito no conteúdo do banco (ex.: `pop_0_3.sql` lê `populacao_idade_rs`).

ETLs do SESI/DB com hardcode de RS (troca de constante + recarga, fontes já são nacionais em disco):

| Arquivo | Linha | Hardcode |
|---|---|---|
| `SESI\DB\censo_escolar.py` | 362 | `.query("SG_UF == 'RS'")` |
| `SESI\DB\municipios.py` | 91, 138 | `municipios["sigla_uf"].eq("RS")` |
| `SESI\DB\adequacao_docente.py` | 20 | `UF_ALVO = "RS"` |
| `SESI\DB\rendimento_escolar.py` | 24 | `UF_ALVO = "RS"` |
| `SESI\DB\vaar.py` | 31, 609 | `UF_ALVO = "RS"`, `WHERE sigla_uf = 'RS'` |
| `SESI\DB\saeb.py` | 61 | `df.query("SG_UF == 'RS'")` |
| `SESI\DB\saeb_proficiencia.py` | 19, 290 | `UF_ALVO = "Rio Grande do Sul"` |
| `SESI\DB\sinopse_estatistica_censo.py` | 17 | `UF_ALVO = "Rio Grande do Sul"` |
| `SESI\DB\alunos_turma.py` | 163 | `df_raw[df_raw["SG_UF"].eq("RS")]` |
| `SESI\DB\distorcao_idade_serie.py` | 29 | `.query("SG_UF == 'RS' & ...")` |
| `SESI\DB\alfabetizacao.py` | 51, 72 | `municipio_csv["SG_UF"] == "RS"` |
| `SESI\DB\censo_populacao.py` | 247, 255 | `WHERE sigla_uf = 'RS'` |
| `SESI\DB\financeiro_educacao.py` | 66 | `WHERE sigla_uf = 'RS'` |
| `SESI\DB\pnate.py` | 323, 357 | `df["uf"].eq("RS")`, prefixo `43` |

## 1. Quadro-resumo de aquisição por produto

| Produto | Fonte real | Situação local | Ação |
|---|---|---|---|
| Educação básica | INEP Censo/SAEB/TDI/AFD via banco `sesi` | banco RS-only; microdados nacionais em disco | recarregar ETL SESI/DB com UF=AL |
| Educação superior | Sinopse Superior 2018–2024 XLSX | nacional em disco | só filtrar |
| Educação especial | Censo Escolar via banco | banco RS-only | recarregar ETL |
| Educação indígena (matrícula) | Sinopse Estatística Censo | nacional em disco | só filtrar |
| Educação indígena (população) | SIDRA 9970 | snapshot RS-only | `N3[43]`→`N3[27]` |
| PNE 2014/2026 (núcleo) | banco `sesi` | RS-only | recarregar ETL |
| Meta 11.b | SIDRA 10061 | snapshot RS-only | `N3[27]` |
| Meta 14 | SIDRA 10058/10059/10061 | snapshot RS-only | `N3[27]` |
| Meta 15.b | Sinopse Superior tab. 2.2 | nacional em disco | filtrar + recalcular `EXPECTED_ROWS_WITH_IES` |
| Meta 11.d (EJA) | Sinopse | snapshot RS-only | filtrar |
| Alfabetização | INEP `alfabetizacao_*.xlsx` | nacional em disco | só filtrar |
| Projeções população | `projecao_pop.xlsx` | nacional em disco | só filtrar |
| FUNDEB/VAAT/VAAR | CSVs FNDE por ente federado | nacional | regex `^AL`, `27\d{5}` |
| SIOPE | OData FNDE `Sig_UF` | API | `@Sig_UF='AL'` |
| RREO | FTP FNDE | nacional | filtrar |
| QSE | PDFs FNDE por ente federado | nacional, já em disco | regex `^AL`, `27\d{5}` |
| MUNIC 2021 | IBGE MUNIC | normalizado RS-only | refiltrar do nacional |
| CAPES 2024 | Sucupira | nacional bruto em disco | filtrar |
| Seleção de diretores | — | `municipalityCount: 0` | indisponível já no RS |
| Conectividade INEC | — | `municipalityCount: 0` | indisponível já no RS |

Hardcodes principais no `data_pipeline` (verificados, arquivo:linha):

- `src/education_task_fingerprint.py:43-44` — 497/499 fixos (flag `enforce_rs_contract` já existe)
- `src/education_transactional_publication.py:971-977` — trava raiz em `public/data/educacao`
- `src/education_municipality_routes.py:161-176` — exige `config/compatibility/education-municipality-routes/<uf>.json` (só existe `rs.json`)
- `src/pne_state_reference.py:17-25` — `STATE_CODE`, `STATE_NAME`, 497, `METHODOLOGY_VERSION = "pne2026-rs-reference-v3"`, cortes 2015–2025
- `src/pne_2014_state_reference.py:543`, `scripts/export_static_data.py:938-1014` (sem `--state`, fallback RS)
- `src/pne_goal_11b_census.py:14-19,56-66`, `src/pne_goal_14_census.py:14-15,93-100,197,213`, `src/pne_goal_15b.py:16-25,109`, `src/pne_goal_11d.py:16,79,125,141,231`
- `src/child_literacy.py:17,19,86,211`, `src/pne_2014_child_literacy.py:165,201`
- `src/indigenous_population_sidra.py:26,33,70-79`, `scripts/sync_indigenous_education_from_sinopse.py:35,37`
- `src/municipal_finance.py:26,241-248,385-519,551,572,1197`
- `src/municipal_finance_constitutional.py:38,41,48-56,126,142,158,181,926`
- `src/municipal_finance_p5b2.py:95`, `src/qse_annual.py:25,93,97-106,190,296,418`
- `src/planning_scenarios.py:34-36`, `src/pne_2026_projections.py:711,803,837,1086,1135,1140`
- `scripts/materialize_pne2026_public_diagnostic_v3.py:18,68,231,285,390,584-590,758`
- `scripts/promote_pne2026_public_diagnostic_v3.py:39`, `scripts/generate_municipal_finance.py:49`
- `scripts/materialize_municipal_education_overview.py:551,570`, `src/higher_education.py:1414`
- `scripts/rematerialize_education_attendance_projections.py:47,499,600`
- `scripts/checks/verify-state-reference.cjs:55,111`

## 2. Mudanças de contrato

1. **State-config ativo**: promover `config/candidates/states/al.json` → `config/states/al.json`
   e `config/candidates/municipalities/al.json` → `config/municipalities/al.json`;
   atualizar `config/publications/al.json`.
2. **Raiz de saída**: `src/config.py:17-21` fixa `PUBLIC_DATA_DIR = public/data`.
   Introduzir `resolve_public_data_dir(state_code)` lendo o manifesto de publicação
   (RS continua em `public/data`; AL resolve `state-publications/al/data`).
   `update_static_data.py` tem `--state` mas escreve sempre em `public/data`;
   `export_static_data.py` não tem `--state`.
3. **Contrato frontend**: `analyticsStatus` é binário (`complete | identity-only`;
   `src/config/publicationConfig.ts:9`, `src/app/AppContent.tsx:26-28`,
   `data_pipeline/src/state_publication.py:15`). Adicionar `'partial'` com
   `enabledProducts: [...]` (schema v3) para publicar Educação de AL antes do resto.
4. **Fingerprints/testes**: derivar universos de `state_config.expected_municipality_count`;
   `verify-state-reference.cjs` fixa 497; `test_pipeline_education_state.py` fixa RS.

## 3. Fases

- **Fase 0 — Banco `sesi` com AL** (repo SESI/DB; caminho crítico). Parametrizar
  `UF_ALVO`/queries dos 14 ETLs, garantir chaves compostas com `sigla_uf`,
  generalizar `populacao_idade_rs` (7 arquivos `queries/pop_*.sql`), rodar carga AL.
  A reconstrução da tabela de população por idade corre em frente separada (§4.1.5).
  Decisão: um banco com duas UFs (recomendado — as consultas já filtram por
  `sigla_uf`). Aceite: 18 views devolvem linhas `27xxxxx`; RS byte-idêntico.
- **Fase 1 — Educação básica + superior + especial de AL** (repo dashboard).
  Promover configs, criar rotas de compatibilidade AL, parametrizar raiz pública,
  fingerprint, amostras de QA (Maceió `2704302`), contrato `partial`
  (`enabledProducts: ["educacao"]`). Aceite: 102 contratos municipais; RS sem regressão.

  **Scaffolding concluído** (configs promovidas, `config/compatibility/education-municipality-routes/al.json`
  com 36 overrides, `resolve_public_data_dir`, fingerprint por UF, amostras de QA
  do registro ativo e `state-publication-v3` com `partial`/`enabledProducts`).
  `config/publications/al.json` permanece `identity-only`: o flip para `partial`
  depende da Fase 0 popular o banco `sesi` com AL e de rodar
  `update_static_data.py --state AL --education-only`.
- **Fase 2 — Financiamento** (paralelizável; 6 de 8 fontes não dependem do banco).
  SIOPE `@Sig_UF='AL'`, regex FUNDEB/QSE `^AL`/`27\d{5}`, crosswalk
  `siope_ibge_crosswalk_al_v1.json`.
- **Fase 3 — PNE 2014–2024**. SIDRA `N3[27]`, metas 11.b/11.d/14/15.b,
  alfabetização, `--state` em `export_static_data.py`,
  `methodology_version pne2014-al-reference-v1`.
- **Fase 4 — PNE 2026–2036 + projeções**. Referência estadual AL, cenários,
  MUNIC/CAPES refiltrados.
- **Fase 5 — Diagnóstico v3 + flip para `complete`**. Depende de todas as anteriores.

```
Fase 0 ──► Fase 1 ──► Fase 3 ──► Fase 4 ──► Fase 5
   └─────► Fase 2 ────────────────────────────┘
```

## 4. Decisões do usuário

### 4.1 Resolvidas

1. **Metas do PNE — nacionais em todos os estados.** Valem as metas da Lei
   13.005/2014 (`src/pne/calculations_2014.py:21-64`), inclusive em Alagoas. O
   Plano Estadual de Educação não substitui a referência nacional: manter a mesma
   estrutura de plataforma em todos os estados facilita a manutenção e preserva a
   comparabilidade entre municípios.
2. **Regionalização — removida da plataforma.** O produto de regiões não é
   utilizado. A agregação regional foi retirada de
   `export_education_indicators.py`, a dependência da coluna `regiao_senai`
   (mapa FIERGS, exclusivo do RS) deixou de existir na consulta municipal e os
   artefatos legados `public/data/educacao/regioes/` foram excluídos. Não há
   decisão regional pendente para AL.
3. **Marca — "Painel SESI de Educação".** O nome é idêntico em todos os estados
   (não há mais "Painel SESI-RS"/"Painel SESI-AL"). A Home declara explicitamente
   o estado de referência a partir de `ACTIVE_STATE_CONFIG.stateName`. A
   identidade visual — cores, tipografia, logos e assinaturas institucionais
   SESI/FIERGS — é mantida sem alteração.
4. **Integração de dados — sempre por código IBGE.** Permanece a regra atual: o
   código IBGE textual de sete dígitos é a única identidade; slugs são cosméticos
   e servem apenas a rotas públicas.
5. **População por idade — frente separada.** A tabela de população por idade do
   banco `sesi` será reconstruída em uma frente própria, a partir das fontes em
   `SESI/DB/data/populacao`, tendo `pop_estimada.py` do projeto CEI como
   referência. Não é pré-requisito do scaffolding de AL neste repositório.

### 4.2 Pendentes

1. **Cortes temporais** da referência estadual (2015–2025, baseline 2025,
   `STATE_PROJECTION_MINIMUM_OBSERVATIONS = 5`): validar densidade da série de AL.
2. **Indicadores indisponíveis herdados** (seleção de diretores, conectividade INEC —
   `municipalityCount: 0` já no RS): herdar a declaração de indisponibilidade (recomendado).
3. **Piso de supressão** para denominadores pequenos (ex.: Meta 15.b terá poucos
   municípios com IES em AL).

## 5. Salvaguardas operacionais

- A carga de AL no banco `sesi` deve preservar o RS: após a carga,
  `update:data --state RS` precisa produzir `git diff` vazio em `public/data/`.
- `scripts/update_static_data.py:125-145` (`ensure_git_update_safe`) é a rede de segurança.
- Volume estimado de AL: ~230 MB (~20,5% do RS); confortável nos limites do
  Cloudflare Pages (20 000 arquivos/deploy, 25 MiB/arquivo).
