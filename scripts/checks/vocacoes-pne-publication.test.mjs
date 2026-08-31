import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test, { after } from 'node:test'

import {
  buildPublicationArtifacts,
  run,
  VOCACOES_PNE_PUBLICATION_PATHS,
} from '../generate-vocacoes-pne-publication.mjs'
import {
  buildVocacoesPnePublicationQueue,
  canonicalJson,
  createVocacoesPneRollbackProposal,
  VocacoesPnePublicationError,
  VOCACOES_PNE_PUBLICATION_REASON_CODES,
} from '../lib/vocacoes-pne-publication.mjs'

const repoRoot = path.resolve(import.meta.dirname, '..', '..')
const generatedDirectory = path.join(
  repoRoot,
  'src',
  'features',
  'vocacoes-regiao',
  'generated',
)
const outputPath = path.join(generatedDirectory, 'vocacoesPnePublicationQueue.json')
const narrativePath = path.join(generatedDirectory, 'vocacoesPneValeDoSinos.json')

const baseInputs = {
  legacyManifest: JSON.parse(await readFile(
    path.join(repoRoot, 'public', 'data', 'vocacoes-regiao', 'manifest.json'),
    'utf8',
  )),
  narrativeRegistry: JSON.parse(await readFile(
    path.join(generatedDirectory, 'vocacoesPneNarrativeRegistry.json'),
    'utf8',
  )),
  narrativeDocuments: [{
    path: 'vocacoesPneValeDoSinos.json',
    raw: await readFile(narrativePath, 'utf8'),
  }],
  transferCoverage: JSON.parse(await readFile(
    path.join(
      repoRoot,
      'scripts',
      'checks',
      'fixtures',
      'vocacoes-pne',
      'transfer-coverage-r9.json',
    ),
    'utf8',
  )),
}

const silentLogger = Object.freeze({ log() {} })
let temporaryDirectory = null

after(async () => {
  if (temporaryDirectory !== null) {
    await rm(temporaryDirectory, { recursive: true, force: true })
  }
})

function cloneInputs() {
  return structuredClone(baseInputs)
}

function findRegion(queue, slug) {
  const region = queue.regions.find((candidate) => candidate.slug === slug)
  assert.ok(region, `região ausente: ${slug}`)
  return region
}

function findManifestRegion(inputs, slug) {
  const region = inputs.legacyManifest.regions.find((candidate) => candidate.slug === slug)
  assert.ok(region, `manifesto sem região: ${slug}`)
  return region
}

function replaceNarrative(inputs, mutate) {
  const document = JSON.parse(inputs.narrativeDocuments[0].raw)
  mutate(document)
  const raw = JSON.stringify(document)
  inputs.narrativeDocuments[0].raw = raw
  inputs.narrativeRegistry.entries[0].narrativeByteSize = Buffer.byteLength(raw, 'utf8')
  inputs.narrativeRegistry.entries[0].narrativeSha256 = createHash('sha256')
    .update(raw, 'utf8')
    .digest('hex')
}

function assertBuildFails(inputs, label) {
  assert.throws(
    () => buildVocacoesPnePublicationQueue(inputs),
    VocacoesPnePublicationError,
    label,
  )
}

test('fila gerada é snapshot byte a byte determinístico e repetível', async () => {
  const first = buildVocacoesPnePublicationQueue(cloneInputs())
  const second = buildVocacoesPnePublicationQueue(cloneInputs())
  const expected = await readFile(outputPath, 'utf8')

  assert.deepEqual(second, first)
  assert.equal(canonicalJson(first), canonicalJson(second))
  assert.equal(canonicalJson(first), expected)
  assert.equal(Object.hasOwn(first, 'generatedAt'), false)
  assert.equal(Object.hasOwn(first, 'timestamp'), false)
})

test('fila contém 10 regiões, 1 ready, 2 almost_ready, 7 blocked e lote único', () => {
  const queue = buildVocacoesPnePublicationQueue(cloneInputs())

  assert.deepEqual(queue.summary, {
    regionCount: 10,
    readyCount: 1,
    almostReadyCount: 2,
    blockedCount: 7,
    narrativeCount: 1,
    legacyCount: 9,
    batchCount: 1,
  })
  assert.equal(queue.regions.length, 10)
  assert.equal(queue.batches.length, 1)
  assert.deepEqual(queue.batches[0].regionSlugs, ['vale-do-sinos'])
  assert.equal(findRegion(queue, 'vale-do-sinos').publicationMode, 'narrative')
})

