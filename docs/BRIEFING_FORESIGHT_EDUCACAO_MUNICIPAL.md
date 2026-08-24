# Briefing — Foresight da educação municipal: quatro cenários em 5 ou 10 anos

**Finalidade deste documento.** Servir de base para uma consultoria metodológica externa.
Descrevemos (a) a plataforma de educação municipal que já operamos, (b) a metodologia
foresight de quatro cenários que já aplicamos em outro projeto (Vocações Regionais) e
(c) a ideia nova: criar uma **metodologia específica de cenários da educação municipal**.
Ao final listamos as perguntas em que queremos ajuda — em especial **quais fontes, estudos
e dados públicos** podem sustentar essa construção.

**Restrição importante:** a metodologia do Vocações Regionais não será alterada. Ela é
apresentada aqui como referência de partida. O objetivo é derivar uma metodologia nova,
própria da plataforma de educação, adaptada ao recorte municipal e ao tema educacional.

Data: 2026-08-22.

> **Nota de 2026-08-24.** Este briefing é um documento congelado na data acima. O
> **caderno de hipóteses** que ele descreve no presente foi removido da plataforma em
> 2026-08-24 e substituído pela **matriz de prioridades**; onde o texto diz "o caderno
> sugere *por que*", leia "a matriz sugere em que frentes agir".

---

## 1. Contexto: a plataforma de educação municipal (PNE 2026–2036)

Operamos uma plataforma web que entrega, por município, uma leitura da situação
educacional frente ao novo Plano Nacional de Educação (PNE 2026–2036, Lei nº 15.388/2026).
O piloto atual é Nova Santa Rita/RS; a arquitetura foi desenhada para escalar aos
municípios do Rio Grande do Sul e, depois, do Brasil.

A plataforma tem hoje três camadas publicadas:

