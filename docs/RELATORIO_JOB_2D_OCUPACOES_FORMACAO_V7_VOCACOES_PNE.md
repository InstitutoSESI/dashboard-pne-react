# Relatório Job 2D — Ocupações e formação V7

## Objetivo e estado

Materializar a oferta de cursos técnicos, o painel ocupacional RAIS e a correspondência normativa curso–subgrupo CBO, sem inferir adequação ou suficiência. Estado final: `READY`.

## Fontes e execução

- Suplementos locais do Censo Escolar 2023 e 2024 e entrada `Tabela_Curso_Tecnico_2025_V2.csv` do ZIP local de 2025.
- PostgreSQL CEI em transação `READ ONLY`: ocupações RAIS 2019–2025, CBO e CNAE, por local de trabalho.
- Projeção versionada `data_pipeline/contracts/vocacoes-pne-course-cbo-rs-v1-projection.json`, derivada sem mudança semântica da ponte R6.
- Hash da fonte R6 da ponte: `e11a6d1d6acf961ca0c28d778158571bef64f108ac32f7b3a9df0e2dac21cf8f`; hash da projeção: `bb3d437efda4f067e1ebb4a3bb05927aaf751ce14294f4fc4800efd321ee97e0`.
- Código executor: `data_pipeline/scripts/materialize_vocacoes_pne_v7_job2.py`, função `_materialize_2d`.

## Artefatos

| Artefato | Grão principal | Linhas | SHA-256 |
|---|---|---:|---|
| `2d/oferta_cursos_tecnicos.csv.gz` | escola × curso × ano | 337 | `1f39c50716b5716140f39e62fc5b372cffe12e575565cb221f5e07b768544cff` |
| `2d/cobertura_oferta_municipal.csv.gz` | município × ano | 30 | `6f169d8be1b3792e29cf614711c6359d8b2a4f23b3822568e051fa8808cece77` |
| `2d/ocupacoes_rais.csv.gz` | município/região × ano × CNAE × CBO | 486.005 | `dcbb50371cf72befe177e6aecdba37b3bbefe00c17328117470aca91ad9169ca` |
| `2d/cursos_cbo_2025.csv.gz` | escola × curso × subgrupo CBO | 138 | `cf60bb4cb49bbe15a35af728b83783418e67fc76c215838521ef14992047f867` |
| `2d/cobertura_ponte_2025.csv.gz` | status de mapeamento | 2 | `6c087c8db5515e01b4edfe88a79bdd6803acef74cf8604b476220aa478ef2d30` |

## Cobertura observada

| Ano | Cursos únicos | Eixos únicos | Matrículas técnicas |
|---:|---:|---:|---:|
| 2023 | 42 | 11 | 13.474 |
| 2024 | 41 | 10 | 14.043 |
| 2025 | 44 | 12 | 13.945 |

Em 2025 havia 113 linhas escola–curso, 33 escolas e oferta observada em sete municípios. Campo Bom, Ivoti e Nova Santa Rita tiveram zero observado, reconciliado com o total técnico do Censo Escolar; zero não foi convertido em ausência de informação.

A ponte cobriu 39 dos 44 cursos regionais de 2025 (88,6364%) e 12.664 das 13.945 matrículas (90,8139%). Permaneceram sem correspondência cinco cursos regionais, somando 1.281 matrículas: Informática, Ensino Médio – Curso Normal/Magistério, Publicidade e duas categorias “Outros”. A ponte global preserva 115 pares, 91 cursos mapeados e 22 não mapeados.

## Regras e limites semânticos

- A ponte é correspondência formativa normativa CNCT–CBO; não prova aderência entre oferta e mercado, suficiência de vagas, empregabilidade, qualidade ou necessidade futura.
- Um curso pode mapear para vários subgrupos CBO. Por isso as matrículas se repetem em `cursos_cbo_2025.csv.gz` e não são aditivas nesse artefato.
- Oferta é por localização da escola; RAIS é por local de trabalho. A junção é contexto territorial, não trajetória individual.
- O total regional é soma de matrículas/vínculos, nunca média simples de municípios.
- A oferta detalhada disponível cobre 2023–2025; o painel ocupacional cobre 2019–2025.

## QA

- Reconciliação absoluta entre suplemento de cursos e matrícula técnica censitária: zero.
- Dez municípios canônicos cobertos; sete pares município–ano com zero observado no período, incluindo os três de 2025.
- Hash do ZIP de 2025: `ad2c389160be5cf6b8e32257677e9b5657f01d10a342355ad9757bfecd2fc90a`.
- Validações do manifesto: `adequacyClaimMaterialized=false`, 39 cursos regionais mapeados e participação de matrícula mapeada `0.9081391179634277`.
