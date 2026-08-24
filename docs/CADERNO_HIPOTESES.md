# Caderno de hipóteses — PNE 2026–2036

Documento interno da seção `#caderno` da plataforma. Descreve o que a seção faz, de onde vem
cada informação, quais metas e causas estão relacionadas e quais são as limitações conhecidas.
As limitações vivem **aqui** — a interface pública não as exibe, por decisão de produto
(2026-08-15): a plataforma apenas relaciona os indicadores das metas com suas possíveis causas.

Estado retratado: piloto **Nova Santa Rita/RS (IBGE 4313375)**, referência 2026-08-14,
contrato PNE 2026–2036 v1.9.0, **caderno v2 com curadoria de seletividade (2026-08-17)**.

---

## 1. O que a seção faz

Para cada objetivo do PNE 2026–2036 com leitura municipal, o caderno mostra:

1. **Como a meta está hoje** — o resultado oficial do indicador (valor, ano, meta e distância),
   idêntico ao publicado na página de Diagnóstico. Somente indicadores com dado disponível
   aparecem; indicador sem dado simplesmente não é exibido.
2. **O que o novo PNE pede** — orientação por objetivo com síntese da Lei nº 15.388/2026,
   metas e estratégias relacionadas e fontes oficiais.
3. **Possíveis causas**, em três camadas distintas desde a revisão de 2026-08-17:
   - **Com indício nos dados públicos** — mecanismo específico com sinal público adverso;
   - **Para verificar na oficina** — mecanismo específico sem base pública, com verificação
     local objetiva e delimitada;
   - **Condições do território** — condições que ajudam a ler o resultado (pobreza, perfil
     social, capacidade instalada), exibidas sem botão de plano: não são causas escolhíveis.
   Cada cartão de causa traz: por que pode pesar, o que costuma ajudar, o que olhar no
   município, o bloco recolhido **O que os dados públicos mostram**, a seção recolhida
   **O que a orientação federal indica**, e de quem é a alavanca (ação do município /
   compartilhada / outras esferas).
4. **Seleção de frentes** — o gestor marca as causas que o município quer atacar
   ("Adicionar ao plano de ação"). A escolha fica só no navegador e pode ser exportada em
   planilha pré-preenchida para a oficina de planejamento. Condições do território não são
   selecionáveis.

O que a seção **não** faz, por regra metodológica: não pontua, não ranqueia causas, não compara
municípios, e a escolha de frentes nunca altera os dados publicados.

## 2. De onde vem cada informação

| elemento na tela | fonte | regra |
|---|---|---|
| Valor, ano, meta, distância, situação | Diagnóstico oficial PNE 2026–2036 (`public/data/pne2026-diagnostic-v3`) | Fonte única de número. O caderno **não recalcula** indicador; usa os mesmos formatadores da página de Diagnóstico. |
| Títulos de meta e indicador | Contrato `pne2026-goal-indicator-contract.json` (v1.9.0) | Verbatim do catálogo. |
| Causas, agrupamento e vínculo causa×indicador | Pipeline de pesquisa (`SESI\PNE`), artefato `caderno.json` (schema v2) | Gerado por regras determinísticas sobre dados públicos; ingerido só via `scripts/generate-pne-caderno.mjs`. |
| **Seleção do que aparece (curadoria)** | `SESI\PNE docs/research/pne-priority-matrix/caderno-curation.csv` + `CADERNO_CURATION_SPEC.md` | Camada universal por meta×fator (`hypothesis`/`context`/`excluded`), igual para todos os municípios; critérios do Novo PAR (causa específica, verificável, direta, tratável); hash da tabela selado no artefato e no manifest. |
| Texto das causas na tela | `src/features/caderno/cadernoPlainLanguage.ts` | Reescrita acessível, fiel ao sentido do texto de pesquisa (que permanece no artefato); desde a revisão, com títulos específicos por meta onde o mesmo fator precisa de tradução concreta distinta. |
| Orientação por meta | `src/data/pne2026FederalGuidance.js`; Lei nº 15.388/2026 e Caderno MEC/SASE | Camada editorial da plataforma; não reclassifica causas. |
| Orientação por causa | `src/features/caderno/cadernoFederalGuidance.ts`; Lei nº 15.388/2026 e Caderno MEC/SASE | Camada editorial da plataforma; não reclassifica causas. |
| Sinais por causa e por condição | Artefato `caderno.json`, campo `signals[]` | Valor e `caution` verbatim; rótulo humano em `src/features/caderno/cadernoSignalLanguage.ts`. |
| Seleção de frentes | `localStorage` do navegador | Nunca vai a servidor; sai apenas na exportação `.xlsx`. |

Cadeia de dados, ponta a ponta: fontes públicas na internet (Inep, IBGE, órgãos federais) →
pipeline de pesquisa versionado → ficha diagnóstica municipal → curadoria universal →
`caderno.json` (com hash) → gerador da plataforma (valida schema v2, injeta títulos do
contrato, registra hashes) → `public/data/pne2026-caderno/`. Nenhum dado é solicitado às
prefeituras.

