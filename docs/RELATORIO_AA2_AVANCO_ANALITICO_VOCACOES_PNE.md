# Relatório AA2 — avanço analítico Vocações × PNE

**Classificação:** `DATA_LOGIC`
**Estágio:** AA2 — pré-registro e laboratório analítico
**Data de referência da execução:** 30 de agosto de 2026
**Município de leitura:** Nova Santa Rita (`4313375`)
**Região:** Vale do Sinos, dez municípios canônicos

## 1. Conclusão do estágio

O AA2 está rematerializado e validado após a reconciliação técnica da primeira revisão
Opus; falta somente a reauditoria limitada prevista no gate do programa. As oito
perguntas pré-registradas produziram um
estado terminal, efeito, intervalo ou limite, robustez, teto de afirmação e comparação
entre RS, Vale e Nova Santa Rita. Resultados negativos, insuficientes e escopos
indisponíveis foram preservados.

O pacote não sustenta uma narrativa simples de “uma variável explica a outra”. Ele
entrega algo mais útil para o produto:

- uma comparação de contexto em que Nova Santa Rita tem resíduo positivo, mas não é
  sinalizada por uma banda ampla — o que não demonstra tipicidade;
- uma decomposição exata mostrando demografia e relação territorial agindo em sentidos
  opostos;
- uma lacuna observada de EPT local combinada a um espaço regional de correspondência
  ocupacional;
- sinais de escolaridade adulta/EJA e ruralidade que merecem acompanhamento; no caso
  rural, o p exato bruto é `0,039`, mas o BH familiar conservador é `0,117`;
- uma tensão em financiamento: a formulação por gasto por matrícula é positiva, mas
  tem construção de denominador e escala confundidas, enquanto o modelo principal
  ajustado pela escala é nulo e 2024 não possui cobertura suficiente. A alternativa
  está bloqueada para promoção isolada.

Nenhum desses resultados autoriza causalidade automática.

## 2. Desenho congelado antes dos resultados

O pré-registro contém exatamente oito perguntas e foi congelado antes da leitura de
`raw_value`:

1. `P1_CONTEXT_ADJUSTED_TRAJECTORY`;
2. `P2_DEMOGRAPHY_ENROLLMENT_DECOMPOSITION`;
3. `P3_SCHOOL_CONDITIONS_AND_TRAJECTORY`;
4. `P4_YOUTH_WORK_AND_HIGH_SCHOOL`;
5. `P5_OCCUPATIONS_AND_EPT`;
6. `P6_ADULT_SCHOOLING_WORK_AND_EJA`;
7. `P7_RURALITY_INCLUSION_AND_ACCESS`;
8. `P8_FINANCING_OFFER_AND_CAPACITY`.

O arquivo do pré-registro tem SHA-256
`aa931e75a8530bf0f9c22c48b937ef0b92b40210240da012bdb33ed16ff24a25`.
O registro externo de congelamento tem SHA-256
`31a7e733b554f6230863e6cf3efbfa0f4e5389ecdc3a0b2ec359d914714e2c13`
e estado `FROZEN_PRE_RESULT`. O probe sem coeficientes, com 27 seletores, zero
falha e sem leitura de valores, permaneceu no hash
`070911de9c63c324318679e9cd91e7c065965ad1e934f3d518ad7ce219f3625c`.

O gate de execução valida esses três artefatos, o contrato, o painel AA1, a ponte
curso–CBO e o digest de `public/data` antes de permitir a leitura analítica.

## 3. Resultados das oito perguntas

