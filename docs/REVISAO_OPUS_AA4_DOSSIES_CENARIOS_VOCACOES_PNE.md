# Revisão Opus AA4 — dossiês e cenários Vocações–PNE

## Consulta inicial

- Modelo exigido: `claude-opus-5`.
- Esforço: máximo, fixado pelo executor protegido.
- Ferramentas e navegação do revisor: desabilitadas.
- Evidência enviada: plano e pacote técnico focalizado do AA4, sem credenciais,
  dados pessoais, `.env` ou arquivos alheios ao estágio.
- Resultado: `ON_TRACK`.
- Confiança: 0,72.
- SHA-256 do parecer:
  `f6e2d22c2022331992e2e45d50d6e69178cdea26d8681c745d9361f15880d687`.

O Opus reconheceu os entregáveis estruturais, a preservação dos resultados negativos,
a decomposição exata, os limites de P5/P7/P8, os cenários condicionais, as agendas,
as guardas de dados externos e a reprodutibilidade. Recomendou não iniciar o AA5 até
fechar lacunas de evidência e ambiguidades de transição editorial.

## Achados aceitos e correções

### Recortes aninhados

Aceito. Nova Santa Rita (`4313375`) integra os dez códigos do Vale. O contrato, os
dois pacotes de escopo, D1 e a visualização D1 agora declaram que município e região
são recortes aninhados, não comparadores independentes. A síntese regional também
explicita soma de contagens, mediana municipal de taxas quando aplicável e preservação
da heterogeneidade no AA2.

### Cinco agendas para dez dossiês

Aceito como lacuna de mapeamento, não como falta de agenda. As agendas são cinco
temas compartilhados entre os dois recortes. Cada uma agora contém:

- dois mapeamentos dossiê–escopo;
- uma variante Nova Santa Rita;
- uma variante Vale;
- papel territorial, baseline e gatilho próprios por variante.

O QA `AA4_AGENDA_SHARED_SCOPE_VARIANTS` prova a cobertura 5 × 2.

### Ruralidade e inclusão/AEE

Aceito como omissão do pacote enviado ao revisor. A implementação já continha as
séries; contrato, saída e relatório agora registram a disposição dos quatro eixos:
ruralidade e inclusão/AEE incluídas como contexto P7; contexto social incluído como
relação não testada; financiamento bloqueado.

### Residual demográfico no cenário

Aceito. O cenário demográfico agora afirma literalmente que o residual é termo
contábil e não é migração, cobertura, comportamento ou resposta institucional. Fluxos
residência–escola aparecem como dados adicionais a investigar, não como significado
do residual. O QA `AA4_P2_SCENARIO_RESIDUAL_GUARD` verifica o texto.

### Cenários não intercambiáveis

Aceito. Além do booleano, cada cenário passou a ter domínio decisório, famílias
primárias de indicadores, população exposta e referência explícita aos outros dois.
O QA compara mecanicamente as três assinaturas. O AA5 não pode reduzir o conjunto
abaixo de três sem reabrir o AA4.

### Valor além de gráficos separados

Aceito. Cada dossiê precisa passar simultaneamente por seis critérios: integração
educação–território; duas direções; lente temporal/comparativa; vínculo evidência–
decisão; fronteira interpretativa; justificativa específica. O QA
`AA4_INCREMENTAL_VALUE_RUBRIC` substitui a confiança isolada em um campo declaratório.

### D1 e banda de predição

Aceito. O contrato visual D1 agora carrega o estado com P3
`NO_ROBUST_ASSOCIATION` e proíbe ler a banda como meta, previsão municipal, padrão
esperado de desempenho ou prova de associação.

### Estados de disponibilidade

Aceito como evidência faltante. O pacote agora registra as contagens do painel
congelado (`observed`, `observed_zero`, `unavailable`) e uma política explícita para
todos os estados: indisponível e suprimido nunca viram número ou zero; não aplicável
vira `null` com estado; ausência de linha nunca é zero. O QA verifica a política e a
existência dos estados observados no insumo.

### Fatos não referenciados

Aceito. A contabilidade agora distingue 119 fatos visíveis, quatro somente técnicos,
123 referenciados no total e 169 fatos de suporte. Estes últimos são séries completas,
pontos excluídos por suficiência visual ou trilha de auditoria; ficam reproduzíveis
sem redundância gerencial. Todos os 123 IDs resolvem dentro dos 292.

### Precisão e manifesto

Aceito. As duas decomposições são documentadas com a mesma precisão armazenada. O
relatório distingue manifestos candidatos, cujo `pythonHashSeed` varia, do manifesto
normalizado final, que contém os dois seeds e é byte-reprodutível com entradas
congeladas.

## Achados não aplicados literalmente

### Criar um quarto cenário

Não aplicado. Era mitigação de risco baixo, não requisito. Um quarto cenário sem base
substantiva poderia forçar relação. A correção adotada é mais forte para o contrato:
o AA5 não pode reduzir os três cenários do piso sem reabrir o AA4.

### Usar nível de responsabilidade `external`

Não aplicado como obrigação. O plano exige que cada agenda tenha um nível entre os
permitidos, não que use todos. A agenda EPT é `regional/shared` e nomeia Estado,
instituições técnicas e municípios como contribuintes, refletindo responsabilidade
compartilhada sem atribuir comando externo indevido.

### Ausência de ruralidade/AEE na implementação

Rejeitado como fato. Os dados, fatos e visual transversal já existiam. A crítica foi
válida como insuficiência do pacote enviado e resultou em disposição explícita.

### Adjacência P4/P6 apenas em prosa

Rejeitado como fato. O QA já verificava estado terminal, `displayMode` recolhido e
`standaloneCoefficientAllowed=false`. A documentação passou a citar o check para
facilitar auditoria externa.

## Releitura focalizada

- Resultado: `ON_TRACK`.
- Confiança: 0,68.
- SHA-256:
  `79c6144e02357e1b20dbf9c809b7f2f661a95e766464336a3af386b034bde300`.

O Opus considerou a entrada no AA5 suportável, condicionada a um adendo curto. O
adendo foi aplicado antes do avanço:

- toda visualização regional passou a carregar o método de agregação; taxas medianas
  dizem explicitamente que não são taxa regional ponderada;
- `AA4_REGIONAL_AGGREGATION_LABELS` verifica rótulos e fronteira;
- dois controles negativos mutam os cenários e a rubrica incremental e comprovam que
  os checks falham quando a restrição é violada;
- o relatório apresenta uma agenda completa, os tetos/checks de entrada, os fallbacks
  de séries curtas e a cadeia de hashes por escopo.

Não foi aceita a sugestão de exigir uma terceira revisão externa: o segundo parecer
autorizou o AA5 mediante condições objetivas, agora todas verificadas localmente.

## Estado após reconciliação e adendo

- QA: 45/45 aprovado, incluindo o gate do recibo Opus e autorização do AA5.
- Testes focados: 15/15 aprovados, incluindo dois controles negativos.
- Processos independentes: seeds 505 e 606, bytes idênticos.
- Conjunto não manifesto:
  `1db90f4fa82d48708d9c126e0b4436259db17a7f908f36ffa1779bc69de68778`.
- Árvore final:
  `80b59cd630274849d32080381ebf0e7713853afc077f0806344595ae29956211`.
- `public/data`:
  `7efdf16f57a8e8da0c26fd27daa8e1331a427fa4376d8929c568ff471a0dafdd`
  antes e depois.

O AA4 está concluído para entrada no AA5. A validação humana da gestora permanece
pendente e não é representada como realizada.
