# Dossiê — Vocações da Região × PNE: o caso completo do Vale do Sinos

Data: 2026-08-27 · Plataforma: Painel SESI de Educação (RS) · Contrato público: `vocacoes-regiao-2.9.0`
Finalidade deste documento: registrar, num único lugar, (1) o pedido da gestão que originou
esta frente, (2) todas as relações calculadas e apresentadas para a região piloto (Vale do
Sinos, 10 municípios), (3) o inventário de variáveis usadas e disponíveis na plataforma
(Vocações e PNE), e (4) as limitações e questões abertas — para submeter a uma consultoria
externa (ChatGPT Pro) com as perguntas da seção 6: que fontes, dados ou caminhos
metodológicos podem enriquecer a análise e aproximá-la do objetivo pedido pela gestão.

---

## 1. O pedido da gestão (origem de tudo)

A gestora pediu (2026-08-26) **relações explícitas entre os dados educacionais (PNE) e os
dados territoriais (Vocações)**, em dois sentidos, com camada temporal:

1. **Saída 1 — O que o território ajuda a explicar sobre a educação?** (PNE → Vocações)
   Partir de um resultado educacional (queda de matrículas no ensino médio, distorção
   idade-série, baixa conclusão, redução da população em idade escolar, permanência) e
   buscar no território variáveis que ajudem a compreendê-lo (evolução populacional,
   migração de jovens, renda, emprego formal, setores predominantes, expansão/retração,
   perfil etário, mercado de trabalho).
   **Regra de ouro da própria gestão:** a plataforma **não afirma que uma variável causou a
   outra** — aponta *fatores associados e hipóteses explicativas, mostrando os dados que
   sustentam essa leitura*.
2. **Saída 2 — O que o futuro do território exige da educação?** (Vocações → PNE)
   Partir das tendências do território (setores que crescem/retraem, mudanças
   demográficas, novas ocupações, transformação tecnológica, perfil de emprego e renda,
   cenários futuros) e perguntar quais questões educacionais precisam entrar na agenda de
   planejamento — escolaridade, ensino médio, EJA, educação profissional, aprendizagem,
   abandono/permanência, metas e estratégias do PNE.
3. **Camada temporal** dentro das duas saídas: com ~20 anos de dado, mostrar se
   determinadas transformações **ocorreram simultaneamente** (demografia × matrículas;
   emprego/renda × permanência; setores × trajetórias formativas).

O contexto que motivou o pedido: a plataforma anterior "apresentava os dados e declarava
que não tinha como trazer relação", o que não fazia sentido para o usuário.

## 2. Como a plataforma responde hoje (método e apresentação)

A resposta foi construída em camadas, todas determinísticas e verificadas em cadeia
(pesquisa → gerador → plataforma, fail-closed; toda frase pública nasce de template
fechado e é reconstruída byte a byte por quem publica):

- **Estatística associativa descritiva (grau E1)** por relação: correlação de Pearson e
  Spearman sobre as **variações anuais** das duas séries (nunca sobre os níveis), com
  força qualificada por faixas fechadas (fraca/moderada/forte); concordância de direção
  ("em X dos N anos as duas variaram no mesmo sentido"); co-movimento por janela idêntica
  (pontas e delta lado a lado); contraste estadual (posição da região na distribuição das
  10); defasagem declarada onde a estrutura define (nascimentos → matrículas k anos
  depois). Sem p-valor: a camada é descritiva, sem inferência.
- **Curadoria por força**: cada leitura é classificada `lead` (força moderada/forte, ou
  estrutural com defasagem declarada) ou `note` (fraca). Só as `lead` viram cartões; as
  `note` permanecem publicadas nos dados com o critério declarado na página. Cada região
  tem o seu próprio conjunto (teto de 8 relações de triagem automática por região, piso
  |r| ≥ 0,6, mínimo 8 intervalos, lista de exclusão declarada).
- **Relações contábeis (grau E2)**: decomposição exata da matrícula
  (matrícula = coorte de nascimentos defasada × taxa de atendimento aparente; Bennet
  simétrico, sem resíduo) por etapa, e shift-share do emprego formal (ritmo do estado ×
  composição setorial × dinâmica própria). Aqui — e só aqui — a palavra "explica" é
  permitida, porque a decomposição é aritmética, não inferência. Se a conta não fecha no
  rebuild, a relação rebaixa a E1 com ausência declarada.
