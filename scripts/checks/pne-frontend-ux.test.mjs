import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { mkdtemp, rm, stat } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import {
  buildPneSingleYearDataModel,
  formatApproximateDifference,
  formatApproximatePercent,
  getPneIndicatorPresentation,
  isApproximateIndicator,
  isComparableIndicator,
  toPnePercentDisplay,
} from '../../src/utils/pneIndicatorPresentation.js'
import { getDataSourceParts } from '../../src/utils/dataSourceNotes.js'
import { mergePne2026DiagnosticResults } from '../../src/utils/pneCycleDiagnosticResults.js'

const CYCLE = 'pne_2026_2036'

test('shared PNE presentation helpers keep card and detail decisions aligned', () => {
  const comparable = {
    atingida: false,
    distance: -10,
    meta: 100,
    tracks_goal: true,
  }

  assert.equal(isComparableIndicator(comparable), true)
  assert.equal(isComparableIndicator({ ...comparable, available: false }), false)
  assert.equal(isComparableIndicator({ ...comparable, monitoring_mode: 'approximate_reference' }), false)
  assert.equal(isApproximateIndicator({ monitoring_mode: 'approximate_reference' }, null), true)
  assert.equal(isApproximateIndicator(null, { monitoring_mode: 'approximate_reference' }), true)
  assert.equal(isApproximateIndicator(null, comparable), false)
  assert.equal(formatApproximatePercent(12.34), '12,3%')
  assert.equal(formatApproximatePercent(undefined), '—')
  assert.equal(formatApproximateDifference(1.2), '+1,2 p.p.')
  assert.equal(formatApproximateDifference(undefined), '—')
})

function presentation(key, metaRef, result) {
  return getPneIndicatorPresentation({
    cycle: CYCLE,
    item: { key, metaRef },
    result,
  })
}

test('2026 percent summaries cap the visual value at 100 and preserve the raw result', () => {
  assert.deepEqual(toPnePercentDisplay(122.4), {
    displayValue: 100,
    displayWasCapped: true,
    rawValue: 122.4,
  })

  const model = presentation(
    'pre_escola',
    '1.c',
    { end_value: 122.4, end_year: 2025, meta: 100, distance: 22.4 },
  )
  assert.equal(model.currentText, '100%')
  assert.equal(model.distanceText, '0 p.p.')
  assert.equal(model.displayWasCapped, true)
})

test('indigenous coverage and AEE are complementary with canonical sources', () => {
  const indigenous = presentation(
    'educacao_indigena_cobertura_estimada_4_17',
    '9.d',
    { end_value: 50, end_year: 2025, meta: 100, distance: -50 },
  )
  const aee = presentation(
    'aee_oferta_escolas_elegiveis',
    '10.b',
    { end_value: 75, end_year: 2025, meta: 100, distance: -25 },
  )

  for (const model of [indigenous, aee]) {
    assert.equal(model.mode, 'complementary')
    assert.equal(model.valueKind, 'percent')
    assert.equal(model.referenceLabel, 'Sem referência municipal')
    assert.equal(model.distanceLabel, null)
    assert.equal(model.quickReadingLabels.goal, 'Meta relacionada')
  }
  assert.deepEqual(indigenous.sourceIds, [
    'inep_censo_escolar',
    'ibge_censo_demografico_2022_indigena_9970',
  ])
  assert.deepEqual(aee.sourceIds, ['inep_censo_escolar'])
})

test('indigenous and AEE data models contain one complete four-column row', () => {
  const cases = [
    {
      denominatorLabel: 'População indígena de 4 a 17 anos',
      indicatorKey: 'educacao_indigena_cobertura_estimada_4_17',
      metaRef: '9.d',
      numeratorLabel: 'Matrículas indígenas',
    },
    {
      denominatorLabel: 'Escolas elegíveis',
      indicatorKey: 'aee_oferta_escolas_elegiveis',
      metaRef: '10.b',
      numeratorLabel: 'Escolas elegíveis com oferta de AEE',
    },
  ]

  for (const item of cases) {
    const result = {
      denominator: 8,
      end_value: 62.5,
      end_year: 2025,
      meta: 100,
      numerator: 5,
    }
    const model = buildPneSingleYearDataModel({
      availableYear: 2025,
      cycle: CYCLE,
      details: null,
      indicatorKey: item.indicatorKey,
      item,
      presentation: presentation(item.indicatorKey, item.metaRef, result),
      result,
      unit: 'percent',
    })

    assert.equal(model.kind, 'table')
    assert.deepEqual(model.columns.map(({ label }) => label), [
      'Ano',
      item.numeratorLabel,
      item.denominatorLabel,
      'Resultado',
    ])
    assert.deepEqual(model.rows, [{
      denominator: 8,
      numerator: 5,
      result: '63%',
      year: 2025,
    }])
  }
})

