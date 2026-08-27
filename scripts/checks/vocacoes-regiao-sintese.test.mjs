/*
 * Camada de conclusões — contrato `vocacoes-regiao-2.8.0` (V5 R2; nasceu no 2.5.0, decisão V2-D8).
 *
 * O teste cobre a cadeia inteira: pacote sha-verificado na origem, forma
 * pública sem enum interno, recomposição estrutural de T1/T3/T4, T4 derivado
 * dos temas emitidos pela plataforma, guarda severa e markup SSR completo.
 */

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

import { SYNTHESIS_ATTACKS } from './fixtures/vocacoes-sintese-corpus.mjs'
import {
  SYNTHESIS_KIND_LABELS,
  UNIVERSE_LABELS,
  createVocacoesDocumentParser,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  createPublicLanguageGuard,
  scanPublicDocument,
} from '../lib/vocacoes-public-language.mjs'
import {
  DEFAULT_SOURCE_ROOT,
  RESEARCH_CONTRACT_FILE,
} from '../generate-vocacoes-regiao.mjs'

const read = (relativePath) => readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')
const manifest = JSON.parse(await read('public/data/vocacoes-regiao/manifest.json'))
const documents = Object.fromEntries(await Promise.all(manifest.regions.map(async (entry) => [
  entry.slug,
  JSON.parse(await read(`public/data/vocacoes-regiao/regioes/${entry.slug}.json`)),
])))
const originManifest = JSON.parse(
  await readFile(`${DEFAULT_SOURCE_ROOT}/MANIFESTO_ORIGEM.json`, 'utf8'),
)
const researchContract = JSON.parse(
  await readFile(`${DEFAULT_SOURCE_ROOT}/${RESEARCH_CONTRACT_FILE}`, 'utf8'),
)
const guard = createPublicLanguageGuard(researchContract)
guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry
const parseDocument = createVocacoesDocumentParser({
  documentSchema: manifest.documentSchemaVersion,
  sourceVersion: manifest.sourceVersion,
  publicationScope: manifest.publicationScope,
  referenceYear: manifest.referenceYear,
  referenceMonth: manifest.referenceMonth,
})

const KIND_LABELS = Object.values(SYNTHESIS_KIND_LABELS)
const ABSENCE_REASON_CODES = [
  'sem_intervalos_comparaveis',
  'janela_curta',
  'variancia_nula',
  'variacao_nula',
  'contraste_sem_regioes_comparaveis',
  'defasagem_sem_janela_suficiente',
  'serie_ausente',
]

test('as dez regiões publicam síntese 2.9.0 sha-verificada e válida', () => {
  assert.equal(manifest.documentSchemaVersion, 'vocacoes-regiao-2.9.0')
  assert.equal(manifest.regions.length, 10)
  for (const [slug, document] of Object.entries(documents)) {
    assert.equal(document.schemaVersion, 'vocacoes-regiao-2.9.0', slug)
    assert.doesNotThrow(() => parseDocument(structuredClone(document)), slug)
    assert.doesNotThrow(() => scanPublicDocument(structuredClone(document), guard), slug)
    const originEntry = originManifest.files.find((entry) =>
      entry.path === `pacotes/conclusoes/${slug}.json`)
    assert.ok(originEntry, `${slug}: pacote de conclusões inventariado na origem`)
    assert.equal(document.provenance.synthesisPackageSha256, originEntry.sha256, slug)
    assert.ok(document.synthesis.items.length > 0, slug)
    for (const item of document.synthesis.items) {
      assert.ok(KIND_LABELS.includes(item.kindLabel), `${slug}: kindLabel público`)
      assert.ok(!Object.prototype.hasOwnProperty.call(item, 'kind'), `${slug}: enum não atravessa`)
      assert.ok(!Object.prototype.hasOwnProperty.call(item, 'basis'), `${slug}: basis interno não atravessa`)
    }
  }
})

