# Metodologia

## Princípios de publicação

- zero é um valor; ausência não deve ser convertida em zero;
- indisponível, não aplicável, inválido e não calculável têm significados distintos;
- período, unidade, fonte e recorte acompanham o resultado;
- séries não comparáveis não são concatenadas nem interpoladas silenciosamente;
- o painel não infere causalidade, elegibilidade a programas ou qualidade de gestão a partir de um indicador isolado.

As regras executáveis prevalecem nos contratos e testes do repositório. Para o PNE 2026–2036, metas, prazos, fórmulas, fontes e relações têm uma única fonte canônica: `contracts/pne2026-goal-indicator-contract.json`. O catálogo público e a [documentação gerada do contrato](generated/PNE_2026_CONTRACT.md) são recompostos por `npm run generate:pne-contract-artifacts`.

## Indicadores educacionais e PNE

As fontes incluem Censo Escolar, Indicadores Educacionais, SAEB/IDEB e Sinopses do INEP, Censos e projeções do IBGE e estimativas populacionais do MS/DATASUS. `public/data/indicadores.json` é uma saída gerada, não uma segunda fonte metodológica.

Percentuais de atendimento preservam o resultado bruto na memória de cálculo. Valores acima de 100% podem ocorrer por diferença entre estimativas populacionais, mobilidade escolar e oferta localizada; para evitar uma leitura enganosa, a interface limita esses resultados a 100% e informa a existência do valor bruto. Indicadores censitários não são apresentados como séries anuais.

Referências do PNE 2026–2036 são resolvidas diretamente do contrato; os mapas JavaScript e Python são adaptadores derivados. Uma referência de acompanhamento não é apresentada como meta legal. Relações complementares não recebem referência, distância, status ou classificação. A contagem atual por modo e o detalhamento de cada relação são gerados em [PNE_2026_CONTRACT.md](generated/PNE_2026_CONTRACT.md), evitando números mantidos manualmente.

Os indicadores de creche, pré-escola e atendimento de 6 a 17 anos relacionam
matrículas registradas no município da escola à população residente estimada.
Essa diferença territorial pode produzir razões brutas acima de 100%. O painel
mantém os componentes e a razão bruta para auditoria, mas apresenta no máximo
100% ao leitor.

## Cenários e valores futuros

Os cenários municipais de atendimento combinam as matrículas do Censo Escolar
com a variação etária da projeção populacional do RS. O denominador parte da
população municipal no último ano observado e recebe os fatores demográficos
da faixa até 2036. Para o numerador, cada indicador usa o modelo que apresentou
melhor desempenho fora da amostra: o recorte de 15 a 17 anos acompanha a
tendência estadual amortecida das matrículas; os recortes de 6 a 17 e de 4 a
17 anos combinam tendências robustas do município e do estado; creche,
pré-escola, 0 a 5 e 6 a 14 anos mantêm o último numerador observado.

A seleção foi feita com backtesting `rolling-origin` de um a cinco anos,
separando 379 municípios para desenvolvimento e 118 para avaliação final. A
métrica usa o erro bruto das matrículas previstas em relação à população
observada no ano-alvo; o teto visual de 100% não participa da escolha nem da
validação do modelo. A
série deve conter pelo menos cinco observações anuais consecutivas, terminar
imediatamente antes do horizonte e não apresentar quebra metodológica. A falta
do fator populacional exato torna o cenário indisponível; não há troca
silenciosa de ano-base nem preenchimento constante.

As referências estaduais anuais mantêm o último par agregado de numerador e
denominador após a mesma validação de atualidade e regularidade. Esse modelo de
persistência substitui a regressão linear separada dos componentes. Nenhum
cenário estima intervalo probabilístico ou constitui previsão oficial. Como a
validação retrospectiva alcança no máximo cinco anos, a incerteza depois desse
horizonte — e especialmente até 2036 — deve ser considerada maior.

Cenários de manutenção de componentes e trajetórias lineares até metas
representam, respectivamente, uma hipótese operacional e o ritmo necessário.
Não são projeções estatísticas. Valores financeiros futuros identificados como
`official_estimate` são importados da publicação oficial e não calculados pela
plataforma.

Os parâmetros, janelas de backtesting e limitações são versionados junto às
fontes e aos contratos de cálculo em `data_pipeline/src` e
`data_pipeline/data`.

## Diagnóstico municipal

O diagnóstico organiza evidências em atenção, preservação, ausência e exclusão metodológica. Comparações estaduais só são publicadas quando valor, unidade, período e regra do indicador são compatíveis. O resumo não transforma posição relativa em ranking de qualidade.

O schema público `pne2026-public-diagnostic-v4` é denso: 42 relações comparáveis
e 9 relações complementares admitidas no Diagnóstico aparecem nos 497 municípios. Cada registro informa
`available`, `unavailable`, `not_applicable` ou `suppressed`; estados negativos
levam `reasonCode`, não carregam valor, referência ou classificação e são
exibidos com rótulo público. Componentes quantitativos usam
`numeratorField`/`numeratorValue` e
`denominatorField`/`denominatorValue`.