test('EJA remains a progress comparison when calculation components are absent', () => {
  const eja = presentation(
    'eja_integrada_educacao_profissional_percentual',
    '12.c',
    {
      display: { status: 'Abaixo da referência' },
      distance: -25,
      end_value: 0,
      end_year: 2025,
      meta: 25,
    },
  )

  assert.equal(eja.mode, 'progress')
  assert.equal(eja.currentText, '0%')
  assert.equal(eja.referenceLabel, 'Referência prevista na meta')
  assert.equal(eja.referenceText, '25%')
  assert.equal(eja.distanceText, '-25 p.p.')
  assert.equal(eja.statusText, 'Abaixo da referência prevista na meta')
  assert.equal(eja.statusTone, 'danger')

  const ratioSource = readFileSync(
    new URL('../../src/components/RatioDualMilestoneDetail.jsx', import.meta.url),
    'utf8',
  )
  assert.match(ratioSource, /readyWithoutBreakdown/)
  assert.match(
    ratioSource,
    /Os componentes de numerador e denominador não estão publicados para este recorte\./,
  )
  assert.doesNotMatch(ratioSource, /Carregando dados do indicador/)
  assert.doesNotMatch(ratioSource, /Detalhamento do cálculo indisponível/)
})

test('career plan is a discrete count and forum is a binary declaration', () => {
  const planResult = { end_value: 2, end_year: 2021, meta: 2 }
  const forumResult = { end_value: 1, end_year: 2021, meta: 1 }
  const plan = presentation('munic_planos_carreira_declarados', '17.c', planResult)
  const forum = presentation('munic_forum_educacao_declarado', '18.c', forumResult)

  assert.equal(plan.mode, 'tracking')
  assert.equal(plan.valueKind, 'countOfTotal')
  assert.equal(plan.currentText, '2 de 2 requisitos')
  assert.equal(plan.referenceText, '2 requisitos')
  assert.equal(plan.distanceText, '0 requisitos')
  assert.equal(plan.scaleKind, 'segmented')
  assert.equal(plan.statusText, 'Referência de acompanhamento alcançada')
  assert.equal(plan.statusTone, 'success')
  assert.doesNotMatch(plan.currentText, /%/)

  assert.equal(forum.mode, 'tracking')
  assert.equal(forum.valueKind, 'binaryDeclaration')
  assert.equal(forum.currentText, 'Declarado')
  assert.equal(forum.referenceText, 'Declarado')
  assert.equal(forum.distanceText, null)
  assert.equal(forum.scaleKind, 'binary')
  assert.equal(forum.showDistance, false)
  assert.equal(forum.statusText, 'Referência de acompanhamento alcançada')
  assert.doesNotMatch(forum.currentText, /%/)

  const planTable = buildPneSingleYearDataModel({
    availableYear: 2021,
    cycle: CYCLE,
    indicatorKey: 'munic_planos_carreira_declarados',
    item: { key: 'munic_planos_carreira_declarados', metaRef: '17.c' },
    presentation: plan,
    result: planResult,
    unit: 'count',
  })
  const forumTable = buildPneSingleYearDataModel({
    availableYear: 2021,
    cycle: CYCLE,
    indicatorKey: 'munic_forum_educacao_declarado',
    item: { key: 'munic_forum_educacao_declarado', metaRef: '18.c' },
    presentation: forum,
    result: forumResult,
    unit: 'count',
  })

  assert.deepEqual(planTable.rows[0], {
    denominator: 2,
    numerator: 2,
    result: '2 de 2 requisitos',
    year: 2021,
  })
  assert.deepEqual(forumTable.rows[0], {
    result: 'Declarado',
    year: 2021,
  })
})