A ficha de pesquisa consome o resultado oficial do PNE 2026–2036 (valor, meta e veredito)
desde 2026-08-14; o veredito publicado tem autoridade sobre qualquer recálculo. Só a análise
de causas continua sendo da camada de pesquisa. A curadoria **não altera** a ficha nem as
classes determinísticas R0–R8: decide apenas pertencimento e camada de apresentação.

## 3. Metas cobertas e causas relacionadas (caderno v2)

17 objetivos, **47 cartões de causa** (eram 106 no v1), nenhum objetivo com mais de 7.
Nomes em linguagem acessível; "indício" = sinal público adverso; "oficina" = sem base
pública, verificação local objetiva; "a favor" = fator protetivo; "contexto" = condição do
território exibida sem botão de plano.

| Obj. | Com indício | Para verificar na oficina | A favor | Contexto |
|---|---|---|---|---|
| 1 | Distância e transporte · Custo para a família manter a criança na creche | Encontrar quem precisa de vaga | — | Condições sociais · Vagas e matrículas na rede |
| 3 | Frequência e busca ativa · Bases de leitura e matemática · Tempo de aula efetivo | Currículo, material e avaliação em sala · Acompanhamento dos professores | Alimentação escolar | Condições sociais |
| 4 | Frequência · Reprovação e atraso · Bases · Distância e transporte · Trabalho · Desastres climáticos | Gravidez e cuidado de dependentes | — | Condições sociais · Vagas e matrículas · Pobreza e apoio de renda · Saúde dos alunos |
| 5 | Bases de leitura e matemática · Frequência · Tempo de aula efetivo | Currículo, material e avaliação · Acompanhamento dos professores | Alimentação escolar | Condições sociais · Professores fora da área · Rotatividade docente |
| 6 | Espaço e estrutura para ampliar a jornada · Distância e transporte | Organização do tempo integral | Alimentação escolar | Vagas e matrículas · Rotatividade docente · Recursos da educação |
| 7 | Internet e equipamentos na escola | Uso da tecnologia em sala | — | Recursos da educação |
| 8 | Estrutura e recursos para climatizar as salas | Educação ambiental na prática | — | Desastres climáticos · Recursos da educação |
| 9 | Distância e transporte | Adequação da escola indígena | — | Condições sociais |
| 10 | Apoio à inclusão e atendimento especializado · Distância e transporte | — | — | Professores fora da área |
| 11 | Oferta de EJA · Trabalho · Distância e transporte · Frequência | Gravidez e cuidado de dependentes | — | Condições sociais · Pobreza · Saúde · Conexão dos cursos com o trabalho |
| 12 | Oferta de EJA · Trabalho | Oferta e qualidade da educação profissional | — | Conexão dos cursos com o trabalho · Distância e transporte |
| 14 | Distância e transporte · Trabalho | Ajuda de custo no superior e técnico · Gravidez e cuidado | — | Condições sociais · Pobreza · Oferta de ensino superior na região |
| 15 | — | — | — | Oferta de ensino superior · Professores e condições nas IES |
| 16 | — | — | — | Capacidade de pós-graduação e pesquisa |
| 17 | Professores fora da área de formação | Plano de carreira e salário na prática | — | Rotatividade docente · Oferta de ensino superior na região |
| 18 | Participação e conselhos | — | — | — |
| 19 | Obras e adaptações de acessibilidade que não saem do papel | — | — | Recursos da educação |

As metas 15 e 16 ficam **sem cartão de causa** por honestidade metodológica: não há alavanca
municipal específica sobre qualidade e titulação nas IES; o painel mostra orientação federal
e contexto.

### Catálogo ativo (26 causas de 42 fatores substantivos)

O modelo causal completo (42 fatores substantivos + 7 de medição) permanece na pesquisa. A
curadoria mantém **26 fatores como causa**, rebaixa **9 a contexto** e aposenta **7 como
causa no caderno** — com razão registrada linha a linha no `caderno-curation.csv`:

- **Aposentados como causa**: Gestão e organização (tema amplo — formulação que o Novo PAR
  manda evitar), Parceria com o estado e a União (descreve esfera, não mecanismo; o escopo de
  ação do cartão já informa), Transparência e fiscalização (genérico), Apoio em casa (sem
  base municipal; risco de responsabilizar famílias), Violência e clima escolar (sem base
  municipal utilizável; a oficina pode levantá-lo), Calor nas salas (redundante com o próprio
  indicador da meta 8), Qualidade da creche e pré-escola (circular para cobertura; distal
  para alfabetização).
- **Contexto**: condições sociais do território (SES), pobreza (exceto meta 1, onde vira
  causa concreta de custo), saúde, vagas/matrículas, rotatividade docente, recursos e
  execução, conexão da EPT com o trabalho, oferta e condições do ensino superior,
  pós-graduação.

