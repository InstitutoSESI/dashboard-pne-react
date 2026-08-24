# Contrato `matriz-4.0.0` da Matriz de Prioridades

> Decisão registrada em 2026-08-20.
> Publicação registrada em 2026-08-20: a coleção publicada passou a `matriz-4.0.0`, com `peerBenchmark` por sinal no piloto de Nova Santa Rita (4313375).

## Escopo da decisão

A plataforma passa a aceitar documentos municipais `matriz-3.0.0` e
`matriz-4.0.0`. O contrato 4 acrescenta contexto publicado para leitura da
trajetória, distribuição do sinal na rede e comparação de medidas com cidades
parecidas. Nenhum desses elementos é calculado, reconstruído ou classificado no
frontend ou no gerador de publicação: a plataforma valida e renderiza o que a
camada de pesquisa entregou.

O parsing permanece fechado por versão. Um documento 3.0.0 conserva exatamente
os campos anteriores e é recusado se contiver qualquer campo exclusivo da v4.
Em um documento 4.0.0, os campos novos são opcionais; a ausência de qualquer um
deles não produz texto substituto nem mensagem de indisponibilidade.

## Delta do documento municipal

### Trajetória da meta

Cada item de `priorityGoals` pode trazer:

```json
{
  "trend": {
    "previousValueRaw": "34.2",
    "previousYear": "2024",
    "direction": "improved"
  }
}
```

O vocabulário de `direction` é fechado em `improved`, `worsened` e `stable`.
`previousValueRaw` deve ser texto numérico finito, `previousYear` deve seguir
`AAAA` e precisa ser estritamente anterior ao `year` da meta. A unidade é a
mesma da meta e não é repetida no objeto.

### Concentração do sinal na rede

Cada item de `priorityGoals` pode trazer:

```json
{
  "networkConcentration": {
    "measureId": "identificador.da.medida",
    "classification": "concentrated_in_few_schools",
    "affectedSchools": 3,
    "totalSchools": 21
  }
}
```

O vocabulário de `classification` é fechado em
`concentrated_in_few_schools` e `spread_across_network`. `affectedSchools` é
inteiro maior ou igual a zero, `totalSchools` é inteiro maior ou igual a um e o
primeiro não pode superar o segundo. O `measureId` deve existir em `proof` ou
em `collapsed.signals` de uma das ocorrências de `causes` da mesma meta. O
objeto não admite nome nem identidade de escola.

### Mediana dos pares por sinal

Objetos de `proof` e de `collapsed.signals` podem trazer `peerBenchmark` com a
mesma forma usada no benchmark da meta:

```json
{
  "peerBenchmark": {
    "statistic": "median",
    "valueRaw": "6.8",
    "differenceRaw": "1",
    "unit": "percent",
    "year": "2025",
    "n": 88
  }
}
```

`statistic` aceita somente `median`; os valores devem ser textos numéricos
finitos; `n` deve ser inteiro maior ou igual a 20; e `differenceRaw` deve
corresponder ao valor municipal menos a mediana, sem arredondamento
intermediário. `unit` deve coincidir com a unidade do sinal e `year` com seu
`period`. Quando `period` for um intervalo, o benchmark não é permitido. O
campo é opcional, mas, quando presente, deve conter o objeto completo e não
pode ser `null`.

## Manifestos e ingestão

O manifesto de publicação mantém o schema
`pne2026-matriz-manifest-v3`, pois sua forma não mudou, e passa a aceitar
`matrizSchemaVersion` 3.0.0 ou 4.0.0. O loader exige que o documento municipal
tenha a versão declarada nesse manifesto. A ingestão também aceita os
manifestos de origem `matriz-manifest-3.0.0` e
`matriz-manifest-4.0.0`, reconcilia a versão declarada com o documento e mantém
as validações de identidade, data, hashes, grupo de pares e publicação
transacional.

O gerador continua sem produzir análise. Ele valida o documento recebido,
reconcilia o manifesto de origem, revalida a saída em staging e só então
promove o lote de forma atômica e com rollback.

Limitação registrada (2026-08-20): o manifesto publicado declara uma única
`matrizSchemaVersion` para toda a coleção, e o gerador impõe a homogeneidade da
release: quando há entradas de outros municípios a preservar, ele recusa uma
nova ingestão cuja versão do documento ou do manifesto de origem diverge da
publicação existente. A troca de contrato exige republicar todos os municípios
da coleção na mesma versão. Uma migração gradual com municípios 3.0.0 e 4.0.0
convivendo exigiria um manifesto novo com versão por entrada; essa mudança só
deve acontecer com contrato explícito.

## Regras de renderização

- **Trajetória:** aparece no cabeçalho da meta depois da situação, no formato
  `Na leitura de {ano}: {valor} · hoje: {valor} — {leitura pública}.` Os rótulos
  públicos são “avançou desde a leitura anterior”, “recuou desde a leitura
  anterior” e “estável desde a leitura anterior”. A plataforma não acrescenta
  interpretação sobre aumento ou redução de distância.
- **Leitura da rede:** aparece no cabeçalho apenas quando o rótulo público da
  medida é resolvido por um sinal da mesma meta. A leitura pública é
  “concentrada em poucas escolas da rede ({afetadas} de {total})” ou
  “distribuída pelas escolas da rede”.
- **Mediana no cartão:** aparece dentro do fato da medida somente quando o
  sinal selecionado possui benchmark e a curadoria editorial da medida possui
  `peerUse`. A posição usa a diferença publicada, mostra `p.p.` para percentual
  e considera valores de módulo inferior a 0,05 como “na mediana”.
- **Sinal de acompanhamento:** os 14 caminhos possuem uma frase editorial
  visível depois de “Resultado esperado”. A frase nomeia um resultado público e
  a direção esperada para a leitura seguinte, sem promessa de prazo ou de
  resultado. Por ser camada editorial, o sinal independe da versão do artefato
  e aparece também sobre documentos 3.0.0 — “elementos ausentes em 3.0.0”
  refere-se somente aos três elementos dirigidos pelo artefato (trajetória,
  leitura da rede e mediana por sinal).
- **Ausência:** campo ausente não cria linha, placeholder, aviso nem mensagem de
  falta de dado. Identificadores, vocabulários técnicos e classificações cruas
  não são apresentados no HTML.

## Responsabilidade da camada de pesquisa

Continuam fora desta plataforma:

- o cálculo e a classificação de `trend`;
- o cálculo e a classificação de `networkConcentration`;
- o cálculo das medianas e diferenças por medida;
- a definição do grupo elegível para cada comparação;
- a adoção de um limiar de diferença material antes de classificar
  `worse_than_peers`.

O último item é uma decisão metodológica pendente da camada de pesquisa. Este
registro não altera a severidade, a classificação existente nem qualquer dado
publicado.
