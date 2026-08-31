import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import react from '@vitejs/plugin-react'
import { createServer } from 'vite'
import {
  checkVocacoesPneAdvancedPublication,
  materializeVocacoesPneAdvancedPublication,
  promoteVocacoesPneAdvancedPublication,
} from '../lib/vocacoes-pne-advanced-publication.mjs'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const bundlePath = path.join(repoRoot, 'src', 'features', 'vocacoes-regiao', 'generated', 'vocacoesPneAdvancedInsightsValeDoSinos.json')
const registryPath = path.join(repoRoot, 'src', 'features', 'vocacoes-regiao', 'generated', 'vocacoesPneAdvancedInsightsRegistry.json')
const selectionPath = path.join(repoRoot, 'data_pipeline', 'contracts', 'vocacoes-pne-aa5-public-selection-v1.json')
const allowlistPath = path.join(repoRoot, 'data_pipeline', 'contracts', 'vocacoes-pne-aa5-allowlist.json')
const allowedCodes = [
  '4303905',
  '4306403',
  '4307609',
  '4307708',
  '4310801',
  '4313375',
  '4313409',
  '4314803',
  '4318705',
  '4320008',
]

const activeStateConfig = {
  schemaVersion: 'state-config-v1',
  stateCode: 'RS',
  stateName: 'Rio Grande do Sul',
  stateNameForms: {
    nominative: 'Rio Grande do Sul',
    withDe: 'do Rio Grande do Sul',
    withCom: 'com o Rio Grande do Sul',
  },
  municipalityIbgePrefix: '43',
  expectedMunicipalityCount: 497,
  locale: 'pt-BR',
}

const vite = await createServer({
  appType: 'custom',
  cacheDir: path.join(repoRoot, '.tmp', 'vite-cache', 'vocacoes-pne-aa5-unit'),
  configFile: false,
  define: {
    __ACTIVE_PUBLICATION_CONFIG__: JSON.stringify({
      schemaVersion: 'state-publication-v3',
      stateCode: 'RS',
      analyticsStatus: 'complete',
      analyticsMessage: null,
      enabledProducts: null,
    }),
    __ACTIVE_REGIONS_CONFIG__: 'null',
    __ACTIVE_STATE_CONFIG__: JSON.stringify(activeStateConfig),
  },
  plugins: [react()],
  publicDir: false,
  root: repoRoot,
  server: { middlewareMode: true, hmr: { port: 24689 } },
})

after(async () => vite.close())

const contractModule = await vite.ssrLoadModule('/src/features/vocacoes-regiao/vocacoesPneAdvancedContract.ts')
const loaderModule = await vite.ssrLoadModule('/src/features/vocacoes-regiao/useVocacoesPneAdvancedBundle.ts')
const surfaceModule = await vite.ssrLoadModule('/src/features/vocacoes-regiao/vocacoesPneSurfaceResolution.ts')
const reportModule = await vite.ssrLoadModule('/src/features/vocacoes-regiao/VocacoesPneAdvancedReport.tsx')
const bundleRaw = await readFile(bundlePath, 'utf8')
const registry = JSON.parse(await readFile(registryPath, 'utf8'))
const bundle = JSON.parse(bundleRaw)
const occurrences = (text, fragment) => text.split(fragment).length - 1

test('geração AA5 é determinística, está atual e fecha hash/tamanho no registro', async () => {
  const first = await materializeVocacoesPneAdvancedPublication(repoRoot)
  const second = await materializeVocacoesPneAdvancedPublication(repoRoot)
  assert.equal(first.bundleBytes, second.bundleBytes)
  assert.equal(first.registryBytes, second.registryBytes)
  await assert.doesNotReject(() => checkVocacoesPneAdvancedPublication(repoRoot))
  assert.equal(createHash('sha256').update(bundleRaw).digest('hex'), registry.bundleSha256)
  assert.equal(Buffer.byteLength(bundleRaw), registry.bundleByteSize)
  assert.equal(bundle.contentVersion, registry.contentVersion)
  assert.equal(registry.sourceManifestSha256, '4d4d10560c8aaf1de4cd569f7d2d80f4bf7ddd7b6fa704a6136af57beaf2d1f5')
  assert.equal(registry.sourceArtifactSetDigestSha256, '1db90f4fa82d48708d9c126e0b4436259db17a7f908f36ffa1779bc69de68778')
  assert.equal(registry.expandedAnalysisEvidenceSha256, 'd032044ad34b3c4a3353e9ae3fd162101c5c2b10a6e6be1db5dd8bb36eb6522e')
  assert.equal(registry.relationshipAtlasArtifactSetDigestSha256, 'eb673cfd423bd6b1d4cce1512f310fe3e09819df8e7d4be609c18ca9a38ea23f')
})

