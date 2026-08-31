import assert from 'node:assert/strict'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'

import {
  promoteTransactional,
  run,
} from '../generate-vocacoes-pne-compilador.mjs'
import {
  buildCompilerArtifacts,
  canonicalJson,
  COMPILER_PATHS,
  compileNarrativeDocument,
  FROZEN_INPUTS,
  FUTURE_LABELS,
  sha256,
  validateFrozenInputBytes,
  VocacoesPneCompilerError,
} from '../lib/vocacoes-pne-compilador.mjs'
import {
  lintPublicDocument,
  loadVocabulario,
} from '../lib/vocacoes-pne-linter.mjs'
import {
  isVocacoesPneNarrativePilot,
  parseVocacoesPneNarrative,
} from '../../src/features/vocacoes-regiao/vocacoesPneNarrativeContract.js'

function loadJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'))
}

function loadInputs() {
  return {
    firstResearch: loadJson(COMPILER_PATHS.firstResearch),
    firstIntegrated: loadJson(COMPILER_PATHS.firstIntegrated),
    secondResearch: loadJson(COMPILER_PATHS.secondResearch),
    secondIntegrated: loadJson(COMPILER_PATHS.secondIntegrated),
    authorship: loadJson(COMPILER_PATHS.authorship),
  }
}

function mutateInputs(mutator) {
  const inputs = structuredClone(loadInputs())
  mutator(inputs)
  return inputs
}

function collectKeys(value, result = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectKeys(item, result))
  } else if (value !== null && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      result.push(key)
      collectKeys(child, result)
    }
  }
  return result
}

function collectStrings(value, field = '', result = []) {
  if (typeof value === 'string') {
    result.push({ field, value })
  } else if (Array.isArray(value)) {
    value.forEach((item, index) => collectStrings(item, `${field}[${index}]`, result))
  } else if (value !== null && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      collectStrings(child, field ? `${field}.${key}` : key, result)
    }
  }
  return result
}

function valueAtPath(root, field) {
  let current = root
  for (const match of field.matchAll(/([^.\[\]]+)|\[(\d+)\]/gu)) {
    current = current[match[2] === undefined ? match[1] : Number(match[2])]
  }
  return current
}

const inputs = loadInputs()
const artifacts = buildCompilerArtifacts()
const document = artifacts.document
const trace = artifacts.trace
const vocab = loadVocabulario()

test('recompõe R5/R6, valida os hashes congelados e gera bytes determinísticos', () => {
  for (const [label, expectedHash] of Object.entries(FROZEN_INPUTS)) {
    const filePath = COMPILER_PATHS[label]
    const bytes = readFileSync(filePath)
    assert.equal(validateFrozenInputBytes(label, bytes), expectedHash)
    assert.equal(sha256(bytes), expectedHash)
  }
  const second = buildCompilerArtifacts()
  assert.deepEqual(second.publicBytes, artifacts.publicBytes)
  assert.deepEqual(second.traceBytes, artifacts.traceBytes)
  assert.equal(canonicalJson(second.document), canonicalJson(document))
  assert.doesNotThrow(() => run(['--check']))
})

test('o contrato público fecha duas seções, 3 + 2 cartões e três destaques válidos', () => {
  assert.equal(document.schemaVersion, 'vocacoes-pne-narrative-pilot-v1')
  assert.equal(document.contractVersion, '1.5.0')
  assert.deepEqual(document.sections.map(({ cards }) => cards.length), [3, 2])
  assert.deepEqual(
    document.sections.flatMap(({ cards }) => cards.map(({ id }) => id)),
    [
      'vds-educacao-infantil-populacao',
      'vds-ensino-fundamental-populacao',
      'vds-ensino-medio-populacao',
      'vds-coortes-rede',
      'vds-deslocamento-oferta',
    ],
  )
  const cardIds = new Set(document.sections.flatMap(({ cards }) => cards.map(({ id }) => id)))
  assert.equal(document.highlights.length, 3)
  assert.ok(document.highlights.every(({ cardId }) => cardIds.has(cardId)))
  assert.equal(isVocacoesPneNarrativePilot(document), true)
  assert.equal(parseVocacoesPneNarrative(document), document)
})

