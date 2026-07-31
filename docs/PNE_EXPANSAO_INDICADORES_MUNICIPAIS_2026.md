# Expansão consolidada dos indicadores municipais do PNE

Esta rodada incorpora as relações 3.a, 11.d, 14.a, 14.b, 14.d e 15.b ao contrato canônico do PNE 2026–2036. Os arquivos brutos permanecem fora do repositório; somente snapshots municipais e estaduais agregados, manifestos e hashes são versionados em `data_pipeline/data`.

## Relações publicadas

| Relação | Indicador | Modo | Referência |
| --- | --- | --- | --- |
| 3.a | Alfabetização ao final do 2º ano — rede municipal | progresso | 80% em 2031; 100% em 2036 |
| 11.d | Matrículas EJA 18+ / população 18+ sem Educação Básica concluída | progresso | 10% em 2031; 20% em 2036 |
| 14.a | Residentes de 18 a 24 anos que frequentam graduação | acompanhamento | 40%, sem classificação legal |
| 14.b | Residentes de 25 a 34 anos com superior completo | acompanhamento | 40%, sem classificação legal |
| 14.d | Taxa bruta de frequência à graduação | progresso | 60% em 2036 |
| 15.b | Docentes em tempo integral no total das IES | progresso | 70% em 2036 |
| 15.b | Universidades, centros universitários e faculdades | acompanhamento | 50%, 40% e 30%, sem classificação legal por categoria administrativa |

As relações 7.a e 18.a permanecem bloqueadas. A relação 17.d permanece complementar, com cobertura parcial e sem referência, distância, situação ou projeção.

## Contagens e conceitos

- 59 relações no contrato: 27 `progress`, 15 `tracking`, 15 `complementary` e 2 `hidden`;
- 51 relações materializadas por município no Diagnóstico: 42 comparáveis e 9 complementares;
- 42 indicadores comparáveis no ciclo: 27 referências previstas nas metas e 15 referências de acompanhamento;
- 50 relações possuem a flag contratual histórica `includeInCycleGoalRefs`, mas esse número inclui relações complementares ou ocultas e não representa cards comparáveis;
- 39 metas legais possuem alguma relação pública municipal e 34 não possuem indicador municipal no contrato atual.

As contagens disponíveis e sem comparação são recalculadas para cada município.

## Fontes e territorialidade

- Alfabetização: resultado percentual oficial do Inep para a rede municipal e o município da escola. A elegibilidade de divulgação é validada pela participação mínima de 70%; ausência não significa zero. A comparação estadual usa o resultado oficial da rede municipal, não a média dos municípios.
- 11.d: numerador da Sinopse Estatística da Educação Básica, por município da escola; denominador do Censo Demográfico 2022, por município de residência. A razão pode superar 100%.
- Meta 14: tabelas SIDRA 10058, 10059 e 10061, todas por município de residência. A comparação estadual é a razão das somas municipais.
- Meta 15.b: tabela 2.2 da Sinopse da Educação Superior, de 2018 a 2024, por sede/reitoria da IES. Os recortes de organização somam as categorias administrativas oficiais e são apenas de acompanhamento porque a fonte não isola com segurança a categoria comunitária exigida pela lei.

## Sincronização reproduzível

Execute primeiro sem `--apply`; somente depois repita o comando com `--apply`.

```powershell
python data_pipeline/scripts/sync_pne_child_literacy.py --source-dir $env:PNE_CHILD_LITERACY_SOURCE_DIR --reference-date 2026-07-30
python data_pipeline/scripts/sync_pne_goal_11d_eja.py --source-dir $env:PNE_GOAL_11D_SOURCE_DIR --reference-date 2026-07-30
python data_pipeline/scripts/sync_pne_goal_14_census.py --reference-date 2026-07-30
python data_pipeline/scripts/sync_pne_goal_15b.py --source-dir $env:PNE_GOAL_15B_SOURCE_DIR --reference-date 2026-07-30
```

Cada sincronizador valida cobertura, unicidade, domínio, reconciliação estadual e hashes antes de materializar. Os diretórios pessoais não são gravados nos manifestos.

## Publicação

A materialização do diagnóstico é feita em staging fora de `public/data`. A promoção usa o fluxo imutável existente: cria uma release nova, valida os 497 municípios e atualiza `current.json` atomicamente somente ao final. Releases anteriores não são alteradas.

```powershell
python data_pipeline/scripts/materialize_pne2026_public_diagnostic_v3.py --output-dir data_pipeline/.staging/pne-consolidated --git-ref HEAD
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py --source-dir data_pipeline/.staging/pne-consolidated --destination-dir public/data/pne2026-diagnostic-v3
```

Nunca edite manualmente os payloads municipais ou os snapshots agregados.