test('as contagens T1–T4 fecham, com T4 derivado somente no Vale do Rio Pardo', () => {
  const allItems = Object.values(documents).flatMap((document) => document.synthesis.items)
  const count = (label) => allItems.filter((item) => item.kindLabel === label).length
  assert.equal(count(SYNTHESIS_KIND_LABELS.observed), 118)
  assert.equal(count(SYNTHESIS_KIND_LABELS.state_position), 34)
  assert.equal(count(SYNTHESIS_KIND_LABELS.scenario_invariant), 2)
  assert.equal(count(SYNTHESIS_KIND_LABELS.agenda), 1)

  const agendaRegions = Object.values(documents)
    .filter((document) => document.synthesis.items.some((item) =>
      item.kindLabel === SYNTHESIS_KIND_LABELS.agenda))
    .map((document) => document.region.slug)
  assert.deepEqual(agendaRegions, ['vale-do-rio-pardo'])
  const vrp = documents['vale-do-rio-pardo']
  const agenda = vrp.synthesis.items.find((item) =>
    item.kindLabel === SYNTHESIS_KIND_LABELS.agenda)
  assert.ok(agenda.statement.includes('Educação profissional e técnica'))
  assert.ok(!vrp.synthesis.absentKinds.some((absence) =>
    absence.kindLabel === SYNTHESIS_KIND_LABELS.agenda))
  assert.ok(documents.noroeste.synthesis.absentKinds.some((absence) =>
    absence.kindLabel === SYNTHESIS_KIND_LABELS.agenda))

  const absences = Object.values(documents).flatMap((document) => document.synthesis.absentKinds)
  assert.equal(absences.filter((item) =>
    item.kindLabel === SYNTHESIS_KIND_LABELS.scenario_invariant).length, 9)
  assert.equal(absences.filter((item) => item.kindLabel === SYNTHESIS_KIND_LABELS.agenda).length, 9)
})

test('o corpus adversarial fecha linguagem, abridores, números, âncoras, temas e ausência', () => {
  assert.equal(SYNTHESIS_ATTACKS.length, 8)
  for (const attack of SYNTHESIS_ATTACKS) {
    const candidate = structuredClone(documents[attack.region])
    attack.mutate(candidate, documents)
    const run = attack.gate === 'language'
      ? () => scanPublicDocument(candidate, guard)
      : () => parseDocument(candidate)
    assert.throws(
      run,
      (error) => error.name === (attack.gate === 'language'
        ? 'PublicLanguageError'
        : 'VocacoesContractError'),
      `${attack.id} passou pelo gate ${attack.gate}`,
    )
  }
})

const vite = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  optimizeDeps: { include: [], noDiscovery: true },
  publicDir: false,
  server: { hmr: false, middlewareMode: true, watch: null },
})

after(async () => {
  await vite.close()
})

const { VocacoesReport } = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/VocacoesRegiaoPage.tsx',
)
const render = (document) => renderToStaticMarkup(createElement(VocacoesReport, { document }))

function expectedRelationCardCount(document) {
  const associationLeadIds = new Set()
  const pairLeadIds = new Set()
  let editorialCards = 0
  for (const lead of document.editorialReading.leads) {
    if (lead.kind === 'curated_association') {
      associationLeadIds.add(lead.associationId)
      editorialCards += 1
    }
    if (lead.kind === 'curated_pair') {
      pairLeadIds.add(lead.pairId)
      editorialCards += 1
    }
  }
  return editorialCards
    + document.associations.items.filter((item) => !associationLeadIds.has(item.associationId)).length
    + document.temporalPairs.items.filter((item) => !pairLeadIds.has(item.pairId)).length
}

function assertPublishedStatement(markup, block, context) {
  if (Object.prototype.hasOwnProperty.call(block, 'statement')) {
    assert.ok(markup.includes(block.statement), context)
  }
}

test('o SSR mantém toda a síntese no markup, com nav, destaques e sem enum interno', () => {
  for (const [slug, document] of Object.entries(documents)) {
    const markup = render(document)
    assert.ok(markup.includes('href="#vocacoes-conclusoes"'), `${slug}: âncora na nav`)
    assert.ok(markup.includes('O que se conclui'), `${slug}: seção`)
    assert.ok(markup.includes(document.synthesis.methodNote), `${slug}: método no SSR`)
    for (const item of document.synthesis.items) {
      assert.ok(markup.includes(item.statement), `${slug}: statement ${item.kindLabel}`)
    }
    for (const absence of document.synthesis.absentKinds) {
      assert.ok(markup.includes(absence.statement), `${slug}: ausência ${absence.kindLabel}`)
    }
    const highlighted = markup.match(/Conclusão observada/gu) ?? []
    assert.equal(
      highlighted.length,
      expectedRelationCardCount(document),
      `${slug}: um destaque por associação e par`,
    )
    assert.ok(!markup.includes('state_position'), `${slug}: sem enum T2`)
    assert.ok(!markup.includes('scenario_invariant'), `${slug}: sem enum T3`)
  }

  assert.ok(render(documents.noroeste).includes('O que vale em qualquer cenário'))
  assert.ok(render(documents['vale-do-rio-pardo']).includes('O que vale em qualquer cenário'))
})