test('bundle público contém cinco leituras, quatro agendas, resultado negativo e zero observado', () => {
  assert.doesNotThrow(() => contractModule.assertVocacoesPneAdvancedBundle(bundle))
  assert.deepEqual(bundle.region.municipalities.map((item) => item.ibgeCode), allowedCodes)
  assert.deepEqual(bundle.region.advancedMunicipalityIbgeCodes, ['4313375'])
  for (const variant of Object.values(bundle.scopeVariants)) {
    assert.equal(variant.readings.length, 5)
    assert.equal(variant.agendas.length, 4)
    assert.equal(variant.transversal.length, 3)
    for (const reading of variant.readings) {
      assert.ok(reading.conclusion.length > 0, reading.id)
      assert.ok(reading.evidence.length >= 2 && reading.evidence.length <= 3, reading.id)
      assert.match(reading.comparisonNote, /(?:Rio Grande do Sul|estadual)/iu, reading.id)
      assert.ok(reading.mechanism.summary.length > 0, reading.id)
      assert.ok(reading.mechanism.alternatives.length > 0, reading.id)
      assert.ok(reading.mechanism.boundary.length > 0, reading.id)
      assert.ok(reading.planning.implication.length > 0, reading.id)
      assert.ok(reading.planning.indicators.length > 0, reading.id)
      assert.ok(reading.limit.length > 0, reading.id)
      assert.ok(reading.sources.length > 0, reading.id)
      assert.ok(['consistent', 'watch', 'not_confirmed', 'not_comparable'].includes(reading.analysisCheck.status), reading.id)
      assert.ok(reading.analysisCheck.scopeDisclosure.length > 0, reading.id)
      assert.ok(reading.analysisCheck.details.length >= 2, reading.id)
      assert.ok(reading.analysisCheck.sources.length > 0, reading.id)
    }
    assert.deepEqual(Object.fromEntries(variant.readings.map((reading) => [reading.id, reading.analysisCheck.status])), {
      'demografia-matriculas-rede': 'not_confirmed',
      'trajetoria-contexto': 'not_confirmed',
      'transformacao-economica-ept': 'watch',
      'escolaridade-adulta-eja': 'watch',
      'trabalho-juvenil-permanencia': 'not_confirmed',
    })
    assert.equal(
      variant.transversal.find((item) => item.id === 'ruralidade-organizacao-rede')?.analysisCheck?.status,
      'consistent',
    )
    assert.ok(variant.readings.some((reading) => reading.evidenceClass.kind === 'boundary'))
    assert.ok(variant.readings.every((reading) => reading.sources.length > 0))
    assert.deepEqual(variant.agendas.map((agenda) => agenda.id), [
      'coordenar-demografia-rede',
      'mapear-acesso-ept',
      'revisar-eja-por-etapa',
      'monitorar-trajetoria-contexto',
    ])
  }
  const novaSantaRita = bundle.scopeVariants.novaSantaRita
  const observedZero = novaSantaRita.readings
    .flatMap((reading) => reading.evidence)
    .find((evidence) => evidence.availability === 'observed_zero')
  assert.equal(observedZero?.value, 0)
  assert.equal(observedZero?.label, 'Matrículas técnicas locais')
  for (const stateLabel of ['Zero registrado', 'dado ausente', 'dado indisponível', 'dado suprimido', 'medida que não se aplica']) {
    assert.match(bundle.methodology.availabilityStatement, new RegExp(stateLabel, 'u'))
  }
  assert.deepEqual(bundle.methodology.relationshipAtlas, {
    testedRelationships: 98,
    robustRows: 6,
    robustMechanisms: 1,
    notRobustRows: 28,
    insufficientRows: 61,
    descriptiveRows: 2,
    blockedRows: 1,
    statement: bundle.methodology.relationshipAtlas.statement,
    familyThresholdStatement: bundle.methodology.relationshipAtlas.familyThresholdStatement,
  })
})

