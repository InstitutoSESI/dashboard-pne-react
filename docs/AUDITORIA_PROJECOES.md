# Auditoria das projeções

Auditoria executada entre 30 e 31 de julho de 2026 sobre cálculos, contratos,
consumidores e textos que apresentam valores futuros na plataforma.

## Escopo

| Família | Tratamento após a auditoria |
| --- | --- |
| Atendimento por idade, sete indicadores e 497 municípios | Seleção por indicador entre persistência, tendência estadual amortecida e tendência robusta municipal combinada à estadual; denominador municipal varia pelos fatores etários da projeção do RS |
| Referências estaduais anuais | Persistência do último numerador e denominador estaduais agregados |
| Cenários de manutenção | Hipóteses operacionais; não são previsões estatísticas |
| Trajetórias até metas legais ou referências | Ritmo necessário; não são previsões estatísticas |
| Tendência histórica Theil–Sen | Descrição do passado; resultado inconclusivo não é usado como ritmo observado |
| Estimativas financeiras de Fundeb e QSE | Valores oficiais importados do FNDE; a plataforma não os estima |
| Indicadores censitários | Sem interpolação ou projeção |

## Qualidade dos dados de atendimento

As sete bases municipais têm 497 municípios e 12 observações anuais por
município, de 2014 a 2025. Não foram encontrados anos duplicados, lacunas,
numeradores negativos, denominadores nulos ou não positivos. A fonte configurada
para a projeção populacional do RS contém idades simples de 0 a 90 anos e todos
os anos necessários entre 2026 e 2036.

O numerador usa matrículas pelo município da escola e o denominador usa
população residente. Essa é a aproximação disponível e adotada para a cobertura
municipal, mas não identifica fluxos de estudantes entre municípios. Também não
há variáveis de capacidade, migração escolar, abertura de vagas ou política
municipal no modelo.

## Validação retrospectiva

Foi usado backtesting `rolling-origin` com horizontes de um a cinco anos. Uma
separação determinística reservou 379 municípios para desenvolver e escolher
parâmetros e 118 para avaliação final, com alvos recentes de 2023 a 2025. Em
cada origem entram apenas observações que já estariam disponíveis. A métrica é
100 vezes o erro absoluto das matrículas previstas, dividido pela população
observada no ano-alvo. O cálculo permanece bruto: o teto visual de 100% não
participa da seleção nem da validação.

Uma alternativa tendencial só foi aceita quando melhorou a persistência no
conjunto reservado e o intervalo bootstrap de 95% para o ganho permaneceu
inteiramente acima de zero.

| Indicador municipal | MAE do modelo anterior | MAE do modelo selecionado | Decisão |
| --- | ---: | ---: | --- |
| Creche | 8,0221 | 8,0221 | Preservar persistência |
| Pré-escola | 15,8213 | 13,1760 | Substituir Holt por persistência |
| Atendimento de 6 a 17 anos | 5,7106 | 4,7686 | Tendência robusta municipal + estadual |
| Atendimento de 15 a 17 anos | 11,1405 | 11,1405 | Preservar Holt estadual amortecido |
| Contexto de 0 a 5 anos | 7,1552 | 7,1552 | Preservar persistência |
| Contexto de 4 a 17 anos | 5,3054 | 4,5609 | Tendência robusta municipal + estadual |
| Contexto de 6 a 14 anos | 5,5472 | 5,5472 | Preservar persistência |

Na pré-escola, a persistência reduziu o MAE em 2,6453 p.p., com intervalo
bootstrap de 95% entre 1,7792 e 3,5227 p.p. No recorte de 6 a 17 anos, o ganho
foi de 0,9420 p.p., com intervalo entre 0,5064 e 1,3788 p.p. No recorte de 4 a
17 anos, o ganho foi de 0,7445 p.p., com intervalo entre 0,3456 e 1,1358 p.p.
Os três ganhos apareceram em todos os horizontes primários de um a cinco anos.

O Holt preservado para 15 a 17 anos é ajustado na série agregada de matrículas
do Rio Grande do Sul e ancorado no último numerador municipal. Os novos modelos
de 6 a 17 e de 4 a 17 anos estimam tendências robustas em `log1p` das
matrículas municipais e estaduais, limitam a inclinação anual a ±0,15 e
encolhem a tendência municipal para a estadual antes da extrapolação
amortecida. A base efetiva começa em 2014 e os anos de 2020 a 2022 permanecem
na série.

## Modelo publicado

Em todos os sete recortes, a população municipal do último ano observado é
projetada pela variação da respectiva faixa etária na projeção do RS. O
numerador segue uma destas regras:

- 15 a 17 anos: tendência estadual Holt amortecida, ancorada no último número
  municipal de matrículas;
- 6 a 17 e 4 a 17 anos: combinação da tendência robusta municipal com a
  estadual;
- creche, pré-escola, 0 a 5 e 6 a 14 anos: persistência do último número de
  matrículas.

São publicados 3.475 cenários municipais com a versão
`pne2026-municipal-attendance-backtested-hybrid-v3`. O indicador de 15 a 17
anos usa `state_aggregate_damped_holt_enrollment_with_state_age_denominator`;
os recortes de 6 a 17 e 4 a 17 anos usam
`municipal_state_shrunk_theil_sen_log_enrollment_with_state_age_denominator`;
os demais usam `last_observed_numerator_with_state_age_denominator`.

## Problemas corrigidos

- A regra antiga combinava uma mediana móvel com inclinação iniciada no último
  ano e criava uma quebra entre o observado e 2026.
- A escolha ad hoc entre tendência recente e longa e limites posteriores de 8%
  no numerador e de 2 ou 3 p.p. não tinham calibração empírica.
- A ausência de fator populacional podia trocar o ano-base ou manter população
  constante silenciosamente; agora torna o cenário indisponível.
- A revisão conservadora seguinte aplicava persistência aos sete indicadores e
  fazia parecer que as projeções de matrículas haviam desaparecido. A seleção
  fora da amostra recupera sua variação somente onde há ganho robusto.
- Razões brutas acima de 100% confundiam a leitura. A apresentação pública foi
  limitada a 100%, sem apagar numeradores, denominadores ou razões brutas dos
  artefatos de auditoria.
- A seleção anterior da pré-escola podia ser influenciada por esse teto visual;
  a validação agora usa somente o erro bruto, sem truncamento.
- A interface e o diagnóstico agora reconhecem os três métodos selecionados e
  rejeitam identificadores metodológicos antigos.

## Limitações

O resultado bruto pode superar 100% pela diferença territorial entre matrículas
e população. Essa razão permanece preservada para auditoria; o teto de 100% é
exclusivamente uma regra de apresentação e não altera os componentes nem o
cálculo bruto.

Não há evidência suficiente para intervalo probabilístico ou previsão causal
de matrículas até 2036. O contrato declara
`backtested_no_probability_interval`. O desempenho foi validado apenas em
horizontes de até cinco anos, portanto a incerteza é maior depois de 2030 e não
se deve atribuir a 2036 o mesmo grau de confiança do teste retrospectivo.

O resultado é um cenário estatístico condicionado às premissas, não uma
previsão oficial nem garantia de alcance das referências do PNE.
