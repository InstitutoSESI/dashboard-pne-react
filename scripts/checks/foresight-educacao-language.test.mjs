import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  findFutureNumericProjection,
  findPublicLanguageViolations,
  HORIZON_SCAN_YEAR,
  HORIZON_STATE_YEAR,
  LAST_OBSERVED_YEAR,
} from '../../src/features/foresight/foresightPublicLanguage.js'
import { parseForesightDocument } from '../../src/features/foresight/foresightEducacaoLoader.js'

const MUNICIPALITY_IDS = ['4313375', '4318705']

const documents = []
for (const municipalityId of MUNICIPALITY_IDS) {
  const raw = await readFile(
    new URL(`../../public/data/foresight-educacao/municipios/${municipalityId}.json`, import.meta.url),
    'utf8',
  )
  documents.push({ document: parseForesightDocument(JSON.parse(raw)), municipalityId, raw })
}

/** Todo texto que a página renderiza, com a classe de linguagem que lhe cabe. */
function renderedTexts(document) {
  const evidence = []
  const framing = []

  framing.push(
    document.page.eyebrow,
    document.page.title,
    document.page.description,
    document.page.neutralityNote,
    document.horizon.stateLabel,
    document.horizon.scanLabel,
    document.howToRead.label,
    document.howToRead.description,
    ...document.howToRead.items,
    document.startingPoint.label,
    document.startingPoint.description,
    document.sharedConditions.label,
    document.sharedConditions.description,
    document.sources.label,
    document.sources.description,
    ...document.sources.notes,
    document.limitations.label,
    document.limitations.description,
    ...document.limitations.items,
  )

  framing.push(
    document.observedSeries.label,
    document.observedSeries.description,
    document.signals.label,
    document.signals.description,
  )

  evidence.push(
    ...document.startingPoint.movements,
    ...document.startingPoint.tensions,
    ...document.startingPoint.limits,
    ...document.sharedConditions.items,
    ...document.signals.items,
    ...document.sources.series.flatMap((serie) => [serie.label, serie.unitLabel, serie.periodLabel]),
  )

  for (const serie of document.observedSeries.items) {
    evidence.push(serie.label, serie.unitLabel)
    for (const window of [serie.fullPeriod, serie.recentWindow]) {
      if (!window) continue
      evidence.push(window.periodLabel, window.startValue, window.endValue, window.directionLabel)
      if (window.caveat) evidence.push(window.caveat)
    }
  }

  for (const scenario of document.scenarios) {
    evidence.push(scenario.title, scenario.summary)
    for (const section of scenario.sections) {
      evidence.push(section.label, ...section.items)
    }
  }

  return { evidence, framing }
}

test('nenhum identificador interno, enum de processo ou termo de pipeline é renderizado', () => {
  for (const { document, municipalityId } of documents) {
    const { evidence, framing } = renderedTexts(document)
    for (const text of evidence) {
      assert.deepEqual(
        findPublicLanguageViolations(text, { kind: 'evidence', label: municipalityId }),
        [],
        `${municipalityId}: "${text.slice(0, 90)}"`,
      )
    }
    for (const text of framing) {
      assert.deepEqual(
        findPublicLanguageViolations(text, { kind: 'framing', label: municipalityId }),
        [],
        `${municipalityId}: "${text.slice(0, 90)}"`,
      )
    }
  }
})

test('nenhum texto renderizado atribui número a ano futuro', () => {
  for (const { document, municipalityId } of documents) {
    const { evidence, framing } = renderedTexts(document)
    for (const text of [...evidence, ...framing]) {
      assert.deepEqual(
        findFutureNumericProjection(text, { label: municipalityId }),
        [],
        `${municipalityId}: "${text.slice(0, 90)}"`,
      )
    }
  }
})

test('anos históricos permanecem nos textos e nos períodos das séries', () => {
  for (const { document, municipalityId } of documents) {
    const evidenceYears = renderedTexts(document).evidence
      .flatMap((text) => [...text.matchAll(/\b(19\d{2}|20\d{2})\b/g)].map((match) => Number(match[1])))
    assert.ok(evidenceYears.length > 0, `${municipalityId}: os textos precisam citar anos observados`)
    for (const year of evidenceYears) {
      assert.ok(year <= LAST_OBSERVED_YEAR, `${municipalityId}: ano ${year} não é observado`)
    }
    for (const serie of document.sources.series) {
      assert.ok(serie.startYear <= serie.endYear)
      assert.ok(serie.endYear <= LAST_OBSERVED_YEAR)
      assert.match(serie.periodLabel, /^\d{4}( a \d{4})?$/)
    }
  }
})