test('allowlist remove chaves internas e candidata rejeitada sem ausência ruidosa', async () => {
  const allowlist = JSON.parse(await readFile(allowlistPath, 'utf8'))
  assert.ok(allowlist.stageOwnedPaths.length > 0)
  assert.ok(allowlist.stageOwnedPaths.every((item) => !item.replaceAll('\\', '/').startsWith('public/data/')))
  assert.deepEqual(allowlist.allowedOutputPaths, [
    'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsValeDoSinos.json',
    'src/features/vocacoes-regiao/generated/vocacoesPneAdvancedInsightsRegistry.json',
  ])
  assert.ok(allowlist.allowedOutputPaths.every((item) => allowlist.stageOwnedPaths.includes(item)))
  const visit = (value) => {
    if (Array.isArray(value)) return value.forEach(visit)
    if (value !== null && typeof value === 'object') {
      for (const [key, child] of Object.entries(value)) {
        assert.ok(!allowlist.forbiddenKeyNames.includes(key), key)
        visit(child)
      }
      return
    }
    if (typeof value === 'string') {
      for (const token of allowlist.forbiddenStringTokens) assert.ok(!value.includes(token), token)
      for (const token of allowlist.forbiddenPublicLanguageTokens) {
        assert.ok(!value.toLocaleLowerCase('pt-BR').includes(token.toLocaleLowerCase('pt-BR')), token)
      }
    }
  }
  visit(bundle)
  assert.doesNotMatch(bundleRaw, /AG3_YOUTH|candidata rejeitada|cartão ausente/iu)
  assert.doesNotMatch(bundleRaw, /(?:comprovou|provou|determinou|garante que)/iu)
})

test('falha após promover o bundle restaura bundle e registro anteriores sem tocar public/data', async (t) => {
  const fixtureRoot = await mkdtemp(path.join(tmpdir(), 'vocacoes-pne-aa5-rollback-'))
  t.after(async () => rm(fixtureRoot, { recursive: true, force: true }))
  const selection = JSON.parse(await readFile(selectionPath, 'utf8'))
  const aa4Root = path.dirname(selection.source.manifestPath)
  const requiredInputs = new Set([
    'data_pipeline/contracts/vocacoes-pne-aa5-public-selection-v1.json',
    'data_pipeline/contracts/vocacoes-pne-aa5-allowlist.json',
    selection.expandedAnalysis.evidenceFreezePath,
    selection.relationshipAtlas.executionContractPath,
    selection.relationshipAtlas.manifestPath,
    selection.relationshipAtlas.allResultsPath,
    selection.relationshipAtlas.promotionLedgerPath,
    selection.relationshipAtlas.qaPath,
    selection.relationshipAtlas.fableAuditPath,
    selection.relationshipAtlas.fableReconciliationPath,
    selection.scope.municipalityRegistryPath,
    selection.source.manifestPath,
    ...Object.keys(selection.source.artifacts).map((name) => path.join(aa4Root, name)),
  ])
  for (const relativePath of requiredInputs) {
    const destination = path.join(fixtureRoot, relativePath)
    await mkdir(path.dirname(destination), { recursive: true })
    await copyFile(path.join(repoRoot, relativePath), destination)
  }

  const fixtureBundle = path.join(fixtureRoot, 'src', 'features', 'vocacoes-regiao', 'generated', 'vocacoesPneAdvancedInsightsValeDoSinos.json')
  const fixtureRegistry = path.join(fixtureRoot, 'src', 'features', 'vocacoes-regiao', 'generated', 'vocacoesPneAdvancedInsightsRegistry.json')
  const sentinel = path.join(fixtureRoot, 'public', 'data', 'aa5-sentinel.txt')
  await mkdir(path.dirname(fixtureBundle), { recursive: true })
  await mkdir(path.dirname(sentinel), { recursive: true })
  await writeFile(fixtureBundle, 'bundle-anterior\n', 'utf8')
  await writeFile(fixtureRegistry, 'registro-anterior\n', 'utf8')
  await writeFile(sentinel, 'não tocar\n', 'utf8')

  const promotionOrder = []
  await assert.rejects(
    () => promoteVocacoesPneAdvancedPublication(fixtureRoot, {
      afterPromote({ kind }) {
        promotionOrder.push(kind)
        if (kind === 'bundle') throw new Error('falha de promoção injetada')
      },
    }),
    /falha de promoção injetada/u,
  )
  assert.deepEqual(promotionOrder, ['bundle'], 'o registro não pode ser promovido antes do bundle')
  assert.equal(await readFile(fixtureBundle, 'utf8'), 'bundle-anterior\n')
  assert.equal(await readFile(fixtureRegistry, 'utf8'), 'registro-anterior\n')
  assert.equal(await readFile(sentinel, 'utf8'), 'não tocar\n')
  assert.ok((await readdir(path.dirname(fixtureBundle))).every((name) => !/aa5-(?:backup|next)/u.test(name)))

  const fixtureEvidence = path.join(fixtureRoot, selection.expandedAnalysis.evidenceFreezePath)
  await writeFile(fixtureEvidence, `${await readFile(fixtureEvidence, 'utf8')} `, 'utf8')
  await assert.rejects(
    () => promoteVocacoesPneAdvancedPublication(fixtureRoot),
    /hash congelado das análises ampliadas/u,
  )
  assert.equal(await readFile(fixtureBundle, 'utf8'), 'bundle-anterior\n')
  assert.equal(await readFile(fixtureRegistry, 'utf8'), 'registro-anterior\n')
  assert.equal(await readFile(sentinel, 'utf8'), 'não tocar\n')
})