test('relation-specific source copy resolves from the canonical contract', () => {
  const indigenous = getDataSourceParts({
    block: 'pne',
    cycle: CYCLE,
    indicatorKey: 'educacao_indigena_cobertura_estimada_4_17',
    result: { end_year: 2025 },
  })
  const aee = getDataSourceParts({
    block: 'pne',
    cycle: CYCLE,
    indicatorKey: 'aee_oferta_escolas_elegiveis',
    result: { end_year: 2025 },
  })
  const plan = getDataSourceParts({
    block: 'pne',
    cycle: CYCLE,
    indicatorKey: 'munic_planos_carreira_declarados',
    result: { end_year: 2021 },
  })
  const forum = getDataSourceParts({
    block: 'pne',
    cycle: CYCLE,
    indicatorKey: 'munic_forum_educacao_declarado',
    result: { end_year: 2021 },
  })

  assert.match(indigenous.source, /INEP — Censo Escolar 2025/)
  assert.match(indigenous.source, /IBGE — Censo Demográfico 2022/)
  assert.equal(aee.source, 'INEP — Censo Escolar 2025')
  assert.equal(plan.source, 'IBGE — MUNIC, Educação 2021')
  assert.equal(forum.source, 'IBGE — MUNIC, Educação 2021')
  for (const note of [indigenous, aee, plan, forum]) {
    assert.match(note.methodology, /Cálculo:/)
  }
})

