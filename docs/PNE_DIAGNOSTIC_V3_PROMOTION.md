# Diagnóstico PNE V3 — releases imutáveis e operação

## Pacote ativo

O V3 público é resolvido exclusivamente por:

1. `public/data/pne2026-diagnostic-v3/current.json`;
2. `releases/<releaseId>/manifest.json`;
3. `releases/<releaseId>/municipios/<id>.json`.

O release ativo é
`dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679`.
Ele contém 497 municípios e 20.874 resultados, com 11.431 `progress`, 4.970
`tracking` e 4.473 `complementary`. O mínimo/máximo municipal é 42/42. Há
17.273 resultados `available`, 3.103 `unavailable`, 498 `not_applicable`,
zero `suppressed`, 427 percentuais acima de 100%, 99 contagens absolutas acima
de 100 e 961 ocorrências `hidden` excluídas.

Identificadores verificados:

- SHA-256 do manifesto de staging:
  `2da41477eeb759de79fd9f6173c1c086c44938f111ab8478c82fead00855a105`;
- hash agregado dos bytes municipais, da identidade de schema/contrato e
  `releaseId`:
  `dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679`;
- hash semântico normalizado de staging e release:
  `3e75fb55510e99d68b564414bb41b8ae0dfeb9161c0df17f051f0326e2ec2e7b`;
- SHA-256 do manifesto do release:
  `4160a6666bb3d34f28f98ef2c9cba2f7a7c9122cca1282e70a28e6de476e68d7`;
- SHA-256 de `current.json`:
  `33e335ac78e3921fc2db8daaa42d9e3e45d37c694f285d78274314ee3a5933c2`.

Não há timestamp, caminho absoluto, hostname ou outro dado de máquina nos
artefatos.

## Hashes dos manifests

Staging e release têm schemas diferentes porque cumprem papéis diferentes. A
comparação semântica normaliza apenas o núcleo abaixo:

| Conceito | Staging | Release | Classificação |
| --- | --- | --- | --- |
| schema do diagnóstico | `diagnosticSchemaVersion` | igual | público/metodológico |
| contrato e política | versões e hashes | iguais | público/metodológico |
| municípios | `generatedMunicipalityCount` | `municipalityCount` | renomeado/recomputado |
| resultados | `totalResultCount` | `resultCount` | renomeado/recomputado |
| modos | `modeCounts` | contagens separadas | renomeado/recomputado |
| classificações e prioridades | campos homônimos | iguais | público/recomputado |
| mínimo, máximo e ocultos | campos homônimos | iguais | público/recomputado |
| percentuais acima de 100% | `percentValuesAbove100Count` | igual | público/recomputado |
| contagens absolutas acima de 100 | `countValuesAbove100Count` | igual | público/recomputado |
| identidade dos bytes | `generationHash` | `aggregateHash` | público/recomputado |

São excluídos do hash semântico, de forma explícita, somente campos
operacionais:

- `schemaVersion`, pois identifica envelopes distintos;
- `expectedMunicipalityCount`, `eligibleRelationCounts`,
  `invalidFileCount`, `duplicateRelationCount`, `orphanFileCount` e
  `v2FieldInventory`, que auditam a geração;
- `municipalFilePattern`, que descreve o layout físico;
- o próprio `semanticHash`.

Nenhum campo analítico é descartado. O release registra `semanticHash`; o
staging o possui de forma computável e o promotor exige igualdade antes da
ativação. Uma diferença no núcleo é erro, não diferença operacional esperada.

## `current.json`

O ponteiro contém somente:

```json
{
  "schemaVersion": "pne2026-diagnostic-release-pointer-v1",
  "releaseId": "dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679",
  "manifestPath": "releases/dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679/manifest.json",
  "aggregateHash": "dafba4dfc235f3a491d7e21850b450c6be8727bcb1a7b259b163e75f6b2f5679",
  "contractVersion": "1.8.0",
  "contractHash": "88b111d379d1f75f37a36f67a992d1b595219c0bcc776009a679c79faefc8dd1",
  "presentationPolicyVersion": "1.6.0",
  "presentationPolicyHash": "0a952914f95058539535210899a39304750bc6e06ee08a9fbd2ae66f6740c1d2"
}
```

O loader rejeita campos extras, `..`, URLs absolutas, caminhos fora do release,
hash divergente e versões incompatíveis.

## Promoção

Verificação somente leitura:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir <staging> `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

Promoção:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --source-dir <staging> `
  --destination-dir public/data/pne2026-diagnostic-v3
```

A rotina valida o staging, recalcula o agregado e o hash semântico, prepara e
revalida um release temporário, cria o diretório final ainda inativo, copia os
bytes já validados, grava o manifesto por último, revalida o release e só então
substitui `current.json` com `os.replace`.

Um release existente nunca é sobrescrito. Se o mesmo hash já existir, todos os
bytes são comparados; qualquer divergência bloqueia a operação. Releases
anteriores são preservados. A rotina não depende de renomear árvore não vazia.
Se a troca atômica do ponteiro for bloqueada, o ponteiro anterior permanece
inalterado e o novo release continua inativo.

Na migração inicial, a antiga cópia
`pne2026-diagnostic-v3/municipalities` foi removida somente depois de ser
comparada byte a byte com o release ativo. O `manifest.json` raiz transitório
foi removido na Rodada 2B2C2C. A rotina de promoção não o cria nem o consulta:
somente `current.json` e os manifests dentro de `releases/<releaseId>` compõem
o pacote público ativo.

## Rollback

### Rollback entre releases V3

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --activate-release <hash-anterior> `
  --destination-dir public/data/pne2026-diagnostic-v3
