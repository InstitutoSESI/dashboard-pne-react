# Contrato de produto e de linguagem — Vocações × PNE

**Versão:** 1.2.0 (Rodada 2: catálogo de mecanismos, registro de séries e catálogos de referência)
**Origem:** Rodada 1 do plano V6 (`docs/PLANO_IMPLEMENTACAO_VOCACOES_PNE.md`, Etapas 1 e 9, §6 e §7). Em conflito entre este contrato e o plano, o plano prevalece; este documento é a forma operacional do plano.
**Aplicação:** este contrato governa tudo o que a página Vocações × PNE publica. É verificado por máquina onde possível (`scripts/checks/fixtures/vocacoes-pne/vocabulario.json` + linter + testes de contrato) e por gate editorial onde não.

---

## 1. As duas saídas

A página existe para responder duas perguntas da gestão, e somente elas:

| Direção | Pergunta da gestão | Conteúdo |
|---|---|---|
| `educacao_para_territorio` | O que o território ajuda a compreender sobre a educação? | **Leituras integradas**: partem de um resultado educacional, separam seus componentes e usam o território para interpretá-lo. |
| `territorio_para_educacao` | O que o futuro do território coloca na agenda da educação? | **Questões de agenda**: partem de uma transformação territorial e chegam a uma implicação concreta para o planejamento educacional. |

A comparação temporal e a heterogeneidade municipal são **incorporadas** a cada cartão das duas direções — nunca uma terceira seção.

### 1.1 Limites e mínimos

| Regra | Valor |
|---|---|
| Leituras publicadas (`educacao_para_territorio`) | mínimo 3, máximo 5 |
| Questões publicadas (`territorio_para_educacao`) | mínimo 2, máximo 5 |
| Página publicável para uma região | somente com os dois mínimos atingidos |
| Região abaixo do mínimo | permanece na rota anterior, **sem mensagem pública de ausência** |

### 1.2 Regra de publicação de um cartão

Um conteúdo só vira cartão quando o insight:

1. combina educação e território;
2. responde a uma das duas perguntas da gestão;
3. é sustentado por dados rastreáveis;
4. altera ou qualifica uma questão de planejamento;
5. é explicável em linguagem pública, sem jargão metodológico;
6. não repete outra leitura já publicada.

Falhou em qualquer item: o cartão **não existe** — nem como aviso, nem como espaço vazio rotulado.

---

## 2. Tipologia do conteúdo

Cinco categorias, com alcance distinto. Todo texto público pertence a uma delas e não pode reivindicar o alcance de outra.

| Categoria | O que é | Exemplo de forma |
|---|---|---|
| **Fato observado** | Número ou variação medida em fonte identificada, período fechado. | "Entre 2014 e 2025, as matrículas no ensino médio passaram de 31.789 para 26.911." |
| **Leitura integrada** | Combinação de dois ou mais fatos compatíveis que interpreta um resultado, sem afirmar causa. | "A redução da população jovem foi maior do que a queda das matrículas; a relação entre matrículas e população da idade aumentou." |
| **Questão de planejamento** | Consequência prática da leitura: nomeia o público **ou** a etapa, o fenômeno e o indicador; o recorte territorial ou temporal entra quando cabível (plano §3.7). Na segunda saída, o afetado pode ser grupo, etapa **ou** território (plano Etapa 7.3). | "O ajuste da oferta precisa ocorrer junto com ações de permanência, sobretudo onde reprovação e abandono se concentram." |
| **Tendência futura** | Extensão de uma mudança sustentada por série observada, projeção adequada ou estudo setorial aprovado (plano Etapa 7.1); sem número futuro fora de cenário; base declarada em `future_basis`. | "As coortes que chegarão ao ensino médio nos próximos anos já nasceram e são menores." |
| **Cenário** | Caminho possível vindo da metodologia de cenários publicada; sempre plural, nunca previsão. | "Em diferentes futuros considerados, a qualificação de adultos permanece na agenda." |

Regras de fronteira:

