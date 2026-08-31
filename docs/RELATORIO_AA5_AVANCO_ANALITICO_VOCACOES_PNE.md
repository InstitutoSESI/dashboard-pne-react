# Relatório AA5 — seleção editorial e integração oficial Vocações × PNE

**Programa:** `vocacoes-pne-advanced-analytics-v1`
**Etapa:** AA5 — seleção editorial e integração oficial
**Classificação principal:** `DATA_LOGIC`
**Domínios associados:** `DATA_PRESENTATION` e `UI_ONLY`
**Recorte público avançado:** Vale do Sinos e Nova Santa Rita — IBGE textual `4313375`
**Data:** 30 de agosto de 2026
**Estado:** implementação, validação automatizada, inspeção visual e auditoria final Fable concluídas

## Resultado entregue

A página oficial **Vocações da Região** passou a resolver um novo pacote analítico
gerado, validado e versionado para o Vale do Sinos e Nova Santa Rita. O pacote
transforma os dossiês internos do AA4 em uma leitura gerencial com dois sentidos:

1. o que o território ajuda a compreender sobre a educação;
2. o que as transformações do território colocam na agenda da educação.

A nova superfície não publica uma coleção de indicadores isolados. Cada leitura
combina conclusão, duas ou três evidências, comparação territorial compatível,
interpretação, alternativas, limite de afirmação, implicação de planejamento,
indicadores de acompanhamento e fontes. Mecanismos e detalhes técnicos ficam
disponíveis sob expansão, sem competir com a narrativa principal.

## Seleção editorial

Foram promovidas cinco leituras:

1. **Demografia, matrículas e organização da rede** — decomposição contábil exata,
   sem nomear o residual como migração, cobertura ou comportamento.
2. **Trajetória escolar e contexto** — comparação ajustada com intervalo e limite
   público, sem converter a banda em meta ou previsão.
3. **Transformação econômica e educação profissional** — mudança observada e
   correspondência nomenclatural, sem afirmar aderência causal entre ocupações e
   cursos.
4. **Escolaridade adulta, trabalho e EJA** — distribuição por etapa, sem chamar
   público potencial de demanda realizada.
5. **Trabalho juvenil e permanência** — resultado negativo/instável publicado como
   fronteira de inferência e agenda de acompanhamento, não como explicação positiva.

Foram promovidas quatro agendas:

- demografia e programação da rede;
- transformação econômica e articulação regional da EPT;
- escolaridade adulta e coordenação da EJA;
- trajetória, permanência e condições escolares.

A agenda de trabalho juvenil não foi promovida como prioridade autônoma porque a
associação robusta não foi demonstrada. O tema permanece visível dentro da leitura
negativa, com indicadores, gatilhos e condições que fortaleceriam ou enfraqueceriam
a hipótese. Isso preserva o resultado sem produzir ausência ruidosa nem forçar uma
relação.

Ruralidade, inclusão/AEE e contexto social registrado aparecem como três camadas
transversais. São condições de planejamento e investigação, não relações causais
locais. Financiamento não foi promovido porque o AA4 o manteve bloqueado por
insuficiência de alinhamento analítico.

## Verificações estatísticas incorporadas às cinco leituras

As análises ampliadas não criaram uma segunda coleção de cartões. Cada uma das
cinco histórias ganhou um bloco chamado **“O que a verificação adicional
mostrou”**, com estado, recorte, síntese, alcance, consequência para o
planejamento e detalhes recolhíveis. Isso mantém uma narrativa única e impede que
o leitor confunda evidência estadual ou regional com um resultado próprio de Nova
Santa Rita.

Os estados publicados são:

- **padrão consistente no conjunto analisado:** população de 6–10 anos e
  matrículas dos anos iniciais; população de 11–14 anos e matrículas dos anos
  finais. Em 3.479 comparações anuais de 497 municípios, uma mudança de 10% na
  população veio acompanhada, em média, de 6,1% e 7,0% de mudança nas matrículas,
  respectivamente. Os intervalos foram 3,9%–8,4% e 5,1%–9,0%. Valores futuros
  também apresentaram sinal, portanto o resultado não estabelece precedência nem
  causa;
- **sinal para acompanhar:** participação industrial no emprego formal regional e
  matrículas técnicas no ano seguinte. O sinal manteve direção nas verificações,
  mas o resultado ajustado para o conjunto de testes foi 0,136, acima do corte
  pré-registrado de 0,10. Ele aparece somente como monitoramento, com a estimativa
  detalhada recolhida;
- **ligações não confirmadas:** contexto socioeconômico × abandono, localização
  rural da escola × distorção idade-série, tempo integral × abandono, emprego e
  renda × EJA, e trabalho formal juvenil × abandono/aprovação. A ausência de
  confirmação não é apresentada como prova de ausência;
- **comparação bloqueada por incompatibilidade de rede:** contexto
  socioeconômico e aprendizagem não foram combinados porque a aprendizagem
  prioriza a rede pública e o contexto disponível reúne todas as dependências.