1. **Diagnóstico municipal.** Para cada meta e indicador do PNE, o valor observado do
   município, o ano da fonte, a meta, a distância e a situação oficial ("Abaixo da
   referência", "Meta não atingida", "Referência alcançada", "Meta atingida").
2. **Caderno de hipóteses.** Para cada meta, um conjunto curado de possíveis causas do
   resultado observado, em linguagem acessível, com o que os dados públicos mostram sobre
   cada causa, a orientação federal correspondente e a indicação de quem detém a alavanca
   de ação (município, estado, União).
3. **Matriz de frentes recomendadas.** Frentes de ação derivadas da orientação federal
   (7 metas, 15 frentes no piloto), com sinais públicos de acompanhamento por frente
   (tendência, concentração, mediana por sinal).

Princípios de produto que já valem e continuarão valendo:

- **Somente dados públicos.** Nada é solicitado às prefeituras; toda evidência vem de
  fontes públicas verificáveis (Inep, IBGE, MEC, MDS, STN, MIDR, entre outras).
- **Determinismo e rastreabilidade.** Os artefatos são gerados por um pipeline
  versionado (13 fontes, ~300 medidas, centenas de testes automatizados), com hash e
  contrato de schema. A interface não recalcula números.
- **Sem ranking e sem comparação entre municípios na interface.** Cada município é uma
  leitura isolada; não há pontuação que ordene causas ou municípios.
- **Linguagem proporcional à evidência.** Correlação não vira causalidade; indício não
  vira veredito; a defasagem temporal de cada fonte é sempre exibida.

O usuário-alvo é o **gestor municipal de educação** (secretaria municipal, equipe de
planejamento), tipicamente em oficinas de planejamento do plano municipal de educação.

**A lacuna que motiva este briefing:** o diagnóstico diz *como o município está*, o
caderno sugere *por que*, a matriz sugere *em que frentes agir*. Falta a camada
prospectiva: *para onde a educação do município pode ir* — e como isso depende das
escolhas dos gestores.

---

## 2. A metodologia foresight que já temos (Vocações Regionais)

Em outro projeto (Vocações Regionais — SESI, com cenários também aplicados à
agroindústria do RS), construímos e aplicamos uma metodologia de **quatro cenários
regionais em horizonte de cinco anos**, fundamentada na literatura de foresight
(FOREN/Comissão Europeia, UNDP Foresight Manual, OCDE Strategic Foresight, Voros,
Popper, Three Horizons, entre outros). Segue um resumo fiel; a metodologia completa é um
guia de ~1.300 linhas com contrato legível por máquina e validadores.

### 2.1 Princípios estruturantes

- **Quatro cenários com perfis fixos e comparáveis**, preenchidos pelas particularidades
  de cada território:
  - `C1 — Continuidade relativa`: mudanças graduais; a configuração atual predomina;
    resposta limitada ou reativa. *Exploratório.*
  - `C2 — Adaptação parcial`: mudança seletiva; resposta parcial, concentrada ou
    incompleta. *Exploratório.*
  - `C3 — Transição tensionada`: mudanças intensas ou rápidas com trajetórias
    divergentes; resposta fragmentada ou defasada. *Exploratório.*
  - `C4 — Transformação articulada`: transformação relevante com resposta coordenada,
    inclusiva e adaptativa. *Normativo — "ideal técnico provisório".*
- Os quatro cenários são organizados por **duas metadimensões**: *ritmo e profundidade
  da mudança* × *capacidade de resposta do território*. Nenhum cenário recebe
  probabilidade; nenhum é "otimista/pessimista/provável". A única assimetria é
  metodológica: C1–C3 exploram, C4 é normativo com critérios de desejabilidade
  declarados **antes** das narrativas (qualidade do trabalho/produção, capital humano,
  resiliência, adaptabilidade, inclusão) e auditados um a um, com trade-offs explícitos.
- **Horizonte duplo:** cenários sempre em `t0 → t+5`; uma varredura de futuros até
  `t0+10`/`t0+15` serve apenas para detectar pressões de maturação longa, sem criar um
  segundo estado futuro.
- **Âncora obrigatória em evidência quantitativa pública.** Toda afirmação é
  classificada como *observado*, *calculado*, *hipótese apoiada* ou *não verificável*,
  com identificadores rastreáveis (E/F/H/N/V…) ligando cenários a arquivos, variáveis,
  períodos e cálculos. Se a evidência é insuficiente para quatro futuros plausíveis e
  distintos, entrega-se um **diagnóstico de insuficiência**, não cenários imaginados.
- **Três camadas de maturidade:** (1) núcleo técnico não participativo — obrigatório e
  produto final legítimo; (2) teste com atores — opcional, com gates de participação;
  (3) pacto decisório — opcional, com mandato e responsáveis. O núcleo técnico nunca
  prescreve prioridades ou planos de ação; agenda é coisa da Camada 3.
- **Vocabulário controlado** (tendência ≠ força motriz ≠ incerteza crítica ≠ cenário;
  sinal fraco, elemento predeterminado, condição estrutural, wildcard como teste de
  estresse e nunca quinto cenário, etc.).

### 2.2 O sistema analisado: seis dimensões

O território é tratado como um sistema com seis dimensões (tecnologia/inovação é
transversal, não uma sétima):

1. Demografia e população;
2. Território, infraestrutura e ambiente;
3. Estrutura produtiva e inserção externa;
4. Trabalho, renda e ocupações;
5. Conhecimento e condições sociais (inclui educação básica, técnica e superior);
6. Instituições e dinâmica sociocultural.

A leitura preserva três escalas: municipal (concentrações e extremos), regional
(configuração levada aos cenários) e suprarregional (RS/Brasil como referência ou
pressão). Uma média nunca é lida como condição uniforme.

### 2.3 O fluxo de oito etapas

`Preparar → Diagnosticar → Selecionar → Interpretar → Estruturar → Desenvolver →
Comparar → Acompanhar`, cada etapa com produto obrigatório e ponto de controle:

1. **Preparar:** inventário e qualidade dos dados (catálogo, dicionário, chaves,
   unidades, denominadores, defasagens); varredura de futuros; condição mínima de
   suficiência antes de prosseguir.
2. **Diagnosticar:** trajetória retrospectiva por indicador (direção, ritmo,
   volatilidade, inflexões), comparação externa compatível, distribuição territorial,
   contratendências.
3. **Selecionar:** vocações/prioridades do território por critérios uniformes,
   classificadas em Três Horizontes (H1 consolidada, H2 em transição, H3 emergente).
4. **Interpretar:** ficha por fator (evidências, impacto e incerteza em 5 anos, alcance,
   controle regional, papel prospectivo); auditoria de relações com encadeamento máximo
   `estado → efeito direto → efeito indireto → indicador`; separação rígida entre
   *dinâmica empírica* (o que os dados mostram) e *capacidade de resposta* (que só é
   fato com evidência direta; caso contrário é condição ou hipótese).
5. **Estruturar:** esqueletos dos quatro cenários por **matriz 2×2** (quando existem
   exatamente duas incertezas críticas válidas, com oito testes de qualidade dos eixos)
   ou **análise morfológica** (4–6 fatores × 2–3 estados, consistência entre pares,
   quatro combinações maximamente distintas). Os critérios normativos do C4 são fixados
   antes; combinações implausíveis mandam de volta à estruturação.
6. **Desenvolver:** para cada cenário, estado em `t+5`, trajetória condicional a partir
   de `t0` respeitando estoques demográficos, tempos de formação e ritmo histórico;
   consequências por dimensão; verificação transversal PESTEL.
7. **Comparar:** matriz comparativa única (efeitos sobre vocações, oportunidades
   condicionais, riscos, tensões, capacidades, dependências, distribuição territorial),
   com implicações classificadas por capacidade de resposta (controle local, influência
   e coordenação, restrição externa). Auditoria específica do C4: critérios atendidos,
   pressupostos frágeis, modos de falha, condições de realização.
8. **Acompanhar:** sinais de acompanhamento por cenário (indicador, comportamento
   esperado, cenário que fortalece/enfraquece) e **validação longitudinal**: novas
   edições das mesmas fontes públicas testam se os sinais aproximam, afastam ou deixam
   inconclusiva cada trajetória.

### 2.4 O que essa metodologia entrega e o que ela se proíbe

Entrega: diagnóstico territorial, mapa de vocações, fatores e incertezas, quatro
cenários comparáveis, auditoria do C4, matriz comparativa, sinais de monitoramento e
apêndice técnico rastreável. Proíbe-se: prever, atribuir probabilidade sem modelo,
converter correlação em causalidade, declarar consenso sem participação, transformar o
C4 em plano de ação, e afirmar demanda/adoção/intenção sem dados diretos.

---

## 3. A ideia nova: cenários da educação do município

Queremos criar, **como metodologia própria da plataforma de educação**, um produto de
foresight que responda, para cada município:

> **Que quatro configurações plausíveis a educação deste município pode assumir nos
> próximos 5 (ou 10) anos, e como cada uma depende da resposta que o município — sua
> gestão, sua rede e suas articulações — der aos desafios que os dados já mostram?**

Traços já definidos da ideia:

- **Quatro cenários**, no espírito da arquitetura C1–C4 (do continuísmo à transformação
  articulada), mas repensados para o objeto educacional e a escala municipal.
- **O desafio é do município, e a capacidade de resposta vira protagonista.** No
  Vocações, "capacidade de resposta regional" é uma metadimensão. Aqui, o eixo central é
  **a resposta do município como um todo** — gestão municipal, rede de ensino,
  articulação com estado e União, comunidade escolar — e não a figura individual do
  gestor. Os cenários devem se diferenciar, em parte relevante, pela intensidade e
  qualidade dessa resposta coletiva (dentro do que a evidência pública permite modelar),
  porque o produto alimenta oficinas de planejamento municipal. Esse enquadramento
  também evita personalizar mérito ou culpa em quem estiver no cargo.
- **Insumos:** dados de educação (acesso, fluxo, aprendizagem, oferta, financiamento,
  docentes, infraestrutura), demografia (coortes, projeções, migração) e o que mais
  ajudar (condições sociais, estrutura produtiva local, capacidade institucional).
- **Horizonte:** 5 ou 10 anos — queremos recomendação fundamentada (ver perguntas).
  O PNE 2026–2036 dá um horizonte natural de década com metas intermediárias.
- **Integração com o que já existe:** o diagnóstico dá o `t0`; o caderno de hipóteses dá
  candidatos a fatores e mecanismos; a matriz de frentes dá o repertório de ações ao
  alcance do município; os sinais públicos já publicados são candidatos a sinais de
  acompanhamento.
- **Mesmas regras de plataforma:** só fontes públicas, pipeline determinístico e
  testável, sem ranking entre municípios, linguagem proporcional à evidência, escala
  para milhares de municípios (nada pode depender de oficina presencial para a Camada 1).

Desafios que já enxergamos na transposição regional → municipal / vocações → educação:

- **Números pequenos.** Municípios pequenos têm coortes minúsculas: taxas e médias
  (Saeb, Ideb, fluxo) oscilam por flutuação amostral/populacional. A metodologia precisa
  de regras para volatilidade de base pequena, supressão e agregação temporal.
- **Defasagem e periodicidade das fontes.** Saeb/Ideb bienais, Censo Demográfico
  decenal, Munic irregular. Como diagnosticar trajetória e monitorar sinais com essa
  cadência?
- **Fronteiras do sistema municipal.** Alunos cruzam municípios (matrícula, transporte,
  rede estadual vs municipal); parte decisiva das alavancas é estadual ou federal. Como
  delimitar o "sistema educacional municipal" e o que é contexto externo?
- **Modelar a "resposta do município" sem dado direto de gestão.** Nossa regra proíbe
  afirmar capacidade de resposta sem evidência. Que proxies públicos observáveis existem
  (execução orçamentária, existência de plano/fórum/conselho, seletividade de programas
  federais aderidos, concurso/plano de carreira docente…) e quais são seus limites?
- **Demografia como elemento predeterminado.** Queda de natalidade e encolhimento de
  coortes são quase-certezas que diferenciam pouco os cenários entre si, mas mudam muito
  o pano de fundo (fechamento/fusão de escolas, ociosidade, oportunidade de qualificar).
  Como tratar bem projeções populacionais em escala municipal?

---

## 4. O que pedimos a você

### 4.1 Pergunta principal: fontes, estudos e dados públicos

Levando em conta o objeto (educação municipal brasileira) e as restrições acima, quais
**fontes de dados públicas, estudos, metodologias e literatura** deveríamos usar para
construir essa metodologia? Interessam especialmente:

1. **Dados públicos brasileiros** além dos que já usamos (Censo Escolar, Saeb/Ideb,
   Censo Demográfico, Munic, Siope/STN, CadÚnico/MDS): microdados, projeções
   populacionais municipais (IBGE e alternativas acadêmicas), fluxo escolar
   (aprovação/abandono/distorção), docentes (formação, vínculo), financiamento
   (Fundeb, VAAT/VAAR), transporte e infraestrutura escolar, educação infantil
   (oferta/demanda), EJA, alfabetização, conectividade.
2. **Estudos e experiências de foresight em educação** (nacionais e internacionais):
   OECD "Back to the Future of Education" e Scenarios for Schooling, UNESCO Futures of
   Education, e o que mais existir de cenários educacionais **subnacionais** — há
   precedente de foresight educacional em escala local/municipal?
3. **Modelos e projeções educacionais** utilizáveis como âncora quantitativa: projeção
   de matrículas por coorte (cohort-component aplicado a matrícula), modelos de fluxo
   escolar, simulações de atingimento de metas (tipo custo-aluno-qualidade, simulador
   Fundeb), e literatura sobre o que efetivamente move indicadores educacionais em
   escala municipal no Brasil (evidência de eficácia de políticas municipais).
4. **Evidência sobre as alavancas municipais:** estudos que liguem práticas observáveis
   publicamente (colaboração com o estado, busca ativa, plano de carreira,
   fortalecimento institucional, participação em programas federais) a resultados
   educacionais — para que os estados dos nossos fatores de "resposta do município"
   tenham base e não sejam wishful thinking.

Para cada fonte/estudo sugerido, ajuda muito indicar: cobertura territorial e temporal,
periodicidade, defasagem típica, forma de acesso (download reproduzível?), e para que
etapa da metodologia serviria (diagnóstico, fatores, estados futuros, sinais).

### 4.2 Perguntas metodológicas para pensarmos juntos

1. **Horizonte:** 5 ou 10 anos para cenários educacionais municipais? (Tempos de
   maturação educacionais são longos — uma coorte alfabetizada em 2027 chega ao fim do
   fundamental em ~2031 — mas 10 anos afasta os cenários do ciclo decisório municipal,
   marcado por mandatos de 4 anos. Há desenho híbrido melhor, ex.: cenários em
   t+8/t+10 com marcos em t+4 alinhados ao ciclo de gestão e às metas intermediárias
   do PNE?)
2. **Eixos dos cenários:** faz sentido manter a moldura *ritmo/profundidade da mudança ×
   capacidade de resposta*, reinterpretando "capacidade de resposta" como intensidade e
   qualidade da resposta do município aos seus desafios educacionais? Ou o objeto
   educacional pede outra moldura (ex.: pressão demográfica × resposta municipal;
   condições externas × escolhas locais)?
3. **Dimensões do sistema:** que decomposição do "sistema educacional municipal"
   substitui as seis dimensões regionais? (Candidatas: demanda demográfica; acesso e
   oferta; fluxo e trajetória escolar; aprendizagem; profissionais da educação;
   financiamento e gestão; condições sociais do entorno.)
4. **Padronização vs. singularidade em milhares de municípios:** o Vocações roda uma
   região por vez, artesanalmente. Aqui a Camada 1 precisa ser **gerada por pipeline**
   para cada município. Como desenhar cenários que sejam ao mesmo tempo determinísticos/
   escaláveis e genuinamente municipais (não texto genérico com números trocados)? Que
   partes devem ser tipologia (municípios agrupados por perfil) e que partes devem ser
   específicas do município?
5. **Números pequenos e incerteza:** que regras a literatura recomenda para foresight
   quantitativo em unidades pequenas (limiares de população/matrícula, faixas em vez de
   pontos, agregação plurianual, vizinhança comparável)?
6. **A resposta do município sem prescrever:** nosso núcleo técnico não pode virar plano
   de ação nem promessa ("se fizer X, acontece Y"). Como formular estados de "resposta
   do município" que diferenciem cenários de forma honesta — condicionais, ancorados em
   proxies públicos — sem prometer resultado nem atribuir culpa a gestões específicas?
7. **Validação:** como avaliar a qualidade de cenários municipais em escala (validação
   longitudinal com novas edições das fontes já está prevista; existe mais o que
   emprestar da literatura de avaliação de foresight)?

### 4.3 Forma da resposta que mais nos ajuda

- Comece pelo inventário de fontes/estudos (pergunta 4.1), organizado por etapa da
  metodologia em que cada item entraria.
- Depois, posicione-se sobre as perguntas de 4.2, indicando referências.
- Aponte o que na nossa metodologia atual **não** deveria ser transposto para o caso
  educacional municipal, e por quê.
- Sinalize riscos que não listamos.

Obrigado — o objetivo desta rodada é convergir para um esboço de metodologia
("Cenários da Educação Municipal v0.1") que depois será formalizado em guia próprio,
com contrato e validadores, nos moldes do que já fazemos.