| Pergunta | Estado terminal | Resultado principal | Leitura permitida |
| --- | --- | --- | --- |
| P1 — trajetória ajustada | `CONTEXT_COMPARISON_COMPLETE` | resíduo de Nova Santa Rita `+0,95 p.p.`; banda conformal `±3,10 p.p.`; RMSE completo `1,722` versus baseline `1,716` | o resultado não foi sinalizado pela banda ampla; isso não é evidência de tipicidade nem de explicação contextual |
| P2 — demografia e matrículas | `ACCOUNTING_DECOMPOSITION_COMPLETE` | Nova Santa Rita: `-41,45` pelo componente populacional e `+58,45` pelo componente da relação territorial; variação total `+17` | demografia e organização territorial atuaram em sentidos opostos; identidade contábil, não causalidade |
| P3 — adequação docente e trajetória | `NO_ROBUST_ASSOCIATION` | efeito principal `+0,10 p.p.` de abandono por `+10 p.p.` de adequação; IC95% `[-0,12; 0,32]`; BH `0,654` | não há associação robusta no desenho pré-registrado |
| P4 — trabalho juvenil e abandono | `NO_ROBUST_ASSOCIATION` | efeito principal `+0,02 p.p.` por vínculo/100 residentes; IC95% `[-0,27; 0,31]`; BH `0,889` | as especificações não foram estáveis; com dez municípios, não rejeição não prova ausência |
| P5 — ocupações e EPT | `DISTRIBUTIONAL_PATTERN_COMPLETE` | Vale: limite local `19,91%`, acesso regional `50,06%`; cobertura mapeada `90,81%` | correspondência normativa observada, não demanda, empregabilidade ou suficiência |
| P6 — escolaridade adulta, EJA e trabalho | `NO_ROBUST_ASSOCIATION` | escolaridade adulta × EJA: Spearman `-0,636`, p bruto `0,053`, BH `0,214`, bootstrap `[-0,958; 0,126]` | magnitude descritiva relevante, mas instável após multiplicidade e reamostragem |
| P7 — ruralidade e AEE | `NO_ROBUST_ASSOCIATION` | rural: elasticidade `0,693`, intervalo aproximado não primário `[0,275; 1,111]`, p exato bruto `0,039`, BH `0,117` | direção e leave-one-out são estáveis, mas o sinal não é significativo após o ajuste familiar conservador pré-registrado; não se afirma ausência |
| P8 — financiamento e tempo integral | `INSUFFICIENT_DATA` | principal 2025: `+0,009 p.p.` por 10% de MDE, IC95% `[-0,462; 0,480]`; alternativa por matrícula `+0,434 p.p.`, BH `0,0014` | 2024 tem somente 11 casos; a alternativa compartilha matrículas na construção e captura escala, ficando bloqueada para promoção independente |

### 3.1 Trajetória ajustada ao contexto

O modelo de cinco folds reteve 496 municípios, incluindo Nova Santa Rita. A cobertura
empírica da banda foi `95,15%`. O RMSE do modelo completo foi `1,722`, contra `1,716`
no modelo sem adequação docente contemporânea, dentro do limite pré-registrado de
`1,05 ×` o baseline. Os três ajustes deram resíduo positivo para o município, mas o
valor principal `+0,946 p.p.` permaneceu dentro da banda `[-3,097; +3,097]`.

O modelo completo não trouxe ganho incremental fora da amostra: seu RMSE foi maior em
`0,0059` que o baseline. O resíduo equivale a cerca de `30,5%` da semilargura da banda,
e os três ajustes têm sinal positivo. Assim, a leitura permitida é estrita: Nova Santa
Rita não ultrapassou uma banda ampla; isso não demonstra que o município seja típico,
que os fatores contextuais expliquem o resultado ou que o abandono observado seja
pequeno.

A cobertura de origem é estadual, mas a amostra válida não representa todos os 497
municípios. Essa perda de um caso fica explícita no claim técnico.

### 3.2 Demografia, coorte e organização territorial

Entre 2018 e 2025:

- Nova Santa Rita ganhou 17 matrículas de Ensino Médio: o componente populacional foi
  `-41,45`, enquanto o componente da relação entre população residente e matrícula por
  local da escola foi `+58,45`;
- o Vale perdeu 2.339 matrículas: `-5.544,38` no componente populacional, compensado em
  parte por `+3.205,38` na relação territorial;
- o RS perdeu 25.925 matrículas: `-61.558,74` no componente populacional, compensado em
  parte por `+35.633,74` na relação territorial.

Na janela 2022–2025, Nova Santa Rita perde 51 matrículas, quase integralmente no
componente populacional (`-50,95`). Isso mostra que a leitura muda conforme a janela e
por que a página deve separar tendência longa de movimento recente.

A razão usada na identidade combina matrícula por local da escola e população
residente. Ela é contexto ecológico e não mede cobertura, frequência ou trajetória das
mesmas pessoas.

A população de 15 a 17 anos vem de `public.populacao_idade.pop_estimada`, materializada
em `population_context.csv.gz`, com 497 municípios anuais entre 2018 e 2025. O snapshot
local não preserva a vintage estatística por ano nem permite identificar uma
sensibilidade ao rebase do Censo 2022. Por isso, o “componente da relação territorial”
é tratado como resíduo exato da identidade: ele também pode absorver revisões da série,
mobilidade, cobertura e organização territorial, nunca um efeito comportamental puro.

