# Relatório AA4 — dossiês, cenários e agendas Vocações–PNE

## Resultado

O AA4 converteu o painel estadual do AA1, os resultados pré-registrados do AA2 e a
biblioteca teórica do AA3 em um pacote narrativo interno para o Vale do Rio dos
Sinos e Nova Santa Rita. O pacote não é publicação oficial: ele é a entrada
controlada da seleção editorial do AA5.

Foram produzidos:

- cinco dossiês para o Vale e cinco para Nova Santa Rita;
- três cenários condicionais, explicitamente não preditivos e não intercambiáveis;
- cinco agendas de planejamento com condição observada, público, etapa, território,
  ação, nível de responsabilidade, responsáveis, indicadores, baseline, gatilho,
  cadência e evidência que fortalece ou enfraquece a leitura;
- uma camada transversal de ruralidade, inclusão/AEE e contexto social registrado;
- 14 contratos visuais orientados por pergunta e conclusão;
- 292 fatos reconciliados: 119 visíveis na narrativa/agenda/visual, quatro apenas em
  notas técnicas recolhidas e 169 preservados como suporte auditável não redundante;
- 45 verificações fail-closed, sem falha.

## Escopo e identidade

- Classificação: `DATA_LOGIC`.
- Estado: Rio Grande do Sul.
- Região: dez municípios canônicos do Vale do Rio dos Sinos.
- Município selecionado: Nova Santa Rita, código IBGE textual `4313375`.
- Nova Santa Rita integra os dez municípios do Vale; município e região são recortes
  aninhados, não grupos comparadores independentes.
- Contagens do Vale são somas dos dez municípios e taxas regionais usadas nos
  dossiês são medianas municipais quando indicado. A síntese não substitui a
  heterogeneidade municipal preservada nos artefatos do AA2.
- Escopo educacional: `total_all_dependencies`.
- Identidade municipal: exclusivamente código IBGE textual de sete dígitos.

## O que cada dossiê acrescenta

1. **Trajetória e contexto:** separa resultado bruto, comparação ajustada e teste de
   relação. Em 2025, Nova Santa Rita tinha abandono mediano de 3,2% no ensino médio,
   ante 2,8% no Vale e 1,5% no RS. Adequação docente maior não virou explicação: P3
   permaneceu `NO_ROBUST_ASSOCIATION` e o resultado contextual ficou inconclusivo.
2. **Demografia e rede:** decompõe exatamente a mudança de matrículas. Em Nova Santa
   Rita, a população de 15–17 anos caiu 64 pessoas e as matrículas cresceram 17; o
   componente populacional foi −41,4494767607 e o componente residual territorial +58,4494767607,
   cuja soma fecha +17. No Vale, −5.544,375734534104 + 3.205,375734534102 fecha
   −2.339 matrículas. O
   residual não é rotulado como migração, cobertura, comportamento ou previsão.
3. **Trabalho juvenil e ensino médio:** mostra movimentos simultâneos em unidades
   separadas. Vínculos formais de 15–17 anos cresceram e abandono caiu entre 2019 e
   2025, mas o teste pré-registrado permaneceu `NO_ROBUST_ASSOCIATION`. Coeficiente,
   intervalo e p-valor ficam recolhidos e adjacentes ao estado terminal.
4. **Transformação econômica e EPT:** conecta recomposição setorial/ocupacional a
   uma agenda de mapeamento da oferta e do acesso regional. A ponte curso–ocupação é
   somente correspondência nomenclatural CBO em dois dígitos; não mede demanda,
   empregabilidade, egresso, suficiência ou efeito. Zero observado de EPT em Nova
   Santa Rita é preservado e não é convertido em ausência de acesso regional.
5. **Escolaridade adulta, trabalho e EJA:** mantém residência, localização da escola
   e localização do estabelecimento como universos distintos. As séries de EJA por
   etapa têm 12 pontos anuais e mostram recomposição, mas P6 permaneceu
   `NO_ROBUST_ASSOCIATION`; matrícula não é demanda ou cobertura.

## Camada transversal

Ruralidade, educação especial e AEE aparecem como contagens de organização da
oferta. Elas não medem distância, capacidade, qualidade, suficiência ou efeito, e P7
permanece `NO_ROBUST_ASSOCIATION`. As contagens sociais de dezembro de 2024 são
registros da fonte, não prevalência populacional; sua relação com educação não foi
testada no AA2 (`RELATIONSHIP_NOT_TESTED_IN_AA2`).

