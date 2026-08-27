import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

import {
  AGENDA_THEME_LABELS,
  AGENDA_THEMES,
  ASSOCIATIVE_METHOD_NOTE,
  EDITORIAL_CRITERIA_STATEMENT,
  EDITORIAL_READING_CRITERIA,
  PNE_SERIES_THEME_MAP,
  SCREENED_ORIGIN_STATEMENT,
  SCREENED_RELATIONS_CRITERIA,
  SCREENING_EXCLUDED_SERIES_IDS,
  UNIVERSE_LABELS,
  VOCACOES_DOCUMENT_SCHEMA,
  computeComovement,
  computeDirectionConcordance,
  computePearsonDelta,
  computeSpearmanDelta,
  correlationStrength,
  createVocacoesDocumentParser,
  renderComovementStatement,
  renderConcordanceStatement,
  renderContrastStatement,
  renderCorrelationStatement,
  renderEditorialNoteStatement,
  renderLaggedStatement,
  roundHalfAwayFromZero,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  ASSOCIATIVE_PACKAGE_SCHEMA,
  DEFAULT_SOURCE_ROOT,
  RESEARCH_CONTRACT_FILE,
  RESEARCH_CONTRACT_VERSION,
  transposeDecompositions,
  transposeRegion,
} from '../generate-vocacoes-regiao.mjs'
import {
  CAUSAL_FLOOR,
  assertResearchContractCoversFloor,
  createPublicLanguageGuard,
  scanPublicDocument,
} from '../lib/vocacoes-public-language.mjs'
import {
  ATAQUES,
  ATTACK_COUNT,
  DECLARED_GAPS,
  HONESTOS,
  HONEST_COUNT,
} from './fixtures/vocacoes-associativo-corpus.mjs'

const PUBLIC_ROOT = new URL('../../public/data/vocacoes-regiao/', import.meta.url)
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json', PUBLIC_ROOT), 'utf8'))
const documents = manifest.regions.map((entry) => ({
  entry,
  document: JSON.parse(fs.readFileSync(new URL(entry.path, PUBLIC_ROOT), 'utf8')),
}))
const researchContract = JSON.parse(fs.readFileSync(
  path.join(DEFAULT_SOURCE_ROOT, RESEARCH_CONTRACT_FILE),
  'utf8',
))
const PREPUBLICATION_SCHEMA = 'vocacoes-regiao-2.7.0'
const PREPUBLICATION_SKIP =
  'publicação V5 R2 2.8.0 ainda não promovida: public/data permanece em vocacoes-regiao-2.7.0'

test('gerador exige contrato de pesquisa v0.6 e pacote associativo v0.3', () => {
  assert.equal(RESEARCH_CONTRACT_VERSION, 'vocacoes-regiao-pesquisa-v0.6')
  assert.equal(researchContract.schemaVersion, 'vocacoes-regiao-pesquisa-contrato-v0.6')
  assert.equal(researchContract.contractVersion, 'v0.6')
  assert.equal(
    researchContract.decompositionLayer.associativeSchemaVersion,
    ASSOCIATIVE_PACKAGE_SCHEMA,
  )
  assert.equal(assertResearchContractCoversFloor(researchContract), true)
})

test('H-V5R2-03: guarda v0.6 preserva os dez documentos 2.7.0 vigentes', () => {
  const guard = createPublicLanguageGuard(researchContract)
  guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry
  for (const { entry, document } of documents) {
    assert.doesNotThrow(() => scanPublicDocument(document, guard), entry.slug)
  }
})