- **Escada de evidência visível (E1–E5)**: a página declara o grau de cada leitura; E3
  (precedência temporal), E4 (painel) e E5 (quase-experimento) existem como degraus
  nomeados, ainda não publicados — retidos até decisão da gestão sobre graduar a regra
  de ouro ("a plataforma afirma o que o grau de evidência sustenta, com o grau
  declarado").
- **Âncora no PNE**: cada relação publicada aponta os temas do novo PNE que toca
  (tabela fechada série ↔ tema), no mesmo vocabulário da matriz municipal.
- **Pergunta 2 (cenários)**: quatro cenários por região (3 exploratórios + 1 normativo,
  horizonte 2031), publicados hoje em 2 das 10 regiões (Vale do Rio Pardo e Noroeste),
  com camada municipal; as demais regiões declaram a ausência. O Vale do Sinos abre o
  próximo lote.
- **Apresentação (redesenho de 2026-08-27)**: hero com 4 números-síntese, escada de
  evidência, cartões compactos por relação (título-história, uma frase de leitura,
  minigráficos pareados, encodings de força/concordância/contraste), análise completa
  (hipóteses, método, "o que não se conclui") sob demanda, triagem em lista, retrato de
  71 séries como camada de consulta. A página caiu de ~20.300px para ~6.965px sem perder
  nenhuma frase de guarda (1.442 conferidas byte a byte).
- **Guardas de linguagem**: corpus adversarial bilateral; linguagem causal bloqueada fora
  do template do grau declarado; prévia sempre rotulada; nenhum número futuro fora dos
  cenários; taxa nunca somada; classe de evidência declarada por série e por ponto.

## 3. Todas as relações calculadas e apresentadas — Vale do Sinos

Universo desta seção: documento público `vale-do-sinos.json` (contrato 2.9.0,
2026-08-27). São **18 leituras `lead`** (1 estrutural + 5 associações curadas + 4 pares
temporais curados + 8 relações de triagem automática), **8 leituras `note`** computadas e
mantidas fora da página, **4 relações contábeis E2** e **15 conclusões** publicadas.

### 3.1 Leituras `lead` (publicadas como cartões, na ordem editorial da página)

**1. [estrutural — defasagem declarada] O que nasce hoje chega à escola 6 anos depois**
- Séries: Nascidos vivos por residência da mãe → Matrículas no ensino fundamental (defasagem k=6 anos)
- Concordância defasada: 4 de 11 anos; correlação defasada: Pearson -0,18 — fraca e negativa
- Frase publicada: "Com defasagem de 6 anos — a coorte nascida em um ano atinge a idade de ingresso no ensino fundamental seis anos depois —, em 4 dos 11 intervalos anuais Nascidos vivos por residência da mãe (2008 a 2019) e Matrículas no ensino fundamental (2014 a 2025) variaram no mesmo sentido; a correlação das variações anuais nessa defasagem é de -0,18."
- Temas do PNE: Conclusão do ensino fundamental na idade certa

**2. [triagem automática] Vínculos formais de pessoas com ensino médio completo × Matrículas na educação profissional**
- Janela 2014–2025 · Correlação: Pearson -0,72 / Spearman -0,85 — forte e negativa (11 intervalos)
- Concordância: 5 de 11 anos no mesmo sentido (6 opostos, 0 empates) · Co-movimento: 101156 → 125039 (Δ 23883 no nível) × 12783 → 15071 (Δ 2288 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Educação profissional e técnica

**3. [triagem automática] População estimada × Matrículas no ensino fundamental**
- Janela 2014–2025 · Correlação: Pearson -0,71 / Spearman -0,7 — forte e negativa (11 intervalos)
- Concordância: 3 de 11 anos no mesmo sentido (8 opostos, 0 empates) · Co-movimento: 900216 → 911305 (Δ 11089 no nível) × 117469 → 104328 (Δ -13141 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Conclusão do ensino fundamental na idade certa

**4. [par temporal curado] O emprego na indústria caiu, a matrícula técnica cresceu**
- Séries: Vínculos formais na indústria × Matrículas na educação profissional técnica · Janela 2014–2025
- Correlação: Pearson -0,71 / Spearman -0,65 — forte e negativa (11 intervalos)
- Concordância: 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)
- Co-movimento: 94355 → 89541 (Δ -4814 no nível) × 12774 → 13945 (Δ 1171 no nível)
- Contraste estadual: 3ª de 10 em alta (4 regiões na mesma direção; variacao_percentual 9,2)
- Temas do PNE: Educação profissional e técnica
- O que NÃO se conclui: "Não se pode concluir que a expansão ou a retração da indústria mostra o rumo que a oferta técnica seguiu."

**5. [triagem automática] Vínculos formais de pessoas com ensino médio completo × Matrículas na educação profissional técnica**
- Janela 2014–2025 · Correlação: Pearson -0,7 / Spearman -0,74 — forte e negativa (11 intervalos)
- Concordância: 4 de 11 anos no mesmo sentido (7 opostos, 0 empates) · Co-movimento: 101156 → 125039 (Δ 23883 no nível) × 12774 → 13945 (Δ 1171 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Educação profissional e técnica

**6. [triagem automática] Famílias inscritas no cadastro social, posição de dezembro × Matrículas no ensino fundamental**
- Janela 2014–2025 · Correlação: Pearson 0,69 / Spearman 0,73 — moderada e positiva (11 intervalos)
- Concordância: 6 de 11 anos no mesmo sentido (5 opostos, 0 empates) · Co-movimento: 94257 → 121405 (Δ 27148 no nível) × 117469 → 104328 (Δ -13141 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Conclusão do ensino fundamental na idade certa

**7. [associação curada] A fatia de vínculos com ensino médio completo cresceu, a matrícula no ensino médio caiu**
- Resultado educacional: Matrículas no ensino médio · Fator territorial: Vínculos formais de pessoas com ensino médio completo por cem vínculos formais · Janela 2014–2025
- Correlação: Pearson 0,68 / Spearman 0,69 — moderada e positiva (11 intervalos)
- Concordância: 6 de 11 anos no mesmo sentido (5 opostos, 0 empates)
- Co-movimento (resultado × fator): 31789 → 26911 (Δ -4878 no nível) × 39,18 → 46,29 (7,11 pontos)
- Contraste estadual: 9ª de 10 em queda (10 regiões na mesma direção; variacao_percentual -15,3)
- Temas do PNE: Universalização e permanência no ensino médio
- Hipóteses (a verificar com dado local): Hipótese a verificar com dado local: a rede de ensino médio convive com um contingente de profissionais do ensino de porte próprio a cada região. | Hipótese a verificar com dado local: o vínculo formal dos profissionais do ensino cobre só parte da força de trabalho da educação, e não mede a rede inteira.
- O que se pode ler: "A leitura permitida é de coexistência entre a matrícula de ensino médio e o emprego formal dos profissionais do ensino da região na mesma janela."
- O que NÃO se conclui: "Não se pode concluir que o número de profissionais do ensino da região determinou a matrícula no ensino médio."

**8. [triagem automática] Vínculos formais na indústria × Matrículas na educação profissional**
- Janela 2014–2025 · Correlação: Pearson -0,67 / Spearman -0,57 — moderada e negativa (11 intervalos)
- Concordância: 4 de 11 anos no mesmo sentido (7 opostos, 0 empates) · Co-movimento: 94355 → 89541 (Δ -4814 no nível) × 12783 → 15071 (Δ 2288 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Educação profissional e técnica

**9. [triagem automática] Vínculos formais ativos × Matrículas na educação profissional técnica**
- Janela 2014–2025 · Correlação: Pearson -0,67 / Spearman -0,52 — moderada e negativa (11 intervalos)
- Concordância: 6 de 11 anos no mesmo sentido (5 opostos, 0 empates) · Co-movimento: 258193 → 270110 (Δ 11917 no nível) × 12774 → 13945 (Δ 1171 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Educação profissional e técnica

**10. [triagem automática] Vínculos formais com grau de instrução declarado × Matrículas na educação profissional técnica**
- Janela 2014–2025 · Correlação: Pearson -0,67 / Spearman -0,52 — moderada e negativa (11 intervalos)
- Concordância: 6 de 11 anos no mesmo sentido (5 opostos, 0 empates) · Co-movimento: 258193 → 270110 (Δ 11917 no nível) × 12774 → 13945 (Δ 1171 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Educação profissional e técnica

**11. [triagem automática] População de 0 a 14 anos × Matrículas no ensino médio**
- Janela 2014–2025 · Correlação: Pearson -0,67 / Spearman -0,67 — moderada e negativa (11 intervalos)
- Concordância: 6 de 11 anos no mesmo sentido (5 opostos, 0 empates) · Co-movimento: 186845 → 165142 (Δ -21703 no nível) × 31789 → 26911 (Δ -4878 no nível)
- Origem: "Relação observada por triagem estatística entre as séries da região; não integra a curadoria e não traz hipóteses."
- Temas do PNE: Universalização e permanência no ensino médio

**12. [par temporal curado] O PIB de serviços caiu, a matrícula na EJA cresceu**
- Séries: Produto interno bruto dos serviços a preços de 2023 × Matrículas na educação de jovens e adultos · Janela 2014–2021
- Correlação: Pearson 0,66 / Spearman 0,75 — moderada e positiva (7 intervalos)
- Concordância: 4 de 7 anos no mesmo sentido (3 opostos, 0 empates)
- Co-movimento: 21859942,88 → 19274125,77 (Δ -2585817,11 no nível) × 8835 → 14651 (Δ 5816 no nível)
- Contraste estadual: 1ª de 10 em alta (1 regiões na mesma direção; variacao_percentual 65,8)
- Temas do PNE: Educação de jovens e adultos
- O que NÃO se conclui: "Não se pode concluir que a evolução do setor de serviços mostra o rumo da educação de jovens e adultos."

**13. [associação curada] As pessoas no perfil de baixa renda caíram, a matrícula na EJA cresceu**
- Resultado educacional: Matrículas na educação de jovens e adultos · Fator territorial: Pessoas inscritas no perfil de baixa renda, posição de dezembro · Janela 2015–2025
- Correlação: Pearson -0,57 / Spearman -0,31 — moderada e negativa (10 intervalos)
- Concordância: 3 de 10 anos no mesmo sentido (7 opostos, 0 empates)
- Co-movimento (resultado × fator): 10399 → 11447 (Δ 1048 no nível) × 76303 → 67072 (Δ -9231 no nível)
- Contraste estadual: 1ª de 10 em alta (1 regiões na mesma direção; variacao_percentual 10,1)
- Temas do PNE: Educação de jovens e adultos
- Hipóteses (a verificar com dado local): Hipótese a verificar com dado local: a procura por conclusão da educação básica convive com o universo inscrito no cadastro social. | Hipótese a verificar com dado local: a oferta de turmas de jovens e adultos depende de decisões de rede, e a matrícula segue a oferta disponível.
- O que se pode ler: "A leitura permitida é de contexto: o cadastro social e a renda do trabalho formal descrevem o território econômico e social onde a educação de jovens e adultos opera, sem medir a demanda por ela."
- O que NÃO se conclui: "Não se pode concluir que o contexto cadastral e a renda do trabalho da região determinaram a matrícula na educação de jovens e adultos."

**14. [associação curada] A população estimada cresceu, as escolas rurais caíram**
- Resultado educacional: Escolas rurais com matrículas na educação básica · Fator territorial: População estimada · Janela 2014–2021
- Correlação: Pearson -0,38 / Spearman -0,46 — moderada e negativa (7 intervalos)
- Concordância: 1 de 7 anos no mesmo sentido (2 opostos, 4 empates)
- Co-movimento (resultado × fator): 30 → 27 (Δ -3 no nível) × 900216 → 913235 (Δ 13019 no nível)
- Contraste estadual: 9ª de 10 em queda (10 regiões na mesma direção; variacao_percentual -10)
- Temas do PNE: Oferta e organização da rede
- Hipóteses (a verificar com dado local): Hipótese a verificar com dado local: a rede rural acompanha a distribuição da população pelo território. | Hipótese a verificar com dado local: fusões e fechamentos de escolas seguem decisões administrativas de cada município, em ritmo próprio.
- O que se pode ler: "A leitura permitida é de coexistência entre a rede escolar rural e o peso da agropecuária no território, na mesma janela."
- O que NÃO se conclui: "Não se pode concluir que o desempenho da agropecuária da região fechou ou abriu escolas rurais."

**15. [par temporal curado] O índice de envelhecimento cresceu, as escolas com matrícula cresceram**
- Séries: Pessoas de 60 anos ou mais por cem pessoas de 0 a 14 anos × Escolas com matrículas na educação básica · Janela 2014–2025
- Correlação: Pearson -0,32 / Spearman -0,27 — moderada e negativa (11 intervalos)
- Concordância: 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)
- Co-movimento: 59,18 → 103,88 (44,7 pontos) × 682 → 693 (Δ 11 no nível)
- Contraste estadual: 3ª de 10 em alta (4 regiões na mesma direção; variacao_percentual 1,6)
- Temas do PNE: Oferta e organização da rede
- O que NÃO se conclui: "Não se pode concluir que o envelhecimento da população mostra o rumo que a rede escolar seguiu."

**16. [associação curada] A fatia de vínculos com ensino médio completo cresceu, a matrícula na EJA cresceu**
- Resultado educacional: Matrículas na educação de jovens e adultos · Fator territorial: Vínculos formais de pessoas com ensino médio completo por cem vínculos formais · Janela 2014–2025
- Correlação: Pearson 0,32 / Spearman 0,13 — moderada e positiva (11 intervalos)
- Concordância: 8 de 11 anos no mesmo sentido (3 opostos, 0 empates)
- Co-movimento (resultado × fator): 8835 → 11447 (Δ 2612 no nível) × 39,18 → 46,29 (7,11 pontos)
- Contraste estadual: 1ª de 10 em alta (1 regiões na mesma direção; variacao_percentual 29,6)
- Temas do PNE: Educação de jovens e adultos
- Hipóteses (a verificar com dado local): Hipótese a verificar com dado local: a procura por conclusão da educação básica acompanha o grau de instrução exigido nos vínculos formais da região. | Hipótese a verificar com dado local: a oferta de turmas de jovens e adultos depende de decisões de rede, e a matrícula segue a oferta disponível.
- O que se pode ler: "A leitura permitida é de coexistência entre a matrícula de jovens e adultos e a composição do emprego formal por grau de instrução, na mesma janela."
- O que NÃO se conclui: "Não se pode concluir que a exigência de escolaridade do mercado formal moveu a matrícula na educação de jovens e adultos."

**17. [par temporal curado] A fatia de vínculos com ensino médio completo cresceu, a matrícula na EJA cresceu**
- Séries: Vínculos formais de pessoas com ensino médio completo por cem vínculos formais × Matrículas na educação de jovens e adultos · Janela 2014–2025
- Correlação: Pearson 0,32 / Spearman 0,13 — moderada e positiva (11 intervalos)
- Concordância: 8 de 11 anos no mesmo sentido (3 opostos, 0 empates)
- Co-movimento: 39,18 → 46,29 (7,11 pontos) × 8835 → 11447 (Δ 2612 no nível)
- Contraste estadual: 1ª de 10 em alta (1 regiões na mesma direção; variacao_percentual 29,6)
- Temas do PNE: Educação de jovens e adultos
- O que NÃO se conclui: "Não se pode concluir que a mudança na composição do emprego formal mostra o que aconteceu com a permanência escolar na região."

**18. [associação curada] O emprego formal cresceu, a matrícula no ensino médio caiu**
- Resultado educacional: Matrículas no ensino médio · Fator territorial: Vínculos formais ativos · Janela 2014–2025
- Correlação: Pearson 0,31 / Spearman 0,08 — moderada e positiva (11 intervalos)
- Concordância: 7 de 11 anos no mesmo sentido (4 opostos, 0 empates)
- Co-movimento (resultado × fator): 31789 → 26911 (Δ -4878 no nível) × 258193 → 270110 (Δ 11917 no nível)
- Contraste estadual: 9ª de 10 em queda (10 regiões na mesma direção; variacao_percentual -15,3)
- Temas do PNE: Universalização e permanência no ensino médio
- Hipóteses (a verificar com dado local): Hipótese a verificar com dado local: territórios com mais renda do trabalho formal convivem com uma rede de ensino médio de porte diferente. | Hipótese a verificar com dado local: a matrícula de ensino médio responde ao tamanho das coortes e a decisões de rede, em direção própria à renda do trabalho.
- O que se pode ler: "A leitura permitida é de coexistência entre a matrícula de ensino médio e a renda do trabalho formal da região — massa salarial e número de vínculos — na mesma janela, com as séries lado a lado."
- O que NÃO se conclui: "Não se pode concluir que a renda do trabalho formal da região determinou a matrícula no ensino médio."

### 3.2 Leituras `note` (computadas e mantidas nos dados, fora da leitura da página)

Critério publicado: "Entram na leitura da região as relações de força moderada ou forte e as relações estruturais com defasagem declarada; as leituras sem essa força permanecem publicadas nos dados da página."
Frase de contagem publicada: "Leituras computadas sem força de publicação nesta região: 8; o cálculo completo permanece publicado nos dados da página."

- **Matrículas na educação profissional técnica × Vínculos formais de pessoas com ensino superior completo** (associação matriculas-na-educacao-profissional-tecnica-e-vinculos-formais-de-pessoas-com-ensino-superior-completo, janela 2014–2025): Pearson 0,14 / Spearman -0,24 — fraca e positiva (11 intervalos); concordância 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)
- **Matrículas na educação profissional técnica × Vínculos formais de pessoas com ensino médio completo por cem vínculos formais** (associação matriculas-na-educacao-profissional-tecnica-e-vinculos-formais-de-pessoas-com-ensino-superior-completo, janela 2014–2025): Pearson -0,29 / Spearman -0,31 — fraca e negativa (11 intervalos); concordância 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)
- **Matrículas no ensino médio × Vínculos formais de profissionais do ensino** (associação matriculas-no-ensino-medio-e-vinculos-formais-de-profissionais-do-ensino, janela 2014–2025): Pearson -0,01 / Spearman 0,01 — fraca e negativa (11 intervalos); concordância 4 de 11 anos no mesmo sentido (7 opostos, 0 empates)
- **Matrículas no ensino médio × Massa salarial de dezembro a preços de 2025** (associação matriculas-no-ensino-medio-e-massa-salarial-de-dezembro-a-precos-de-2025, janela 2014–2025): Pearson 0,11 / Spearman -0,02 — fraca e positiva (11 intervalos); concordância 3 de 11 anos no mesmo sentido (8 opostos, 0 empates)
- **Escolas rurais com matrículas na educação básica × Produto interno bruto da agropecuária a preços de 2023** (associação escolas-rurais-com-matriculas-na-educacao-basica-e-produto-interno-bruto-da-agropecuaria-a-precos-de-2023, janela 2014–2021): Pearson 0,27 / Spearman 0,36 — fraca e positiva (7 intervalos); concordância 3 de 7 anos no mesmo sentido (0 opostos, 4 empates)
- **Matrículas na educação de jovens e adultos × Vínculos formais ativos** (associação matriculas-na-educacao-de-jovens-e-adultos-e-vinculos-formais-de-pessoas-com-ensino-medio-completo-por-cem-vinculos-formais, janela 2014–2025): Pearson -0,16 / Spearman -0,12 — fraca e negativa (11 intervalos); concordância 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)
- **Matrículas na educação de jovens e adultos × Massa salarial de dezembro a preços de 2025** (associação matriculas-na-educacao-de-jovens-e-adultos-e-pessoas-inscritas-no-perfil-de-baixa-renda-posicao-de-dezembro, janela 2015–2025): Pearson -0,08 / Spearman 0,13 — fraca e negativa (10 intervalos); concordância 5 de 10 anos no mesmo sentido (5 opostos, 0 empates)
- **Massa salarial de dezembro a preços de 2025 × Matrículas na educação de jovens e adultos** (par massa-salarial-do-trabalho-formal-e-matriculas-na-educacao-de-jovens-e-adultos, janela 2014–2025): Pearson -0,2 / Spearman -0,1 — fraca e negativa (11 intervalos); concordância 5 de 11 anos no mesmo sentido (6 opostos, 0 empates)

Total de notes: 8 (noteCount publicado: 8).

### 3.3 Relações contábeis — grau E2 (decomposições)

Método (matrícula): "A decomposição é contábil: matrículas = coorte de nascimentos defasada × taxa de atendimento aparente. A taxa de atendimento aparente absorve, sem distinguir, atendimento escolar, fluxo (aprovação, reprovação e abandono), migração e matrícula fora da região de residência; a conta não afirma causa. A coorte soma os nascidos vivos dos anos que correspondem às idades da etapa; anos com registro preliminar não entram na conta."

**Matrícula na educação infantil** (coorte 0–5 anos, janela 2014–2024):
- Termos: matrículas 31194 → 41950; coorte 70909 → 61677; taxa de atendimento aparente 43,99 → 68,02 por cem
- Contribuições: variação total 34,48%; efeito demográfico -16,57 p.p.; efeito taxa 51,06 p.p.
- Frase publicada: "Entre 2014 e 2024, as matrículas na educação infantil da região foram de 31 194 para 41 950 (variação de 34,5%). Na conta decomposta, a coorte de nascimentos correspondente às idades de 0 a 5 anos foi de 70 909 para 61 677 e explica -16,6 pontos percentuais dessa variação; a taxa de atendimento aparente (matrículas por cem pessoas da coorte) foi de 44,0 para 68,0 e explica 51,1 pontos percentuais. Os dois termos somam a variação total; valores exibidos arredondados a uma casa decimal."

**Matrícula no ensino fundamental** (coorte 6–14 anos, janela 2014–2025):
- Termos: matrículas 117469 → 104328; coorte 116648 → 108422; taxa de atendimento aparente 100,7 → 96,22 por cem
- Contribuições: variação total -11,19%; efeito demográfico -6,9 p.p.; efeito taxa -4,29 p.p.
- Frase publicada: "Entre 2014 e 2025, as matrículas no ensino fundamental da região foram de 117 469 para 104 328 (variação de -11,2%). Na conta decomposta, a coorte de nascimentos correspondente às idades de 6 a 14 anos foi de 116 648 para 108 422 e explica -6,9 pontos percentuais dessa variação; a taxa de atendimento aparente (matrículas por cem pessoas da coorte) foi de 100,7 para 96,2 e explica -4,3 pontos percentuais. Os dois termos somam a variação total; valores exibidos arredondados a uma casa decimal."

**Matrícula no ensino médio** (coorte 15–17 anos, janela 2014–2025):
- Termos: matrículas 31789 → 26911; coorte 46217 → 34238; taxa de atendimento aparente 68,78 → 78,6 por cem
- Contribuições: variação total -15,34%; efeito demográfico -27,77 p.p.; efeito taxa 12,42 p.p.
- Frase publicada: "Entre 2014 e 2025, as matrículas no ensino médio da região foram de 31 789 para 26 911 (variação de -15,3%). Na conta decomposta, a coorte de nascimentos correspondente às idades de 15 a 17 anos foi de 46 217 para 34 238 e explica -27,8 pontos percentuais dessa variação; a taxa de atendimento aparente (matrículas por cem pessoas da coorte) foi de 68,8 para 78,6 e explica 12,4 pontos percentuais. Os dois termos somam a variação total; valores exibidos arredondados a uma casa decimal."

**Emprego formal (shift-share, janela 2006–2025)** — fonte Relação Anual de Informações Sociais:
- Totais região: 209013 → 270110 vínculos; estado: 2320741 → 3366473
- Contribuições: variação total 29,23%; ritmo comum do estado 45,06 p.p.; composição setorial -7,12 p.p.; dinâmica própria -8,7 p.p.
- Setores na conta: Agropecuária; Comércio; Construção civil; Indústria; Serviços
- Frase publicada: "Entre 2006 e 2025, os vínculos formais nos cinco setores classificados da região foram de 209 013 para 270 110 (variação de 29,2%). Na conta decomposta, o ritmo comum do estado explica 45,1 pontos percentuais dessa variação; a composição setorial de partida da região explica -7,1 pontos percentuais; a dinâmica própria dos setores na região explica -8,7 pontos percentuais. Os três termos somam a variação total; valores exibidos arredondados a uma casa decimal."

### 3.4 Números-síntese do hero (contrato 2.9.0)

- **Ensino médio** (educação): 26 911 matrículas · 2025 · -15,3% desde 2014 · contraste: "Entre as 10 regiões comparáveis do estado, esta é a 9ª maior queda acumulada de Matrículas no ensino médio nessa janela; 10 das 10 regiões registraram queda."
- **Educação técnica** (educação): 13 945 matrículas · 2025 · +9,2% desde 2014 · contraste: "Entre as 10 regiões comparáveis do estado, esta é a 3ª maior alta acumulada de Matrículas na educação profissional técnica nessa janela; 4 das 10 regiões registraram alta."
- **Escolaridade do emprego** (território): 46,3 de cada 100 vínculos com ensino médio completo · 2025 · eram 26,3 em 2006
- **Nascimentos** (território): 9 276 nascidos vivos · 2024 · eram 15 482 em 1994

### 3.5 Conclusões publicadas (síntese)

**Do observado** (11):
- Conclui-se do observado que, entre 2014 e 2025, Matrículas na educação profissional técnica passou de 12 774 para 13 945 e, no mesmo período, Vínculos formais de pessoas com ensino superior completo passou de 28 503 para 57 640 e Vínculos formais de pessoas com ensino médio completo por cem vínculos formais passou de 39,2 para 46,3.
- Conclui-se do observado que, entre 2014 e 2025, Matrículas no ensino médio passou de 31 789 para 26 911 e, no mesmo período, Vínculos formais de profissionais do ensino passou de 8 827 para 10 484 e Vínculos formais de pessoas com ensino médio completo por cem vínculos formais passou de 39,2 para 46,3.
- Conclui-se do observado que, entre 2014 e 2025, Matrículas no ensino médio passou de 31 789 para 26 911 e, no mesmo período, Massa salarial de dezembro a preços de 2025 passou de 974 856 117,8 para 1 071 650 457,9 e Vínculos formais ativos passou de 258 193 para 270 110.
- Conclui-se do observado que, entre 2014 e 2021, Escolas rurais com matrículas na educação básica passou de 30 para 27 e, no mesmo período, Produto interno bruto da agropecuária a preços de 2023 passou de 160 366,9 para 196 218,8 e População estimada passou de 900 216 para 913 235.
- Conclui-se do observado que, entre 2015 e 2025, Matrículas na educação de jovens e adultos passou de 10 399 para 11 447 e, no mesmo período, Pessoas inscritas no perfil de baixa renda, posição de dezembro passou de 76 303 para 67 072 e Massa salarial de dezembro a preços de 2025 passou de 918 228 470,2 para 1 071 650 457,9.
- Conclui-se do observado que, entre 2014 e 2025, Matrículas na educação de jovens e adultos passou de 8 835 para 11 447 e, no mesmo período, Vínculos formais de pessoas com ensino médio completo por cem vínculos formais passou de 39,2 para 46,3 e Vínculos formais ativos passou de 258 193 para 270 110.
- Conclui-se do observado que, entre 2014 e 2025, Pessoas de 60 anos ou mais por cem pessoas de 0 a 14 anos passou de 59,2 para 103,9 e, no mesmo período, Escolas com matrículas na educação básica passou de 682 para 693.
- Conclui-se do observado que, entre 2014 e 2025, Vínculos formais de pessoas com ensino médio completo por cem vínculos formais passou de 39,2 para 46,3 e, no mesmo período, Matrículas na educação de jovens e adultos passou de 8 835 para 11 447.
- Conclui-se do observado que, entre 2014 e 2025, Vínculos formais na indústria passou de 94 355 para 89 541 e, no mesmo período, Matrículas na educação profissional técnica passou de 12 774 para 13 945.
- Conclui-se do observado que, entre 2014 e 2025, Massa salarial de dezembro a preços de 2025 passou de 974 856 117,8 para 1 071 650 457,9 e, no mesmo período, Matrículas na educação de jovens e adultos passou de 8 835 para 11 447.
- Conclui-se do observado que, entre 2014 e 2021, Produto interno bruto dos serviços a preços de 2023 passou de 21 859 942,9 para 19 274 125,8 e, no mesmo período, Matrículas na educação de jovens e adultos passou de 8 835 para 14 651.

**De posição na comparação estadual** (4):
- Conclui-se que a mediana dos municípios da região em aprovação no ensino médio está em 91,5, ante a mediana estadual de 95,2.
- Conclui-se que a mediana dos municípios da região em reprovação no ensino médio está em 6, ante a mediana estadual de 2,9.
- Conclui-se que a mediana dos municípios da região em abandono escolar no ensino médio está em 2,8, ante a mediana estadual de 1,5.
- Conclui-se que a mediana dos municípios da região em abandono escolar no ensino fundamental está em 0,1, ante a mediana estadual de 0,2.

- Ausência declarada — Sustentado nos quatro cenários: "Conclusão invariante dos cenários ausente: a região não possui quatro cenários publicados."
- Ausência declarada — Frentes da agenda mobilizadas: "Conclusão de agenda ausente: a região não possui quatro cenários publicados."

### 3.6 Cenários (Pergunta 2)

Status no Vale do Sinos: **ausência declarada**.
Frase publicada: "Esta região ainda não tem cenários publicados. Os cenários regionais foram construídos, até aqui, para duas regiões do estado, e esta não é uma delas. O que está publicado nesta página são os blocos anteriores: o retrato do território, a leitura entre educação e território, as transformações simultâneas e as relações observadas por triagem."

## 4. Variáveis: usadas e disponíveis

### 4.1 As 71 séries do retrato do território (Vocações — Vale do Sinos)

| Série | Fonte | Janela | Unidade | Classe | Uso nas leituras |
|---|---|---|---|---|---|
| Famílias inscritas no cadastro social, posição de dezembro | Cadastro social do governo federal, painel de informações sociais | 2012 a 2025 | famílias inscritas | observed | triagem |
| Pessoas inscritas no perfil de baixa renda, posição de dezembro | Cadastro social do governo federal, painel de informações sociais | 2012 a 2025 | pessoas inscritas | observed | lead, associação |
| Famílias inscritas com cadastro atualizado | Cadastro social do governo federal, painel de informações sociais | abril de 2015 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Famílias inscritas no perfil de baixa renda | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Famílias inscritas no cadastro social | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Famílias inscritas com renda familiar mensal por pessoa de até meio salário mínimo | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Famílias inscritas no perfil de pobreza do programa de transferência de renda | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Famílias inscritas com cadastro atualizado e renda declarada igual a zero | Cadastro social do governo federal, painel de informações sociais | abril de 2015 a agosto de 2026 | famílias inscritas | observed | só retrato (disponível, não usada em leitura) |
| Pessoas inscritas no perfil de baixa renda | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | pessoas inscritas | observed | só retrato (disponível, não usada em leitura) |
| Pessoas inscritas no cadastro social | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | pessoas inscritas | observed | só retrato (disponível, não usada em leitura) |
| Pessoas inscritas em famílias com renda familiar mensal por pessoa de até meio salário mínimo | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | pessoas inscritas | observed | só retrato (disponível, não usada em leitura) |
| Pessoas inscritas no perfil de pobreza do programa de transferência de renda | Cadastro social do governo federal, painel de informações sociais | agosto de 2012 a agosto de 2026 | pessoas inscritas | observed | só retrato (disponível, não usada em leitura) |
| Escolas com matrículas na educação básica | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | escolas | observed | lead, par |
| Escolas rurais com matrículas na educação básica | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | escolas | observed | lead, associação |
| Eventos climáticos registrados | Atlas Digital de Desastres no Brasil | 1991 a 2024 | eventos registrados | observed | só retrato (disponível, não usada em leitura) |
| Valor total das exportações | Comex Stat do Ministério do Desenvolvimento, Indústria, Comércio e Serviços | 2019 a 2025 | dólares dos Estados Unidos | observed | só retrato (disponível, não usada em leitura) |
| Pessoas de 60 anos ou mais por cem pessoas de 0 a 14 anos | Estimativas populacionais do IBGE consolidadas para as regiões | 2010 a 2025 | pessoas de 60 anos ou mais por cem pessoas de 0 a 14 anos | calculated | lead, par |
| Massa salarial de dezembro a preços de 2025 | Relação Anual de Informações Sociais e índice de preços ao consumidor | 2006 a 2025 | reais de 2025 | calculated | associação, par |
| Matrículas na educação infantil | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | E2 |
| Matrículas na educação de jovens e adultos | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | lead, associação, par |
| Matrículas na educação profissional | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | triagem |
| Matrículas na educação profissional técnica | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | lead, triagem, associação, par, hero |
| Matrículas no ensino fundamental | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | lead, triagem, E2 |
| Matrículas no ensino médio | Censo Escolar do Instituto Nacional de Estudos e Pesquisas Educacionais | 2014 a 2025 | matrículas | observed | lead, triagem, associação, E2, hero |
| Pessoas de 15 a 19 anos que já moraram fora do município e estão nele há menos de cinco anos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| Pessoas de 20 a 24 anos que já moraram fora do município e estão nele há menos de cinco anos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| Nascidos vivos atribuídos à coorte nascida depois do Censo de 2010 | Sistema de informações sobre nascidos vivos do Ministério da Saúde | 2022 | nascidos vivos | calculated | só retrato (disponível, não usada em leitura) |
| Nascidos vivos por residência da mãe | Sistema de informações sobre nascidos vivos do Ministério da Saúde | 1994 a 2026 | nascidos vivos | observed | lead, E2, hero |
| Óbitos da coorte de 0 a 4 anos no Censo de 2010 entre os dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | óbitos | calculated | só retrato (disponível, não usada em leitura) |
| Óbitos da coorte de 10 a 14 anos no Censo de 2010 entre os dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | óbitos | calculated | só retrato (disponível, não usada em leitura) |
| Óbitos da coorte de 15 a 19 anos no Censo de 2010 entre os dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | óbitos | calculated | só retrato (disponível, não usada em leitura) |
| Óbitos da coorte de 5 a 9 anos no Censo de 2010 entre os dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | óbitos | calculated | só retrato (disponível, não usada em leitura) |
| Óbitos da coorte nascida depois do Censo de 2010 entre os dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | óbitos | calculated | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 10 a 14 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 15 a 19 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 1 a 4 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 20 a 29 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 30 a 39 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 40 a 49 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 50 a 59 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 5 a 9 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 60 a 69 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 70 a 79 anos | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, 80 anos e mais | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, idade ignorada | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, menor 1 ano | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Óbitos por residência, todas as idades | Sistema de informações sobre mortalidade do Ministério da Saúde | 1996 a 2026 | óbitos | observed | só retrato (disponível, não usada em leitura) |
| Vínculos formais de pessoas com ensino médio completo por cem vínculos formais | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos por cem vínculos | calculated | lead, associação, par, hero |
| Produto interno bruto da administração pública a preços de 2023 | Contas Regionais do IBGE e índice de preços ao consumidor | 2002 a 2021 | mil reais de 2023 | calculated | só retrato (disponível, não usada em leitura) |
| Produto interno bruto da agropecuária a preços de 2023 | Contas Regionais do IBGE e índice de preços ao consumidor | 2002 a 2021 | mil reais de 2023 | calculated | associação |
| Produto interno bruto da indústria a preços de 2023 | Contas Regionais do IBGE e índice de preços ao consumidor | 2002 a 2021 | mil reais de 2023 | calculated | só retrato (disponível, não usada em leitura) |
| Produto interno bruto dos serviços a preços de 2023 | Contas Regionais do IBGE e índice de preços ao consumidor | 2002 a 2021 | mil reais de 2023 | calculated | lead, par |
| População de 0 a 14 anos | Estimativas populacionais do IBGE consolidadas para as regiões | 2010 a 2025 | pessoas | estimated_indirect | triagem |
| População de 60 anos ou mais | Estimativas populacionais do IBGE consolidadas para as regiões | 2010 a 2025 | pessoas | estimated_indirect | só retrato (disponível, não usada em leitura) |
| População da coorte de 0 a 4 anos no Censo de 2010, contada nos dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| População da coorte de 10 a 14 anos no Censo de 2010, contada nos dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| População da coorte de 15 a 19 anos no Censo de 2010, contada nos dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| População da coorte de 5 a 9 anos no Censo de 2010, contada nos dois censos | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2010 a 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| População da coorte nascida depois do Censo de 2010, contada no Censo de 2022 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | observed | só retrato (disponível, não usada em leitura) |
| População estimada | Estimativas populacionais do IBGE consolidadas para as regiões | 2010 a 2025 | pessoas | estimated_indirect | triagem, lead, associação |
| Saldo migratório aparente da coorte de 0 a 4 anos no Censo de 2010 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | calculated | só retrato (disponível, não usada em leitura) |
| Saldo migratório aparente da coorte de 10 a 14 anos no Censo de 2010 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | calculated | só retrato (disponível, não usada em leitura) |
| Saldo migratório aparente da coorte de 15 a 19 anos no Censo de 2010 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | calculated | só retrato (disponível, não usada em leitura) |
| Saldo migratório aparente da coorte de 5 a 9 anos no Censo de 2010 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | calculated | só retrato (disponível, não usada em leitura) |
| Saldo migratório aparente da coorte nascida depois do Censo de 2010 | Censo Demográfico do Instituto Brasileiro de Geografia e Estatística | 2022 | pessoas | calculated | só retrato (disponível, não usada em leitura) |
| Vínculos formais ativos | Relação Anual de Informações Sociais e índice de preços ao consumidor | 2006 a 2025 | vínculos formais | observed | triagem, lead, associação |
| Vínculos formais na indústria | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos formais | observed | lead, triagem, par |
| Vínculos formais de pessoas com ensino médio completo | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos | observed | triagem |
| Vínculos formais com grau de instrução declarado | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos | observed | triagem |
| Vínculos formais de profissionais do ensino | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos formais | observed | associação |
| Vínculos formais de pessoas com ensino superior completo | Relação Anual de Informações Sociais | 2006 a 2025 | vínculos | observed | associação |

Critérios da triagem: correlação absoluta mínima 0,6, mínimo 8 intervalos, teto 8 por região; séries excluídas da elegibilidade: 13 (fatias etárias de óbitos).

### 4.2 O que mais existe na plataforma (disponível para cruzamento, hoje fora do Vocações)

O Vocações usa as 71 séries acima. A plataforma PNE, no mesmo painel, publica por
município (497 municípios do RS) outras famílias de dados que **ainda não entram** nas
leituras regionais:

**PNE 2014–2024 (ciclo encerrado) — 24 indicadores municipais**, entre eles:
cobertura de creche e pré-escola; atendimento 6–17 anos; educação integral (matrículas e
escolas); EJA integrada à educação profissional; pós-graduação docente; participação
pública no médio-técnico; alfabetização (15+ e crianças); conclusão do fundamental
(6–14) e do médio (15–17); IDEB anos iniciais/finais/médio; adequação da formação
docente (AI/AF/EM); rendimento do magistério ante demais profissionais; escolaridade
média 18–29; razão racial de escolaridade 18–29; medio-técnico total.

**PNE 2026–2036 (novo plano) — 50 indicadores municipais**, incluindo tudo acima
atualizado mais: infraestrutura e conectividade das escolas (internet, banda larga, rede
local/wireless, equipamentos por aluno, salas climatizadas e acessíveis), docentes
temporários, conselho escolar e proposta pedagógica, educação ambiental, AEE
(atendimento educacional especializado), idade regular no 5º/9º ano e no médio,
conclusão do fundamental e do médio por faixas etárias, SAEB matemática e português
(AI/AF/EM), expansão do subsequente.

**Matriz de priorização municipal (matriz-4.0.0)**: para cada município, metas
prioritárias do novo PNE (ex.: NSR prioriza 1.a, 5.a, 11.c, 17.a, 4.a, 4.b, 19.c) com
frentes de atuação recomendadas (orientação federal, 7 metas / 15 frentes), grupo de
pares, sinais de acompanhamento com tendência/concentração/mediana, e causas fora de
alcance declaradas.

**Visão geral educacional municipal**: composição da educação básica, educação especial,
ensino médio por rede, desempenho escolar (aprovação/reprovação/abandono por etapa —
séries anuais), comparação de matrículas, primeira infância, ensino superior (cursos,
IES, matrículas), SIOPE (financiamento educacional municipal: receitas, despesas,
percentuais constitucionais, QSE anual).

**Financeiro municipal**: finanças municipais da educação (transferências, ICMS
educação, FUNDEB etc.), séries anuais.

**Diagnóstico PNE 2026 (v3) e ficha diagnóstica**: leitura consolidada por município do
estado de cada meta, com gate de trajetória.

**Cenários da educação (foresight municipal → regional)**: metodologia própria (v0.6 no
piloto municipal; guia v1.6 regional), hoje publicada como camada regional em 2 regiões.

Fora da plataforma, já adquirido na camada de pesquisa (SESI/PNE) e disponível para uso:
microdados agregados de SINASC/SIM (1994–2026), RAIS por setor e instrução (2006–2025),
CadÚnico mensal (2012–2026), Censos 2010/2022 (coortes, migração), PIB municipal
(2002–2021), Comex (2019–2025), Atlas de Desastres (1991–2024), fluxo escolar INEP
(rendimento e distorção — dados locais, ainda não publicados como leitura regional).

## 5. Limitações conhecidas e leitura crítica (registro honesto)

1. **Associação ≠ causa, por decisão**: toda a camada E1 é descritiva. A regra de ouro
   da gestão proíbe afirmar causa; os graus E3–E5 (precedência temporal, painel
   municipal 497×20, quase-experimento) estão especificados em plano, mas **retidos**
   aguardando a gestão decidir se gradua a regra ("afirmar o que o grau sustenta").
2. **Risco de correlação espúria na triagem**: duas séries com tendência monotônica na
   mesma janela correlacionam alto sem sentido substantivo (ex.: `eventos climáticos ×
   matrículas profissionais` em outras regiões, r=+0,83 no Norte). Mitigado por teto,
   piso de intervalos, moldura "observada por triagem, sem hipóteses" e lista de
   exclusão — mas um **catálogo de mecanismos com lastro em literatura** para as
   hipóteses ainda não existe (backlog).
3. **Taxa de atendimento aparente pode passar de 100** (fundamental do Vale do Sinos:
   100,7 → 96,2 por cem): honesto — a coorte é local e a matrícula absorve migração e
   rede que atende além dela — mas exige explicação ao leitor.
4. **Correlação sobre variações anuais é conservadora**: relações estruturais lentas
   (nascimentos → matrículas) aparecem fracas ano a ano (r=−0,18) mesmo quando o vínculo
   demográfico é forte — por isso a decomposição E2 é o instrumento correto para elas, e
   por isso a relação estrutural é lead por mecanismo, não por coeficiente.
5. **Redundância editorial pontual**: no piloto, a associação curada e o par curado
   cobrem o mesmo par de séries (fatia de vínculos com EM completo × matrícula EJA),
   gerando dois cartões de título idêntico; e o cartão da associação "ensino médio ×
   fatia de vínculos" herda hipóteses escritas para outro fator da mesma associação.
   Dedup e granularidade de hipóteses por fator são itens de curadoria abertos.
6. **Cobertura da Pergunta 2**: cenários em 2 de 10 regiões (as demais declaram
   ausência); a expansão é a próxima rodada do plano vigente.
7. **Matrícula municipal por etapa via microdados do Censo Escolar** (Opção C): não
   incorporada; hoje a região soma municípios, e a camada municipal existe só dentro dos
   cenários.
8. **Sem dados de demanda/oferta qualitativa**: nada sobre vagas ofertadas, procura por
   curso, evasão por motivo, ocupações em falta (ex.: pesquisas de demanda de trabalho),
   nem projeções demográficas oficiais por idade escolar.

## 6. Perguntas para a consultoria externa (ChatGPT Pro)

Contexto a considerar: painel público estadual (RS), dados sempre municipais/regionais,
tudo determinístico e auditável (nada de estimativa não reproduzível na publicação), a
regra de ouro da gestão vigente (associação declarada, causa proibida — possivelmente
graduável por decisão futura), e as duas perguntas da gestão como norte.

1. **Fontes**: que bases públicas brasileiras (ou métodos sobre as já usadas) poderiam
   enriquecer as duas saídas? Candidatas que conhecemos e ainda não usamos: microdados
   do Censo Escolar (fluxo, distorção, transporte, turno), SAEB por escola, Novo CAGED
   mensal, RAIS ocupacional (CBO — ocupações em expansão), projeções populacionais
   municipais (quais são defensáveis?), PNAD Contínua (limitada a UF), CEMPRE/empresas,
   MEI/SEBRAE, SISTEC (educação profissional), Censo da Educação Superior, dados de
   arrecadação municipal. O que mais — e o que cada uma acrescentaria a qual pergunta?
2. **Método**: mantida a regra "sem causa afirmada", que instrumentos descritivos
   fortaleceriam a leitura além do que temos (correlação de variações, concordância,
   co-movimento, contraste estadual, decomposição contábil, shift-share)? Ex.:
   decomposições adicionais (idade×etapa; rede pública/privada), medidas de similaridade
   de trajetória, benchmarks de pares territoriais.
3. **Se a gestão liberar E3–E5**: qual seria o caminho tecnicamente honesto e
   comunicável para precedência temporal e painel (497 municípios × ~20 anos) num
   produto público municipal — e quais armadilhas evitar (comparações múltiplas,
   pré-tendências, granularidade)?
4. **Pergunta 2 (futuro do território)**: que fontes prospectivas sérias existem para
   território/emprego/demografia em nível municipal/regional no Brasil (projeções
   setoriais, transição energética/tecnológica, mapa de ocupações) que poderiam ancorar
   os cenários além das séries históricas?
5. **Apresentação**: dado o desenho atual (cartões por relação com grau declarado,
   hipóteses sob demanda, escada de evidência), o que a literatura de comunicação de
   evidência recomendaria acrescentar ou mudar para gestores municipais de educação?
6. **Priorização**: dos caminhos acima, quais dão o maior ganho de valor para a gestão
   com o menor risco metodológico, na ordem que você seguiria?

---

*Documento gerado a partir dos artefatos publicados da plataforma (contrato 2.9.0,
verificação byte a byte) e dos planos internos V3–V5. Números do Vale do Sinos extraídos
do documento público em 2026-08-27.*