```

O release é validado antes da troca e apenas `current.json` muda. Esse
procedimento é válido diretamente somente entre releases com a mesma versão e
hash de contrato e política. Voltar do contrato 1.5.0 para a release 1.4.0
exige republicar de forma coordenada o build 1.4.0 correspondente; trocar
somente o ponteiro deixaria o loader e os payloads incompatíveis.

Use `--check` antes da ativação quando a intenção for apenas validar:

```powershell
python data_pipeline/scripts/promote_pne2026_public_diagnostic_v3.py `
  --activate-release <hash-anterior> `
  --destination-dir public/data/pne2026-diagnostic-v3 `
  --check
```

### Rollback da aplicação

O build atual não possui troca runtime entre V2 e V3. Se for necessário
reverter a aplicação, deve-se republicar um build anterior conhecido e
validado. Os arquivos públicos V2 são preservados temporariamente apenas para
que esse build anterior possa operar durante a janela de rollback. Não existe
feature flag substituta nem fallback automático.

## Loader V3 exclusivo

Cada carga consulta `current.json` com `cache: no-store`. Manifesto e payload
municipal são deduplicados e cacheados por `releaseId`; a troca do ponteiro
cria novas chaves e um payload antigo nunca é tratado como corrente.

O caminho normal faz exatamente três requisições: ponteiro, manifesto do
release e um município do release. Ele não importa `staticData`, não executa o
normalizador V2 e não solicita o JSON V2.

Falhas no ponteiro, release, manifesto, hashes, payload municipal, parser ou
resumo geram erro estruturado, registrado uma única vez para a mesma
ocorrência. Nenhum dado parcial é entregue, nenhuma release é misturada e
nenhum payload de release anterior é apresentado como atual. Como promises
rejeitadas são removidas dos caches, uma nova tentativa pelo fluxo existente
faz nova leitura do ponteiro. O estado visual de carregamento e erro permanece
o mesmo.

## Inventário do legado

| Ocorrência | Classificação | Estado após 2B2C2C |
| --- | --- | --- |
| `pne2026DiagnosticV2Compatibility.js` | runtime de produção | removido de `src` |
| seleção `VITE_PNE_DIAGNOSTIC_SOURCE` | runtime/build | removida sem substituta |
| fallback `goalId × indicatorId` e normalizador do resumo V2 | runtime de produção | removidos |
| tipos brutos e envelope V2 em `diagnosticTypes.ts` | runtime de produção | removidos |
| comparação V2 × V3 | auditoria histórica | mantida em `scripts/checks/support`, usando blobs versionados |
| campos legados em produtores e catálogos V2 | pipeline legado | preservados; não são contrato V3 |
| campos homônimos em PNE, Educação ou componentes de razão | outros domínios | preservados |
| arquivos `public/data/municipios/*/diagnostico.json` | rollback frio/histórico | preservados byte a byte |
| manifesto V3 raiz transitório | arquivo público transitório | removido |

Os modelos V3 e o view model canônico não declaram `tracksGoal`,
`tracks_goal`, `hasDistance`, `relationshipType`, `tier`, `priorityOrder`,
`classificationPolicy`, `valuePolicy` ou `meta_label`. O V3 exige `relationId`;
não há resolução frontend por par `goalId × indicatorId`.

## Descontinuação do V2 público

Os payloads V2 preservados:

- não são fonte autoral nem fallback automático do Diagnóstico atual;
- não recebem novos indicadores, correções ou regenerações no fluxo V3;
- permanecem apenas para auditoria histórica e para republicação temporária de
  um build anterior;
- não podem ser removidos sem autorização específica.

A remoção física futura exige, cumulativamente:

1. pelo menos uma nova release V3 real publicada;
2. rollback entre duas releases V3 validado em produção;
3. build anterior fora da janela operacional de rollback;
4. busca de rede e código sem referências V2;
5. autorização específica para remover os arquivos públicos.

## Correção metodológica das Metas 12.a e 12.b

O contrato 1.8.0 calcula a articulação como matrículas integradas mais
concomitantes, divididas pelas matrículas do ensino médio no mesmo município e
ano. A fonte contém matrículas agregadas, não estudantes únicos; por isso a
relação é `tracking`, com referência municipal de acompanhamento de 50% e sem
classificação legal. O valor estadual é uma razão de somas, nunca média
municipal.

A participação pública usa expansão líquida pública dividida pela expansão
líquida total, ambas contra a base fixa de 2025. A expansão dos cursos
subsequentes usa `(atual - base2025) / base2025`, com referência absoluta
`base2025 × 1,60`. As duas relações são `progress` e geram registros
`unavailable`, mas não valor, distância, status, classificação ou projeção
enquanto o último ano observado for 2025. O `reasonCode` é
`no_post_baseline_observation` para os 497 municípios.

Base zero é `not_applicable`; base ou observação corrente ausente é
`unavailable`; expansão total pública nula ou negativa é `not_applicable`.
Retrações, valores negativos e valores acima de 100% são preservados sem
truncamento. Na atualização anual, a primeira observação válida posterior a
2025 será calculada automaticamente pela mesma fórmula, sem deslocar a base.

A release anterior
`3832c3417fdf969af52cd706240b1a15784c1e0f29391dc0397992c16c828933`
permanece imutável. Os arquivos públicos V2 não foram regenerados nem
alterados; a árvore municipal V2 permanece com 2.485 arquivos e com o hash de
auditoria anterior
`8e9e30415738fe9325bc0a02ba410633a22c80cd015163d7a9a1286fc7c1845a`.
