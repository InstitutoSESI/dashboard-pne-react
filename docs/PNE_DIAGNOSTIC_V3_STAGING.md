# Diagnóstico PNE V3 — histórico de staging e estado final

## Staging consolidado do contrato 1.8.0

O staging consolidado de 29 de julho de 2026 foi gerado fora de `public/data`,
validado pelo promotor em modo `--check` e promovido sem editar payloads
manualmente. Ele contém 497 municípios e 20.874 resultados: exatamente 42 por
município. Os estados são 17.273 `available`, 3.103 `unavailable`, 498
`not_applicable` e zero `suppressed` nesta fotografia.

Identidades verificadas:

- SHA-256 do manifesto de staging:
  `2da41477eeb759de79fd9f6173c1c086c44938f111ab8478c82fead00855a105`;
- hash agregado e `releaseId`:
  `dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679`;
- hash semântico:
  `3e75fb55510e99d68b564414bb41b8ae0dfeb9161c0df17f051f0326e2ec2e7b`.

O schema municipal passou a `pne2026-public-diagnostic-v4`. Os campos de
componentes são explícitos e tipados:
`numeratorField`/`numeratorValue` e
`denominatorField`/`denominatorValue`. Estados negativos exigem `reasonCode`
e não podem carregar valor, referência, distância, status ou classificação.

> Estado corrente após a rodada acelerada de AEE, atendimento indígena,
> infraestrutura e Educação Superior: consulte
> `docs/PNE_EXPANSAO_ACELERADA_RODADA_4.md`. As seções abaixo preservam o
> histórico das rodadas anteriores.

## Staging das Metas 12.a e 12.b

Dois pacotes completos foram gerados fora de `public/data`:

- `C:\tmp\pne-diagnostic-v3-staging-12a-12b-final-a`;
- `C:\tmp\pne-diagnostic-v3-staging-12a-12b-final-b`.

Os 498 arquivos de cada pacote são idênticos byte a byte. O hash agregado e
release candidato é
`b1780788a3598d6993a02f8180b25ef6d241d31163325b41a9e9b0a7b77e5743`;
o SHA-256 do manifesto é
`7935b13df871cf1e19976e1cd3ba82d8b8ce0f3f887359647a5625fcddfe0255`;
o hash semântico é
`f91a7b35b4f77c9130490545269d45fc454dc45cf2f756e27a9246af8de40bc1`.

O pacote contém 497 municípios, 15.114 resultados, zero duplicidades, zero
inválidos e zero órfãos. São 10.155 resultados `progress`, 4.959
`complementary`, 8.166 `advance`, 1.492 `maintain`, 497 `unclassified`, 413
valores acima de 100% e mínimo/máximo municipal de 25/31.

O último ano observado é 2025. A articulação tem 496 resultados observados e
um `denominator_zero`. Participação pública e expansão subsequente têm, cada
uma, 497 ausências `no_post_baseline_observation`; portanto não aparecem entre
os resultados visíveis. A comparação registro a registro com a release
anterior encontrou divergência somente em
`relation.12.a.medio_tecnico_articulado_percentual`; todas as demais relações
permaneceram idênticas.

## Release histórica derivada do staging 2B2C1.1

O staging fechado na Rodada 2B2C1.1 foi promovido sem alteração dos 497
payloads municipais. A release ativa é:

`3832c3417fdf969af52cd706240b1a15784c1e0f29391dc0397992c16c828933`

O staging usa `municipalities/{id}.json`; a release imutável usa
`releases/<aggregateHash>/municipios/{id}.json`. Os bytes municipais e o hash
agregado são idênticos. O hash semântico normalizado é
`bb04b9aba664cd1ccf365fca2fa88cf26388f8a615703204bb684cab4714628f`.

O staging anterior
`37562de7537cbf783dc3b77d97b128a455a0b6b11ca732a3314dbe365a02cc2e`
permanece rejeitado: ele tratava `relation.4.a.basico_15_17` como `progress` e
não pode ser promovido.

## Contrato e política fixados

- contrato: `pne2026-goal-indicator-contract-v1`, versão `1.2.0`;
- hash do contrato:
  `2d99a5cabfba22e52588771d4218036c7c90567ae26f8e83693137a2cdf6b037`;
- política: `pne2026-diagnostic-presentation-policy-v1`, versão `1.0.0`;
- hash da política:
  `522ff8ef8319863d5a03a2434a33e1aafbaa921ddea0fc77c81966c86bf95edb`.

A relação `relation.4.a.basico_15_17` permanece `complementary`, sem referência,
distância, status, classificação ou projeção. A referência 85%/2036 não é
reconstruída. As metas 12.a e 12.b não foram corrigidas nesta rodada.

## Schema municipal V3

Cada resultado exige `relationId`, `goalId`, `indicatorId` e `dataStatus`.
`year` e `value` são obrigatórios somente em registros `available`. O parser
rejeita campos desconhecidos, relações `hidden`,
identidade canônica incompatível e campos classificatórios em relações
`complementary`.

Campos materiais opcionais autorizados:

`reasonCode`, `numeratorField`, `numeratorValue`, `denominatorField`,
`denominatorValue`, `resolvedReferenceId`, `distance`,
`remainingGap`, `favorableDifference`, `status`, `classification`,
`publicReading`, `stateComparison`, `statewidePosition`,
`similarMunicipalityComparison`, `trend` e `projection`.

Campos V2 depreciados não pertencem ao schema nem ao view model V3:

`tracksGoal`, `tracks_goal`, `hasDistance`, `relationshipType`, `tier`,
`priorityOrder`, `classificationPolicy`, `valuePolicy` e `meta_label`.

## Contagens preservadas

- 497 municípios;
- 15.114 resultados visíveis;
- 10.155 `progress` e 4.959 `complementary`;
- 8.166 `advance`, 1.492 `maintain` e 497 `unclassified`;
- 782 `hidden` excluídos;
- 412 resultados acima de 100%;
- mínimo/máximo municipal de 25/31;
- 31 relações visuais, 8 temas, 9 `essential` e 22 `standard`;
- zero duplicidades.

## Estado após a Rodada 2B2C2C

`current.json` é a única autoridade mutável. O runtime carrega exclusivamente:

1. `current.json` com `cache: no-store`;
2. o manifesto do release apontado;
3. o município dentro do mesmo release.

Não existe feature flag V2, dual run, fallback automático, resolução por
`goalId × indicatorId` ou manifesto raiz. Falhas produzem erro estruturado e
preservam o estado visual operacional; não entregam dados parciais.

A comparação histórica V2 × V3 permanece apenas em checks offline, fora de
`src`, sobre blobs versionados. Os produtores V2 continuam históricos e não
participam da materialização ou promoção V3.

## Rollback e descontinuação

Rollback de dados ocorre com
`promote_pne2026_public_diagnostic_v3.py --activate-release <hash>`. Rollback de
aplicação ocorre pela republicação de um build anterior. Os arquivos públicos
V2 permanecem como rollback frio temporário e não devem receber correções ou
novos indicadores.

Sua remoção física exige nova release V3 real, rollback entre duas releases V3
validado em produção, encerramento da janela do build anterior, busca de
rede/código sem referências V2 e autorização específica.

## Próxima rodada

A correção metodológica de 12.a e 12.b deve gerar um novo staging e um novo
release imutável. Nem a release ativa, nem `current.json`, nem os payloads V2
devem ser editados manualmente.