test('2031 e 2036 são admitidos apenas como horizonte declarado', () => {
  for (const { document, municipalityId } of documents) {
    assert.equal(document.horizon.stateYear, HORIZON_STATE_YEAR, municipalityId)
    assert.equal(document.horizon.scanThroughYear, HORIZON_SCAN_YEAR, municipalityId)

    const framingYears = renderedTexts(document).framing
      .flatMap((text) => [...text.matchAll(/\b(19\d{2}|20\d{2})\b/g)].map((match) => Number(match[1])))
    for (const year of framingYears) {
      assert.ok(
        year === HORIZON_STATE_YEAR || year === HORIZON_SCAN_YEAR,
        `${municipalityId}: ano ${year} fora do horizonte em texto editorial`,
      )
    }
    assert.ok(framingYears.includes(HORIZON_STATE_YEAR), municipalityId)
    assert.ok(framingYears.includes(HORIZON_SCAN_YEAR), municipalityId)
  }
})

test('nenhum cenário é destacado como melhor, pior, ideal ou mais provável', () => {
  const RANKING = [
    'melhor', 'pior', 'ideal', 'otimista', 'pessimista', 'provável', 'provavel',
    'recomendado', 'preferível', 'preferivel', 'prioritário', 'prioritario',
    'primeiro cenário', 'cenário 1', 'cenario 1', 'ranking', 'pontuação', 'nota',
  ]
  for (const { document, municipalityId } of documents) {
    const { evidence } = renderedTexts(document)
    for (const text of evidence) {
      const folded = text.toLocaleLowerCase('pt-BR')
      for (const term of RANKING) {
        assert.equal(folded.includes(term), false, `${municipalityId}: "${term}" em "${text.slice(0, 80)}"`)
      }
    }
    for (const scenario of document.scenarios) {
      assert.equal(/^\s*\d/.test(scenario.title), false, `${municipalityId}: título numerado`)
      assert.equal(/\bcen[aá]rio\s+\d/i.test(scenario.title), false, `${municipalityId}: título numerado`)
    }
  }
})

test('o texto bruto publicado não carrega identificador metodológico algum', async () => {
  const FORBIDDEN = [
    /"C[1-4]"/,
    /\bMC-\d{3}\b/,
    /\bRP-\d{2}\b/,
    /\bF0[1-5]\b/,
    /\bNAR-\d{7}/,
    /\bTRJ-\d{7}/,
    /\bSHR-\d{7}/,
    /\bEV-F0\d/,
    /evidenceIds/,
    /assertionFingerprint/,
    /scenarioFingerprint/,
    /municipalBasisFingerprint/,
    /packageStatus/,
    /selectionRobustness/,
    /gateId/,
    /not_located/,
    /requires_change_from/,
    /oneOccurrenceSensitivity/,
  ]
  for (const { municipalityId, raw } of documents) {
    for (const pattern of FORBIDDEN) {
      assert.equal(pattern.test(raw), false, `${municipalityId}: ${pattern} presente no arquivo público`)
    }
  }
  const manifestRaw = await readFile(
    new URL('../../public/data/foresight-educacao/manifest.json', import.meta.url),
    'utf8',
  )
  for (const pattern of FORBIDDEN) {
    assert.equal(pattern.test(manifestRaw), false, `manifesto: ${pattern} presente`)
  }
})

test('as condições comuns e os limites da leitura não se repetem entre si', () => {
  for (const { document, municipalityId } of documents) {
    const shared = new Set(document.sharedConditions.items)
    for (const limit of document.limitations.items) {
      assert.equal(shared.has(limit), false, `${municipalityId}: limite repetido nas condições comuns`)
    }
    for (const note of document.sources.notes) {
      assert.equal(shared.has(note), false, `${municipalityId}: nota repetida nas condições comuns`)
    }
  }
})

test('a página declara os limites do horizonte e a ausência de projeção demográfica', () => {
  for (const { document, municipalityId } of documents) {
    const notes = document.sources.notes.join(' ')
    assert.match(notes, /dimensão demográfica/, municipalityId)
    assert.match(notes, /não apresenta projeções numéricas de nascimentos ou população/, municipalityId)
    assert.match(document.limitations.items.join(' '), /não recebem probabilidade/, municipalityId)
  }
})

/*
 * Fase 6 da reorganização: o corpo da leitura saiu da página municipal para o
 * relatório compartilhado, que o Vocações da Região reusa com a identidade
 * regional. A ordem das seções é a mesma e continua vigiada — só mudou o
 * arquivo que é dono do JSX.
 */