A candidata demográfica `DN04`, embora tenha passado o gate numérico principal,
ficou fora da página por fragilidade ao excluir 2020–2021 e insuficiência do
mecanismo teórico. A decisão editorial foi preservada explicitamente no contrato
de evidências.

## Arquitetura de publicação

O contrato de seleção congela os hashes do manifesto e dos artefatos AA4, o
contrato durável das análises ampliadas, os dez códigos IBGE do Vale, Nova Santa
Rita como único município com dossiê avançado e a allowlist de campos públicos. O
gerador:

- lê apenas os artefatos AA4 congelados, a evidência ampliada congelada e o
  registro municipal canônico;
- reconcilia os hashes dos três conjuntos analíticos e recusa mudança de estado,
  escopo, referência ou decisão editorial;
- valida o estado terminal, o QA e a autorização de entrada do AA5;
- preserva código IBGE como texto e zero observado como zero;
- rejeita chaves e termos internos não autorizados;
- materializa JSON determinístico em staging;
- valida conteúdo, hash e tamanho antes da promoção;
- promove transacionalmente, com rollback em falha;
- grava o registro por último.

No frontend, o carregador importa o bundle sob demanda e confere bytes, SHA-256,
tamanho, schema e versão de conteúdo antes de disponibilizá-lo. A resolução pública
é, em ordem:

```text
pacote avançado AA5
  → página oficial anterior
    → narrativa/legado existente
```

O pacote avançado é elegível somente para a visão regional e para Nova Santa Rita.
Os outros nove municípios do Vale continuam na página oficial anterior porque não
possuem dossiê municipal avançado no AA4. Uma falha deliberada do novo bundle aciona
o fallback real, sem deixar a rota vazia.

## Identidade, universos e fórmulas

- Identidade municipal: código IBGE textual de sete dígitos.
- Região: os dez códigos canônicos do Vale do Sinos; Nova Santa Rita é declarada
  como recorte contido, não comparador independente.
- Universo educacional: `total_all_dependencies`.
- Lentes territoriais de residência, escola, trabalho, ruralidade e executor
  continuam separadas.
- Zero observado, `null`, `unavailable`, `suppressed`, `not_applicable` e ausência de
  linha não são fundidos.
- Denominador zero continua produzindo `null`.
- Nenhuma fórmula dos indicadores ou fatos AA4 foi alterada. As novas análises
  estatísticas são uma camada separada e congelada, sem reescrever dados-fonte ou
  outputs públicos de dados.
- A decomposição demografia–matrículas usa os valores brutos do AA4 e mantém o
  fechamento aditivo exato; arredondamento ocorre apenas na apresentação.
- Literatura sustenta mecanismos possíveis e fronteiras, mas não cria efeito local.

## Artefatos e integridade

### Contratos e geração

- `data_pipeline/contracts/vocacoes-pne-aa5-public-selection-v1.json` — SHA-256
  `62c1eda1c5cc5515c3974d50d7831d3d5b966687c051e5acca247dcca8d9e180`.
- `data_pipeline/contracts/vocacoes-pne-aa5-allowlist.json` — SHA-256
  `40e3563833b76bf278d44554aa6c1a103a159deed26412d0622f54d0ca8ea0f5`.
- `data_pipeline/contracts/vocacoes-pne-aa5-expanded-evidence-v1.json` —
  evidências selecionadas, estados de QA, decisões editoriais e hashes dos três
  conjuntos analíticos; SHA-256
  `d032044ad34b3c4a3353e9ae3fd162101c5c2b10a6e6be1db5dd8bb36eb6522e`.
- `scripts/lib/vocacoes-pne-advanced-publication.mjs` — materialização, validação e
  promoção transacional.
- `scripts/generate-vocacoes-pne-advanced-insights.mjs` — entrada de geração e
  verificação `--check`.

### Pacote publicado no aplicativo

- Bundle: `src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json`.
- SHA-256 do bundle:
  `824fb1c726d7cce0c87de97bc577b46246a3023eef95c385d8405d01e2f66017`.
- Tamanho: `99.576` bytes.
- Versão de conteúdo:
  `50a6be88f34d4bf3dc65b50cf1088484a097bda0e95f62ca68afb569f285ddcd`.
- Registro: `src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsRegistry.json`.
- SHA-256 do registro:
  `ebb35b5d451ad34719891cef707d21055d92e8a5b77be96e517c7bb9318d786d`.
- Manifesto AA4 de origem:
  `4d4d10560c8aaf1de4cd569f7d2d80f4bf7ddd7b6fa704a6136af57beaf2d1f5`.
- Conjunto de artefatos AA4 de origem:
  `1db90f4fa82d48708d9c126e0b4436259db17a7f908f36ffa1779bc69de68778`.
- Evidência congelada das análises ampliadas:
  `d032044ad34b3c4a3353e9ae3fd162101c5c2b10a6e6be1db5dd8bb36eb6522e`.