test('os cinco cartões exigem G1–G10 ok e nenhuma retenção entra na projeção', () => {
  const integratedCards = [
    ...inputs.firstIntegrated.cards,
    ...inputs.secondIntegrated.cards,
  ]
  for (const card of integratedCards) {
    assert.deepEqual(Object.keys(card.internal.gates).sort(), [
      'G1', 'G10', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9',
    ])
    assert.ok(Object.values(card.internal.gates).every(({ status }) => status === 'ok'))
  }
  const serialized = JSON.stringify(document)
  for (const { candidateId } of [
    ...inputs.firstIntegrated.retainedCandidates,
    ...inputs.secondIntegrated.retainedCandidates,
  ]) {
    assert.equal(serialized.includes(candidateId), false)
  }
  assert.equal(serialized.includes('reasonCode'), false)
})

test('future_label é derivado pela tabela fechada e o piloto não usa cenário ou número futuro', () => {
  const cards = document.sections[1].cards
  assert.deepEqual(cards.map(({ future_label: label }) => label), [
    FUTURE_LABELS.tendencia_sustentada,
    FUTURE_LABELS.mudanca_observada,
  ])
  assert.equal(FUTURE_LABELS.estudo_setorial, 'Tendência para os próximos anos')
  assert.equal(FUTURE_LABELS.cenario, 'Tema presente nos cenários')
  for (const card of inputs.secondIntegrated.cards) {
    assert.notEqual(card.internal.transformation_class, 'cenario')
    assert.equal(card.internal.future_basis.scenarioId, null)
    assert.deepEqual(card.internal.future_basis.futureNumericValues, [])
  }
})

test('visuais e distribuições copiam valores brutos dos fatos aprovados', () => {
  assert.deepEqual(
    document.sections.flatMap(({ cards }) => cards.map(({ primary_visual }) => primary_visual.template)),
    ['aligned_series', 'aligned_series', 'aligned_series', 'aligned_series', 'category_bars'],
  )
  for (const card of document.sections.flatMap(({ cards }) => cards)) {
    assert.equal(card.municipal_distribution.items.length, 10)
    assert.ok(card.municipal_distribution.items.every(({ value }) => Number.isFinite(value)))
    assert.equal(collectKeys(card.municipal_distribution).includes('ibgeCode'), false)
  }
  const displacement = document.sections[1].cards[1].primary_visual
  assert.deepEqual(
    displacement.categories.map(({ region_value, state_value }) => [region_value, state_value]),
    [
      [14.761093265806895, 8.81484168915293],
      [7.01195591257239, 3.3018410814228547],
      [15.089832796759788, 8.2202237766851],
    ],
  )
})

test('a projeção pública não contém chaves ou paths internos recursivamente', () => {
  const forbidden = new Set([
    'internal',
    'gates',
    'checks',
    'mechanism_id',
    'reasonCode',
    'evidenceFactIds',
    'factId',
    'factIds',
    'visualizationIds',
    'research_candidate_id',
    'retainedCandidates',
    'transformation_class',
    'future_basis',
    'publication_decision',
  ])
  assert.deepEqual(collectKeys(document).filter((key) => forbidden.has(key)), [])
  const serialized = JSON.stringify(document)
  assert.doesNotMatch(serialized, /primeira-saida-pesquisa|segunda-saida-pesquisa|scripts[\\/]checks[\\/]fixtures/iu)
  assert.doesNotMatch(serialized, /\b\d{7}\b/u)
})

test('o parser aplica additionalProperties false em todos os níveis públicos', () => {
  const mutations = [
    (value) => { value.extra = true },
    (value) => { value.region.extra = true },
    (value) => { value.page.extra = true },
    (value) => { value.page.details.extra = true },
    (value) => { value.highlights[0].extra = true },
    (value) => { value.sections[0].extra = true },
    (value) => { value.sections[0].cards[0].extra = true },
    (value) => { value.sections[0].cards[0].primary_visual.extra = true },
    (value) => { value.sections[0].cards[0].primary_visual.series[0].extra = true },
    (value) => { value.sections[1].cards[1].primary_visual.series_labels.extra = true },
    (value) => { value.sections[1].cards[1].primary_visual.categories[0].extra = true },
    (value) => { value.sections[0].cards[0].municipal_distribution.extra = true },
    (value) => { value.sections[0].cards[0].municipal_distribution.period.extra = true },
    (value) => { value.sections[0].cards[0].municipal_distribution.items[0].extra = true },
    (value) => { value.consultation.extra = true },
    (value) => { value.generation.extra = true },
  ]
  for (const mutate of mutations) {
    const candidate = structuredClone(document)
    mutate(candidate)
    assert.throws(() => parseVocacoesPneNarrative(candidate), TypeError)
  }
})