### 3.3 Educação e trabalho juvenil

O painel estadual não encontrou associação robusta entre mudança da adequação docente
e abandono/reprovação. No Vale, a intensidade de vínculos formais de 15 a 17 anos e o
abandono também não passou pelos critérios combinados. Os sinais mudaram entre
defasagens e sensibilidades; o lead placebo teve magnitude maior que o ajuste principal
na pergunta de trabalho juvenil.

O painel populacional P2 tem os 497 municípios em cada ano. Já P3 requer casos
completos simultâneos de abandono e adequação docente nos oito anos. São Pedro da Serra
(`4319356`) tem adequação docente `SOURCE_VALUE_MISSING` em 2018–2025 e, por isso, P3
usa `G=496` e `N=3.968`; não há divergência de identidade ou universo estadual.

Esses resultados são negativos no sentido estatístico do gate, não evidência de que
condições docentes ou trabalho juvenil sejam irrelevantes. Confundimento variável no
tempo, lentes territoriais diferentes e baixa potência regional continuam plausíveis.

### 3.4 Transformação econômica e EPT

A ponte normativa reconciliou exatamente com os totais municipais de EPT do painel.
Foram 113 unidades de oferta deduplicadas, 99 com correspondência mapeada; 12.664 de
13.945 matrículas técnicas ficaram mapeadas (`90,81%`).

O mapeamento usa subgrupos CBO de dois dígitos. Essa granularidade é um teto de
correspondência e não sustenta inferência ocupacional fina; a ponte congelada não
permite uma sensibilidade equivalente a quatro dígitos.

No Vale, `19,91%` dos vínculos formais estão em subgrupos conectados a algum curso
observado no próprio município. Admitindo acesso à oferta observada em qualquer
município do Vale, o limite chega a `50,06%`.

Nova Santa Rita tem zero observado de matrícula técnica em 2025. Por isso, a parcela
conectada à oferta local é `0%`, enquanto `46,49%` de seus vínculos pertencem a grupos
ocupacionais conectados à oferta observada em algum ponto do Vale. Essa diferença é
uma base forte para uma agenda regional de acesso; não prova demanda individual nem
recomenda automaticamente abrir um curso específico.

### 3.5 Escolaridade adulta, EJA e trabalho

Nova Santa Rita tinha `50,29%` da população adulta com Ensino Médio completo em 2022,
próximo à mediana do Vale (`51,73%`) e acima da mediana municipal do RS (`37,72%`). A
intensidade de EJA foi `17,75` matrículas por mil adultos, acima da mediana do Vale
(`10,19`).

A correlação entre maior conclusão adulta e intensidade de EJA foi negativa e de
magnitude alta (`rho=-0,636`), coerente com uma hipótese de oferta mais intensa onde o
déficit acumulado é maior. Porém, o intervalo bootstrap inclui zero e o p-valor ajustado
é `0,214`; portanto, o AA2 retém isso como sinal para monitoramento e aprofundamento,
não como relação robusta ou causal.

### 3.6 Ruralidade, inclusão e financiamento

Nova Santa Rita registrou 773 matrículas rurais e seis escolas rurais em 2025, contra
medianas regionais de 190,5 e 2,5. O componente rural apresentou magnitude e direção
estáveis nas três especificações e leave-one-out, com p exato bruto `0,039`. O BH
principal ficou em `0,117`, acima do alfa pré-registrado de `0,10`. O intervalo normal
é aproximado e não primário; a inferência principal é o teste exato de sinais com dez
municípios. A formulação correta é “não significativo após o ajuste familiar
conservador pré-registrado”, não “ausência de relação”. A relação AEE–unidades
ofertantes não foi robusta.

No financiamento, a parcela de matrículas em tempo integral de Nova Santa Rita foi
`23,12%`, próxima da mediana do Vale (`23,67%`) e acima da mediana municipal do RS
(`21,34%`). O MDE nominal por matrícula foi R$ 6.808, contra R$ 5.090 no Vale e
R$ 10.558 no RS. O ajuste principal por escala foi nulo; a alternativa por gasto por
matrícula foi positiva, mas não prevalece sobre a falta de cobertura de 2024 e a
divergência entre especificações. Financiamento e oferta são simultâneos e endógenos.
Além disso, matrículas participam do denominador da alternativa e da construção do
desfecho, gerando confusão mecânica com escala. O resultado alternativo está marcado
`BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT`; valores nominais não
podem ser comparados entre anos.