test('gerador rebaixa demographicPp divergente sem remover a leitura E1', () => {
  const sourceBytes = fs.readFileSync(path.join(
    DEFAULT_SOURCE_ROOT,
    'pacotes',
    'regioes',
    'vale-do-sinos.json',
  ))
  const sourcePackage = JSON.parse(sourceBytes.toString('utf8'))
  const associativePackage = JSON.parse(fs.readFileSync(path.join(
    DEFAULT_SOURCE_ROOT,
    'pacotes',
    'associativo',
    'vale-do-sinos.json',
  ), 'utf8'))
  const stage = associativePackage.decompositions.enrollment.items[0].stage
  const valid = transposeDecompositions({ associativePackage, sourcePackage })
  assert.ok(valid.enrollment.items.some((item) => item.stage === stage))

  const tampered = structuredClone(associativePackage)
  tampered.decompositions.enrollment.items[0].contributions.demographicPp += 2
  const downgraded = transposeDecompositions({
    associativePackage: tampered,
    sourcePackage,
  })
  assert.ok(!downgraded.enrollment.items.some((item) => item.stage === stage))
  assert.ok(downgraded.enrollment.absences.some((absence) =>
    absence.stage === stage && absence.reasonCode === 'conta_nao_fecha'))

  const synthesisBytes = fs.readFileSync(path.join(
    DEFAULT_SOURCE_ROOT,
    'pacotes',
    'conclusoes',
    'vale-do-sinos.json',
  ))
  const synthesisPackage = JSON.parse(synthesisBytes.toString('utf8'))
  const registry = JSON.parse(fs.readFileSync(path.join(
    DEFAULT_SOURCE_ROOT,
    'registro',
    'registro_regioes_rs_v0_1.json',
  ), 'utf8'))
  const registryRegion = registry.regions.find((region) => region.slug === 'vale-do-sinos')
  const guard = createPublicLanguageGuard(researchContract)
  guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry
  const common = {
    registryRegion,
    sourcePackage,
    sourcePackageSha256: createHash('sha256').update(sourceBytes).digest('hex'),
    synthesisPackage,
    synthesisPackageSha256: createHash('sha256').update(synthesisBytes).digest('hex'),
    researchContract,
    guard,
  }
  const validDocument = transposeRegion({ ...common, associativePackage })
  const downgradedDocument = transposeRegion({ ...common, associativePackage: tampered })
  const parseGenerated = createVocacoesDocumentParser({
    sourceVersion: researchContract.schemaVersion,
    publicationScope: 'estadual',
    referenceYear: researchContract.referenceYear,
    referenceMonth: researchContract.referenceMonth,
  })
  assert.doesNotThrow(() => parseGenerated(structuredClone(downgradedDocument)))
  assert.ok(!downgradedDocument.decompositions.enrollment.items.some((item) =>
    item.stage === stage))
  assert.ok(downgradedDocument.decompositions.enrollment.absences.some((absence) =>
    absence.stage === stage && absence.reasonCode === 'conta_nao_fecha'))
  assert.deepEqual(downgradedDocument.associations, validDocument.associations)
})