Financiamento e capacidade (P8) permanecem integralmente bloqueados da camada
gerencial por `INSUFFICIENT_DATA`.

Disposição explícita dos quatro eixos transversais:

- ruralidade: incluída como contexto P7, sem relação robusta;
- inclusão/AEE: incluída como contexto P7, sem relação robusta;
- contexto social registrado: incluído, com relação educacional não testada;
- financiamento/capacidade: bloqueado por insuficiência de dados.

## Fórmulas e tetos preservados

- A decomposição demográfica usa a identidade exata `M = P × R` e os componentes
  simétricos já pré-registrados no AA2; nenhuma fórmula foi alterada no AA4.
- Mudança absoluta é `fim − início`.
- Mudança percentual é `(fim − início) / início × 100`; início igual a zero produz
  `null` e estado `NOT_APPLICABLE_ZERO_START`.
- Valores brutos permanecem sem arredondamento em `FATOS_RECONCILIADOS_AA4.csv.gz`;
  arredondamento ocorre apenas na prosa de apresentação.
- `observed`, `observed_zero`, indisponibilidade, `null` e não aplicável permanecem
  estados diferentes.
- O painel congelado contém 154.230 linhas `observed`, 21.656 `observed_zero` e 1.379
  `unavailable`. Linhas indisponíveis ou suprimidas não viram número nem zero;
  `not_applicable` permanece `null` com estado explícito; ausência de linha nunca é zero.
- Literatura não cria efeito municipal nem amplia o teto empírico do AA2.

## Cenários e agendas

Os cenários cobrem três decisões distintas:

- pressão demográfica e organização da rede;
- recomposição econômica e acesso regional à EPT;
- escolaridade adulta e coordenação da EJA.

Todos usam a forma “se... então investigar/decidir...”, sem produzir número futuro.
O contexto social registrado entra com fronteira explícita: não é prevalência e sua
relação com EJA não foi testada.

As cinco agendas são temáticas e compartilhadas, com mapeamento explícito de cada
dossiê para sua agenda e duas variantes obrigatórias: Nova Santa Rita e Vale. Cada
variante tem papel territorial, fatos de baseline e gatilho próprios. Os níveis de
responsabilidade são `municipal` ou `regional/shared`. Nenhum item é promovido
automaticamente a prioridade do PME; o gatilho e a cadência determinam quando
reavaliá-lo.

O AA5 não pode reduzir os três cenários abaixo do piso do AA4 sem reabrir este gate.
Cada cenário possui domínio decisório e famílias de indicadores diferentes, além de
declarar os outros dois cenários com os quais não é intercambiável.

## Política visual

- D1: ponto, benchmarks e banda de predição; a incerteza domina a leitura.
- D2: waterfall somente porque a identidade é aditiva e fecha exatamente.
- D3: barras início–fim em painéis e unidades separados; sem dispersão e sem eixo duplo.
- D4: barras horizontais ranqueadas e faixa de correspondência nomenclatural.
- D5: pequenas múltiplas de 12 pontos anuais por etapa.
- Camada transversal: cartões início–fim, sem inferência de acesso ou efeito.

Cada contrato registra pergunta, takeaway, fatos, suficiência de dados, fallback,
unidades, distinção não cromática e máximo de duas raízes de cor.
O limiar contratual para uma tendência principal é oito pontos temporais: sete pontos
de vínculos juvenis e três de EPT não passam; doze pontos por etapa da EJA passam.

No D1, a banda não pode ser apresentada como meta, previsão municipal, padrão
esperado de desempenho ou prova de associação de P3. A própria visualização carrega
o estado `CONTEXT_COMPARISON_COMPLETE_WITH_P3_NO_ROBUST_ASSOCIATION`.

Toda visualização regional carrega a forma de agregação. Para taxas de D1 e D3, a
legenda informa que se trata de mediana municipal, não de taxa regional ponderada.
Contagens aparecem como somas dos dez municípios. O check
`AA4_REGIONAL_AGGREGATION_LABELS` vincula esses rótulos ao contrato visual.

Séries abaixo de oito pontos não são usadas para afirmar tendência: os sete pontos de
trabalho juvenil viram barras início–fim em unidades separadas; os três pontos de EPT
viram estado início–fim e faixa nomenclatural. Os valores permanecem como fatos de
suporte e a narrativa fala em mudança observada, não tendência estimada.