- fato nunca é apresentado como leitura ("a matrícula caiu" não é insight);
- leitura nunca afirma causa nem oferece explicação não sustentada. Verbos como **acompanhar, ajudar a compreender, interpretar, conviver com, indicar** são exemplos seguros — a regra é o alcance, não uma lista fechada: proibido atribuir uma mudança à outra (**causar, provocar, determinar, levar a, ser responsável por**);
- tendência futura exige base rastreável (`future_basis`); número futuro só dentro de cenário publicado (invariante herdada, V6-D5);
- cenário nunca substitui dado observado; enriquece a segunda saída onde existir (no piloto Vale do Sinos **não há cenários** — V6-D3 — e a segunda saída se apoia em mudanças observadas e tendências sustentadas).

---

## 3. Anatomia dos cartões

### 3.1 Cartão da primeira saída (`educacao_para_territorio`)

Blocos públicos, nesta ordem:

1. **Título com a principal leitura** — uma frase completa que já entrega o insight; nunca o nome de um indicador ou de um par de variáveis.
2. **O que mudou na educação** — fatos educacionais com valores, período e variação.
3. **O que o território ajuda a compreender** — a leitura integrada com os fatos territoriais.
4. **Como isso aparece entre os municípios** — contribuição municipal, direções divergentes, concentração.
5. **O que entra no planejamento** — a questão de planejamento.
6. **Indicadores e fontes** — em detalhe recolhido ("Ver dados e fontes").

Schema lógico (campos públicos + camada interna, plano §6.1):

```yaml
id:                       # estável, kebab-case
direction: educacao_para_territorio
title:                    # string, a leitura principal
education_question:       # a pergunta educacional de origem (catálogo §5 do plano)
education_facts: []       # fatos observados, quantitativos ou qualitativos; cada um reconstruível
                          # com período e fonte (no cartão via period/sources; internamente via
                          # fatos estruturados — ver §3.4); valor numérico obrigatório apenas
                          # quando a afirmação for quantitativa
territorial_facts: []     # fatos territoriais compatíveis
integrated_reading:       # a leitura integrada (texto público central)
municipal_pattern:        # como varia entre municípios
planning_question:        # questão concreta: etapa+público+fenômeno+recorte+indicador
pne_topics: []            # temas/metas do PNE relacionados
monitoring_indicators: [] # o que acompanhar
period:                   # janela da leitura (ex.: "2014–2025")
sources: []               # fontes nomeadas
internal:                 # NUNCA chega ao documento público
  mechanism_id:           # mecanismo do catálogo (M1–M7)
  universe_check:         # ok | incompativel
  temporal_check:         # ok | incoerente
  sensitivity_check:      # ok | instavel
  territorial_check:      # ok | concentrado
  publication_decision:   # publicada | retida
```

### 3.2 Cartão da segunda saída (`territorio_para_educacao`)

Blocos públicos, nesta ordem:

1. **Transformação do território** (título com a transformação e sua consequência educacional)
2. **O que já está mudando** — fatos territoriais observados.
3. **Ponto de partida da educação** — situação educacional atual relacionada.
4. **O que essa mudança coloca na agenda** — a questão de agenda.
5. **Municípios ou públicos mais expostos**
6. **Indicadores para acompanhar**
7. **Metas e temas relacionados** (PNE)

Schema lógico (plano §6.2):

```yaml
id:
direction: territorio_para_educacao
title:
territorial_transformation:        # a transformação em curso, nomeada
territorial_facts: []
education_starting_point:          # ponto de partida educacional
exposed_groups_or_municipalities:  # quem é mais afetado
education_agenda:                  # o que entra na agenda (texto público central)
pne_topics: []
monitoring_indicators: []
horizon:                           # "próximos anos" / janela do cenário; nunca ano+número futuro fora de cenário
sources: []
internal:
  transformation_class:  # mudanca_observada | tendencia_sustentada | estudo_setorial | cenario
  mechanism_id:
  future_basis:          # série/estudo/cenário que sustenta a extensão ao futuro
  sensitivity_check:     # ok | instavel
  publication_decision:  # publicada | retida
```

Rótulo público da classe (único vocabulário permitido para o futuro):

| `transformation_class` | Rótulo público |
|---|---|
| `mudanca_observada` | **Mudança já em curso** |
| `tendencia_sustentada` | **Tendência para os próximos anos** |
| `estudo_setorial` | **Tendência para os próximos anos** |
| `cenario` | **Tema presente nos cenários** |

