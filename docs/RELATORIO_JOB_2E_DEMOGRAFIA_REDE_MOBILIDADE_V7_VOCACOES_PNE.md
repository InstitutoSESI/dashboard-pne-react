# Relatório Job 2E — Demografia, rede e mobilidade V7

## Objetivo e estado

Relacionar coortes demográficas, rede/matrículas escolares, um cenário mecânico de envelhecimento e a mobilidade educacional já validada na R6. Estado final: `READY`. O cenário não é previsão.

## Fontes, lentes e classes de evidência

- PostgreSQL SESI em transação `READ ONLY`: `populacao_idade`, `censo_escolas`, `censo` e `eja_integrada_educacao_profissional`.
- Artefato R6 versionado `scripts/checks/fixtures/vocacoes-pne/segunda-saida-pesquisa-vale-do-sinos.json`, SHA-256 `bee5d4b7a255631eb6dd49a8c0cb80e7ae68d2f8ff0c5ccc26e78047e31754b8`.
- População/coortes: residência, classe `estimated_indirect`; rede: localização da escola, classe `observed`; mobilidade 2022: residência do estudante, classe `preliminary`; cenário: `calculated`.
- Código executor: `data_pipeline/scripts/materialize_vocacoes_pne_v7_job2.py`, função `_materialize_2e`.

## Artefatos

| Artefato | Grão | Linhas | SHA-256 |
|---|---|---:|---|
| `2e/coortes_demograficas.csv.gz` | município/região × ano × faixa | 1.440 | `412a5e8eb7de29b5286c25ac00a16a2a5698a291799f37e52205cb986585b060` |
| `2e/rede_escolar.csv.gz` | município/região × ano | 144 | `550d85efd220e3e9798a1f65c941472bc4103c2b8b456c22ec96dab708af21df` |
| `2e/cenario_mecanico_coortes.csv.gz` | município/região × ano-alvo × etapa | 165 | `753444cc4639caab7a3b49945061aa18d4b744f434fe33df502ae378e340a50a` |
| `2e/mobilidade_educacional_2022.csv.gz` | município/região × universo | 33 | `0eb890a6c15c16362dee888666071d7825a255680512a60cfdffbc3d546c6a87` |
| `2e/contexto_v6.json` | contexto regional versionado | n/a | `a1b5445f5523f42bf6ad89b4dc660458b030c0fa3e26259c1faf5c58d4756f3e` |

## Leituras demográficas e de rede

Entre 2014 e 2025, a população estimada regional passou de 47.666 para 39.225 em 0–3 anos; 22.824 para 21.436 em 4–5; 61.470 para 58.579 em 6–10; 54.885 para 45.902 em 11–14; 43.264 para 33.093 em 15–17; e 101.703 para 87.176 em 18–24. Nas faixas mais velhas, 60–79 aumentou de 97.518 para 150.971 e 80+ de 13.063 para 20.580.

No mesmo período, a rede regional passou de 737 para 734 escolas; matrículas de pré-escola de 17.251 para 20.716; fundamental de 117.469 para 104.328; médio de 31.789 para 26.911; técnica de 12.774 para 13.945; EJA de 8.835 para 11.447.

O contexto R6 registra 13.004 nascimentos no início da série e 9.276 em 2024, queda absoluta de 3.728 e relativa de 28,6681%.

## Cenário mecânico

Método: envelhecimento fixo da coorte estimada de 2025, sem ajustes de migração, mortalidade, entrada, repetência, evasão, políticas, capacidade ou preferência. A razão compara tamanho mecânico da coorte com matrículas de 2025 e não é taxa de atendimento.

| Ano-alvo | Etapa | Coorte mecânica | Matrículas-base 2025 | Razão |
|---:|---|---:|---:|---:|
| 2026 | Fundamental | 104.269 | 104.328 | 0,9994 |
| 2026 | Médio | 33.148 | 26.911 | 1,2318 |
| 2026 | Pré-escola | 20.579 | 20.716 | 0,9934 |
| 2030 | Fundamental | 97.737 | 104.328 | 0,9368 |
| 2030 | Médio | 35.379 | 26.911 | 1,3147 |
| 2030 | Pré-escola | 9.448 | 20.716 | 0,4561 |

## Mobilidade e limites

Em 2022, no Vale do Sinos, 33.868 de 229.441 estudantes residentes estudavam fora do próprio município (14,7611%). No fundamental eram 7.507 de 107.060 (7,0120%); no médio, 5.812 de 38.516 (15,0898%). As participações estaduais comparáveis eram 8,8148%, 3,3018% e 8,2202%.

- A fonte não identifica o município de destino; nenhum fluxo origem–destino foi criado.
- A mobilidade é preliminar e não deve ser combinada mecanicamente com oferta ou vagas.
- População e rede usam lentes territoriais diferentes.
- A queda de nascimentos termina em 2024 e não autoriza extrapolação automática.
- Validações do manifesto: dez municípios, destino indisponível e `scenarioIsForecast=false`.