## Valor além de gráficos separados

Cada dossiê passa por uma rubrica mecânica que exige simultaneamente: integração
entre educação e território; os dois sentidos de leitura; lente temporal ou
comparativa; vínculo entre evidência e decisão; fronteira interpretativa pública; e
justificativa específica de valor incremental. Os 10 dossiês passaram. Isso impede
que a presença isolada do campo `incrementalValue` seja tratada como prova suficiente.

Os 169 fatos não referenciados na camada gerencial são séries intermediárias completas,
pontos excluídos por suficiência visual ou suporte de auditoria. Eles permanecem no
CSV para reprodução, mas não são repetidos na narrativa. A integridade referencial
foi verificada: todos os 123 fatos referenciados resolvem dentro dos 292.

## Fontes congeladas

- AA1: painel analítico, catálogo e manifesto.
- AA2: resultados, robustez, heterogeneidade, comparações de escopo, claims e manifesto.
- AA3: biblioteca de mecanismos, fronteiras, evidências, QA e manifesto.
- Plano de execução avançada e contrato AA4.

Não houve aquisição de fonte, consulta a banco nem alteração metodológica.

## Artefatos e integridade

Raiz interna: `.tmp/vocacoes-pne/advanced-analytics-v1/aa4/`.

- `DOSSIES_VALE_AA4.json`: SHA-256
  `74e58cae6005b6bbdb523370c92b77c140d60d7f67c81b0f852893eeb00e7493`.
- `DOSSIES_NOVA_SANTA_RITA_AA4.json`: SHA-256
  `4902aee5c915a968a9b72b6c7fd6412edc4e5d066af31d026c318ca3055bbd49`.
- `CENARIOS_CONDICIONAIS_AA4.json`: SHA-256
  `a3f6aa3359aa9c8fb24b20b05638b8b02ef0dffdc861f5bcae70b7565d6beb34`.
- `AGENDAS_PLANEJAMENTO_AA4.json`: SHA-256
  `fb8c44eceacdf621b2aa328ed9e9c32e5d57432b85b6a4be4c3e039925de56bb`.
- `MAPA_VISUAIS_AA4.json`: SHA-256
  `31546ef667508369990b981ef9c875e00edd13c6680e031637a67562b1f783eb`.
- `FATOS_RECONCILIADOS_AA4.csv.gz`: SHA-256
  `27d05ab5aa13b6d520fe17bf106e8192b529f9ec40e6121e65406dd76b218647`.
- `QA_SUMMARY_AA4.json`: SHA-256
  `cd4918303d6c7d1d78fd4105ca70c26db443e68563ee2610c8c137ef7d770648`.
- Conjunto não manifesto: SHA-256
  `1db90f4fa82d48708d9c126e0b4436259db17a7f908f36ffa1779bc69de68778`.
- Árvore final: SHA-256
  `80b59cd630274849d32080381ebf0e7713853afc077f0806344595ae29956211`.
- Manifesto: SHA-256
  `4d4d10560c8aaf1de4cd569f7d2d80f4bf7ddd7b6fa704a6136af57beaf2d1f5`.

Dois processos independentes, com `PYTHONHASHSEED=505` e `606`, produziram todos os
artefatos não manifestos com os mesmos bytes. Após normalização da evidência de
execução, as árvores completas ficaram idênticas. A promoção usou staging, validação,
`os.replace` e rollback para o diretório anterior.

Antes da normalização, o único campo operacional variante é `pythonHashSeed`; o
manifesto também registra o estado provisório de verificação. O manifesto citado
acima é o manifesto normalizado compartilhado: contém ambos os seeds e os digests
pré-normalização e é reprodutível com as entradas congeladas.

## Validações executadas

- `python -m py_compile` no módulo, runner e teste AA4: aprovado.
- runner `--verify-inputs`: 17 hashes aprovados.
- runner `--probe`: 45 verificações, zero falha.
- runner `--materialize`: dois processos idênticos e promoção transacional aprovada.
- runner `--check`: aprovado.
- `pytest data_pipeline/tests/test_vocacoes_pne_dossiers.py -q`: 15 aprovados,
  incluindo dois controles negativos que violam deliberadamente não
  intercambialidade e valor incremental e comprovam falha dos checks correspondentes.