O rótulo público é **derivado** pelo compilador (Rodada 7) a partir de
`transformation_class` — campo público `future_label`, preenchido antes da
remoção de `internal` e validado contra esta tabela. Nenhum texto autoral
digita o rótulo.

### 3.3 Regras estruturais

- Campo público vazio = cartão inválido (fail-closed no gerador; nenhum bloco renderiza vazio). **Vazio** = string em branco após trim, array `[]`, ou array contendo apenas strings em branco. Itens de `pne_topics`, `monitoring_indicators` e `sources` são strings não vazias e únicas e, desde a Rodada 2, resolvem por label exato contra `catalogo-referencias.json` (item em branco, desconhecido ou duplicado = violação individual). O `internal.mechanism_id` resolve contra `catalogo-mecanismos.json`, e a direção do cartão deve estar entre as direções permitidas do mecanismo.
- A serialização pública **constrói um objeto novo por allowlist** dos campos públicos da direção — não apenas remove `internal`. Campo desconhecido no autoral não passa; nenhuma chave interna (`mechanism_id`, checks, `publication_decision`, `transformation_class`, `future_basis`) pode existir no resultado. O teste de contrato verifica.
- `publication_decision: publicada` exige todos os checks internos `ok` (e, na segunda saída, `future_basis` preenchido). Qualquer check reprovado força `retida`. Cartão `retida` não aparece e não gera mensagem. Hoje a decisão é declarada e auditada pelo gate; quando o motor de candidatos existir (Rodada 5), ela passa a ser **derivada** do registro de gates G1–G10, nunca digitada.
- Uma mesma história não é dividida em vários cartões de pares; um cartão carrega a história inteira.

### 3.4 Evolução prevista da camada interna (compromissos das próximas rodadas)

Lacunas apontadas pela revisão adversarial da R1 que este contrato assume como
evolução, na rodada que o plano já destina a cada uma:

| Compromisso | Rodada |
|---|---|
| Fato estruturado com id, série/indicador, valor+unidade, janela e `source_id`; cada trecho narrativo referencia os fatos que o sustentam (torna G10 verificável) | R5 (Etapa 6) e R7 (Etapa 9, camada 1) |
| Registro interno dos gates G1–G10 por cartão; `publication_decision` derivada | R5 |
| Componentes estruturados da questão de planejamento (público/etapa, fenômeno, recorte, indicador) validados estruturalmente, não por regex | R5 |
| `future_basis` estruturada por tipo (série/projeção/estudo/cenário) com janela observada e `scenario_id` obrigatório para qualquer valor futuro | R6 |
| Schema autoral e projeção pública com `additionalProperties: false` nos dois lados | R7 (compilador) |

---

## 4. Requisito da gestora → bloco da página

| Requisito (plano §2.1) | Campo/bloco |
|---|---|
| o que mudou | `education_facts` / `territorial_facts` + bloco 2 |
| qual parte da mudança acompanha demografia, trajetória, oferta | `integrated_reading` (decomposição traduzida) |
| características do território que ajudam a interpretar | `territorial_facts` + `integrated_reading` |
| variação entre municípios | `municipal_pattern` / `exposed_groups_or_municipalities` |
| questão concreta de planejamento | `planning_question` / `education_agenda` |
| transformação em curso | `territorial_transformation` + bloco 2 |
| ponto de partida educacional | `education_starting_point` |
| temas e metas do PNE | `pne_topics` |
| indicadores a acompanhar | `monitoring_indicators` |
| comparação temporal | `period`/`horizon` + fatos com janelas; incorporada, não seção |
| fontes | `sources` (detalhe recolhido) |

---

## 5. O que nunca aparece ao usuário

Nenhum destes, em nenhum campo público (a lista operacional, com padrões, vive em `vocabulario.json`):

