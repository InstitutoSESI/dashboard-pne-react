# Decisão canônica de escopo educacional — rede total — Job 4B V7

**Data da decisão:** 28 de agosto de 2026
**Classificação do registro:** DOCUMENTATION_ONLY
**Vigência:** próximos jobs da V7, a partir da aprovação documental do Job 4B
**Natureza:** correção posterior de escopo do produto, sem alteração retroativa de resultados

## 1. Decisão explícita

Por decisão do responsável pelo produto, toda análise educacional municipal da
V7 deve usar exclusivamente a rede total do município, agregando todas as
dependências administrativas observadas e compatíveis: municipal, estadual,
privada e federal, quando presente.

Parâmetros canônicos:

    network_scope = total_all_dependencies
    analytical_grain = municipality_year_stage
    administrative_dependency_is_analytic_dimension = false
    administrative_dependency_is_QA_dimension = true
    retrospective_preregistration_edit = false

Para fotografias educacionais, o grão correspondente é
municipality_stage_reference_year. A dependência administrativa não é unidade
principal, filtro, eixo de seleção, modelagem, comparação ou narrativa.

## 2. Justificativa de produto

A V7 deve orientar decisões municipais sobre o conjunto da oferta educacional
localizada no território, sem atribuir um resultado agregado a uma parcela
administrativa. A rede total:

- mantém uma leitura municipal única e comparável;
- evita transformar repartições institucionais em explicações de desempenho;
- preserva a possibilidade de coordenação entre entes sem estratificar
  resultados;
- alinha os 162 modelos H2 já executados, todos com network=total, ao escopo
  atual do produto;
- mantém separadas as lentes de residência, localização da escola e local do
  estabelecimento de trabalho.

O nome H1_DEMOGRAFIA_REDE é preservado por compatibilidade. Nesse identificador,
rede significa o conjunto total da oferta escolar localizada no município.

## 3. Escopo abrangido

A decisão cobre matrículas, escolas, turmas, docentes, aprovação, reprovação,
abandono, distorção idade-série, condições escolares, EJA, educação profissional
e qualquer outro indicador educacional municipal da V7.

As unidades são:

- histórico educacional: município × ano × etapa;
- fotografia educacional: município × etapa × ano de referência;
- mobilidade: município de residência × etapa × 2022;
- oferta educacional: localização das escolas do município;
- trabalho: localização do estabelecimento, sempre em lente separada.

## 4. Regras de agregação

### 4.1 Contagens

Para grandezas aditivas:

    total_municipal = soma das dependências administrativas compatíveis

Somente parcelas pertencentes ao mesmo indicador, período, etapa, unidade,
lente e contrato podem ser somadas. Ausência, indisponibilidade ou supressão de
uma parcela não pode ser convertida em zero.

### 4.2 Taxas

A ordem obrigatória é:

1. usar preferencialmente o registro oficial de dependência total;
2. quando necessário e possível, recomputar:

       taxa_total =
         soma dos numeradores das dependências
         /
         soma dos denominadores das dependências

3. se os componentes ou ponderadores declarados não existirem, preservar o
   estado de indisponibilidade e documentar o limite.

É proibido fazer média simples das taxas das dependências, somar percentuais ou
usar média ponderada sem ponderador declarado. Denominador zero produz null.
Zero observado, null, unavailable, suppressed e not_applicable permanecem
distintos. Arredondamento ocorre apenas na apresentação ou serialização final.

## 5. Papel residual da dependência administrativa

Campos de dependência podem permanecer nas fontes brutas somente para:

- reconstruir a rede total;
- conferir duplicidades e fechamento;
- preservar proveniência;
- executar QA;
- identificar a ausência de uma parcela esperada.

Esses campos não podem originar cartão, ranking, filtro, candidata, modelo,
seleção ou conclusão de desempenho. A dimensão permanece técnica e residual,
não analítica.

## 6. Rede total, lentes territoriais e responsabilidade

Rede total não unifica universos diferentes. Devem continuar separados:

- população residente;
- matrículas localizadas nas escolas do município;
- residentes que estudam fora;
- vínculos localizados nos estabelecimentos de trabalho.

Essas lentes não representam necessariamente as mesmas pessoas e não autorizam
inferência individual.

A responsabilidade institucional permanece apenas como contexto sobre quem
pode agir, coordenar, articular ou acompanhar. Pode incluir município, Estado,
coordenação regional, instituições ofertantes e Sistema S. Não pode ser inferida
por estratificação de desempenho, nem atribuir a um ente o resultado agregado
da rede total.

