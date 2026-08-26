/*
 * A camada municipal dentro do cenário regional — contrato `vocacoes-regiao-2.4.0`,
 * Rodada 5 do V2 (sucessora da D11).
 *
 * Quatro coisas se provam aqui:
 *
 *   1. **A guarda municipal**, contra o corpus bilateral
 *      (`fixtures/vocacoes-municipal-corpus.mjs`): número futuro municipal,
 *      probabilidade, ranking implícito e causalidade município↔região.
 *   2. **A forma publicada**: as duas regiões com cenário trazem a camada; as oito
 *      sem cenário têm `block` nulo e, com ele, camada nenhuma (fail-closed).
 *   3. **Intercambialidade municipal**: a composição de cada município é distinta
 *      da dos demais — trocar dois municípios é denunciado pelos números.
 *   4. **A página**: a seção municipal aparece com o seletor quando há cenário, e
 *      **some** quando não há, sem quebrar a página.
 */

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

import { ATTACKS, DECLARED_GAPS, HONEST } from './fixtures/vocacoes-municipal-corpus.mjs'
import { UNIVERSE_LABELS } from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import { createPublicLanguageGuard, scanPublicDocument } from '../lib/vocacoes-public-language.mjs'
import { DEFAULT_SOURCE_ROOT, RESEARCH_CONTRACT_FILE } from '../generate-vocacoes-regiao.mjs'

const read = (relativePath) => readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const researchContract = JSON.parse(
  await readFile(`${DEFAULT_SOURCE_ROOT}/${RESEARCH_CONTRACT_FILE}`, 'utf8'),
)
const guard = createPublicLanguageGuard(researchContract)
guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

const REGIONS_WITH_LAYER = ['vale-do-rio-pardo', 'noroeste']
const REGIONS_WITHOUT_LAYER = [
  'central',
  'encosta-da-serra',
  'metropolitana',
  'norte',
  'serra',
  'sul',
  'vale-do-sinos',
  'vale-do-taquari',
]
const documents = Object.fromEntries(
  await Promise.all(
    [...REGIONS_WITH_LAYER, ...REGIONS_WITHOUT_LAYER].map(async (slug) => [
      slug,
      JSON.parse(await read(`public/data/vocacoes-regiao/regioes/${slug}.json`)),
    ]),
  ),
)

/* ================================================================= *
 * 1. A guarda municipal, contra o corpus bilateral
 * ================================================================= */

test('a guarda municipal recusa todos os ataques do corpus', () => {
  for (const [id, text] of ATTACKS) {
    assert.throws(
      () => guard.checkMunicipalText(text, `corpus.${id}`),
      (error) => error.name === 'PublicLanguageError',
      `o ataque ${id} passou pela guarda: "${text}"`,
    )
  }

  /* `scanPublicDocument` é a porta usada pelo gerador. Estes três probes
   * provam que a varredura alcança cada campo de prosa municipal pedido pelo
   * gate, e não apenas que `checkMunicipalText` funciona quando chamado à mão. */
  const scanned = [
    ['fut-sem-ano', (candidate, text) => {
      candidate.scenarios.block.municipalLayer.municipalities[0].composition[0].statement = text
    }],
    ['rank-maior-exposicao', (candidate, text) => {
      candidate.scenarios.block.municipalLayer.municipalities[0]
        .scenarioExposure[0].exposureStatement = text
    }],
    ['causa-explica-porque', (candidate, text) => {
      candidate.scenarios.block.municipalLayer.municipalities[0]
        .scenarioExposure[0].allowedInterpretation = text
    }],
  ]
  for (const [id, mutate] of scanned) {
    const text = ATTACKS.find(([attackId]) => attackId === id)?.[1]
    assert.ok(text, `o ataque ${id} existe no corpus`)
    const candidate = structuredClone(documents['vale-do-rio-pardo'])
    mutate(candidate, text)
    assert.throws(
      () => scanPublicDocument(candidate, guard),
      (error) => error.name === 'PublicLanguageError',
      `scanPublicDocument deixou passar ${id}`,
    )
  }
})

test('a guarda municipal aceita todos os textos honestos do corpus', () => {
  for (const [id, text] of HONEST) {
    assert.doesNotThrow(
      () => guard.checkMunicipalText(text, `corpus.${id}`),
      `o texto honesto ${id} foi barrado indevidamente: "${text}"`,
    )
  }
})

test('os furos de classe aberta continuam declarados como abertos', () => {
  for (const [id, text] of DECLARED_GAPS) {
    assert.doesNotThrow(
      () => guard.checkMunicipalText(text, `gap.${id}`),
      `o furo declarado ${id} passou a ser fechado; remova-o de DECLARED_GAPS: "${text}"`,
    )
  }
})

/* ================================================================= *
 * 2. A forma publicada e o fail-closed por ausência
 * ================================================================= */