1. **Método estatístico**: correlação, Pearson, Spearman, significância, p-valor, coeficientes.
2. **Força e grau**: relação fraca/moderada/forte, escada E1–E5, grau de evidência (V6-D2).
3. **Maquinaria interna**: triagem (automática), lead, note, decomposição Bennett, shift-share, efeito demográfico, efeito taxa, taxa de atendimento aparente, universo incompatível, fail-closed, gates/checks internos, hipótese. *Nota: o plano (§9.2) veda "hipótese a verificar"; este contrato amplia deliberadamente para qualquer uso de "hipótese" na camada pública — decisão editorial da R1, registrada aqui.*
4. **Mensagens negativas** (§3.6 do plano): "não foi possível medir", "relação fraca", "dados insuficientes", "cenário ausente"/"não há cenários", "hipótese a verificar", "não se pode concluir", "a plataforma não possui dados". **Ausência é silêncio**, nunca conteúdo.
5. **Recomendações genéricas** (§3.7): "aprofundar a análise", "acompanhar os dados", "realizar ações", "investigar as causas" sem sujeito, etapa, fenômeno e indicador.
6. **Causalidade**: causou/provocou/acarretou/determinou/é responsável por/por causa de. A proteção contra conclusão indevida é a redação, não o aviso.
7. **Listas técnicas**: relações descartadas, classificações da triagem, detalhes de método como conteúdo de primeiro nível.

Traduções obrigatórias (interno → público, plano §9.3):

| Interno | Público |
|---|---|
| efeito demográfico | parte da mudança ligada ao tamanho da população |
| taxa de atendimento aparente | matrículas em relação à população da idade |
| defasagem de seis anos | seis anos depois |
| correlação das variações | mudanças ocorridas no mesmo período |
| contribuição municipal | participação de cada município na mudança regional |
| público elegível da EJA | adultos que ainda não concluíram essa etapa |
| shift-share | componentes da mudança do emprego |
| cenário invariante | questão que permanece importante em diferentes futuros |

---

## 6. Texto de enquadramento da página

Texto fixo, único aviso metodológico da página (adotado do plano, Etapa 1.8):

> Esta página reúne mudanças da educação e do território ao longo do tempo. Os dados são apresentados em conjunto quando ajudam a interpretar uma mesma questão de planejamento. A leitura não atribui automaticamente uma mudança à outra.

---

## 7. Guia editorial

### 7.1 Título

- Frase completa com a leitura principal ("A queda das matrículas no ensino médio acompanha principalmente a redução da população jovem"), nunca rótulo de par ("Matrículas × população 15–17").
- O título deve continuar verdadeiro se lido sozinho, sem o corpo do cartão.
- O título descreve o mesmo período e a mesma métrica que o corpo (problema P4 da auditoria: título de pontas com métrica de variações anuais é proibido).

### 7.2 Números

- Todo número público tem período e fonte reconstruíveis (fato estruturado por trás).
- Arredondamento só na exibição; valores absolutos com separador de milhar; variações com sinal e uma casa decimal.
- Sem número futuro fora de cenário publicado (V6-D5).
- Taxas acima de 100 não recebem nota técnica no cartão principal: a redação usa a forma "para cada 100 pessoas na idade, há X matrículas, o que inclui alunos de outras idades ou de outros municípios" apenas quando a leitura precisar do valor; caso contrário, o valor fica na camada de consulta.

### 7.3 Tempo

Traduzir sempre a relação temporal: "no mesmo período", "seis anos depois", "desde o início da série", "a mudança começou antes", "a diferença se concentrou nos anos X–Y". Nunca o termo técnico.

### 7.4 Municípios

- Toda leitura regional informa como se distribui: quem mais contribuiu, quem foi na direção contrária, se a mudança está concentrada.
- Leitura que depende quase exclusivamente de um município não é publicada como característica da região (check interno `territorial_check`).

### 7.5 Estratégia de redação (plano §9.5)

Redigir apenas o que os dados permitem; o limite aparece na escolha das frases, não em avisos.

- Evitar: "A relação entre emprego formal e matrícula do ensino médio é moderada e não permite concluir causalidade."
- Preferir: "Enquanto o emprego formal cresceu, a matrícula do ensino médio diminuiu. A queda da população de 15 a 17 anos foi ainda maior, indicando que a mudança demográfica é central para interpretar esse resultado."

### 7.6 Teste de valor (bloqueante, plano §9.6)

Antes de publicar qualquer cartão:

1. O usuário aprende algo que não obteria olhando um único indicador?
2. Há ao menos um fato educacional e um territorial combinados?
3. Existe questão de planejamento específica?
4. O texto se sustenta sem método estatístico?
5. Cada frase tem números e fontes por trás?
6. O conteúdo difere dos demais cartões?