test('loader valida bytes, hash e conteúdo e falha fechado em mutações', async () => {
  const loadValid = loaderModule.createVocacoesPneAdvancedLoader(async () => ({ bundleRaw, registry }))
  const loaded = await loadValid()
  assert.equal(loaded.contentVersion, bundle.contentVersion)
  assert.equal(await loadValid(), loaded, 'segunda carga reutiliza o mesmo objeto validado')

  const corruptedText = bundleRaw.replace('Cinco leituras', 'Seiss leituras')
  const loadCorruptHash = loaderModule.createVocacoesPneAdvancedLoader(async () => ({
    bundleRaw: corruptedText,
    registry,
  }))
  await assert.rejects(loadCorruptHash, /hash do bundle diverge/u)

  const invalidBundle = JSON.parse(bundleRaw)
  invalidBundle.scopeVariants.region.readings.pop()
  const invalidRaw = `${JSON.stringify(invalidBundle, null, 2)}\n`
  const invalidRegistry = {
    ...registry,
    bundleSha256: createHash('sha256').update(invalidRaw).digest('hex'),
    bundleByteSize: Buffer.byteLength(invalidRaw),
  }
  const loadInvalidContract = loaderModule.createVocacoesPneAdvancedLoader(async () => ({
    bundleRaw: invalidRaw,
    registry: invalidRegistry,
  }))
  await assert.rejects(loadInvalidContract, /cinco leituras públicas/u)

  const loadRejected = loaderModule.createVocacoesPneAdvancedLoader(async () => {
    throw new Error('falha injetada')
  })
  await assert.rejects(loadRejected, /falha injetada/u)
})

test('resolução da rota aciona a página oficial anterior quando o pacote novo falha', () => {
  assert.equal(surfaceModule.resolveVocacoesPneSurface({
    eligible: true,
    advancedRequested: true,
    advancedStatus: 'ready',
    advancedScopeSupported: true,
    officialStatus: 'loading',
    officialScopeSupported: false,
  }), 'advanced')
  assert.equal(surfaceModule.resolveVocacoesPneSurface({
    eligible: true,
    advancedRequested: true,
    advancedStatus: 'error',
    advancedScopeSupported: false,
    officialStatus: 'ready',
    officialScopeSupported: true,
  }), 'official_previous')
  assert.equal(surfaceModule.resolveVocacoesPneSurface({
    eligible: true,
    advancedRequested: true,
    advancedStatus: 'error',
    advancedScopeSupported: false,
    officialStatus: 'error',
    officialScopeSupported: false,
  }), 'legacy')
  assert.equal(surfaceModule.resolveVocacoesPneSurface({
    eligible: true,
    advancedRequested: false,
    advancedStatus: 'idle',
    advancedScopeSupported: false,
    officialStatus: 'ready',
    officialScopeSupported: true,
  }), 'official_previous')
})

function renderAdvanced(municipalityId) {
  return renderToStaticMarkup(createElement(reportModule.VocacoesPneAdvancedReport, {
    bundle,
    municipalityId,
  }))
}