for (const slug of REGIONS_WITH_LAYER) {
  test(`${slug}: o bloco de cenários traz a camada municipal completa`, () => {
    const block = documents[slug].scenarios.block
    assert.ok(block !== null, 'a região com cenário tem bloco')
    const layer = block.municipalLayer
    assert.ok(layer, 'o bloco traz a camada municipal')
    assert.equal(
      layer.municipalities.length,
      documents[slug].region.municipalityCount,
      'a camada cobre todos os municípios da região',
    )
    assert.ok(layer.dimensions.length > 0, 'há dimensões declaradas')
    assert.ok(layer.undecomposableDomains.length > 0, 'há domínios não decomponíveis declarados')

    const orders = new Set(block.items.map((item) => item.order))
    for (const municipality of layer.municipalities) {
      assert.match(municipality.municipalityId, /^\d{7}$/, 'o id é o código IBGE')
      assert.ok(municipality.composition.length > 0, 'o município tem composição')
      assert.equal(
        municipality.scenarioExposure.length,
        orders.size,
        'o município tem uma leitura de exposição por cenário',
      )
      for (const exposure of municipality.scenarioExposure) {
        assert.ok(orders.has(exposure.order), 'a exposição aponta para um cenário existente')
      }
    }
  })
}

test('as oito regiões sem cenário não têm camada municipal (fail-closed)', () => {
  for (const slug of REGIONS_WITHOUT_LAYER) {
    const scenarios = documents[slug].scenarios
    assert.equal(scenarios.status, 'absent', `${slug}: cenário ausente`)
    assert.equal(scenarios.block, null, `${slug}: sem bloco, sem camada municipal`)
  }
})

test('a procedência da camada acompanha o cenário: hash presente onde há, nulo onde não há', () => {
  for (const slug of REGIONS_WITH_LAYER) {
    assert.match(documents[slug].provenance.municipalPackageSha256, /^[a-f0-9]{64}$/)
  }
  for (const slug of REGIONS_WITHOUT_LAYER) {
    assert.equal(documents[slug].provenance.municipalPackageSha256, null, slug)
  }
})

/* ================================================================= *
 * 3. Intercambialidade municipal — o texto denuncia a troca pelos dados
 * ================================================================= */

for (const slug of REGIONS_WITH_LAYER) {
  test(`${slug}: a composição de cada município é distinta da dos demais`, () => {
    const municipalities = documents[slug].scenarios.block.municipalLayer.municipalities
    const fingerprints = municipalities.map((municipality) =>
      JSON.stringify(municipality.composition))
    const distinct = new Set(fingerprints)
    assert.equal(
      distinct.size,
      municipalities.length,
      'duas composições idênticas tornariam dois municípios indistinguíveis pelos números',
    )
  })

  test(`${slug}: trocar dois municípios é denunciado pela composição`, () => {
    const municipalities = documents[slug].scenarios.block.municipalLayer.municipalities
    /* Dois municípios de dados comprovadamente diferentes: o de maior e o de
     * menor participação populacional. Trocar a identidade de um pelo outro
     * deixa a composição inconsistente com o município que a recebe. */
    const shareOf = (municipality) => {
      const line = municipality.composition.find((entry) =>
        entry.dimensionLabel.startsWith('População'))
      return line ? line.statement : ''
    }
    const sorted = [...municipalities].sort((left, right) =>
      shareOf(left).localeCompare(shareOf(right)))
    const smallest = sorted[0]
    const largest = sorted[sorted.length - 1]
    assert.notEqual(smallest.municipalityId, largest.municipalityId)
    assert.notDeepEqual(
      smallest.composition,
      largest.composition,
      'a troca não seria denunciada se as composições coincidissem',
    )
  })
}

/* ================================================================= *
 * 4. A página: a seção municipal e o fail-closed
 * ================================================================= */

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

test('a página mostra a seção municipal com o seletor quando há cenário', () => {
  const layer = documents['vale-do-rio-pardo'].scenarios.block.municipalLayer
  const markup = render(documents['vale-do-rio-pardo'])

  assert.ok(markup.includes(layer.label), 'o título da seção municipal aparece')
  assert.ok(markup.includes('vocacoes-municipal-select'), 'o seletor de município aparece')
  const cadastralDimension = layer.dimensions.find((dimension) => dimension.universeLabel !== null)
  assert.ok(cadastralDimension, 'a camada declara a dimensão de universo cadastral')
  assert.ok(
    markup.includes(cadastralDimension.universeLabel),
    'a página torna explícito que a participação cadastral não é taxa sobre a população',
  )
  /* O primeiro município em ordem alfabética é o selecionado por padrão, e a
   * composição dele aparece renderizada. */
  const first = [...layer.municipalities]
    .sort((left, right) => left.name.localeCompare(right.name, 'pt-BR'))[0]
  assert.ok(markup.includes(first.name), 'o município selecionado aparece')
  assert.ok(
    markup.includes(first.composition[0].statement),
    'a composição do município selecionado é renderizada',
  )
  /* Todos os municípios aparecem como opção do seletor. */
  for (const municipality of layer.municipalities) {
    assert.ok(markup.includes(`value="${municipality.municipalityId}"`),
      `o município ${municipality.name} está no seletor`)
  }
})

test('a página não mostra a seção municipal quando não há cenário — e não quebra', () => {
  const markup = render(documents.central)
  assert.ok(!markup.includes('Os municípios no cenário'), 'sem cenário, sem seção municipal')
  assert.ok(!markup.includes('vocacoes-municipal-select'), 'sem seletor de município')
  /* A frase de ausência do cenário continua no ar. */
  assert.ok(markup.includes(documents.central.scenarios.absenceStatement))
})