test('o SSR publica os quatro tiles, os storyTitles e toda frase quantificada ou de guarda', () => {
  for (const [slug, document] of Object.entries(documents)) {
    const markup = render(document)
    assert.equal(markup.match(/data-tile-id=/gu)?.length ?? 0, 4, `${slug}: quatro tiles no hero`)
    assert.ok(markup.includes(document.hero.title), `${slug}: título do hero`)
    assert.ok(markup.includes(document.hero.lede), `${slug}: lede do hero`)
    assert.ok(markup.includes(document.hero.methodNote), `${slug}: método do hero`)
    for (const tile of document.hero.tiles) {
      assert.ok(markup.includes(tile.valueStatement), `${slug}: valor do tile ${tile.tileId}`)
      assert.ok(markup.includes(tile.deltaStatement), `${slug}: delta do tile ${tile.tileId}`)
      if (tile.contrastStatement !== null) {
        assert.ok(markup.includes(tile.contrastStatement), `${slug}: contraste do tile ${tile.tileId}`)
      }
    }

    for (const lead of document.editorialReading.leads) {
      if (lead.kind !== 'screened') {
        assert.ok(markup.includes(lead.storyTitle), `${slug}: storyTitle ${lead.kind}`)
      }
    }

    for (const association of document.associations.items) {
      assert.ok(markup.includes(association.observedStatement), `${slug}: observado ${association.associationId}`)
      assert.ok(markup.includes(association.allowedInterpretation), `${slug}: permitido ${association.associationId}`)
      assert.ok(markup.includes(association.prohibitedClaim), `${slug}: guarda ${association.associationId}`)
      assert.ok(markup.includes(association.associativeReading.methodNote), `${slug}: método ${association.associationId}`)
      for (const reading of association.associativeReading.factorReadings) {
        assertPublishedStatement(markup, reading.correlation, `${slug}: correlação ${reading.factorSeriesId}`)
        assertPublishedStatement(markup, reading.directionConcordance, `${slug}: concordância ${reading.factorSeriesId}`)
        assertPublishedStatement(markup, reading.comovement, `${slug}: co-movimento ${reading.factorSeriesId}`)
      }
      assertPublishedStatement(markup, association.associativeReading.stateContrast, `${slug}: contraste ${association.associationId}`)
    }

    for (const pair of document.temporalPairs.items) {
      assert.ok(markup.includes(pair.observedStatement), `${slug}: observado ${pair.pairId}`)
      assert.ok(markup.includes(pair.prohibitedClaim), `${slug}: guarda ${pair.pairId}`)
      assert.ok(markup.includes(pair.associativeReading.methodNote), `${slug}: método ${pair.pairId}`)
      assertPublishedStatement(markup, pair.associativeReading.correlation, `${slug}: correlação ${pair.pairId}`)
      assertPublishedStatement(markup, pair.associativeReading.directionConcordance, `${slug}: concordância ${pair.pairId}`)
      assertPublishedStatement(markup, pair.associativeReading.comovement, `${slug}: co-movimento ${pair.pairId}`)
      assertPublishedStatement(markup, pair.associativeReading.stateContrast, `${slug}: contraste ${pair.pairId}`)
    }

    for (const item of document.temporalPairs.laggedItems) {
      assert.ok(markup.includes(item.statement), `${slug}: leitura defasada`)
    }
    for (const relation of document.screenedRelations.items) {
      assert.ok(markup.includes(relation.originStatement), `${slug}: origem ${relation.relationId}`)
      assertPublishedStatement(markup, relation.correlation, `${slug}: correlação triada ${relation.relationId}`)
      assertPublishedStatement(markup, relation.directionConcordance, `${slug}: concordância triada ${relation.relationId}`)
      assertPublishedStatement(markup, relation.comovement, `${slug}: co-movimento triado ${relation.relationId}`)
    }
    assert.ok(markup.includes(document.screenedRelations.methodNote), `${slug}: método da triagem`)
    assert.ok(markup.includes(document.editorialReading.criteriaStatement), `${slug}: critérios editoriais`)
    assert.ok(markup.includes(document.editorialReading.noteStatement), `${slug}: notas editoriais`)

    assert.ok(markup.includes(document.decompositions.enrollment.methodStatement), `${slug}: método E2 matrícula`)
    for (const item of document.decompositions.enrollment.items) {
      assert.ok(markup.includes(item.statement), `${slug}: E2 ${item.stage}`)
    }
    for (const absence of document.decompositions.enrollment.absences) {
      assert.ok(markup.includes(absence.statement), `${slug}: ausência E2 ${absence.stage}`)
    }
    if (document.decompositions.employment.item !== null) {
      assert.ok(markup.includes(document.decompositions.employment.item.statement), `${slug}: E2 emprego`)
      assert.ok(markup.includes(document.decompositions.employment.methodStatement), `${slug}: método E2 emprego`)
    }
    if (document.decompositions.employment.absence !== null) {
      assert.ok(markup.includes(document.decompositions.employment.absence.statement), `${slug}: ausência E2 emprego`)
    }
  }
})