if (manifest.documentSchemaVersion === PREPUBLICATION_SCHEMA) {
  test('publicação associativa V5 R2', { skip: PREPUBLICATION_SKIP }, () => {})
} else {
  test('manifesto publicado usa o contrato associativo 2.8.0', () => {
    assert.equal(manifest.documentSchemaVersion, VOCACOES_DOCUMENT_SCHEMA)
    assert.equal(manifest.regions.length, 10)
  })

  const documentBySlug = new Map(documents.map(({ document }) => [document.region.slug, document]))
  const parseDocument = createVocacoesDocumentParser({
    sourceVersion: manifest.sourceVersion,
    publicationScope: manifest.publicationScope,
    referenceYear: manifest.referenceYear,
    referenceMonth: manifest.referenceMonth,
  })

  function seriesById(document) {
    return new Map(document.territoryPortrait.series.map((serie) => [serie.seriesId, serie]))
  }

  function deltaKindOf(serie) {
    return serie.ratioOf === null ? 'nivel' : 'pontos'
  }

  function expectedDirection(serieA, serieB, window) {
    const computed = computeDirectionConcordance(serieA.points, serieB.points, window)
    if ('reasonCode' in computed) return computed
    return {
      ...computed,
      statement: renderConcordanceStatement({
        ...computed,
        labelA: serieA.label,
        labelB: serieB.label,
      }),
    }
  }

  function expectedComovement(serieA, serieB, window, roles) {
    const movementA = computeComovement(serieA.points, window, deltaKindOf(serieA))
    const movementB = computeComovement(serieB.points, window, deltaKindOf(serieB))
    if ('reasonCode' in movementA || 'reasonCode' in movementB) {
      return { reasonCode: 'sem_intervalos_comparaveis' }
    }
    return {
      [roles[0]]: { seriesId: serieA.seriesId, ...movementA },
      [roles[1]]: { seriesId: serieB.seriesId, ...movementB },
      statement: renderComovementStatement({
        a: movementA,
        b: movementB,
        labelA: serieA.label,
        labelB: serieB.label,
      }),
    }
  }

  function expectedCorrelation(serieA, serieB, window, { statement = true } = {}) {
    const direction = computeDirectionConcordance(serieA.points, serieB.points, window)
    const intervals = 'reasonCode' in direction ? 0 : direction.intervals
    if (intervals < 5) return { reasonCode: 'janela_curta' }
    const pearsonRaw = computePearsonDelta(serieA.points, serieB.points, window)
    const spearmanRaw = computeSpearmanDelta(serieA.points, serieB.points, window)
    if (pearsonRaw === null || spearmanRaw === null) return { reasonCode: 'variancia_nula' }
    const correlationDirection = pearsonRaw > 0 ? 'positiva' : pearsonRaw < 0 ? 'negativa' : 'nula'
    const result = {
      intervals,
      pearsonDelta: roundHalfAwayFromZero(pearsonRaw, 2),
      spearmanDelta: roundHalfAwayFromZero(spearmanRaw, 2),
      strength: correlationStrength(Math.abs(pearsonRaw)),
      direction: correlationDirection,
    }
    if (statement) {
      result.statement = renderCorrelationStatement({
        windowStart: window.start,
        windowEnd: window.end,
        pearsonDelta: result.pearsonDelta,
        strength: result.strength,
        direction: result.direction,
      })
    }
    return result
  }

  function expectedSalience(serieA, serieB, window) {
    const pearson = computePearsonDelta(serieA.points, serieB.points, window)
    return pearson !== null
      && EDITORIAL_READING_CRITERIA.leadStrengths.includes(correlationStrength(Math.abs(pearson)))
      ? 'lead'
      : 'note'
  }

  function expectedPneThemes(...seriesIds) {
    const resolved = new Set(seriesIds.flatMap((seriesId) => PNE_SERIES_THEME_MAP[seriesId] ?? []))
    return AGENDA_THEMES.filter((theme) => resolved.has(theme)).map((theme) => ({
      theme,
      themeLabel: AGENDA_THEME_LABELS[theme],
    }))
  }

  function assertComparison(reading, serieA, serieB, window, roles, label) {
    assert.deepEqual(reading.directionConcordance, expectedDirection(serieA, serieB, window),
      `${label}.directionConcordance`)
    assert.deepEqual(reading.comovement, expectedComovement(serieA, serieB, window, roles),
      `${label}.comovement`)
    assert.deepEqual(reading.correlation, expectedCorrelation(serieA, serieB, window),
      `${label}.correlation`)
    assert.equal(reading.salience, expectedSalience(serieA, serieB, window), `${label}.salience`)
    assert.equal(reading.grade, EDITORIAL_READING_CRITERIA.gradeEnum[0], `${label}.grade`)
  }

  function comparableStateMovements(seriesId, window) {
    const comparable = []
    for (const { document } of documents) {
      const serie = seriesById(document).get(seriesId)
      if (serie === undefined) continue
      const movement = computeComovement(serie.points, window, deltaKindOf(serie))
      if ('reasonCode' in movement || (movement.deltaKind === 'nivel' && movement.valueStart === 0)) {
        continue
      }
      comparable.push({
        regionSlug: document.region.slug,
        serie,
        movement,
        value: movement.deltaKind === 'pontos'
          ? movement.delta
          : movement.delta / movement.valueStart * 100,
      })
    }
    return comparable
  }

  function expectedContrast(document, serie, window) {
    const comparable = comparableStateMovements(serie.seriesId, window)
    if (comparable.length < 2) return { reasonCode: 'contraste_sem_regioes_comparaveis' }
    const own = comparable.find((entry) => entry.regionSlug === document.region.slug)
    assert.ok(own, `contraste excluiu a própria região ${document.region.slug}`)
    if (own.value === 0) return { reasonCode: 'variacao_nula' }
    const direction = own.value > 0 ? 'alta' : 'queda'
    const result = {
      seriesId: serie.seriesId,
      statistic: own.movement.deltaKind === 'pontos'
        ? 'variacao_em_pontos'
        : 'variacao_percentual',
      value: roundHalfAwayFromZero(own.value, 1),
      rank: 1 + comparable.filter((entry) =>
        direction === 'alta' ? entry.value > own.value : entry.value < own.value).length,
      totalComparable: comparable.length,
      sameDirectionCount: comparable.filter((entry) =>
        direction === 'alta' ? entry.value > 0 : entry.value < 0).length,
      direction,
    }
    return {
      ...result,
      statement: renderContrastStatement({ ...result, label: serie.label }),
    }
  }

  function lagPeriods(serieA, serieB, lagYears) {
    const valuesA = new Set(serieA.points.map((point) => point.period))
    const valuesB = new Set(serieB.points.map((point) => point.period))
    return [...valuesA]
      .filter((period) => valuesA.has(period - 1)
        && valuesB.has(period + lagYears - 1)
        && valuesB.has(period + lagYears))
      .sort((left, right) => left - right)
  }

  function assertLagged(document, item, index) {
    const byId = seriesById(document)
    const serieA = byId.get(item.aSeriesId)
    const serieB = byId.get(item.bSeriesId)
    assert.ok(serieA && serieB, `laggedItems[${index}] referencia série ausente`)
    const periods = lagPeriods(serieA, serieB, item.lagYears)
    if (periods.length < 5) {
      assert.equal(item.reasonCode, 'defasagem_sem_janela_suficiente')
      assert.equal(item.statement, renderLaggedStatement({
        aSeriesLabel: serieA.label,
        bSeriesLabel: serieB.label,
        lagYears: item.lagYears,
        reasonCode: item.reasonCode,
      }))
      return
    }
    const windowA = { start: periods[0] - 1, end: periods[periods.length - 1] }
    const windowB = { start: windowA.start + item.lagYears, end: windowA.end + item.lagYears }
    const shiftedB = {
      ...serieB,
      points: serieB.points.map((point) => ({ ...point, period: point.period - item.lagYears })),
    }
    const concordance = computeDirectionConcordance(serieA.points, shiftedB.points, windowA)
    assert.ok(!('reasonCode' in concordance))
    assert.deepEqual(item.windowA, windowA)
    assert.deepEqual(item.windowB, windowB)
    assert.deepEqual(
      {
        intervals: item.intervals,
        concordant: item.concordant,
        opposite: item.opposite,
        ties: item.ties,
      },
      {
        intervals: concordance.intervals,
        concordant: concordance.concordant,
        opposite: concordance.opposite,
        ties: concordance.ties,
      },
    )
    assert.deepEqual(item.correlation, expectedCorrelation(serieA, shiftedB, windowA, {
      statement: false,
    }))
    assert.equal(item.statement, renderLaggedStatement({
      aSeriesLabel: serieA.label,
      bSeriesLabel: serieB.label,
      lagYears: item.lagYears,
      rationale: item.rationale,
      windowA,
      windowB,
      concordant: item.concordant,
      intervals: item.intervals,
      correlation: item.correlation,
    }))
    assert.equal(item.salience, 'lead')
    assert.equal(item.grade, EDITORIAL_READING_CRITERIA.gradeEnum[0])
    assert.deepEqual(item.pneThemes, expectedPneThemes(item.bSeriesId))
  }

  test('piso da plataforma é subconjunto do contrato de pesquisa v0.6', () => {
    assert.equal(researchContract.contractVersion, 'v0.6')
    assert.equal(assertResearchContractCoversFloor(researchContract), true)
    const causal = new Set(researchContract.causalLanguagePatterns)
    for (const pattern of CAUSAL_FLOOR) assert.ok(causal.has(pattern), pattern)
    /*
     * V3-D8 em forma comportamental: o piso não pode recusar o coeficiente
     * dentro da moldura fechada. Um padrão que cite "correla" por proximidade
     * (comprova + relação/correlação) é permitido; banir o termo, não.
     */
    const honestCorrelation = 'Na janela de 2014 a 2025, a correlação entre as variações '
      + 'anuais das duas séries é de -0,72 — forte e negativa.'
    for (const pattern of CAUSAL_FLOOR) {
      assert.ok(!new RegExp(pattern, 'iu').test(honestCorrelation), pattern)
    }
  })

  test('dez documentos passam no parser e na recomputação associativa integral', () => {
    for (const { document } of documents) {
      parseDocument(structuredClone(document))
      const byId = seriesById(document)
      document.associations.items.forEach((association, associationIndex) => {
        assert.equal(association.associativeReading.methodNote, ASSOCIATIVE_METHOD_NOTE)
        assert.deepEqual(
          association.pneThemes,
          expectedPneThemes(association.educationOutcome.seriesId),
        )
        const outcome = byId.get(association.educationOutcome.seriesId)
        association.associativeReading.factorReadings.forEach((reading, factorIndex) => {
          const factor = byId.get(reading.factorSeriesId)
          assertComparison(
            reading,
            outcome,
            factor,
            association.window,
            ['outcome', 'factor'],
            `${document.region.slug}.associations[${associationIndex}].factorReadings[${factorIndex}]`,
          )
        })
        assert.deepEqual(
          association.associativeReading.stateContrast,
          expectedContrast(document, outcome, association.window),
        )
      })
      document.temporalPairs.items.forEach((pair, pairIndex) => {
        const serieA = byId.get(pair.seriesA.seriesId)
        const serieB = byId.get(pair.seriesB.seriesId)
        assert.deepEqual(pair.pneThemes, expectedPneThemes(pair.seriesA.seriesId, pair.seriesB.seriesId))
        assertComparison(
          pair.associativeReading,
          serieA,
          serieB,
          pair.window,
          ['a', 'b'],
          `${document.region.slug}.temporalPairs[${pairIndex}]`,
        )
        assert.deepEqual(
          pair.associativeReading.stateContrast,
          expectedContrast(document, serieB, pair.window),
        )
      })
      document.temporalPairs.laggedItems.forEach((item, index) =>
        assertLagged(document, item, index))
    }
  })

  const EDUCATION_SERIES_IDS = new Set([
    'matriculas-na-educacao-infantil',
    'matriculas-no-ensino-fundamental',
    'matriculas-no-ensino-medio',
    'matriculas-na-educacao-profissional',
    'matriculas-na-educacao-profissional-tecnica',
    'matriculas-na-educacao-de-jovens-e-adultos',
    'escolas-com-matriculas-na-educacao-basica',
    'escolas-rurais-com-matriculas-na-educacao-basica',
  ])

  function screenedCandidates(document) {
    const education = document.territoryPortrait.series.filter((serie) =>
      EDUCATION_SERIES_IDS.has(serie.seriesId) && serie.periodGranularity === 'annual')
    const territorial = document.territoryPortrait.series.filter((serie) =>
      !EDUCATION_SERIES_IDS.has(serie.seriesId)
      && !SCREENING_EXCLUDED_SERIES_IDS.includes(serie.seriesId)
      && serie.periodGranularity === 'annual')
    const curated = new Set()
    const unordered = (left, right) => [left, right].sort().join('|')
    for (const association of document.associations.items) {
      for (const factor of association.territorialFactors) {
        curated.add(unordered(association.educationOutcome.seriesId, factor.seriesId))
      }
    }
    for (const pair of document.temporalPairs.items) {
      curated.add(unordered(pair.seriesA.seriesId, pair.seriesB.seriesId))
    }
    const candidates = []
    for (const serieA of territorial) {
      for (const serieB of education) {
        if (curated.has(unordered(serieA.seriesId, serieB.seriesId))) continue
        const periodsA = serieA.points.map((point) => point.period)
        const periodsB = serieB.points.map((point) => point.period)
        const window = {
          start: Math.max(Math.min(...periodsA), Math.min(...periodsB)),
          end: Math.min(Math.max(...periodsA), Math.max(...periodsB)),
        }
        if (window.start >= window.end) continue
        const direction = computeDirectionConcordance(serieA.points, serieB.points, window)
        const pearson = computePearsonDelta(serieA.points, serieB.points, window)
        if (
          'reasonCode' in direction
          || direction.intervals < SCREENED_RELATIONS_CRITERIA.minIntervals
          || pearson === null
          || Math.abs(pearson) < SCREENED_RELATIONS_CRITERIA.minAbsPearson
        ) continue
        candidates.push({
          relationId: `${serieA.seriesId}--${serieB.seriesId}`,
          serieA,
          serieB,
          window,
          absPearson: Math.abs(pearson),
        })
      }
    }
    return candidates
      .sort((left, right) => right.absPearson - left.absPearson
        || left.relationId.localeCompare(right.relationId, 'en'))
      .slice(0, SCREENED_RELATIONS_CRITERIA.maxItems)
  }

  test('triagem respeita limiar, teto, ordem e exclusão dos pares curados', () => {
    for (const { document } of documents) {
      assert.deepEqual(document.screenedRelations.criteria, {
        ...SCREENED_RELATIONS_CRITERIA,
        excludedSeries: [...SCREENING_EXCLUDED_SERIES_IDS],
      })
      const expected = screenedCandidates(document)
      assert.deepEqual(
        document.screenedRelations.items.map((item) => item.relationId),
        expected.map((item) => item.relationId),
        document.region.slug,
      )
      document.screenedRelations.items.forEach((item, index) => {
        const candidate = expected[index]
        assert.equal(item.originStatement, SCREENED_ORIGIN_STATEMENT)
        assert.ok(!SCREENING_EXCLUDED_SERIES_IDS.includes(item.seriesAId))
        assert.deepEqual(item.pneThemes, expectedPneThemes(item.seriesBId))
        assert.deepEqual(item.window, candidate.window)
        assertComparison(
          item,
          candidate.serieA,
          candidate.serieB,
          candidate.window,
          ['a', 'b'],
          `${document.region.slug}.screenedRelations.items[${index}]`,
        )
      })
    }
  })

  function editorialRefId(reference) {
    if (reference.kind === 'structural') {
      return `${reference.kind}/${reference.aSeriesId}/${reference.bSeriesId}/${reference.lagYears}`
    }
    if (reference.kind === 'curated_association') {
      return `${reference.kind}/${reference.associationId}/${reference.factorSeriesId}`
    }
    if (reference.kind === 'curated_pair') return `${reference.kind}/${reference.pairId}`
    return `${reference.kind}/${reference.relationId}`
  }

  function expectedEditorial(document) {
    const byId = seriesById(document)
    const structural = document.temporalPairs.laggedItems
      .filter((item) => item.reasonCode === undefined)
      .map((item) => ({
        kind: 'structural',
        aSeriesId: item.aSeriesId,
        bSeriesId: item.bSeriesId,
        lagYears: item.lagYears,
      }))
    const ranked = []
    let noteCount = 0
    const add = (reference, serieA, serieB, window) => {
      if (expectedSalience(serieA, serieB, window) === 'note') {
        noteCount += 1
        return
      }
      ranked.push({
        reference,
        absPearson: Math.abs(computePearsonDelta(serieA.points, serieB.points, window)),
        refId: editorialRefId(reference),
      })
    }
    for (const association of document.associations.items) {
      const outcome = byId.get(association.educationOutcome.seriesId)
      for (const reading of association.associativeReading.factorReadings) {
        add({
          kind: 'curated_association',
          associationId: association.associationId,
          factorSeriesId: reading.factorSeriesId,
        }, outcome, byId.get(reading.factorSeriesId), association.window)
      }
    }
    for (const pair of document.temporalPairs.items) {
      add(
        { kind: 'curated_pair', pairId: pair.pairId },
        byId.get(pair.seriesA.seriesId),
        byId.get(pair.seriesB.seriesId),
        pair.window,
      )
    }
    for (const item of document.screenedRelations.items) {
      add(
        { kind: 'screened', relationId: item.relationId },
        byId.get(item.seriesAId),
        byId.get(item.seriesBId),
        item.window,
      )
    }
    ranked.sort((left, right) => right.absPearson - left.absPearson
      || (left.refId < right.refId ? -1 : left.refId > right.refId ? 1 : 0))
    return { leads: [...structural, ...ranked.map((entry) => entry.reference)], noteCount }
  }

  test('ordem editorial, saliência, grau, temas e templates são derivados byte a byte', () => {
    for (const { document } of documents) {
      const expected = expectedEditorial(document)
      assert.deepEqual(document.editorialReading.criteria, EDITORIAL_READING_CRITERIA)
      assert.equal(document.editorialReading.criteriaStatement, EDITORIAL_CRITERIA_STATEMENT)
      assert.deepEqual(document.editorialReading.leads, expected.leads)
      assert.equal(document.editorialReading.noteCount, expected.noteCount)
      assert.equal(
        document.editorialReading.noteStatement,
        renderEditorialNoteStatement(expected.noteCount),
      )
    }
  })

  /*
   * Leituras em ausência declarada (janela de um ano, como o saldo de coortes
   * censitárias) são idênticas entre regiões por construção honesta — tupla de
   * reasonCodes, sem número nenhum. O anti-template compara só o que foi
   * computado; uma associação toda ausente fica fora da comparação.
   */
  function associativeTuple(association) {
    return association.associativeReading.factorReadings
      .filter((reading) => !(reading.directionConcordance.reasonCode !== undefined
        && reading.correlation.reasonCode !== undefined))
      .map((reading) => ({
        intervals: reading.directionConcordance.intervals,
        concordant: reading.directionConcordance.concordant,
        pearson: reading.correlation.pearsonDelta,
        valueStart: reading.comovement.outcome?.valueStart,
        valueEnd: reading.comovement.outcome?.valueEnd,
      }))
  }

  function associativeStatements(association) {
    const statements = []
    for (const reading of association.associativeReading.factorReadings) {
      for (const block of [
        reading.directionConcordance,
        reading.comovement,
        reading.correlation,
      ]) {
        if (block.statement !== undefined) statements.push(block.statement)
      }
    }
    if (association.associativeReading.stateContrast.statement !== undefined) {
      statements.push(association.associativeReading.stateContrast.statement)
    }
    return statements.join('\n')
  }

  test('anti-template e intercambialidade diferenciam regiões com associação compartilhada', () => {
    const groups = new Map()
    for (const { document } of documents) {
      const sourcePackage = JSON.parse(fs.readFileSync(path.join(
        DEFAULT_SOURCE_ROOT,
        'pacotes',
        'regioes',
        `${document.region.slug}.json`,
      ), 'utf8'))
      assert.equal(sourcePackage.associations.length, document.associations.items.length)
      document.associations.items.forEach((association, index) => {
        const associationKey = sourcePackage.associations[index].associationKey
        const entries = groups.get(associationKey) ?? []
        entries.push({ regionSlug: document.region.slug, association })
        groups.set(associationKey, entries)
      })
    }
    let shared = 0
    for (const [associationKey, entries] of groups) {
      if (entries.length < 2) continue
      shared += 1
      for (let left = 0; left < entries.length; left += 1) {
        for (let right = left + 1; right < entries.length; right += 1) {
          const pairLabel = `${associationKey}: `
            + `${entries[left].regionSlug}/${entries[right].regionSlug}`
          const leftTuple = associativeTuple(entries[left].association)
          const rightTuple = associativeTuple(entries[right].association)
          if (leftTuple.length === 0 && rightTuple.length === 0) continue
          assert.notDeepEqual(leftTuple, rightTuple, `anti-template ${pairLabel}`)
          assert.notEqual(
            associativeStatements(entries[left].association),
            associativeStatements(entries[right].association),
            `intercambialidade ${pairLabel}`,
          )
        }
      }
    }
    assert.ok(shared > 0, 'nenhuma associação compartilhada foi exercitada')
  })

  test('corpus bilateral V3 R1 + V5 R1 + V5 R2 tem 100% dos casos contabilizados', () => {
    assert.equal(ATTACK_COUNT, 25)
    assert.equal(HONEST_COUNT, 12)
    assert.deepEqual(DECLARED_GAPS, ['A-V3R1-07'])
    const base = documentBySlug.get('vale-do-sinos')
    assert.ok(base, 'Vale do Sinos não está na publicação')
    const guard = createPublicLanguageGuard(researchContract)
    guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

    let caught = 0
    let declared = 0
    for (const [id, _vector, mutate] of ATAQUES) {
      const candidate = structuredClone(base)
      mutate(candidate)
      let guardError = null
      let parserError = null
      try { scanPublicDocument(candidate, guard) } catch (error) { guardError = error }
      try { parseDocument(candidate) } catch (error) { parserError = error }
      if (DECLARED_GAPS.includes(id)) {
        declared += 1
        assert.equal(guardError, null, `${id} deixou de ser furo declarado na guarda`)
        assert.equal(parserError, null, `${id} deixou de ser furo declarado no parser`)
      } else {
        assert.ok(guardError !== null || parserError !== null, `${id} atravessou as duas guardas`)
        caught += 1
      }
    }
    assert.equal(caught + declared, ATTACK_COUNT)

    for (const [id, mutate] of HONESTOS) {
      const candidate = structuredClone(base)
      mutate(candidate)
      assert.doesNotThrow(() => scanPublicDocument(candidate, guard), `${id} barrado pela guarda`)
      assert.doesNotThrow(() => parseDocument(candidate), `${id} barrado pelo parser`)
    }
  })
}