Municípios semelhantes são contexto analítico, não grupo de controle. A seleção usa atributos disponíveis e comparáveis, registra indisponibilidades e não autoriza inferência causal. Sínteses decisórias devem distinguir resultado observado, interpretação técnica e decisão da gestão.

## Financiamento

As fontes atuais incluem FNDE/SIOPE, Fundeb, PNATE, QSE, Siconfi, demonstrativos RREO e, para o Rio Grande do Sul, IMERS/PRE do DEE/SPGG e da SEDUC/RS. Snapshots, documentos e revisões necessários para reproduzir contratos ficam em `data_pipeline/data/municipal_finance` e `data_pipeline/data/qse_annual`.

No ICMS Educação do RS, `ANO` é o ano da avaliação do SAERS: 2022, 2023 e 2024 correspondem às distribuições de 2024, 2025 e 2026. O IMERS preserva a fórmula oficial `40% × IQA + 35% × IQI + 15% × IQF + 10% × IA`. O PRE é a participação municipal na quota-educação do ICMS e não é publicado como valor recebido, transferência confirmada ou estimativa em reais. A soma dos PRE publicados para 2024 é `100,002323507%`; os valores municipais oficiais são mantidos sem normalização, com aviso de qualidade explícito. A fonte é exclusiva do RS e não é imputada a Alagoas.

Valores financeiros preservam exercício, estágio da despesa, natureza, fonte e condição de cobertura. Empenhado, liquidado e pago não são somados entre si. Retificações substituem a versão anterior segundo a política do pipeline, mantendo a evidência da revisão. Valores nominais não são tratados como corrigidos pela inflação.

Relações entre indicador e programa financeiro são apresentadas como contexto de ação. Elas não comprovam repasse, seleção, elegibilidade ou efeito. Sistemas de informação fiscal não são descritos como fontes de transferência.

## Qualidade e validação

O pipeline testa domínio, denominadores, cobertura municipal, contratos de saída, reconciliação financeira e referências estaduais. Falhas de fonte ou de cobertura devem produzir estado explícito e nunca preenchimento inventado. Mudanças metodológicas exigem atualização conjunta de cálculo, contrato, testes e desta documentação.

## PNE 2026 — Meta 11.b

No contrato 1.4.0, a Meta 11.b publica dois snapshots censitários de 2022. O
15–29 soma o componente elegível de 15–17 anos às categorias com Ensino
Fundamental concluído de 18–24 e 25–29; o denominador soma os totais das mesmas
faixas. O 15+ soma o mesmo componente de 15–17 às categorias concluídas de 18
anos ou mais e usa o total 15–17 + 18+ como denominador.

Os componentes de 18 anos ou mais vêm da tabela IBGE/SIDRA 10061. Fundamental
completo e Médio incompleto, Médio completo e Superior incompleto e Superior
completo entram no numerador; sem instrução e Fundamental incompleto ficam
fora. Ausência ou supressão não vira zero, denominador zero não gera
percentual e a referência estadual é razão de somas. Não há série 2010–2022,
interpolação, tendência ou projeção. O indicador 18+ permanece disponível em
outros contextos, mas sua relação pública com a Meta 11.b é oculta.

Os arquivos brutos, componentes, manifesto e hashes estão em
`data_pipeline/data/pne_goal_11b_census_2022`.

## PNE 2026 — Metas 12.a e 12.b

No contrato atual, a articulação da educação profissional ao ensino
médio usa `100 × (matrículas integradas + concomitantes) ÷ matrículas do ensino
médio`, no mesmo município e ano. As colunas são agregados distintos de
matrículas e reconciliam por dependência administrativa, mas não identificam
estudantes únicos. A soma é reproduzível para os 497 municípios; a aderência
ao conceito legal de estudantes únicos não pode ser comprovada com a fonte
agregada, então a relação usa apenas a referência municipal de acompanhamento
de 50%, sem classificação legal.

A participação pública na expansão usa `100 × (públicaAtual - pública2025) ÷
(totalAtual - total2025)`. A rede pública corresponde à soma federal,
estadual e municipal. Denominador nulo ou negativo torna a razão não
aplicável; expansão pública negativa e participação acima de 100% são
preservadas quando a expansão total é positiva. O total público da base pode
ser zero: se o total geral crescer após 2025, a participação pública da
expansão continua calculável normalmente.

A expansão dos cursos subsequentes usa `100 × (atual - base2025) ÷ base2025`;
a referência absoluta é `base2025 × 1,60`. Base zero é não aplicável. Nenhuma
das duas fórmulas desloca a base para 2015 ou para o primeiro ano disponível.

Os valores do Rio Grande do Sul são calculados a partir dos totais estaduais
dos numeradores e denominadores. Percentuais municipais não são somados nem
submetidos a média simples. Como a fonte mais recente é 2025, as duas
expansões usam `no_post_baseline_observation`. Elas aparecem como registros
públicos `unavailable`, sem valor, distância, status, classificação ou
projeção, até chegar uma observação posterior comparável.