test('a seção de fontes é a última do componente da página', async () => {
  const source = await readFile(
    new URL('../../src/features/foresight/ForesightScenarioReport.tsx', import.meta.url),
    'utf8',
  )
  const labels = [...source.matchAll(/aria-labelledby="(cenarios-[a-z-]+)"/g)].map((match) => match[1])
  assert.deepEqual(labels, [
    'cenarios-como-ler',
    'cenarios-ponto-de-partida',
    'cenarios-condicoes-comuns',
    'cenarios-entrada',
    'cenarios-comparacao-titulo',
    'cenarios-detalhe-titulo',
    'cenarios-sinais',
    'cenarios-fontes',
  ])
})

test('cada valor observado reproduz o texto aprovado, com o mesmo ano e a mesma unidade', () => {
  for (const { document, municipalityId } of documents) {
    const approved = [
      ...document.startingPoint.movements,
      ...document.scenarios.flatMap(
        (scenario) => scenario.sections.find((section) => section.key === 'de-onde-o-municipio-parte')?.items ?? [],
      ),
    ].join(' ')

    assert.ok(document.observedSeries.items.length > 0, municipalityId)
    for (const serie of document.observedSeries.items) {
      for (const window of [serie.fullPeriod, serie.recentWindow].filter(Boolean)) {
        assert.ok(
          approved.includes(window.startValue),
          `${municipalityId}: valor inicial "${window.startValue}" ausente do texto aprovado`,
        )
        assert.ok(
          approved.includes(window.endValue),
          `${municipalityId}: valor final "${window.endValue}" ausente do texto aprovado`,
        )
        assert.ok(approved.includes(String(window.startYear)), `${municipalityId}: ano ${window.startYear} ausente`)
        assert.ok(approved.includes(String(window.endYear)), `${municipalityId}: ano ${window.endYear} ausente`)
        assert.ok(window.endYear <= LAST_OBSERVED_YEAR, municipalityId)
        assert.match(window.periodLabel, /^\d{4} a \d{4}$/)
        assert.match(
          window.directionLabel,
          /^(alta|queda|estabilidade|oscilação|sem direção única) no período$/,
          `${municipalityId}: direção fora do vocabulário público`,
        )
      }
      assert.ok(approved.includes(serie.label), `${municipalityId}: série "${serie.label}" ausente do texto aprovado`)
    }
  }
})

test('os sinais consolidados vêm dos cenários, sem repetição e sem texto novo', () => {
  for (const { document, municipalityId } of documents) {
    const fromScenarios = new Set(
      document.scenarios.flatMap(
        (scenario) => scenario.sections.find((section) => section.key === 'o-que-acompanhar')?.items ?? [],
      ),
    )
    assert.ok(document.signals.items.length > 0, municipalityId)
    assert.equal(new Set(document.signals.items).size, document.signals.items.length, municipalityId)
    for (const signal of document.signals.items) {
      assert.ok(fromScenarios.has(signal), `${municipalityId}: sinal fora dos cenários publicados`)
    }
    assert.deepEqual([...fromScenarios].sort(), [...document.signals.items].sort(), municipalityId)
  }
})

test('a comparação só reagrupa seções já publicadas, sem escolher nem reescrever', async () => {
  const source = await readFile(
    new URL('../../src/features/foresight/ForesightScenarioComparison.tsx', import.meta.url),
    'utf8',
  )
  const compared = [...source.matchAll(/^ {2}'([a-z-]+)',$/gm)].map((match) => match[1])
  assert.deepEqual(compared, [
    'como-este-cenario-se-forma',
    'o-que-pode-mudar-no-sistema-educacional',
    'o-que-precisa-ocorrer-para-este-cenario-ganhar-forca',
  ])

  for (const { document, municipalityId } of documents) {
    for (const key of compared) {
      const present = document.scenarios.filter(
        (scenario) => scenario.sections.some((section) => section.key === key),
      )
      assert.equal(present.length, document.scenarios.length, `${municipalityId}: ${key} ausente em algum cenário`)
    }
  }
})

test('a interface não escreve código IBGE de município publicado', async () => {
  const files = [
    'src/features/foresight/ForesightEducacaoPage.tsx',
    'src/features/foresight/ForesightScenarioTabs.tsx',
    'src/features/foresight/foresightEducacaoLoader.js',
    'src/hooks/useForesightEducacao.ts',
    'src/components/Header.jsx',
    'src/app/AppPageRouter.tsx',
  ]
  for (const file of files) {
    const source = await readFile(new URL(`../../${file}`, import.meta.url), 'utf8')
    for (const municipalityId of MUNICIPALITY_IDS) {
      assert.equal(source.includes(municipalityId), false, `${file} fixa o código ${municipalityId}`)
    }
    assert.equal(source.includes('4312625'), false, `${file} fixa o código de Muliterno`)
  }
})
