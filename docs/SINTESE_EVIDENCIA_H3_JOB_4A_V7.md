# Síntese de evidência H3 — Job 4A V7

## Escopo e separação das fontes

A matriz contém os 66 modelos efetivamente executados, todos com **RAIS como estoque**. O CAGED permaneceu **fluxo descritivo**; nenhum coeficiente CAGED foi estimado. Os contextos de ocupação e CNAE na matriz vêm do cubo CAGED de 2025 e estão marcados como contexto, nunca como explicação do coeficiente RAIS.

## Respostas às seis perguntas

1. **Padrão mais estável.** Entre os padrões executados, `RAIS active bonds 15–17 × age-grade distortion do ensino médio` em lag 0/1 é o mais estável por direção e controles. O principal é `-1.1326770423912371` ponto percentual por unidade de `log1p(vínculos)`. O lag 2 muda o sinal para `+0.213378166367629`; portanto a estabilidade não cobre todos os lags pré-registrados.

| Execução | Lag | Coeficiente | Sinal | Municípios | N |
|---|---|---|---|---|---|
| MAIN_2019_2025 | 0 | -1.132677 | negative | 493 | 3203 |
| LAG_1 | 1 | -0.962258 | negative | 492 | 2731 |
| LAG_2 | 2 | 0.213378 | positive | 490 | 2268 |
| EXCLUDE_2020_2021 | 0 | -1.097103 | negative | 490 | 2298 |
| EXCLUDE_LARGEST_RS_10 | 0 | -1.120871 | negative | 483 | 3133 |
| EXCLUDE_SMALL_POPULATION_DECILE | 0 | -0.973007 | negative | 462 | 2957 |
| POPULATION_WEIGHTED | 0 | -1.343798 | negative | 493 | 3203 |
| WITH_INSE | 0 | -1.119373 | negative | 484 | 1358 |
| VALE_ONLY | 0 | -5.530660 | negative | 10 | 70 |
| NO_FE_DIAGNOSTIC | 0 | -0.025636 | negative | 493 | 3203 |

2. **RS e expressão no Vale.** O modelo principal cobre 493 municípios e 3.203 observações; a sensibilidade `VALE_ONLY` cobre dez municípios e 70 observações, preservando o sinal (`-5.530660`). A diferença de magnitude e a amostra regional pequena impedem tratar a expressão do Vale como réplica equivalente do painel estadual.

3. **Controle populacional e exclusão de 2020–2021.** O modelo com controle populacional preserva o sinal (`-1.145499355139825`). A exclusão de 2020–2021 também preserva sinal e ordem de magnitude (`-1.097103266318456`). A ponderação populacional resulta em `-1.343797727152513`. A janela alternativa 2022–2025 não foi executada como janela contínua; a exclusão de 2020–2021 conserva 2019 e não a substitui.

4. **Decisão.** O padrão sustenta monitoramento conjunto de estoque formal 15–17 e distorção do médio. Não entrega horário, rede específica, setor RAIS ou ator operacional adicional; assim, no estado executado, vai além da demografia mas não além da recomendação de acompanhar trabalho e educação em conjunto.

5. **Municípios.** Não houve limiar pré-registrado de “concentração dos dois fatos”. Os dez municípios tiveram aumento de RAIS 15–17 e redução de abandono e distorção do médio:

| Município | RAIS 15–17 | Δ abs. | Δ rel. | Saldo CAGED 15–17 | Abandono médio % | Distorção médio % |
|---|---|---|---|---|---|---|
| Campo Bom | 274→441 | +167 | 60.9% | 151→241 | 8.2→3.2 | 22.6→8.3 |
| Dois Irmãos | 274→387 | +113 | 41.2% | 38→74 | 1.6→1.4 | 36.8→17.1 |
| Estância Velha | 144→267 | +123 | 85.4% | 84→121 | 6.6→1.5 | 23.9→11.7 |
| Esteio | 111→299 | +188 | 169.4% | 69→199 | 8.7→4.0 | 35.3→21.9 |
| Ivoti | 130→174 | +44 | 33.8% | 66→69 | 5.0→2.4 | 16.4→15.4 |
| Nova Santa Rita | 104→172 | +68 | 65.4% | 39→100 | 4.7→3.2 | 43.3→24.8 |
| Novo Hamburgo | 722→1256 | +534 | 74.0% | 372→633 | 4.9→1.7 | 25.4→15.0 |
| Portão | 94→168 | +74 | 78.7% | 60→73 | 4.2→1.3 | 25.5→19.0 |
| São Leopoldo | 494→782 | +288 | 58.3% | 273→355 | 9.3→3.7 | 36.6→22.6 |
| Sapucaia do Sul | 136→279 | +143 | 105.1% | 98→187 | 9.3→4.1 | 39.4→22.2 |

Novo Hamburgo concentrou a maior mudança absoluta de RAIS 15–17 (`+534`); Esteio, a maior mudança relativa (`+169,4%`). São Leopoldo teve a maior redução de abandono (`-5,6 pp`) e Dois Irmãos a maior redução de distorção (`-19,7 pp`). Esses destaques não coincidem em um único município e não constituem critério de aprovação.

6. **Utilidade sem inferência individual/causal.** Sim, como quadro ecológico de monitoramento territorial. Em Nova Santa Rita, RAIS 15–17 passou de 104 para 172 (`+65,4%`), o saldo CAGED 15–17 de 39 para 100, o abandono do médio de 4,7% para 3,2% e a distorção de 43,3% para 24,8%. Isso descreve coexistência de movimentos agregados; não identifica as mesmas pessoas nem efeito do trabalho sobre a escola.

## Contexto setorial e ocupacional disponível

O estoque RAIS usado no modelo H3 não contém setor ou ocupação no artefato anual. O cubo CAGED contém essa composição de fluxo. Em 2025, para 15–17, os maiores volumes ajustados regionais incluíram Auxiliar de escritório (CBO 411005), Assistente administrativo (411010) e Embalador à mão (784105); entre CNAEs, supermercados (4711302), hipermercados (4711301) e fabricação de calçados de couro (1531901). Esse contexto não pode ser transportado para o coeficiente de estoque.

## Limite factual

RAIS e CAGED não medem informalidade, desemprego ou primeiro emprego. Lentes de estabelecimento de trabalho, localização da escola e residência permanecem distintas. `same_person_inference_allowed=false` em todas as linhas.
