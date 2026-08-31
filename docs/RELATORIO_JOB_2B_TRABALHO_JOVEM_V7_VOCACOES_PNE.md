# Relatório Job 2B — Trabalho jovem V7

## Objetivo e estado

Materializar estoque formal anual e fluxo mensal de trabalho para jovens de 15–17 e 18–24 anos no Vale do Sinos. Estado final: `READY`. O bloco não materializa “primeiro emprego” e não usa a tabela defeituosa `public.estoque_emprego_faixa_etaria`.

## Fontes e execução

- PostgreSQL CEI em transação `READ ONLY`: `municipio` e `rais_vinculos` para estoque jovem; `rais_vinculos_ocupacao`, `rais_ocupacoes_rs_25`, `ocupacao` e `cnae` apoiam o bloco ocupacional do Job 2D.
- Arquivos locais do Novo CAGED `CAGEDMOV`, `CAGEDFOR` e `CAGEDEXC`, sem download: 211 arquivos consumidos para 2020–2025.
- Código executor: `data_pipeline/scripts/materialize_vocacoes_pne_v7_job2.py`, função `_materialize_2b`.
- RAIS: 2019–2025; CAGED: 2020–2025. O ano parcial de 2026 foi excluído.

## Artefatos

| Artefato | Grão principal | Linhas | SHA-256 |
|---|---|---:|---|
| `2b/rais_estoque_jovem_anual.csv.gz` | escopo × ano × faixa etária | 168 | `a16b1959a3bdf5f404151ed26f34e77c7cfb6b0d0daf2714cbb49def63ae1afd` |
| `2b/rais_cubo_jovem.csv.gz` | município × ano × faixa × CNAE × natureza jurídica × tamanho | 6.243 | `f7f129dacfaa2be88a06e35cb21712ee11005bd6966368cc6fbccba48861f0c1` |
| `2b/caged_jovens_mensal.csv.gz` | município/estado × ano × mês × faixa | 1.577 | `b105f0ecd50469624ab3d330964bb8e7e2a60dcf8a3d023132bc30a9c88f4af2` |
| `2b/caged_jovens_cubo.csv.gz` | município × mês × faixa × evento × movimento × CBO × CNAE × escolaridade × sexo × raça/cor × aprendiz | 330.020 | `d7cf807ed11f38fd8592ee1c462f9258fb5e9d3d0938bda6f1d51f6a53fd1d5e` |

## Fórmulas e semântica

- RAIS representa estoque de vínculos formais ativos; CAGED representa fluxo. Os dois não são somados.
- Ajuste CAGED por célula: `eventos_ajustados = MOV + FOR - EXC`.
- Admissões e desligamentos são classificados pela direção original do movimento; `saldo = admissões - desligamentos`.
- Correções tardias e exclusões permanecem rastreáveis no cubo; 52 células hiperfinas têm ajuste negativo, com mínimo -3. Isso é correção de evento, não “emprego negativo”.
- Agregados mensais de admissões e desligamentos não possuem valores negativos.

## Resultados de referência

Estoque RAIS regional: 2.483 vínculos de 15–17 e 36.742 de 18–24 em 2019; em 2025, 4.225 e 37.885.

| Ano | Faixa | Admissões | Desligamentos | Saldo |
|---:|---|---:|---:|---:|
| 2020 | 15–17 | 2.434 | 1.184 | 1.250 |
| 2020 | 18–24 | 25.772 | 22.302 | 3.470 |
| 2021 | 15–17 | 2.744 | 925 | 1.819 |
| 2021 | 18–24 | 24.233 | 18.033 | 6.200 |
| 2022 | 15–17 | 2.953 | 1.750 | 1.203 |
| 2022 | 18–24 | 27.291 | 24.334 | 2.957 |
| 2023 | 15–17 | 4.911 | 2.926 | 1.985 |
| 2023 | 18–24 | 36.131 | 33.361 | 2.770 |
| 2024 | 15–17 | 5.600 | 3.248 | 2.352 |
| 2024 | 18–24 | 39.593 | 34.967 | 4.626 |
| 2025 | 15–17 | 5.855 | 3.803 | 2.052 |
| 2025 | 18–24 | 38.757 | 36.249 | 2.508 |

Para `aprendiz_indicator_code=1`, o cubo ajustado registra 16.922 admissões e 17.031 desligamentos no período. O indicador não identifica se o vínculo é o primeiro da pessoa.

## QA, cobertura e limites

- Dez municípios canônicos em RAIS e CAGED; chave natural RAIS validada sem duplicatas.
- Inventário local CAGED: SHA-256 `4a62c4586ffd910c3cb78434a55870547a71f0ff229df25a5794892708ed94b2`.
- Dois arquivos opcionais `FOR` estavam vazios (`202003` e `202204`); nenhum `MOV` vazio. O manifesto registra `emptyAdjustmentFileCount=2`.
- A tabela proibida possuía 600.834 linhas, 297.492 grupos duplicados, 262.231 conflitos e 89.395 grupos negativos e permaneceu sem uso.
- O CAGED não cobre informalidade, desemprego ou primeira inserção laboral; RAIS e CAGED são por local de trabalho.