test('cycle cards keep metrics on one row and move technical metadata to detail notes', () => {
  const cardSource = readFileSync(
    new URL('../../src/components/MetaCard.jsx', import.meta.url),
    'utf8',
  )
  const cardCss = readFileSync(
    new URL('../../src/styles/pne-cycle-experience.css', import.meta.url),
    'utf8',
  )
  const cyclePageSource = readFileSync(
    new URL('../../src/pages/CyclePage.jsx', import.meta.url),
    'utf8',
  )

  assert.doesNotMatch(cardSource, /meta-card__metadata/)
  assert.doesNotMatch(cardSource, /meta-card__metric--trend/)
  assert.match(cardSource, /toPnePercentDisplay\(result\?\.end_value\)\.displayValue/)
  assert.match(cyclePageSource, /<footer className="cycle-card-workspace__notes">/)
  assert.doesNotMatch(cardCss, /\.meta-card--cycle \.meta-card__metadata/)
  assert.match(cardCss, /grid-template-columns: minmax\(min-content, 1fr\) minmax\(0, 1\.8fr\) minmax\(0, 1fr\)/)
  assert.match(cardCss, /\.meta-card--cycle \.meta-card__metric > span \{[\s\S]*?white-space: nowrap/)
  assert.match(cardCss, /\.cycle-card-workspace__notes \{[\s\S]*?padding: 0 var\(--space-4\) var\(--space-4\)/)

  const detailNote = getDataSourceParts({
    cycle: CYCLE,
    indicatorKey: 'pre_escola',
    item: { key: 'pre_escola', metaRef: '1.c' },
    result: { end_value: 122.4, end_year: 2025, meta: 100 },
  }).methodology
  assert.match(detailNote, /Territorialidade:/)
  assert.match(detailNote, /Limitação:/)
  assert.match(detailNote, /resumos exibem no máximo 100%[\s\S]*122,4%/i)
  assert.doesNotMatch(detailNote, /\b(?:Numerador|Denominador):/i)
  assert.doesNotMatch(detailNote, /\b(?:mat_infantil_pre|pop_4_5)\b/)
})

test('theme filters wrap complete labels without horizontal clipping', () => {
  const cyclePageSource = readFileSync(
    new URL('../../src/pages/CyclePage.jsx', import.meta.url),
    'utf8',
  )
  const css = readFileSync(
    new URL('../../src/styles/pne-cycle-experience.css', import.meta.url),
    'utf8',
  )

  assert.match(cyclePageSource, /\{group\.label\}/)
  assert.doesNotMatch(cyclePageSource, /group\.shortLabel/)
  assert.match(css, /\.dashboard-shell \.content-area \.cycle-theme-nav__chips \{[\s\S]*?flex-wrap: wrap;[\s\S]*?overflow: visible;/)
  assert.match(css, /\.dashboard-shell \.content-area \.cycle-theme-nav__chip \{[\s\S]*?max-width: none;/)
  assert.match(css, /\.dashboard-shell \.content-area \.cycle-theme-nav__chip-label \{[\s\S]*?white-space: normal;/)
  assert.match(css, /\.legal-goals-theme-filter__chips\.platform-filter-list \{[\s\S]*?flex-wrap: wrap;[\s\S]*?overflow-x: visible;/)
})

test('print and mobile CSS expose sources and use responsive grids without internal scroll', () => {
  const sourceNotes = readFileSync(
    new URL('../../src/components/PneSourceNotes.jsx', import.meta.url),
    'utf8',
  )
  const css = readFileSync(
    new URL('../../src/styles/pne-cycle-experience.css', import.meta.url),
    'utf8',
  )

  assert.match(sourceNotes, /className="pne-source-notes-print"/)
  assert.match(css, /\.cycle-page \.pne-source-notes-print/)
  assert.match(css, /size: A4 portrait/)
  assert.match(css, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/)
  assert.match(css, /\.pne-presentation-table td::before/)
  assert.match(css, /content: attr\(data-label\)/)
  assert.match(css, /\.basic-education-filter[\s\S]*overflow: visible/)
})

test('real A4 PDF includes the expanded source and calculation block', {
  skip: !process.env.PNE_UX_BASE_URL,
}, async () => {
  const { chromium } = await import('playwright')
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {}),
  })
  const outputDirectory = await mkdtemp(join(tmpdir(), 'pne-frontend-ux-'))
  const outputPath = join(outputDirectory, 'forum-educacao-a4.pdf')

  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
    await page.goto(`${process.env.PNE_UX_BASE_URL}#pne2026`, {
      waitUntil: 'networkidle',
    })
    await page.locator('.context-bar input[role="combobox"]').fill('São Leopoldo')
    await page.getByRole('option', { name: 'São Leopoldo', exact: true }).click()
    await page.getByRole('heading', { name: 'PNE 2026–2036', exact: true }).waitFor()
    await page.getByRole('button', {
      name: 'Gestão Escolar e Educação Ambiental 3',
      exact: true,
    }).click()
    await page.getByRole('button', {
      name: 'Abrir detalhe do indicador Fórum de educação declarado',
      exact: true,
    }).click()
    await page.emulateMedia({ media: 'print' })

    const printSource = page.locator('.pne-source-notes-print')
    await assert.doesNotReject(() => printSource.waitFor({ state: 'visible' }))
    const printText = await printSource.innerText()
    assert.match(printText, /Fonte: IBGE — MUNIC, Educação 2021/)
    assert.match(printText, /Período do resultado: 2021/)
    assert.doesNotMatch(printText, /Numerador:/)
    assert.doesNotMatch(printText, /Denominador:/)
    assert.doesNotMatch(printText, /\b(?:[A-Za-z][A-Za-z0-9]*_)+[A-Za-z0-9]+\b/)
    assert.match(printText, /Nota metodológica:/)

    await page.pdf({
      format: 'A4',
      margin: {
        bottom: '12mm',
        left: '12mm',
        right: '12mm',
        top: '12mm',
      },
      path: outputPath,
      printBackground: true,
    })
    assert.ok((await stat(outputPath)).size > 10_000)
  } finally {
    await browser.close()
    await rm(outputDirectory, { force: true, recursive: true })
  }
})

test('keeps numerator and denominator when diagnostic results enter the cycle view model', () => {
  const merged = mergePne2026DiagnosticResults({}, {
    goals: [{
      results: [{
        current: {
          denominator: 10,
          numerator: 4,
          unit: 'percent',
          value: 40,
          year: 2022,
        },
        denominator: 10,
        distance: -60,
        indicatorId: 'aee_oferta_escolas_elegiveis',
        indicatorReference: {
          direction: 'at_least',
          value: 100,
        },
        mode: 'tracking',
        numerator: 4,
        status: 'Abaixo da referência',
      }],
    }],
  })

  assert.equal(merged.aee_oferta_escolas_elegiveis.numerator, 4)
  assert.equal(merged.aee_oferta_escolas_elegiveis.denominator, 10)
})
