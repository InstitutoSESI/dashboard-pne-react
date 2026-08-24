# Caderno de hipóteses — PNE 2026–2036 · Estado anterior à revisão de seletividade

> **Documento histórico (retrato de 2026-08-17, antes da revisão).** A revisão de
> seletividade descrita em `SESI\PNE docs/research/pne-priority-matrix/CADERNO_CURATION_SPEC.md`
> foi aplicada em 2026-08-17: o caderno passou de 106 para 47 cartões de causa, com três
> camadas de apresentação. O estado vigente está em `docs/CADERNO_HIPOTESES.md`. Este
> arquivo é mantido como base de comparação antes/depois.

**Briefing para revisão externa.** Descreve o que já está construído na seção `#caderno` da
plataforma: quais metas cobrimos, quais causas apresentamos, quais indicadores exibimos, em que
ordem tudo aparece na tela, quais regras são invioláveis e o que ainda está em aberto.

- Estado retratado: piloto **Nova Santa Rita/RS (IBGE 4313375)**, data de referência **2026-08-14**.
- Contrato de metas e indicadores do PNE 2026–2036: **v1.9.0**.
- Documento gerado em 2026-08-17.

---

## 1. O problema que a seção resolve

O diagnóstico municipal já publica **como cada meta do PNE está**. Ele não diz **por que**. O
gestor municipal fica com o número na mão e sem hipótese de trabalho para a oficina de
planejamento.

O caderno de hipóteses acrescenta a camada seguinte: para cada meta, um conjunto de **possíveis
causas** do resultado observado, em linguagem acessível, com o que os dados públicos mostram
sobre cada uma, o que a orientação federal indica, e de quem é a alavanca de ação. O gestor
marca as causas que o município quer atacar e exporta a seleção para uma planilha de oficina.

### Regras metodológicas invioláveis

Estas restrições são de produto e estão testadas em código:

1. **Não pontua e não ranqueia.** Nenhum campo do artefato publicado é numérico de forma que
   permita ordenar hipóteses. Há um teste dedicado a isso.
2. **Não compara municípios.** Cada caderno é uma leitura isolada do próprio município.
3. **Não recalcula indicador.** Todo número exibido vem do diagnóstico oficial publicado, pelos
   mesmos formatadores da página de Diagnóstico. O município nunca vê dois números para o mesmo
   indicador.
4. **A seleção de frentes nunca altera dado publicado.** Ela vive apenas no navegador do gestor.
5. **Sem cor semafórica e sem hierarquia de gravidade entre causas.** As marcas são informativas.
6. **Nenhum dado é solicitado às prefeituras.** Tudo vem de fontes públicas na internet.

---

## 2. Cadeia de dados, ponta a ponta

```
fontes públicas (Inep, IBGE, MEC, MDS, STN, MIDR…)
  → pipeline de pesquisa versionado (repositório separado, 357 testes)
  → ficha diagnóstica municipal
  → caderno.json (artefato com hash)
  → gerador da plataforma (valida schema, injeta títulos do contrato, registra hashes)
  → public/data/pne2026-caderno/municipios/<ibge7>.json + manifest.json
  → interface
```

| elemento na tela | origem | regra |
|---|---|---|
| Valor, ano, meta, distância, situação | Diagnóstico oficial PNE 2026–2036 | Fonte única de número; o caderno não recalcula. |
| Títulos de meta e indicador | Contrato v1.9.0 | Verbatim do catálogo. |
| Causas, agrupamento e vínculo causa×indicador | Artefato `caderno.json` | Regras determinísticas sobre dados públicos. |
| Texto acessível das causas | Camada editorial da plataforma | Reescrita fiel ao texto técnico, que permanece no artefato. |
| Orientação federal por meta e por causa | Camada editorial da plataforma | Lei nº 15.388/2026 e Caderno MEC/SASE; não reclassifica causas. |
| Sinais públicos por causa | Artefato, campo `signals[]` | Valor e cautela verbatim; rótulo humano na plataforma. |
| Seleção de frentes | `localStorage` | Nunca vai a servidor; sai apenas na exportação. |

