# Fechamento metodológico da Meta 11.b — 15–29 e 15 anos ou mais

Data da rodada: 28 de julho de 2026.

## Decisão

A barreira metodológica identificada na auditoria anterior foi resolvida. O
denominador do indicador 15–29 deixou de usar `populacao_idade_rs` e passou a
ser formado com componentes censitários de 2022 compatíveis com o numerador.
Foi criado o indicador exato de 15 anos ou mais, o 15–29 foi preservado e
reconciliado, e a relação pública 18+ foi retirada somente da Meta 11.b.

O contrato promovido é o 1.4.0, com SHA-256 normalizado
`c40d40f7ab0789161fe1237d451537aedef9c5e5eab80c57b823f0e1d5b95228`.
A política editorial promovida é a 1.2.0, com SHA-256 normalizado
`f6833a5f227b3dfc2e0097e8cfc72223ec3534c4b28ad7c0e12b0f6d6c15971a`.

## Matriz final das relações

| Relação | Recorte e referência | Modo público | Tratamento |
| --- | --- | --- | --- |
| `relation.11.b.fundamental_concluido_15_29` | 15–29; 100% em 2036 | `progress`, com distância, status e comparação estadual; sem projeção | preservada e recalculada com denominador censitário compatível |
| `relation.11.b.fundamental_concluido_15_mais` | 15+; 85% em 2036 | `progress`, com distância, status e comparação estadual; sem projeção | criada como segundo card público da Meta 11.b |
| `relation.11.b.fundamental_concluido_18_mais` | 18+ | `hidden` na Meta 11.b | indicador bruto preservado para outros contextos educacionais; ausente do ciclo, Diagnóstico, impressão, relatório e workbook da Meta 11.b |

A política mantém o 15–29 na ordem 19 e coloca o 15+ na ordem 20. A Meta 11.b
possui exatamente dois resultados públicos.

## Fonte, universo e categorias

O snapshot combina:

- o componente municipal de 15–17 anos já reproduzido pelo pipeline local;
- a tabela IBGE/SIDRA 10061, Censo Demográfico 2022, para as faixas 18–24,
  25–29 e 18 anos ou mais.

Entram no numerador de 18 anos ou mais as categorias:

- Fundamental completo e Médio incompleto;
- Médio completo e Superior incompleto;
- Superior completo.

Ficam fora do numerador as pessoas sem instrução ou com Fundamental
incompleto. A tabela 10061 de 2022 não oferece categoria municipal separada de
instrução indeterminada; valores suprimidos ou ausentes tornam o componente
indisponível, sem conversão em zero. Denominador zero não produz percentual.
Valores negativos são inválidos. O resultado é um snapshot de 2022: não há
interpolação, tendência ou projeção.

As fórmulas são:

- 15–29: componente elegível 15–17 + categorias concluídas 18–24 e 25–29,
  dividido pelo total 15–17 + totais 18–24 e 25–29;
- 15+: componente elegível 15–17 + categorias concluídas 18+, dividido pelo
  total 15–17 + total 18+.

A referência do Rio Grande do Sul é sempre razão de somas dos numeradores e
denominadores municipais, nunca média simples de percentuais.

## Proveniência reproduzível

O snapshot versionado está em
`data_pipeline/data/pne_goal_11b_census_2022`. Ele contém a resposta bruta, os
metadados da tabela 10061, o componente local 15–17, os componentes municipais
reconciliados e o manifesto de hashes.

| Arquivo | SHA-256 |
| --- | --- |
| `component_15_17_local_2022.json` | `99111c13db0f6f0791de7bba1e466a79d5e44ee2eee94b849d5b7e826478dc35` |
| `metadata_10061.json` | `173d5bf4e0b54b9980ce87eccf6eef9c76dd44416e6f1cb0bce981b7a7161927` |
| `municipal_components.json` | `f340630018b4e20837e0df7ec0a6438a4a404a5838866b44992f371cc8a0922f` |
| `response_10061_rs_2022.json` | `5c1e0b95a03c947bd7c5b32711f641fff917e8f7efee416c078ce7f6cd470eed` |

A cobertura é de 497 municípios. Os numeradores oficiais e locais de 18–29 e
18+ coincidem nos 497 casos. A razão estadual de 2022 é 83,3168775111% para
15–29 (`1.838.736 / 2.206.919`) e 67,5494251531% para 15+
(`6.062.619 / 8.975.086`).

## Staging, comparação e validação

Foram gerados dois stagings independentes, byte a byte idênticos:

- `C:\tmp\pne-diagnostic-v3-staging-11b-full-a`;
- `C:\tmp\pne-diagnostic-v3-staging-11b-full-b`.

O pacote contém 497 municípios e 15.114 resultados. O identificador da release
é `8378537cbf4aef5e35e89c09550f7802e548d15d33eca8b3fe7fa9a915c84dea`;
o SHA-256 do manifesto de staging é
`b1e028f1997a5b2c542298d23a76ba79755b97b294d73c4747f3284295d05377`;
o hash semântico é
`f3ea8d047ef03a2de1cdf17230daecfd32a3a40eb3c0967eb24397aea0d7983d`.
Após os gates, a release foi promovida pelo script oficial. O manifesto da
release tem SHA-256
`1e3b089f5e08ceed62bca2a51fbe8bba28e6bf50fd4d1c97a6481a8de98c3132`
e o novo `current.json` tem SHA-256
`48d96ba0ff59725ddd66066f5fee4e01b13266fc571fd93b00737a83d6a9f0af`.

Contra a release anterior, somente os três registros esperados da Meta 11.b
mudam por município: retirada do 18+, reconciliação do 15–29 e inclusão do
15+. As demais relações são idênticas. No 15–29, a variação ficou entre
0,2605061841 e 13,0296791903 pontos percentuais, com média absoluta de
5,5079422407 pontos; os 497 municípios permaneceram classificados como
`advance`.

Passaram:

- validações dirigidas de limites etários, categorias, ausência, supressão,
  zero, razão de somas, status e cardinalidade 497;
- paridade de contrato e hashes entre JavaScript e Python;
- geração dupla determinística e `--check` oficial de promoção;
- suíte Python completa: 323 testes;
- lint, build e testes de contrato, ciclo, metodologia, Diagnóstico e Educação;
- inspeção do candidato em 1440 px e 390 px, sem overflow horizontal;
- conteúdo de impressão, com exatamente os cards 15–29 e 15+ e sem o 18+ do
  Ensino Fundamental.

O V2 e as releases V3 anteriores
`3832c3417fdf969af52cd706240b1a15784c1e0f29391dc0397992c16c828933`
e `b1780788a3598d6993a02f8180b25ef6d241d31163325b41a9e9b0a7b77e5743`
permanecem preservados, cada uma com seus 497 municípios e manifesto.