## 4. Métodos e fórmulas preservados

- Educação usa exclusivamente `total_all_dependencies`.
- Identidade municipal usa código IBGE textual com sete dígitos; nenhum join por nome
  ou conversão numérica foi realizado.
- Mudança contextual do P1 usa `log1p(fim) - log1p(início)` e predição OLS fora da
  amostra com folds derivados do SHA-256 do código textual.
- P2 usa decomposição Shapley simétrica de `M = P × R`, com fechamento relativo
  `|resíduo| ≤ 1e-9 × max(1, |ΔM|)`.
- P3, P4 e P7 usam efeitos fixos de município e ano. P4/P7 enumeram exatamente os
  `2^G` vetores de sinais Rademacher para `G=9` ou `10`.
- P6 usa 99.999 permutações PCG64, p bilateral `(k+1)/(B+1)` e 10.000 reamostragens
  bootstrap descritivas.
- P8 usa OLS cross-sectional com HC3; o efeito de 10% é o coeficiente em log
  multiplicado exatamente por `ln(1,1)`.
- BH é aplicado com denominador fixo por família. Um fit inválido ocupa internamente o
  slot com `p=1`, mas permanece com p bruto e ajustado nulos no artefato.
- Zero observado, `null`, indisponível, suprimido, não aplicável e ausência de linha
  continuam distintos. Denominador não positivo gera indisponível, nunca zero.
- Cada ajuste serializa `N`, contagem de clusters quando aplicável e primazia do
  intervalo. Em P4/P7, o intervalo aproximado é não primário e o p exato é primário.
- Mínimo efeito detectável não foi pré-registrado e não foi calculado pós-hoc; os
  resultados regionais negativos carregam `LOW_POWER_NO_ABSENCE_CLAIM`.
- As 5.574 linhas de heterogeneidade têm teto `EXPLORATORY_NO_INFERENCE` e promoção
  `BLOCKED_FROM_MANAGER_FACING`.
- Nenhuma fórmula, fonte ou metodologia dos dados publicados foi alterada.

## 5. Validação e reprodutibilidade

O pacote contém:

- 49 linhas de resultados;
- 86 linhas de robustez;
- 5.574 linhas de heterogeneidade;
- 51 comparações de escopo, em 17 medidas com a tríade RS–Vale–Nova Santa Rita;
- 27 slots pré-registrados de p-valor, 26 ajustes válidos e um fit insuficiente;
- 26 controles QA, todos aprovados.

As cinco famílias BH foram recomputadas de forma independente. As 18 linhas da
decomposição fecharam dentro da tolerância; o maior resíduo absoluto foi
`3,64e-11`. A ponte EPT reconciliou com diferença máxima zero.

Duas materializações em processos de sistema operacional distintos, com
`PYTHONHASHSEED=101` e `202`, produziram o mesmo conjunto. O digest canônico dos seis
artefatos analíticos não-manifesto é
`b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879`.

Os manifestos candidatos registram seeds operacionais diferentes por desenho. O
manifesto final normaliza `101` e `202` numa evidência comum e declara explicitamente
que igualdade byte a byte dos manifestos candidatos não é o objeto do teste.

O notebook
`docs/notebooks/AA2_AVANCO_ANALITICO_VOCACOES_PNE.ipynb` foi validado como JSON e seus
code cells foram executados sequencialmente, no mesmo namespace, do início ao fim. O
runtime congelado não possui `nbformat`, `nbclient` ou Jupyter; por isso não houve
execução via `nbconvert` nem gravação automática de outputs no arquivo. O comando de
validação alternativo terminou com `NOTEBOOK_TOP_TO_BOTTOM_OK`.

O notebook é acompanhante de auditoria, não fonte nem artefato autoritativo. A prova
determinística e os valores canônicos permanecem nos seis arquivos do pacote
transacional.

### Testes e gates executados

- `python -m pytest -q data_pipeline/tests/test_vocacoes_pne_advanced_analysis.py`:
  `10 passed in 18.17s`, incluindo guardas literais no relatório;
- runner AA2 `--check`: aprovado, oito perguntas;
- notebook: JSON válido e execução top-to-bottom aprovada;
- baseline AA0 com allowlist AA2: havia passado antes da interferência concorrente;
  a execução final falhou fechada somente pela aparição posterior de
  `scripts/generate-regioes.mjs` e `scripts/lib/regional-panorama.mjs`, fora das 18
  regras AA2. O verificador não reportou drift nas 243 entradas protegidas; os dois
  paths não foram absorvidos silenciosamente pela allowlist;
