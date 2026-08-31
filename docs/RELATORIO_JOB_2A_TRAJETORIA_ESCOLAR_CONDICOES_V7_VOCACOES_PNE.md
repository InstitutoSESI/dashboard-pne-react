# Relatório Job 2A — Trajetória escolar e condições auxiliares V7

## Objetivo e estado

Materializar séries auditáveis para leitura municipal e regional da trajetória escolar e de condições associadas no Vale do Sinos. Estado final: `READY`. A saída é analítica, não pública, e não altera metodologia, indicadores ou `public/data`.

## Fontes e execução

- PostgreSQL SESI, sempre em transação `READ ONLY`: `rendimento_escolar`, `distorcao_idade_serie`, `alunos_turma`, `adequacao_docente`, `inse`, `saeb_ideb`, `censo` e `censo_escolas`.
- Registro regional: `config/regions/rs.json`; identidade e nomes: `config/municipalities/rs.json`.
- Código executor: `data_pipeline/scripts/materialize_vocacoes_pne_v7_job2.py`, função `_materialize_2a`.
- Cobertura disponível, conforme a fonte: rendimento 2018–2025; distorção 2019–2025; alunos por turma 2016–2025; adequação 2014–2025; INSE 2019/2021/2023; SAEB/IDEB 2011–2025; condições censitárias 2014–2025.

## Artefatos

| Artefato | Grão principal | Linhas | SHA-256 |
|---|---|---:|---|
| `2a/trajetoria_municipal.csv.gz` | município × ano × dependência × localização × etapa × métrica | 5.823 | `efd0c5e7689c08da1c94a0e789823c2d9a5c20a3ba828bbb0fe717e428ad0ad8` |
| `2a/trajetoria_comparacoes.csv.gz` | escopo × ano × dependência × localização × etapa × métrica | 1.389 | `02f183e1d5e16f155a5942921abfddbbb92e7ffa6039225c80e19702b78aac5b` |
| `2a/condicoes_oferta.csv.gz` | município × ano × dimensão × métrica | 5.280 | `f6923988861303610035243693294bde4425edaa586fab51e2428fa669a38687` |
| `2a/condicoes_comparacoes.csv.gz` | escopo × ano × dimensão × métrica | 1.145 | `8f45299d3544b0b932b1c4765ded52744b7cfb041f87713f114ae6b45228188b` |

## Regras preservadas

- Código IBGE permanece texto de sete dígitos; não há join por nome.
- Quando existem numerador e denominador, a comparação regional/estadual usa `soma(numerador) / soma(denominador)`.
- INSE usa média ponderada por estudantes.
- Quando a taxa regional não pode ser recomposta, o artefato expõe distribuição municipal: contagem, mínimo, quartis, mediana e máximo. Não há média regional simples.
- Denominador zero e componentes indisponíveis resultam em `null`, nunca em zero inventado.
- Percentuais não são limitados artificialmente e cálculos usam valores brutos.

## Resultados de referência

Em 2025, para dependência total, a distribuição entre os dez municípios apresentou:

| Indicador | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|
| Aprovação no fundamental | 97,15% | 92,2% | 99,3% |
| Reprovação no fundamental | 2,85% | 0,5% | 6,9% |
| Abandono no fundamental | 0,10% | 0,0% | 0,9% |
| Aprovação no médio | 91,45% | 81,1% | 93,7% |
| Reprovação no médio | 6,00% | 3,2% | 15,7% |
| Abandono no médio | 2,80% | 1,3% | 4,1% |
| Distorção no fundamental | 7,50% | 2,5% | 14,4% |
| Distorção nos anos finais | 12,75% | 4,0% | 23,3% |
| Distorção nos anos iniciais | 4,15% | 1,3% | 9,5% |
| Distorção no médio | 18,05% | 8,3% | 24,8% |

O INSE ponderado de 2023 foi 5,461036 no Vale do Sinos e 5,395712 no RS. Em 2025, a proporção recomposta de escolas com banda larga foi 89,100817% na região e 75,122216% no estado; para internet, 96,457766% e 89,317400%, respectivamente.

## QA, limites e uso seguro

- Dez municípios canônicos presentes; comparações estaduais usam até 497 municípios, conforme disponibilidade da fonte.
- Água potável, biblioteca e quadra não apresentaram componentes utilizáveis no recorte censitário de 2025: ficaram `null`/indisponíveis, não zero.
- A lente é predominantemente localização da escola, não residência do estudante.
- Distribuições municipais descrevem heterogeneidade; não devem ser lidas como taxa regional agregada.
- Validações do manifesto: `municipalityCount=10`, `simpleRegionalAverageUsed=false`, `publicDataChanged=false`.