function cardContaining(markup, marker, context) {
  const markerPosition = markup.indexOf(marker)
  assert.ok(markerPosition >= 0, `${context}: marcador do cartão no SSR`)
  const cardStart = markup.lastIndexOf('<article class="vocacoes-card', markerPosition)
  const cardEnd = markup.indexOf('</article>', markerPosition)
  assert.ok(cardStart >= 0 && cardEnd > markerPosition, `${context}: limites do cartão no SSR`)
  return markup.slice(cardStart, cardEnd + '</article>'.length)
}

function assertMethodologicalClaim(card, claim, context) {
  const claimPosition = card.indexOf(claim)
  const detailsStart = card.lastIndexOf('<details', claimPosition)
  const summaryPosition = card.lastIndexOf(
    'Nota metodológica — o que não se conclui',
    claimPosition,
  )
  const detailsEnd = card.indexOf('</details>', claimPosition)
  assert.ok(
    claimPosition >= 0
      && detailsStart >= 0
      && summaryPosition > detailsStart
      && summaryPosition < claimPosition
      && detailsEnd > claimPosition,
    `${context}: prohibitedClaim dentro da nota metodológica`,
  )
}

test('a leitura quantificada lidera e a negação fecha o cartão', () => {
  for (const [slug, document] of Object.entries(documents)) {
    const markup = render(document)
    const lead = document.editorialReading.leads.find((item) => item.kind === 'curated_association')
    assert.ok(lead, `${slug}: associação editorial declarada`)
    const association = document.associations.items.find((item) => item.associationId === lead.associationId)
    assert.ok(association, `${slug}: associação editorial resolvida`)
    const factorReading = association.associativeReading.factorReadings.find((reading) =>
      reading.factorSeriesId === lead.factorSeriesId)
    assert.ok(factorReading, `${slug}: leitura editorial resolvida`)
    const associationCard = cardContaining(
      markup,
      association.observedStatement,
      `${slug}: primeira associação quantificada`,
    )
    const visibleStatement = Object.prototype.hasOwnProperty.call(factorReading.comovement, 'statement')
      ? factorReading.comovement.statement
      : factorReading.correlation.statement
    const readingPosition = associationCard.indexOf(visibleStatement)
    const supportLabelStart = associationCard.indexOf('vocacoes-support__label')
    const supportLabelPosition = associationCard.indexOf(
      association.educationOutcome.label,
      supportLabelStart,
    )
    const prohibitedPosition = associationCard.indexOf(association.prohibitedClaim)
    assert.ok(
      readingPosition >= 0
        && readingPosition < supportLabelPosition
        && readingPosition < prohibitedPosition,
      `${slug}: leitura antes da sustentação e da negação`,
    )

    for (const item of document.associations.items) {
      const card = cardContaining(markup, item.observedStatement, `${slug}: ${item.associationId}`)
      assertMethodologicalClaim(card, item.prohibitedClaim, `${slug}: ${item.associationId}`)
    }
    for (const pair of document.temporalPairs.items) {
      const card = cardContaining(markup, pair.observedStatement, `${slug}: ${pair.pairId}`)
      assertMethodologicalClaim(card, pair.prohibitedClaim, `${slug}: ${pair.pairId}`)
    }

    const scenarioBlock = document.scenarios.block
    const expectedMethodologicalNotes = expectedRelationCardCount(document)
      + (scenarioBlock === null
        ? 0
        : scenarioBlock.items.length
          + 1
          + scenarioBlock.municipalLayer.municipalities[0].scenarioExposure.length)
    const methodologicalNotes = markup.match(/Nota metodológica — o que não se conclui/gu) ?? []
    assert.equal(
      methodologicalNotes.length,
      expectedMethodologicalNotes,
      `${slug}: contagem precisa das notas metodológicas`,
    )

    for (const reasonCode of ABSENCE_REASON_CODES) {
      assert.ok(!markup.includes(reasonCode), `${slug}: enum ${reasonCode} fora do markup`)
    }
    assert.ok(markup.includes(document.screenedRelations.label), `${slug}: seção de triagem`)
    for (const relation of document.screenedRelations.items) {
      assert.ok(markup.includes(relation.originStatement), `${slug}: origem ${relation.relationId}`)
    }
    for (const item of document.temporalPairs.laggedItems) {
      assert.ok(markup.includes(item.statement), `${slug}: leitura defasada`)
    }
    assert.ok(markup.includes('href="#vocacoes-triagem"'), `${slug}: triagem na nav`)
  }
})