test('VRP e Noroeste ficam no legado com os dois bloqueios mesmo tendo cenário', () => {
  const inputs = cloneInputs()
  const queue = buildVocacoesPnePublicationQueue(inputs)
  const expectedReasons = [
    VOCACOES_PNE_PUBLICATION_REASON_CODES.FIRST_OUTPUT_ARTIFACT_MISSING,
    VOCACOES_PNE_PUBLICATION_REASON_CODES.SECOND_OUTPUT_ARTIFACT_MISSING,
  ]

  for (const slug of ['noroeste', 'vale-do-rio-pardo']) {
    assert.equal(findManifestRegion(inputs, slug).scenarioStatus, 'published')
    const region = findRegion(queue, slug)
    assert.equal(region.readiness, 'almost_ready')
    assert.equal(region.publicationMode, 'legacy')
    assert.deepEqual(region.reasonCodes, expectedReasons)
    assert.equal(region.narrative, null)
  }
})

test('sete regiões não auditadas usam somente TRANSFER_NOT_AUDITED', () => {
  const queue = buildVocacoesPnePublicationQueue(cloneInputs())
  const blocked = queue.regions.filter((region) => region.readiness === 'blocked')

  assert.equal(blocked.length, 7)
  for (const region of blocked) {
    assert.equal(region.publicationMode, 'legacy')
    assert.deepEqual(region.reasonCodes, [
      VOCACOES_PNE_PUBLICATION_REASON_CODES.TRANSFER_NOT_AUDITED,
    ])
  }
})

test('identidade, UF, versão, schema, contrato, hash, tamanho e cardinalidades falham fechados', () => {
  const attacks = [
    ['nome', (inputs) => { findManifestRegion(inputs, 'vale-do-sinos').name = 'Outro Vale' }],
    ['UF', (inputs) => { findManifestRegion(inputs, 'vale-do-sinos').uf = 'AL' }],
    ['contagem', (inputs) => { findManifestRegion(inputs, 'vale-do-sinos').municipalityCount += 1 }],
    ['versão legada', (inputs) => { inputs.narrativeRegistry.entries[0].legacySourceVersion = 'outra-versao' }],
    ['contrato', (inputs) => { inputs.narrativeRegistry.entries[0].narrativeContractVersion = '9.9.9' }],
    ['hash', (inputs) => { inputs.narrativeRegistry.entries[0].narrativeSha256 = 'f'.repeat(64) }],
    ['tamanho', (inputs) => { inputs.narrativeRegistry.entries[0].narrativeByteSize += 1 }],
    ['schema do documento', (inputs) => replaceNarrative(inputs, (document) => {
      document.schemaVersion = 'outro-schema'
    })],
    ['contrato do documento', (inputs) => replaceNarrative(inputs, (document) => {
      document.contractVersion = '9.9.9'
    })],
    ['primeira saída curta', (inputs) => replaceNarrative(inputs, (document) => {
      document.sections[0].cards.splice(2)
    })],
    ['segunda saída longa', (inputs) => replaceNarrative(inputs, (document) => {
      while (document.sections[1].cards.length < 6) {
        const card = structuredClone(document.sections[1].cards[0])
        card.id = `${card.id}-${document.sections[1].cards.length}`
        document.sections[1].cards.push(card)
      }
    })],
  ]

  for (const [label, mutate] of attacks) {
    const inputs = cloneInputs()
    mutate(inputs)
    assertBuildFails(inputs, label)
  }
})

test('região, cobertura, registro ou documento ausente, extra ou duplicado falha', () => {
  const attacks = [
    ['manifesto ausente', (inputs) => { inputs.legacyManifest.regions.pop() }],
    ['manifesto extra', (inputs) => {
      const extra = structuredClone(inputs.legacyManifest.regions[0])
      extra.slug = 'extra'
      inputs.legacyManifest.regions.push(extra)
    }],
    ['manifesto duplicado', (inputs) => {
      inputs.legacyManifest.regions[0] = structuredClone(inputs.legacyManifest.regions[1])
    }],
    ['cobertura ausente', (inputs) => { inputs.transferCoverage.regions.pop() }],
    ['cobertura extra', (inputs) => {
      const extra = structuredClone(inputs.transferCoverage.regions[0])
      extra.slug = 'extra'
      inputs.transferCoverage.regions.push(extra)
    }],
    ['cobertura duplicada', (inputs) => {
      inputs.transferCoverage.regions[0] = structuredClone(inputs.transferCoverage.regions[1])
    }],
    ['registro desconhecido', (inputs) => {
      inputs.narrativeRegistry.entries[0].slug = 'extra'
    }],
    ['registro duplicado', (inputs) => {
      inputs.narrativeRegistry.entries.push(structuredClone(inputs.narrativeRegistry.entries[0]))
    }],
    ['documento ausente', (inputs) => { inputs.narrativeDocuments = [] }],
    ['documento extra', (inputs) => {
      inputs.narrativeDocuments.push({ path: 'extra.json', raw: '{}' })
    }],
    ['documento duplicado', (inputs) => {
      inputs.narrativeDocuments.push(structuredClone(inputs.narrativeDocuments[0]))
    }],
  ]

  for (const [label, mutate] of attacks) {
    const inputs = cloneInputs()
    mutate(inputs)
    assertBuildFails(inputs, label)
  }
})

