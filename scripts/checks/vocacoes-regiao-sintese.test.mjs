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

test('as dez regiões publicam síntese 2.8.0 sha-verificada e válida', () => {
  assert.equal(manifest.documentSchemaVersion, 'vocacoes-regiao-2.8.0')
  assert.equal(manifest.regions.length, 10)
  for (const [slug, document] of Object.entries(documents)) {
    assert.equal(document.schemaVersion, 'vocacoes-regiao-2.8.0', slug)
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
      document.associations.items.length + document.temporalPairs.items.length,
      `${slug}: um destaque por associação e par`,
    )
    assert.ok(!markup.includes('state_position'), `${slug}: sem enum T2`)
    assert.ok(!markup.includes('scenario_invariant'), `${slug}: sem enum T3`)
  }

  assert.ok(render(documents.noroeste).includes('O que vale em qualquer cenário'))
  assert.ok(render(documents['vale-do-rio-pardo']).includes('O que vale em qualquer cenário'))
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
    const association = document.associations.items.find((item) =>
      item.associativeReading.factorReadings.some((reading) =>
        Object.prototype.hasOwnProperty.call(reading.correlation, 'statement')))
    assert.ok(association, `${slug}: associação com correlação declarada`)
    const factorReading = association.associativeReading.factorReadings.find((reading) =>
      Object.prototype.hasOwnProperty.call(reading.correlation, 'statement'))
    const associationCard = cardContaining(
      markup,
      association.observedStatement,
      `${slug}: primeira associação quantificada`,
    )
    const correlationPosition = associationCard.indexOf(factorReading.correlation.statement)
    const supportLabelStart = associationCard.indexOf('vocacoes-support__label')
    const supportLabelPosition = associationCard.indexOf(
      association.educationOutcome.label,
      supportLabelStart,
    )
    const prohibitedPosition = associationCard.indexOf(association.prohibitedClaim)
    assert.ok(
      correlationPosition >= 0
        && correlationPosition < supportLabelPosition
        && correlationPosition < prohibitedPosition,
      `${slug}: correlação antes da sustentação e da negação`,
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
    const expectedMethodologicalNotes = document.associations.items.length
      + document.temporalPairs.items.length
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