### Contagens públicas

- 5 leituras em cada recorte.
- 5 verificações adicionais em cada recorte: 1 consistente, 1 para acompanhar e
  3 não confirmadas.
- 4 agendas em cada recorte.
- 3 sinais executivos em cada recorte.
- 3 camadas transversais em cada recorte.
- 10 municípios reconciliados no registro regional.
- 1 município com superfície municipal avançada: `4313375`.

## Interface e experiência

Foram criados contrato tipado, carregador fail-closed, resolvedor de superfície,
relatório React e CSS responsivo/imprimível. A página contém:

- síntese executiva orientada a decisão;
- navegação pelas duas direções de leitura;
- cinco cartões de evidência;
- cinco blocos de verificação estatística com alcance e decisão de planejamento;
- visualização específica para a decomposição exata;
- implicações de planejamento sempre visíveis;
- mecanismos, alternativas, limites e fontes recolhíveis;
- quatro agendas com responsável, cadência, gatilho e evidências de revisão;
- três condições transversais;
- rodapé metodológico sobre associação e causalidade.

A inspeção no navegador real cobriu desktop e viewport móvel de `390 × 844`, além
dos testes automatizados de tablet e impressão. Não houve overflow horizontal nem
erro de console. A inspeção visual identificou que a navegação fixa podia encobrir o
título de uma seção ao usar âncora; a correção adicionou margem de rolagem e foi
revalidada com o título inteiramente visível abaixo da navegação.

## Validações executadas antes da auditoria final

- `npm run check:vocacoes-pne-aa5`: aprovado; hash, tamanho, 5 leituras, 4 agendas e
  10 municípios reproduzidos.
- `npm run test:vocacoes-pne-aa5`: 9/9 aprovados.
- `npm run test:vocacoes-pne-aa5:e2e`: aprovado em desktop, tablet, mobile,
  impressão, região e fallback forçado.
- `npm run test:vocacoes-pne`: 112/112 aprovados.
- `npm run typecheck`: aprovado no gate consolidado.
- `npm run lint`: aprovado.
- `npm run check:fast`: aprovado, incluindo build app-only.
- `git diff --check` no escopo AA5: aprovado; somente avisos LF/CRLF.
- Inspeção visual real: desktop e mobile aprovados; console sem erros.
- Auditoria Fable da seleção pré-implementação: `ON_TRACK`, confiança `0,85`; a
  recomendação de agrupar as duas relações demográficas e declarar o salto de
  escopo foi incorporada.

## Auditoria final Fable e reconciliação

O Fable 5 concluiu a auditoria final com veredito `ON_TRACK`, confiança `0,72` e
nenhum bloqueio de alto impacto. Quatro lacunas de evidência foram reconciliadas:

1. **comparação incompatível não é resultado negativo:** o bloco social agora
   mostra, sem expansão, “Três ligações não se confirmaram; uma comparação não
   foi feita” e declara que aprendizagem não foi testada porque os dados não
   cobrem a mesma rede;
2. **fail-closed em caminho negativo:** o teste adultera o contrato congelado e
   comprova rejeição antes da promoção, preservando bundle, registro e um sentinela
   em `public/data`;
3. **estados de disponibilidade:** o texto metodológico visível nomeia zero,
   ausência, indisponibilidade, supressão e não aplicabilidade como estados
   distintos; o zero observado continua testado como `0`;
4. **estimativa de monitoramento recolhida:** o E2E comprova que `0,136` começa em
   detalhes fechados e só aparece visualmente depois da expansão.

As observações sobre bidirecionalidade e comparação temporal eram insuficiência
do pacote enviado ao auditor, não da interface: a página mostra explicitamente os
dois títulos de direção e os cartões exibem períodos e mudanças antes/depois. A
revisão foi preservada em
`.tmp/vocacoes-pne/expanded-relations/fable-final/FABLE_IMPLEMENTATION_AUDIT.json`.

## Efeito externo e exceção de concorrência

- O AA5 não contém `public/data` entre seus destinos e não executou gerador de dados
  públicos.
- Banco: não usado.
- Rede para aquisição de dados: não usada.
- Build completo: não executado; somente `build:app` por `check:fast`.
- Nenhum commit, push ou pull request foi criado.

O verificador global AA0 recusou a nova árvore mesmo com a allowlist cumulativa do
programa. A recusa não foi causada por um destino do AA5: o working tree contém
alterações paralelas em documentação, Matriz, Regional e centenas de arquivos de
`public/data/pne2026-matriz` e `public/data/regioes`. Esses paths não foram absorvidos
pela allowlist, restaurados ou modificados por esta etapa. Assim, há prova focada de
que o AA5 não escreve em `public/data`, mas não se declara que a árvore pública global
permaneceu invariável enquanto outro trabalho a alterava.

## Pendências após o fechamento técnico

1. preparar o roteiro de validação humana da gestora;
2. registrar a validação humana apenas quando ela de fato ocorrer.