test('rollback cria proposta isolada, não muta registro e recusa alvo inválido', () => {
  const registry = structuredClone(baseInputs.narrativeRegistry)
  const before = structuredClone(registry)
  const proposal = createVocacoesPneRollbackProposal(registry, 'vale-do-sinos')

  assert.deepEqual(registry, before)
  assert.equal(proposal.entries[0].status, 'rolled_back')
  assert.equal(registry.entries[0].status, 'published')
  assert.throws(
    () => createVocacoesPneRollbackProposal(registry, 'slug-desconhecido'),
    VocacoesPnePublicationError,
  )
  assert.throws(
    () => createVocacoesPneRollbackProposal(proposal, 'vale-do-sinos'),
    VocacoesPnePublicationError,
  )
})

test('rolled_back continua exigindo documento narrativo íntegro', () => {
  const inputs = cloneInputs()
  inputs.narrativeRegistry = createVocacoesPneRollbackProposal(
    inputs.narrativeRegistry,
    'vale-do-sinos',
  )
  const queue = buildVocacoesPnePublicationQueue(inputs)
  const vale = findRegion(queue, 'vale-do-sinos')
  assert.equal(vale.readiness, 'blocked')
  assert.equal(vale.publicationMode, 'legacy')
  assert.deepEqual(vale.reasonCodes, [
    VOCACOES_PNE_PUBLICATION_REASON_CODES.NARRATIVE_ROLLED_BACK,
  ])

  inputs.narrativeDocuments[0].raw += '\n'
  assertBuildFails(inputs, 'rolled_back adulterado')
})

test('fila e reason codes não entram na página, relatório ou registro de runtime', async () => {
  const sources = await Promise.all([
    readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-regiao',
      'VocacoesRegiaoPage.tsx',
    ), 'utf8'),
    readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-regiao',
      'VocacoesPneNarrativeReport.tsx',
    ), 'utf8'),
    readFile(path.join(
      repoRoot,
      'src',
      'features',
      'vocacoes-regiao',
      'vocacoesPneNarrativeRegistry.js',
    ), 'utf8'),
  ])
  const internalTokens = [
    'vocacoesPnePublicationQueue',
    'FIRST_OUTPUT_ARTIFACT_MISSING',
    'SECOND_OUTPUT_ARTIFACT_MISSING',
    'TRANSFER_NOT_AUDITED',
  ]
  for (const source of sources) {
    for (const token of internalTokens) assert.equal(source.includes(token), false, token)
  }
})

test('--check passa no artefato, detecta diferença e geração preserva bytes', async () => {
  run(['--check'], { logger: silentLogger })

  temporaryDirectory = await mkdtemp(path.join(os.tmpdir(), 'vocacoes-pne-publication-'))
  const temporaryOutput = path.join(temporaryDirectory, 'queue.json')
  const paths = { ...VOCACOES_PNE_PUBLICATION_PATHS, output: temporaryOutput }
  const first = run([], { paths, logger: silentLogger, runId: 'test-first' })
  const second = run([], { paths, logger: silentLogger, runId: 'test-second' })
  assert.equal(first.changed, true)
  assert.equal(second.changed, false)
  run(['--check'], { paths, logger: silentLogger })

  await writeFile(temporaryOutput, '{}\n', 'utf8')
  assert.throws(
    () => run(['--check'], { paths, logger: silentLogger }),
    VocacoesPnePublicationError,
  )
  const repaired = run([], { paths, logger: silentLogger, runId: 'test-repair' })
  assert.equal(repaired.changed, true)
  run(['--check'], { paths, logger: silentLogger })
})

test('--rollback imprime somente proposta, não escreve e argumentos incompatíveis falham', async () => {
  const before = await readFile(outputPath)
  const messages = []
  const result = run(['--rollback=vale-do-sinos'], {
    logger: { log(message) { messages.push(message) } },
  })
  const afterBytes = await readFile(outputPath)

  assert.equal(result.mode, 'rollback')
  assert.equal(result.proposal.entries[0].status, 'rolled_back')
  assert.equal(messages.length, 1)
  assert.deepEqual(JSON.parse(messages[0]), result.proposal)
  assert.deepEqual(afterBytes, before)
  assert.throws(
    () => run(['--check', '--rollback=vale-do-sinos'], { logger: silentLogger }),
    VocacoesPnePublicationError,
  )
  assert.throws(
    () => run(['--desconhecido'], { logger: silentLogger }),
    VocacoesPnePublicationError,
  )
})

test('carregador de artefatos usa somente documentos narrativos da pasta gerada', () => {
  const artifacts = buildPublicationArtifacts()
  assert.equal(artifacts.queue.summary.regionCount, 10)
  assert.equal(artifacts.queue.summary.narrativeCount, 1)
})