test('adulterações de gate, projeção, hash e texto falham fechadas', () => {
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ firstIntegrated }) => {
      firstIntegrated.cards[0].internal.gates.G5.status = 'reprovado'
    })),
    /gate não aprovado/u,
  )
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ firstIntegrated }) => {
      firstIntegrated.publicProjection[0].title = 'Texto adulterado'
    })),
    /publicProjection diverge/u,
  )
  const tamperedBytes = Buffer.concat([readFileSync(COMPILER_PATHS.firstResearch), Buffer.from(' ')])
  assert.throws(
    () => validateFrozenInputBytes('firstResearch', tamperedBytes),
    /SHA-256 divergente/u,
  )
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ authorship }) => {
      authorship.page.framing = 'A correlação determina a decisão.'
    })),
    /linter reprovou/u,
  )
})

test('adulterações de visual/fato e identidade municipal falham fechadas', () => {
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ firstResearch }) => {
      firstResearch.candidates[0].visualizations[0].series[0].points[0].value += 1
    })),
    /visual diverge/u,
  )
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ secondResearch }) => {
      const candidate = secondResearch.candidates.find(({ id }) => id === 'vds-coortes-rede')
      const fact = candidate.facts.find(({ id }) => id.endsWith('.municipios'))
      fact.values.entries[0].ibgeCode = '9999999'
    })),
    /município fora da identidade/u,
  )
})

test('campo autoral extra, chave interna, candidata retida, cenário e número futuro são recusados', () => {
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ authorship }) => {
      authorship.page.extra = 'não permitido'
    })),
    /campos extras ou ausentes/u,
  )
  const leaked = structuredClone(document)
  leaked.sections[0].cards[0].internal = { gates: {} }
  assert.throws(() => parseVocacoesPneNarrative(leaked), TypeError)
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ authorship, firstIntegrated }) => {
      authorship.highlights[0].cardId = firstIntegrated.retainedCandidates[0].candidateId
    })),
    /destaque sem cartão/u,
  )
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ secondIntegrated }) => {
      secondIntegrated.cards[0].internal.transformation_class = 'cenario'
    })),
    /cenário é recusado/u,
  )
  assert.throws(
    () => compileNarrativeDocument(mutateInputs(({ secondIntegrated }) => {
      secondIntegrated.cards[0].internal.future_basis.futureNumericValues = [2030]
    })),
    /número futuro é recusado/u,
  )
})

test('o linter cobre moldura, navegação, detalhes, fontes, gráfico e texto alternativo', () => {
  assert.deepEqual(lintPublicDocument(document, vocab), [])
  const mutations = [
    (value) => { value.page.framing = 'correlação' },
    (value) => { value.sections[0].title = 'triagem automática' },
    (value) => { value.page.details.sources = 'p-valor' },
    (value) => { value.sections[0].cards[0].sources[0] = 'coeficiente de Pearson' },
    (value) => { value.sections[0].cards[0].primary_visual.title = 'relação forte' },
    (value) => { value.sections[0].cards[0].primary_visual.alt_text = 'relação moderada' },
    (value) => { value.consultation.description = 'dados insuficientes' },
  ]
  for (const mutate of mutations) {
    const candidate = structuredClone(document)
    mutate(candidate)
    assert.ok(lintPublicDocument(candidate, vocab).length > 0)
  }
  for (const section of document.sections) {
    assert.deepEqual(lintPublicDocument(section.cards, vocab), [])
  }
})

test('o registro interno cobre todo texto público, fatos, fontes, visuais e IBGE textual', () => {
  const publicStrings = collectStrings(document)
  assert.equal(trace.textTrace.length, publicStrings.length)
  assert.equal(new Set(trace.textTrace.map(({ publicPath }) => publicPath)).size, publicStrings.length)
  for (const entry of trace.textTrace) {
    const value = valueAtPath(document, entry.publicPath)
    assert.equal(typeof value, 'string')
    assert.equal(entry.valueSha256, sha256(Buffer.from(value, 'utf8')))
  }
  assert.equal(trace.cards.length, 5)
  for (const card of trace.cards) {
    assert.ok(card.factReferences.length > 0)
    assert.ok(card.primaryVisual.visualizationIds.length > 0)
    assert.ok(card.primaryVisual.factIds.length > 0)
    assert.equal(card.municipalDistribution.municipalities.length, 10)
    for (const municipality of card.municipalDistribution.municipalities) {
      assert.match(municipality.ibgeCode, /^\d{7}$/u)
    }
  }
  assert.equal(trace.publicDocument.sha256, sha256(artifacts.publicBytes))
  assert.equal(trace.publicDocument.byteSize, artifacts.publicBytes.length)
})