## 4. Como uma causa entra em cada camada

1. Cada causa tem medidas públicas associadas; regras determinísticas (R0–R8) classificam
   cada vínculo causa×indicador do município: adverso, sem base pública, protetivo ou apenas
   contexto. O veredito de cumprimento que alimenta as regras é o **publicado** — vocabulário
   fechado; valor fora dele interrompe o processamento.
2. A **curadoria universal** (mesma para todos os municípios) decide então o pertencimento:
   `hypothesis` mantém o fator nas seções determinísticas; `context` o rebaixa a condição do
   território (a classe segue verbatim no artefato); `excluded` o retira do caderno, com a
   razão registrada. Critérios (Novo PAR): causa específica, verificável, direta e tratável.
3. A interface traduz o resultado em três camadas — "os dados apontam para cá", "a confirmar
   no município" e "condições do território" — sem cores de gravidade e sem ordenação entre
   causas.

## 5. Limitações conhecidas (não exibidas na plataforma)

**De escopo de dados**
- Só dados públicos disponíveis na internet; nenhum dado é solicitado às prefeituras.
- Objetivos **2 e 13** não têm indicador municipal publicado e não aparecem no caderno.
- **Meta 7 (conectividade)** tem causas mas nenhum resultado oficial publicado.
- Indicadores de ensino superior majoritariamente indisponíveis no piloto; indicador sem dado
  é omitido, nunca exibido como "não disponível".
- Defasagem temporal: Saeb 2023, Censo Demográfico 2022, Munic 2021. O ano exibido é sempre o
  da fonte.

**De método**
- As causas são **hipóteses estruturadas**, não diagnóstico causal comprovado; a confirmação é
  local, via oficina.
- A curadoria é uma decisão editorial-metodológica **universal** (nunca por município),
  versionada e auditável; ela reduz o que aparece, não o que existe no modelo. Um fator
  aposentado pode voltar por revisão da tabela, sem tocar a ficha.
- O gate de trajetória (piora persistente) exige três edições da mesma fonte; com fontes de
  edição única ele fica inerte no piloto.
- Caso-limite conhecido de arredondamento (Santo Augusto, 69,96% → "Meta atingida (70,0%)"):
  o veredito publicado manda.

**De apresentação**
- As condições do território passaram a ser exibidas (bloco recolhido, sem botão), decisão
  desta revisão; `evidence[]`, `readingCautions`, classes de deliberação e códigos seguem
  ocultos e auditáveis no artefato.
- A planilha exportada mantém as abas **Frentes da oficina** (26 colunas do modelo da
  pesquisa) e **Orientação federal**.

## 6. Rastreabilidade

- Artefato municipal publicado: `public/data/pne2026-caderno/municipios/<ibge7>.json` +
  `manifest.json` (hashes de entrada e saída).
- Origem: `SESI\PNE/data_pipeline/data/pne_priority_matrix_diagnostics/<ibge7>/<data>/caderno.json`
  (sha256 `a5e75ca0…`, schema `pne-priority-hypothesis-workbook-v2`); ficha diagnóstica
  **intocada** pela revisão (`diagnostic.csv` `cae9f878…`).
- Curadoria: `caderno-curation.csv` (137 pares meta×fator, cobertura fechada) com hash selado
  no payload e no `caderno-manifest.json`; decisão D15 em `MODEL_V2_DECISIONS.md`; spec em
  `CADERNO_CURATION_SPEC.md`.
- Números oficiais: release `pne2026-diagnostic-v3` (ponteiro `current.json`), contrato v1.9.0.
- Testes: loader do caderno (plataforma) e suíte da pesquisa (369 testes) cobrem schema,
  hashes, vocabulários fechados, cobertura da curadoria e a garantia de que nenhum valor do
  caderno publicado é numérico de forma ordenável.

## 7. Referências metodológicas da revisão (2026-08-17)

- FNDE/MEC — [PAR, Plano de Ações Articuladas](https://www.fnde.gov.br/1ccr/par.html) (Lei
  nº 12.695/2012).
- MEC — Novo PAR 2025–2028, etapas de diagnóstico e planejamento
  ([lançamento](https://www.gov.br/mec/pt-br/assuntos/noticias/2025/setembro/lancada-etapa-de-planejamento-do-novo-par);
  guias em gov.br/mec/pt-br/novo-par).
- Material de formação estadual sobre [árvore de problemas no Novo PAR](https://midiasstoragesec.blob.core.windows.net/001/2025/10/13_arvore_de_problemas_derpt_10-10-2025.pdf)
  (out/2025): causas específicas, verificáveis, diretas e controláveis; evitar "falta de
  recursos", "problemas de gestão", "dificuldades socioeconômicas" sem especificação.
- UNA-SUS — [Árvore de problemas](https://ares.unasus.gov.br/acervo/handle/ARES/15256):
  causas versus consequências e nós críticos.