- `git diff --check` no escopo AA4: aprovado.

## Efeito externo

- `public/data` antes e depois:
  `7efdf16f57a8e8da0c26fd27daa8e1331a427fa4376d8929c568ff471a0dafdd`.
- Dados públicos modificados pelo AA4: nenhum.
- Banco: não usado e bloqueado.
- Rede para dados: não usada e bloqueada.
- Build completo: não executado.

## Reconciliação inicial do Opus

A auditoria inicial, SHA-256
`f6e2d22c2022331992e2e45d50d6e69178cdea26d8681c745d9361f15880d687`,
retornou `ON_TRACK` com confiança 0,72. Foram aceitos e implementados os pontos sobre:
contenção de Nova Santa Rita no Vale; variantes de escopo das agendas; disposição de
ruralidade e inclusão/AEE; guarda do residual também no cenário; teste mecânico de
cenários; rubrica de valor incremental; guarda visual de D1; contabilidade dos fatos
de suporte; política de disponibilidade; piso de três cenários; precisão uniforme e
manifesto normalizado.

Não se criou um quarto cenário porque o contrato exige três e agora impede o AA5 de
reduzir o conjunto sem reabrir o AA4. Também não se forçou responsabilidade `external`:
o plano exige um nível válido por agenda, e a EPT foi corretamente classificada como
`regional/shared`, com Estado e instituições entre os contribuintes.

## Releitura Opus e adendo de entrada do AA5

A releitura focalizada, SHA-256
`79c6144e02357e1b20dbf9c809b7f2f661a95e766464336a3af386b034bde300`,
retornou novamente `ON_TRACK`, confiança 0,68, e autorizou o início do AA5 mediante
um adendo de evidência. O adendo foi cumprido:

- agregação regional rotulada em cada visual e verificada pelo novo check;
- 15 testes, incluindo mutações que provam que dois gates estruturais falham;
- tetos reatestados com checks: `AA4_EDUCATION_SCOPE`,
  `AA4_P5_CBO2_NOMENCLATURE_ONLY`, `AA4_SOCIAL_CONTEXT_NOT_TESTED`,
  `AA4_PERCENT_CHANGE_ZERO_DENOMINATOR_NULL` e uso de valor bruto no fechamento D2;
- agenda completa demonstrada no artefato, além do check
  `AA4_FIVE_COMPLETE_AGENDAS`;
- fallback explícito para séries abaixo do limiar temporal;
- cadeia de hashes e escopos descrita abaixo.

Exemplo completo, agenda demografia–rede: condição observada de divergência entre
população 15–17 e matrículas; público de 15–17 e estudantes do ensino médio; etapa
ensino médio; territórios Nova Santa Rita e Vale; ação de cruzar residência–escola,
capacidade, vagas e transporte antes da programação; responsabilidade
`regional/shared`; liderança do planejamento da rede; contribuintes de planejamento,
Estado e municípios do Vale; indicadores de população, matrículas, componentes e
fluxos; baselines próprios por variante; gatilho de duas atualizações ou mudança de
capacidade; cadência anual; e condições explícitas de fortalecimento/enfraquecimento.

Cadeia de hashes:

- `f6e2d22c…`: JSON da auditoria Opus inicial; não é digest do pacote.
- `79c6144e…`: JSON da releitura Opus; não é digest do pacote.
- `f60d178a…` → `ce7b6a46…` → `1db90f4f…`: conjunto dos sete artefatos não
  manifestos antes do adendo, depois do adendo e após incorporar o recibo Opus final.
- `5c729f45…` → `35ea699a…` → `80b59cd6…`: árvore AA4 completa normalizada nas
  mesmas três versões.
- `0613e2ef…` → `66e34a08…` → `4d4d1056…`: manifesto AA4 normalizado nas mesmas
  três versões.
- `7efdf16f…` → `7efdf16f…`: árvore `public/data`, invariável.

As diferenças pré-normalização entre os dois manifestos candidatos limitam-se ao
`pythonHashSeed` operacional. A normalização substitui esse campo por
`MULTI_PROCESS_FINALIZED`, grava os seeds 505/606 e os digests candidatos comuns e
produz árvores completas idênticas; nenhuma ordenação de conteúdo analítico varia.

## Estado do gate

O AA4 está concluído e autorizado a entrar no AA5. A validação humana da gestora
continua pendente e não é representada como realizada.