Desde 2026-08-14 a própria ficha de pesquisa **consome o veredito oficial** do PNE ("Abaixo da
referência", "Meta não atingida", "Referência alcançada", "Meta atingida") em vez de calcular
veredito próprio. Vocabulário fechado: valor fora dele interrompe o processamento em vez de
adivinhar. Só a análise de causas continua sendo da camada de pesquisa.

---

## 3. Ordem de apresentação na tela

### 3.1 Nível da página

1. **Cabeçalho** — "Caderno de hipóteses — PNE 2026–2036", município/UF, e a frase de propósito.
2. **Como usar este caderno** — bloco fixo explicando que a seção mostra resultado e possíveis
   causas, e que **não decide nem prioriza**. Rodapé com contagem: *N metas · N possíveis causas ·
   atualizado em <data>*.
3. **Frentes escolhidas pelo município** — contador de frentes selecionadas, aviso de que a escolha
   fica só no navegador, e o botão *Exportar frentes para a oficina*.
4. **Área de trabalho em duas colunas**:
   - **Índice de objetivos** (esquerda, fixo no desktop, faixa rolável no celular): número do
     objetivo, título curto, contagem de causas e, se houver, "N no plano".
   - **Painel do objetivo selecionado** (direita).

Escolher outra meta no índice troca **apenas o painel da direita**. Nada ao redor se move.

### 3.2 Dentro do painel de um objetivo

Ordem fixa das seções:

1. **Cabeçalho** — "Objetivo N" + títulos das metas legais reunidas nesse objetivo, separados por `·`.
2. **Como a meta está hoje** — só aparece se houver ao menos um indicador com resultado publicado.
   Por indicador: nome público, valor, ano, meta, distância, situação, leitura histórica quando
   existe e a ressalva do indicador quando existe. **Indicador sem dado simplesmente não aparece** —
   nunca exibimos "não disponível".
3. **O que o novo PNE pede** — síntese da Lei nº 15.388/2026 para o objetivo, bloco recolhido
   *Ver metas e estratégias relacionadas* e links para as fontes oficiais.
4. **Possíveis causas** — todas as causas do objetivo, primeiro as com indício nos dados públicos,
   depois as teóricas a investigar. Dentro de cada grupo, a ordem é a do artefato; não há
   ordenação por relevância.
5. **O que já joga a favor** — só aparece quando existem fatores protetivos identificados.

### 3.3 Dentro de um cartão de causa

Ordem fixa:

1. **Marca de origem** — "Os dados apontam para cá" ou "A confirmar no município"; nos fatores
   protetivos, "Ponto forte a proteger".
2. **Escopo de ação** — "Ação do município" / "Ação compartilhada" / "Depende de outras esferas".
3. **Nome da causa** em linguagem acessível.
4. **Por que pode pesar** — o mecanismo, reescrito de forma acessível.
5. **O que costuma ajudar**.
6. **O que olhar no município** (recolhido) — perguntas de verificação local.
7. **O que os dados públicos mostram** (recolhido) — sinais agrupados por leitura, com período,
   valor e cautela quando o dado exige.
8. **O que a orientação federal indica** (recolhido) — texto editorial e referências oficiais.
9. **Botão** *Adicionar ao plano de ação* / *No plano de ação*.

O único destaque de cor da tela é o verde do cartão que já entrou no plano.

---

## 4. Metas cobertas, indicadores e causas

**17 objetivos**, na ordem em que aparecem: 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17,
18, 19. São **106 vínculos causa×meta** apresentados como possíveis causas, mais 3 fatores
protetivos, a partir de um catálogo de **37 causas distintas**.

Legenda: **indício** = os dados públicos do município apontam para essa causa em ao menos um
indicador da meta; **a investigar** = causa plausível pela literatura, sem dado público municipal
que confirme ou descarte; **a favor** = fator que os dados indicam estar sustentando a meta.
As causas estão listadas na ordem exata em que aparecem na tela.

### Objetivo 1 — Creche · Pré-escola
- **Indicadores exibidos:** creche 35,1% (meta 60, 2025) · pré-escola 97,1% (meta 100).
- **Com indício:** Distância e transporte até a escola · Pobreza e apoio de renda às famílias.
- **A investigar:** Encontrar quem precisa de vaga · Qualidade da creche e da pré-escola.
- Ressalva do indicador de creche: acompanha matrícula sobre população estimada e não mede a
  demanda manifesta prevista na meta.

### Objetivo 3 — Alfabetização ao final do 2º ano
- **Indicadores exibidos:** alfabetização 49,0% (meta 80).
- **Com indício:** Frequência e busca ativa · Gestão e organização da escola · Bases de leitura e
  matemática · Tempo de aula efetivo.
- **A investigar:** Apoio à aprendizagem em casa · Acompanhamento dos professores · Currículo,
  material e avaliação em sala · Qualidade da creche e da pré-escola.
- **A favor:** Alimentação escolar.

### Objetivo 4 — Acesso e conclusão na idade certa (4 metas legais)
- **Indicadores exibidos:** 5 resultados entre 75,2% e 92,2% (meta 100).
- **Com indício (9):** Parceria com o estado e a União · Desastres e eventos climáticos ·
  Distância e transporte · Frequência e busca ativa · Pobreza e apoio de renda · Bases de leitura
  e matemática · Reprovação e atraso escolar · Saúde física e mental dos alunos · Trabalho que
  concorre com o estudo.
- **A investigar:** Gravidez e cuidado de dependentes · Currículo, material e avaliação em sala ·
  Violência, bullying e clima escolar.

### Objetivo 5 — Aprendizagem AI · AF · EM
- **Indicadores exibidos:** 6 resultados Saeb 2023, de 1,8% a 69,0% (metas de 50 a 70).
- **Com indício:** Parceria com o estado e a União · Frequência e busca ativa · Gestão e
  organização da escola · Bases de leitura e matemática · Tempo de aula efetivo.
- **A investigar:** Apoio à aprendizagem em casa · Calor e conforto nas salas · Acompanhamento dos
  professores · Currículo, material e avaliação em sala · Violência, bullying e clima escolar.
- **A favor:** Alimentação escolar.

### Objetivo 6 — Tempo integral
- **Indicadores exibidos:** matrículas em tempo integral 21,0% (meta 35) · escolas 42,9% (meta 50).
- **Com indício:** Distância e transporte · Gestão e organização da escola · Infraestrutura básica
  da escola · Tempo de aula efetivo.
- **A investigar:** Organização do tempo integral.
- **A favor:** Alimentação escolar.

### Objetivo 7 — Conectividade nas escolas
- **Indicadores exibidos:** nenhum resultado oficial publicado; o painel mostra só as causas.
- **Com indício:** Gestão e organização da escola · Infraestrutura básica da escola · Internet e
  equipamentos na escola.
- **A investigar:** Uso da tecnologia em sala.

### Objetivo 8 — Conforto térmico · Educação ambiental
- **Indicadores exibidos:** salas climatizadas 82,1% · educação ambiental 57,1% (metas 100).
- **Com indício:** Desastres e eventos climáticos · Gestão e organização da escola ·
  Infraestrutura básica da escola.
- **A investigar:** Calor e conforto nas salas · Educação ambiental na prática · Acompanhamento
  dos professores.

### Objetivo 9 — Atendimento escolar indígena
- **Indicadores exibidos:** cobertura estimada 0,0% (indicador de acompanhamento).
- **Com indício:** Parceria com o estado e a União · Distância e transporte.
- **A investigar:** Adequação da escola indígena.

### Objetivo 10 — Atendimento educacional especializado
- **Indicadores exibidos:** oferta de AEE em escolas elegíveis 8,0% (acompanhamento).
- **Com indício:** Apoio à inclusão e atendimento especializado · Parceria com o estado e a União ·
  Distância e transporte · Infraestrutura básica da escola.

### Objetivo 11 — Escolaridade de jovens e adultos (4 metas legais)
- **Indicadores exibidos:** 6 resultados; alfabetização de 15+ na referência (97,0%); os demais
  entre 1,2% e 80,0%, abaixo.
- **Com indício (9):** Oferta de EJA para jovens e adultos · Parceria com o estado e a União ·
  Distância e transporte · Frequência e busca ativa · Pobreza e apoio de renda · Bases de leitura
  e matemática · Reprovação e atraso escolar · Saúde física e mental · Trabalho que concorre com
  o estudo.
- **A investigar:** Gravidez e cuidado de dependentes · Violência, bullying e clima escolar.

### Objetivo 12 — Educação profissional (3 metas legais)
- **Indicadores exibidos:** técnico articulado 0,0% (meta 50) · EJA articulada à educação
  profissional 0,0% (meta 25).
- **Com indício:** Oferta de EJA · Parceria com o estado e a União · Distância e transporte ·
  Trabalho que concorre com o estudo.
- **A investigar:** Ajuda de custo no ensino superior e técnico · Oferta e qualidade da educação
  profissional.

### Objetivo 14 — Acesso e conclusão na graduação (4 metas legais)
- **Indicadores exibidos:** 4 resultados entre 8,5% e 26,0% (metas de 40 a 60).
- **Com indício:** Parceria com o estado e a União · Distância e transporte · Pobreza e apoio de
  renda · Bases de leitura e matemática · Trabalho que concorre com o estudo.
- **A investigar:** Ajuda de custo no ensino superior e técnico · Professores e condições no
  ensino superior · Gravidez e cuidado de dependentes · Oferta de ensino superior na região.

### Objetivo 15 — Qualidade e corpo docente das IES
- **Indicadores exibidos:** nenhum disponível no piloto.
- **Com indício:** Gestão e organização da escola.
- **A investigar:** Carreira e salário dos professores · Capacidade de pós-graduação e pesquisa ·
  Professores e condições no ensino superior · Oferta de ensino superior na região.

### Objetivo 16 — Titulação de mestres e doutores
- **Indicadores exibidos:** nenhum disponível no piloto.
- **Com indício:** Parceria com o estado e a União.
- **A investigar:** Ajuda de custo no ensino superior e técnico · Capacidade de pós-graduação e
  pesquisa · Professores e condições no ensino superior.

### Objetivo 17 — Valorização docente (5 metas legais)
- **Indicadores exibidos:** adequação da formação docente 65,8% a 78,1% (meta 100) · plano de
  carreira: 1 de 2 requisitos · profissionais temporários 13,2% · pós-graduação dos docentes 49,4%.
- **Com indício:** Professores dando aula fora da sua área de formação · Parceria com o estado e a
  União · Bases de leitura e matemática · Transparência e fiscalização.
- **A investigar:** Carreira e salário dos professores · Ajuda de custo no ensino superior e
  técnico · Professores e condições no ensino superior · Acompanhamento dos professores · Oferta
  de ensino superior na região.

### Objetivo 18 — Conselhos e fóruns de educação
- **Indicadores exibidos:** conselho escolar 95,2% (meta 100) · fórum de educação não declarado.
- **Com indício:** Gestão e organização da escola · Participação e conselhos · Transparência e
  fiscalização.

### Objetivo 19 — Infraestrutura mínima
- **Indicadores exibidos:** salas acessíveis 47,1% (meta 100).
- **Com indício:** Apoio à inclusão e atendimento especializado · Infraestrutura básica da escola ·
  Transparência e fiscalização.

---

## 5. Catálogo de causas (37), por escopo de ação

**Ação do município (15)** — Encontrar quem precisa de vaga · Qualidade da creche e da pré-escola ·
Frequência e busca ativa · Gestão e organização da escola · Bases de leitura e matemática · Tempo
de aula efetivo · Acompanhamento dos professores · Currículo, material e avaliação em sala ·
Reprovação e atraso escolar · Organização do tempo integral · Uso da tecnologia em sala · Educação
ambiental na prática · Apoio à inclusão e atendimento especializado · Oferta de EJA para jovens e
adultos · Participação e conselhos.

**Ação compartilhada (18)** — Distância, tempo, custo e transporte até a escola · Pobreza e apoio
de renda às famílias · Apoio à aprendizagem em casa · Alimentação escolar · Parceria com o estado
e a União · Desastres e eventos climáticos · Saúde física e mental dos alunos · Trabalho que
concorre com o estudo · Gravidez e cuidado de dependentes · Violência, bullying e clima escolar ·
Calor e conforto nas salas · Infraestrutura básica da escola · Internet e equipamentos na escola ·
Adequação da escola indígena · Oferta e qualidade da educação profissional · Carreira e salário
dos professores · Transparência e fiscalização · Professores dando aula fora da sua área de
formação.

**Depende de outras esferas (4)** — Ajuda de custo no ensino superior e técnico · Professores e
condições no ensino superior · Oferta de ensino superior na região · Capacidade de pós-graduação e
pesquisa.

Cada causa carrega no artefato, além do nome: mecanismo, relação esperada, papel diagnóstico,
evidências da literatura com nível de desenho, perguntas de confirmação local, sinais públicos
associados e a justificativa da classificação.

---

## 6. Como uma causa entra em "os dados apontam para cá"

1. Cada causa tem medidas públicas associadas — por exemplo, frequência puxa abandono e busca
   ativa declarada; pobreza puxa CadÚnico e Bolsa Família.
2. Regras determinísticas classificam cada vínculo causa×indicador conforme os sinais públicos:
   adverso, sem base pública, protetivo, ou apenas contexto de monitoramento.
3. As regras exigem gates explícitos — base elegível, territorialidade compatível, confiança
   utilizável, referência normativa ou trajetória própria. Um vínculo que falha um gate cai para
   uma classe mais fraca com a justificativa registrada no artefato.
4. O veredito de cumprimento que alimenta essas regras é o **publicado**, não um recálculo.
5. A interface traduz tudo em duas marcas apenas: "os dados apontam para cá" e "a confirmar no
   município".

O que fica no artefato mas **não** aparece na tela, por decisão de produto: evidências da
literatura, contexto de monitoramento (28 vínculos no piloto), cautelas de leitura, classes de
deliberação, códigos de fator e de medida, classes de observabilidade, sinais sem valor e
indisponibilidades. Tudo permanece auditável.

---

## 7. Exportação para a oficina

Botão *Exportar frentes para a oficina* gera uma planilha com duas abas:

- **Frentes da oficina** — uma linha por hipótese selecionada e por relação meta×indicador que a
  sustenta. 26 colunas, idênticas ao modelo da pesquisa: identificação do município, ciclo de
  decisão, meta, indicador, fator, data de referência, classe pública vigente e perfil de peso
  municipal vêm pré-preenchidos; decisão, descrição da ação, responsável, parceiros, prazo,
  orçamento, indicadores de processo e de resultado, linha de base, meta da ação, justificativa,
  data da oficina, participantes, data de revisão e notas ficam em branco para a oficina.
- **Orientação federal** — aba informativa gerada pela plataforma, com objetivo, causa, orientação
  da meta, orientação da causa e referências, apenas para as frentes selecionadas.

A exportação não altera, não agrega e não pontua nada.

---

## 8. Limitações conhecidas

Estas limitações vivem na documentação interna. A interface pública não as exibe — decisão de
produto de 2026-08-15: a plataforma apenas relaciona os indicadores das metas com suas possíveis
causas.

**De escopo de dados**
- Só dados públicos disponíveis na internet. O que o município souber além disso entra apenas pela
  oficina, nos campos em branco da planilha.
- **Objetivos 2 e 13** não têm indicador municipal publicado no PNE 2026–2036 e por isso não
  aparecem no caderno.
- **Objetivo 7** tem causas mas nenhum resultado oficial publicado.
- No piloto, os indicadores de ensino superior (objetivos 15 e 16, e parte de 12 e 17) estão
  majoritariamente indisponíveis na fonte oficial.
- Defasagem temporal: Saeb 2023, Censo Demográfico 2022 (objetivos 11 e 14), Munic 2021 (fórum de
  educação e plano de carreira). O ano exibido é sempre o da fonte.

**De método**
- As causas são **hipóteses estruturadas**, não diagnóstico causal comprovado. A evidência que as
  sustenta é da literatura, no nível de transferibilidade, não de prova local; os sinais municipais
  são indícios. A confirmação é local, via oficina.
- O gate de trajetória (piora persistente) exige três edições da mesma fonte. Com fontes de edição
  única ele fica inerte — nenhuma causa entra "por piora" no piloto.
- Caso-limite conhecido de arredondamento em outro município: valor 69,96% publicado como "Meta
  atingida (70,0%)". Regra vigente: o veredito publicado manda.

**De apresentação**
- A tela exibe os sinais públicos por hipótese, sem códigos, ranqueamento ou leitura causal
  adicional.
- Não há visão comparativa entre metas nem qualquer agregação municipal.

---

## 9. Rastreabilidade e testes

- Artefato publicado: `public/data/pne2026-caderno/municipios/<ibge7>.json` + `manifest.json` com
  hashes de entrada e de saída.
- Números oficiais: release `pne2026-diagnostic-v3`, contrato v1.9.0.
- Testes da plataforma no caderno (11): hash do manifesto, parsers, cache, falha fechada para
  município sem publicação, recusa de código municipal inválido, recusa de manifesto adulterado,
  recusa de documento divergente, erro de rede estruturado e reportado uma única vez, preservação
  de ordem e vocabulário do artefato, recorte de observação por sinal, e a garantia de que **nenhum
  valor do caderno publicado é numérico de forma ordenável**.
- Suíte da pesquisa: 357 testes cobrindo schema, hashes, vocabulários fechados e a identidade
  valor − distância = meta declarada no contrato.

---

## 10. Pendências e pontos em aberto

1. **Cobertura**: o caderno está publicado apenas para o piloto. Falta definir o critério de
   expansão município a município.
2. **Endurecimento de guarda bidirecional** entre a ficha de pesquisa e o diagnóstico oficial ficou
   pendente por restrição de ambiente na última execução.
3. **Objetivos 2 e 13** seguem fora do caderno por ausência de indicador municipal.
4. **Fatores de contexto de monitoramento** (28 vínculos no piloto) seguem ocultos; não há decisão
   sobre expô-los em alguma forma.
5. **Ciclo de revisão**: não há ainda um processo definido de reavaliação periódica dos textos
   editoriais de orientação federal frente a atualizações normativas.

---

## 11. O que gostaríamos de avaliar

Pontos onde uma revisão externa ajudaria mais:

1. A ordem de apresentação (resultado → orientação federal → causas → pontos fortes) é a melhor
   para um gestor municipal que vai conduzir uma oficina?
2. A separação em duas marcas apenas ("os dados apontam para cá" / "a confirmar no município") é
   suficiente, ou perde informação decisória relevante?
3. A recusa de ranquear causas protege a metodologia, mas deixa o gestor com até 12 causas por
   meta sem apoio de priorização. Existe um caminho que preserve a regra e ainda assim ajude a
   decidir por onde começar?
4. O escopo de ação (município / compartilhada / outras esferas) é o eixo certo de organização, ou
   haveria eixo mais útil para planejamento?
5. Faltam causas relevantes no catálogo de 37, ou há causas que deveriam ser fundidas?
6. A decisão de ocultar evidências, cautelas e classes de deliberação é adequada para o público
   municipal, ou cria um problema de confiança?
7. A planilha de oficina, com 8 colunas pré-preenchidas e 18 em branco, é o artefato certo de
   saída da conversa?