test('Nova Santa Rita renderiza uma leitura acessível, com três histórias e biblioteca de oito relações', () => {
  const markup = renderAdvanced('4313375')
  assert.match(markup, /data-publication="official-advanced"/u)
  assert.match(markup, /data-scope="municipality"/u)
  assert.match(markup, /Nova Santa Rita: educação e território/u)
  assert.equal(occurrences(markup, 'data-reading-card="'), 3)
  assert.equal(occurrences(markup, 'data-agenda-card="'), 3)
  assert.equal(occurrences(markup, 'data-agenda-secondary="'), 1)
  assert.equal(occurrences(markup, 'data-relation-group="'), 4)
  assert.equal(occurrences(markup, 'data-relation-item="'), 8)
  assert.equal(occurrences(markup, 'data-reading-boundary="visible"'), 3)
  assert.equal(occurrences(markup, 'data-analysis-check="'), 3)
  assert.equal(occurrences(markup, '<details'), 9)
  for (const id of [
    'demografia-matriculas-rede',
    'transformacao-economica-ept',
    'escolaridade-adulta-eja',
  ]) {
    assert.match(markup, new RegExp('data-reading-card="' + id + '"', 'u'))
  }
  for (const id of [
    'trajetoria-contexto',
    'trabalho-juvenil-permanencia',
    'ruralidade-organizacao-rede',
    'inclusao-aee',
    'contexto-social-registrado',
  ]) {
    assert.match(markup, new RegExp('data-relation-item="' + id + '"', 'u'))
    assert.doesNotMatch(markup, new RegExp('data-reading-card="' + id + '"', 'u'))
  }
  assert.doesNotMatch(markup, /financiamento|agenda ausente|candidata rejeitada/iu)
  for (const text of [
    'Resumo para decidir',
    'O que o território ajuda a entender sobre a educação?',
    'O que precisamos preparar na educação para os próximos anos?',
    'Outras relações que analisamos',
    'Quando dois dados mudam juntos, isso abre uma pergunta. Não prova, sozinho, que um causou o outro.',
    'A conta organiza a mudança; a explicação segue em aberto.',
    'Faltam anos e dados de acesso para saber se o movimento permanece.',
    'não sabemos qual veio primeiro',
    'O padrão que mais se repetiu nos dados:',
    'Isso não mostra o que veio primeiro',
    'Ver dados, fontes e outras explicações',
    'zero observado',
    'Como chegamos a estas leituras',
    'Mapa completo das relações avaliadas',
  ]) assert.ok(markup.includes(text), text)
  assert.match(markup, /<b>98<\/b> relações avaliadas/u)
  assert.match(markup, /<b>1<\/b> sem comparação segura/u)

  const primaryMarkup = markup.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gu, ' ')
  const primaryText = primaryMarkup
    .replace(/<[^>]+>/gu, ' ')
    .replace(/&[a-z0-9#]+;/giu, ' ')
    .replace(/\s+/gu, ' ')
    .trim()
  const visibleWords = primaryText.split(/\s+/u).filter(Boolean)
  assert.ok(visibleWords.length <= 1_500, 'camada principal tem ' + visibleWords.length + ' palavras')
  assert.doesNotMatch(
    primaryText,
    /\b(?:p-valor|significância|regressão|bootstrap|placebo|intervalo de confiança|correlação|causalidade|inferência|robustez|modelo|efeito fixo|evidência insuficiente|Pearson|Spearman)\b|(?:^|\s)q(?:\s|$)/iu,
  )
  const notComparableSentence = reportModule.vocacoesPnePublicStatusSentence('not_comparable')
  assert.equal(
    notComparableSentence,
    'Os dados medem períodos ou grupos diferentes e ainda não permitem uma comparação segura.',
  )
  assert.doesNotMatch(notComparableSentence, /se repetiu|confirmad|comprovad/iu)
  assert.match(markup, /Pergunta que testamos\./u)
  assert.match(markup, /Por que isso importa para a gestão\./u)
})

test('visão regional usa o mesmo contrato e municípios sem dossiê avançado falham fechados', () => {
  const markup = renderAdvanced(null)
  assert.match(markup, /Vale do Sinos: educação e território/u)
  assert.match(markup, /data-scope="region"/u)
  assert.equal(occurrences(markup, 'data-reading-card="'), 3)
  assert.equal(occurrences(markup, 'data-analysis-check="'), 3)
  assert.equal(occurrences(markup, 'data-relation-item="'), 8)
  assert.throws(() => renderAdvanced('4303905'), /ainda não possui dossiê público próprio/u)
})

test('página oficial integra pacote avançado e conserva as duas camadas de fallback', async () => {
  const source = await readFile(path.join(
    repoRoot,
    'src',
    'features',
    'vocacoes-regiao',
    'VocacoesRegiaoPage.tsx',
  ), 'utf8')
  assert.match(source, /useVocacoesPneAdvancedBundle/u)
  assert.match(source, /resolveVocacoesPneSurface/u)
  assert.match(source, /<VocacoesPneAdvancedReport/u)
  assert.match(source, /<VocacoesPneOfficialReport/u)
  assert.match(source, /advancedScopeNotice=/u)
  assert.match(source, /<VocacoesResolvedReport/u)
})