Uma resposta negativa bloqueia a publicação.

---

## 8. Gates de publicação (plano §7)

G1 relevância PNE · G2 mecanismo catalogado · G3 universo compatível · G4 tempo coerente · G5 estabilidade (janela/município dominante) · G6 valor além dos indicadores isolados · G7 questão de planejamento concreta · G8 clareza sem jargão · G9 não redundância · G10 rastreabilidade total.

Falha em qualquer gate = cartão não publicado, sem mensagem. G2/G3 são verificáveis por máquina desde a Rodada 2: o catálogo de mecanismos (M1–M7, default-deny — nenhum par fora de `paresPermitidos`/`paresProvisorios` alimenta cartão) e o registro canônico de séries (universo, lente territorial, faixa etária, denominadores) sustentam `validatePair` e `validateCardCatalog`, que bloqueiam os erros conhecidos do piloto (população 0–14 × ensino médio, cadastro social como denominador de EJA, vínculos totais como trabalho juvenil, lente mista não declarada, fotografia censitária como série anual). G5 depende das validações internas (Rodada 5); G8 e a parte formal de G10 já são verificáveis por este contrato (linter + testes).

---

## 9. Verificação por máquina

| Artefato | Papel |
|---|---|
| `scripts/checks/fixtures/vocacoes-pne/vocabulario.json` | Fonte canônica das regras de linguagem (termos, frases, padrões, rótulos permitidos). Versionado; muda só por decisão de gate. |
| `scripts/checks/fixtures/vocacoes-pne/exemplos-cartoes.json` | Exemplos aprovados (0 violações) e reprovados (violações esperadas nomeadas). Corpus dos testes; os números dos aprovados são ilustrativos (do plano) e serão recalculados na Etapa 6 antes de qualquer publicação. |
| `scripts/lib/vocacoes-pne-linter.mjs` | Linter: aplica o vocabulário a todos os campos públicos de um cartão; valida estrutura, decisão de publicação e serialização pública. |
| `scripts/checks/vocacoes-pne-linguagem.test.mjs` | Linter × corpus + injeção sintética de cada regra. |
| `scripts/checks/vocacoes-pne-contrato.test.mjs` | Schema, mínimos/máximos, coerência de `publication_decision`, remoção de `internal`. |
| `scripts/checks/fixtures/vocacoes-pne/catalogo-mecanismos.json` | Catálogo versionado M1–M7 (Etapa 2): pergunta, justificativa, universo de referência, pares permitidos/provisórios, leitura pública máxima, afirmações proibidas, disponibilidade. Substância muda só por decisão de gate. |
| `scripts/checks/fixtures/vocacoes-pne/registro-series.json` | Registro canônico das séries (Etapa 3), GERADO por `scripts/generate-vocacoes-pne-registro.mjs` (`--check` byte a byte): universo, lente territorial, faixa etária, `ratioOf`, status (`disponivel_plataforma` / `disponivel_pesquisa` / `pendente_*`). |
| `scripts/checks/fixtures/vocacoes-pne/regras-universo.json` | Taxonomia de universos e lentes, classificação por padrão, dicionário de denominadores (adequados e proibidos) e ordem das regras de par com `reasonCode`. |
| `scripts/checks/fixtures/vocacoes-pne/catalogo-referencias.json` | Catálogos de temas do PNE, indicadores de acompanhamento e fontes; itens dos cartões resolvem por label exato. |
| `scripts/lib/vocacoes-pne-registro.mjs` | Loaders fail-closed + referências cruzadas (mecanismos × registro × referências). |
| `scripts/lib/vocacoes-pne-compatibilidade.mjs` | `validatePair` (default-deny + regras de universo, janela e lente) e `validateCardCatalog` (mecanismo, direção, itens de catálogo). |
| `scripts/checks/vocacoes-pne-mecanismos.test.mjs` | Catálogo × corpus × triagem do pacote (default-deny). |
| `scripts/checks/vocacoes-pne-series.test.mjs` | Registro × pacote publicado + bloqueio nomeado dos erros conhecidos. |

O linter é **necessário, não suficiente**: ele captura vocabulário e estrutura; valor, mecanismo e universo são gates editoriais e das rodadas seguintes.