test('o gerador preserva arquivos idênticos e --check detectaria qualquer byte divergente', () => {
  const publicBefore = readFileSync(COMPILER_PATHS.publicOutput)
  const traceBefore = readFileSync(COMPILER_PATHS.traceOutput)
  const result = run([])
  assert.equal(result.changed, 0)
  assert.deepEqual(readFileSync(COMPILER_PATHS.publicOutput), publicBefore)
  assert.deepEqual(readFileSync(COMPILER_PATHS.traceOutput), traceBefore)
  assert.doesNotThrow(() => run(['--check']))
  assert.throws(() => run(['--unknown']), VocacoesPneCompilerError)
})

test('falha ao promover o segundo output restaura ambos os anteriores byte a byte', (t) => {
  const directory = mkdtempSync(path.join(tmpdir(), 'vocacoes-pne-rollback-'))
  t.after(() => rmSync(directory, { recursive: true, force: true }))
  const firstPath = path.join(directory, 'primeiro.json')
  const secondPath = path.join(directory, 'segundo.json')
  const firstBefore = Buffer.from('{"versao":"anterior-1"}\n')
  const secondBefore = Buffer.from('{"versao":"anterior-2"}\n')
  writeFileSync(firstPath, firstBefore)
  writeFileSync(secondPath, secondBefore)

  const runId = 'falha-segundo-output'
  const fs = {
    existsSync,
    mkdirSync,
    readFileSync,
    readdirSync,
    rmSync,
    writeFileSync,
    renameSync(source, target) {
      if (source === `${secondPath}.tmp-${runId}` && target === secondPath) {
        throw new Error('falha injetada na promoção do segundo output')
      }
      renameSync(source, target)
    },
  }
  const outputs = [
    { filePath: firstPath, bytes: Buffer.from('{"versao":"nova-1"}\n') },
    { filePath: secondPath, bytes: Buffer.from('{"versao":"nova-2"}\n') },
  ]

  let error
  assert.throws(
    () => {
      try {
        promoteTransactional(outputs, { fs, runId })
      } catch (caught) {
        error = caught
        throw caught
      }
    },
    VocacoesPneCompilerError,
  )
  assert.equal(error.cause?.message, 'falha injetada na promoção do segundo output')
  assert.deepEqual(readFileSync(firstPath), firstBefore)
  assert.deepEqual(readFileSync(secondPath), secondBefore)
  assert.deepEqual(
    readdirSync(directory).filter((name) => name.includes('.backup-') || name.includes('.tmp-')),
    [],
  )
})

test('falha no rollback preserva o backup recuperável e restaura o outro output', (t) => {
  const directory = mkdtempSync(path.join(tmpdir(), 'vocacoes-pne-backup-'))
  t.after(() => rmSync(directory, { recursive: true, force: true }))
  const firstPath = path.join(directory, 'primeiro.json')
  const secondPath = path.join(directory, 'segundo.json')
  const firstBefore = Buffer.from('{"versao":"anterior-1"}\n')
  const secondBefore = Buffer.from('{"versao":"anterior-2"}\n')
  writeFileSync(firstPath, firstBefore)
  writeFileSync(secondPath, secondBefore)

  const runId = 'falha-no-rollback'
  const secondBackup = `${secondPath}.backup-${runId}`
  const fs = {
    existsSync,
    mkdirSync,
    readFileSync,
    readdirSync,
    rmSync,
    writeFileSync,
    renameSync(source, target) {
      if (source === `${secondPath}.tmp-${runId}` && target === secondPath) {
        throw new Error('falha injetada na promoção')
      }
      if (source === secondBackup && target === secondPath) {
        throw new Error('falha injetada na restauração')
      }
      renameSync(source, target)
    },
  }
  const outputs = [
    { filePath: firstPath, bytes: Buffer.from('{"versao":"nova-1"}\n') },
    { filePath: secondPath, bytes: Buffer.from('{"versao":"nova-2"}\n') },
  ]

  let error
  assert.throws(
    () => {
      try {
        promoteTransactional(outputs, { fs, runId })
      } catch (caught) {
        error = caught
        throw caught
      }
    },
    VocacoesPneCompilerError,
  )
  assert.match(error.message, /rollback ficou incompleto/u)
  assert.ok(error.cause instanceof AggregateError)
  assert.deepEqual(readFileSync(firstPath), firstBefore)
  assert.equal(existsSync(secondPath), false)
  assert.equal(existsSync(secondBackup), true)
  assert.deepEqual(readFileSync(secondBackup), secondBefore)
  assert.deepEqual(
    readdirSync(directory).filter((name) => name.includes('.backup-')),
    [path.basename(secondBackup)],
  )
})
