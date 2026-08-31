# Relatório Job 2C — EJA V7

## Objetivo e estado

Materializar a série histórica de EJA integrada à educação profissional e a relação municipal entre público potencial e matrículas. Estado final: `READY`.

## Fontes, período e lentes

- PostgreSQL SESI em transação `READ ONLY`.
- `eja_integrada_educacao_profissional`: matrículas de 2014–2025, por localização da escola.
- `censo_populacao_ensino_fundamental_concluido_18_mais` e `censo_populacao_ensino_medio_concluido_18_mais`: universo residente de 2022.
- Código executor: `data_pipeline/scripts/materialize_vocacoes_pne_v7_job2.py`, função `_materialize_2c`.
- A comparação é explicitamente `população residente × localização da escola`; não representa fluxo pendular nem taxa de atendimento individual.

## Artefatos

| Artefato | Grão | Linhas | SHA-256 |
|---|---|---:|---|
| `2c/eja_integrada_historica.csv.gz` | município/região × ano | 144 | `4a837ec880066016de82a3fc90d00a3de51244877b4a0815f7faa1cd5917d154` |
| `2c/eja_demanda_oferta_2022.csv.gz` | município/região × etapa | 22 | `094a4fb453c23511b913b604f6081323e1a00378a3ed72c2dc803b139a959f59` |

## Fórmulas canônicas preservadas

- `participacao_publico_i = publico_potencial_i / publico_potencial_regiao`.
- `participacao_matriculas_i = matriculas_i / matriculas_regiao`.
- `diferenca_distribuicao_pp = participacao_matriculas_i - participacao_publico_i`.
- Apesar do sufixo histórico `_pp`, a diferença é armazenada como fração entre 0 e 1; a conversão para pontos percentuais cabe somente à apresentação.
- `matriculas_por_mil = 1000 × matriculas_i / publico_potencial_i`.
- Denominador zero produz `null`; zero observado permanece zero.

## Resultados de referência

- EJA regional total: 8.835 matrículas em 2014 e 11.447 em 2025.
- EJA integrada à educação profissional: 171 em 2014 e 157 em 2025.
- Participação integrada no total da EJA: 1,935484% em 2014 e 1,371538% em 2025.
- Em 2022, público potencial sem fundamental concluído: 221.260; matrículas de EJA fundamental: 5.528; 24,984182 matrículas por mil.
- Em 2022, público potencial com fundamental e sem médio concluído: 127.367; matrículas de EJA médio: 9.251; 72,632629 matrículas por mil.

## QA e limites

- Dez municípios canônicos presentes.
- Para cada etapa, as participações municipais de público e matrícula somam 1 dentro da tolerância de ponto flutuante; as diferenças somam aproximadamente zero.
- A série de matrícula não deve ser comparada a outro ano de público potencial como se os universos fossem contemporâneos; a análise demanda–oferta está ancorada em 2022.
- A métrica não mede pessoas únicas, intenção de matrícula, capacidade disponível, adequação de curso nem destino territorial do estudante.
- Validações do manifesto: escala `fraction_0_1`, denominador zero como `null` e dez municípios.