- `npm run check:fast`: typecheck, lint, compilador narrativo e build app-only
  aprovados;
- `git diff --check`: aprovado; apenas avisos preexistentes de LF/CRLF;
- primeira revisão Opus AA2: `AT_RISK`, sem erro computacional detectado;
- reconciliação: guardas de interpretação, promoção, proveniência e testes aplicadas;
- reauditoria Opus limitada: `ON_TRACK`, confiança `0,80`, SHA-256
  `74585729780496bd4c20f5b0d12d50b4243f268539a167538db8a8093af28e54`.

O build app-only emitiu apenas avisos de tamanho de chunk e timing de plugins, sem
falha. Nenhum aviso foi tratado como erro metodológico.

## 6. Fontes

- painel analítico AA1:
  `.tmp/vocacoes-pne/advanced-analytics-v1/aa1/PAINEL_ANALITICO_ESTADUAL_AA1.csv.gz`,
  SHA-256 `d6cadfec911863b93699b826da6ef340687db5c0f77350319a9eeefa0dfb652f`;
- gate AA1:
  `.tmp/vocacoes-pne/advanced-analytics-v1/aa1/AA2_ENTRY_GATE_AA1.json`,
  SHA-256 `8baef0754bd6e7b5caa5428e9cf16d8ae3c01d3eace4de68d24d1e42ba286f02`;
- ponte normativa curso–CBO:
  `.tmp/vocacoes-pne/v7-job2/2d/cursos_cbo_2025.csv.gz`,
  SHA-256 `cf60bb4cb49bbe15a35af728b83783418e67fc76c215838521ef14992047f867`;
- configurações canônicas de município, estado e região no repositório;
- referências oficiais preservadas no inventário AA1 e nos artefatos de origem dos
  Jobs V7 já congelados.

Não houve acesso a banco, aquisição de dados por rede nem atualização de fonte. A rede
e o SQLite ficaram bloqueados em runtime. A revisão Opus usa rede somente para a
auditoria independente autorizada pelo usuário e não participa do cálculo.

## 7. Arquivos do AA2

Criados ou alterados neste estágio:

- `data_pipeline/contracts/vocacoes-pne-advanced-analysis-v1.json`;
- `data_pipeline/contracts/vocacoes-pne-aa2-preregistration-freeze.json`;
- `data_pipeline/contracts/vocacoes-pne-aa2-allowlist.json`;
- `data_pipeline/src/vocacoes_pne_advanced_analysis.py`;
- `data_pipeline/scripts/run_vocacoes_pne_advanced_analysis.py`;
- `data_pipeline/tests/test_vocacoes_pne_advanced_analysis.py`;
- `docs/PRE_REGISTRO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.json`;
- `docs/notebooks/AA2_AVANCO_ANALITICO_VOCACOES_PNE.ipynb`;
- este relatório;
- `docs/REGISTRO_HISTORICO_PRE_REGISTRO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.md`;
- `docs/REVISAO_OPUS_AA2_AVANCO_ANALITICO_VOCACOES_PNE.md`, registro canônico da
  reconciliação;
- `docs/RECIBO_DOCUMENTAL_AA2_AVANCO_ANALITICO_VOCACOES_PNE.json`, com os hashes dos
  três documentos de auditoria;
- pacote local `.tmp/vocacoes-pne/advanced-analytics-v1/aa2/`.

Nenhum arquivo foi removido ou movido pelo AA2. O worktree já continha um conjunto
amplo de alterações e artefatos de etapas anteriores; eles foram preservados.

## 8. Efeito sobre dados públicos e pendências

`public/data` permaneceu inalterado no digest
`4a52e3891163cb3427c5c01f2ef5414c5fe7855dd491a9a125b509899dcc23e1`.
Não houve publicação pública, banco, refresh de fonte ou build completo. O build
executado foi somente `build:app`, como parte de `check:fast`.

O gate analítico AA2 está fechado e a reauditoria Opus autorizou a entrada no AA3. A
única pendência operacional é repetir o verificador AA0 quando os dois paths
concorrentes fora do escopo deixarem de interferir; eles não serão adicionados à
allowlist AA2. Essa condição não altera o pacote, os números ou a autorização analítica
para iniciar o próximo estágio.