## 7. Efeito por candidata

| Candidata | Efeito da decisão |
|---|---|
| H1_DEMOGRAFIA_REDE | Usa matrículas, escolas e turmas totais por etapa; preserva população residente versus matrícula localizada; mantém o ID por compatibilidade. |
| H2_TRAJETORIA_PERMANENCIA | A execução com network=total está alinhada ao produto. A antiga ausência de estratificação administrativa deixa de ser lacuna ou bloqueio, mas as demais divergências metodológicas permanecem. |
| H3_TRABALHO_JUVENIL_MEDIO | Os resultados educacionais agregados estão no escopo correto. A candidata continua retida por insuficiência de decision_delta, instabilidade e limites ecológicos, nunca por ausência de estratificação administrativa. |
| H4_EJA_DISTRIBUICAO | Usa matrículas totais de EJA, com fundamental e médio separados e com lentes de residente e matrícula localizada preservadas. |
| A3_OCUPACOES_FORMACAO | Usa a oferta técnica total observada. Instituições ofertantes são atores de governança, não eixos de desempenho. |
| A4_MOBILIDADE_COORDENACAO | Usará rede total e a lente de residência de 2022; não atribuirá mobilidade a uma dependência administrativa. |

A1_COORTES_REDE e A2_TRABALHO_PERMANENCIA continuam retidas por redundância.
A decisão de rede total não altera C11 nem restaura candidatas para completar
quantidade.

## 8. Efeito sobre C1–C12

Para os próximos jobs:

- C1 continua sendo relevância para PNE/PME;
- C2 continua exigindo mecanismo anterior ao resultado;
- C3 passa a exigir universos e lentes compatíveis, com educação em rede total;
- C4 continua exigindo período coerente;
- C5 continua exigindo estabilidade suficiente;
- C6 continua exigindo integração de fatos;
- C7 continua exigindo diferença municipal útil;
- C8 deve nomear município, etapa, público, indicador e questão de planejamento;
- C9 continua sendo comunicabilidade editorial;
- C10 continua sendo rastreabilidade;
- C11 continua sendo não redundância;
- C12 continua exigindo valor incremental além da demografia.

C8 não exige dependência administrativa. A responsabilidade institucional
continua obrigatória como ação, coordenação, articulação ou acompanhamento,
sempre contextual.

## 9. Tratamento histórico do pré-registro 1.0.0

O arquivo [PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml](PRE_REGISTRO_ANALITICO_JOB_3_V7.yaml)
permanece congelado e byte a byte inalterado. A
[auditoria do Job 4A](AUDITORIA_PRE_REGISTRO_JOB_4A_V7.md) continua
historicamente correta ao registrar como NOT_EXECUTED os testes ausentes
exigidos literalmente pelo texto antigo.

A partir desta decisão:

1. a ausência de execuções separadas por dependência deixa de ser lacuna do
   produto;
2. essa ausência deixa de ser critério de retenção ou bloqueio;
3. os modelos H2 com network=total estão alinhados ao escopo atual;
4. a mudança é correção posterior do produto, não emenda retroativa;
5. nenhuma candidata é aprovada ou retida retroativamente por esta correção;
6. janelas, ponderações, pequeno denominador, especificações, documentação e
   sensibilidades não executadas permanecem divergências válidas.

Nenhum NOT_EXECUTED será convertido retrospectivamente em
EXECUTED_WITH_RECORDED_INAPPLICABILITY.

## 10. Preservação e vigência

Os Jobs 2, 3 e 4A não são alterados por este documento. Seus cálculos,
artefatos, manifests, hashes, estados históricos e conclusões permanecem como
evidência congelada. O contrato canônico também não é editado neste job.

Esta decisão rege o futuro [pré-registro do Job 5A](PRE_REGISTRO_JOB_5A_REDESENHO_DIRIGIDO_V7.yaml),
o [plano do Job 5A](PLANO_JOB_5A_REDESENHO_DIRIGIDO_V7.md), o
[julgamento externo final](DECISAO_JULGAMENTO_EXTERNO_FINAL_JOB_4B_V7.md) e o
[aditivo provisório 3+2](ADITIVO_PROVISORIO_PORTFOLIO_3_MAIS_2_V7.md).
Ela não autoriza cálculo, narrativa pública, interface, publicação ou abertura
do PILOT_GATE_11_V7.
