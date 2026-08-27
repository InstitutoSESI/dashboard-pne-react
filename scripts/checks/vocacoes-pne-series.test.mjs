import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { promisify } from 'node:util'
import { fileURLToPath } from 'node:url'

import { validatePair } from '../lib/vocacoes-pne-compatibilidade.mjs'
import {
  loadCatalogoMecanismos,
  loadRegistroSeries,
  loadRegrasUniverso,
} from '../lib/vocacoes-pne-registro.mjs'

const execFileAsync = promisify(execFile)
const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url))
const mecanismos = loadCatalogoMecanismos()
const registro = loadRegistroSeries()
const regras = loadRegrasUniverso()
const valeDoSinos = JSON.parse(
  readFileSync(
    new URL('../../public/data/vocacoes-regiao/regioes/vale-do-sinos.json', import.meta.url),
    'utf8',
  ),
)
const dependencies = { mecanismos, registro, regras }

function seededRandom(seed) {
  let state = seed >>> 0
  return () => {
    state += 0x6D2B79F5
    let value = state
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

function deterministicSample(items, size, seed) {
  const shuffled = [...items]
  const random = seededRandom(seed)
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]]
  }
  return shuffled.slice(0, size)
}

test('registro tem 101 séries, contagens esperadas e classificação das 71 publicadas', () => {
  assert.equal(registro.series.length, 101)
  const counts = Object.fromEntries(
    [...Map.groupBy(registro.series, ({ status }) => status)]
      .map(([status, items]) => [status, items.length]),
  )
  assert.equal(counts.disponivel_plataforma, 71)
  assert.equal(counts.disponivel_pesquisa, 16)
  assert.equal((counts.pendente_r3 ?? 0) + (counts.pendente_r4 ?? 0), 14)

  const published = registro.series.filter(
    ({ status }) => status === 'disponivel_plataforma',
  )
  const registryById = new Map(registro.series.map((series) => [series.seriesId, series]))
  assert.equal(valeDoSinos.territoryPortrait.series.length, 71)
  assert.deepEqual(
    new Set(published.map(({ seriesId }) => seriesId)),
    new Set(valeDoSinos.territoryPortrait.series.map(({ seriesId }) => seriesId)),
  )

  for (const series of published) {
    assert.ok(series.universo.trim().length > 0, `${series.seriesId}.universo`)
    assert.ok(series.lente.trim().length > 0, `${series.seriesId}.lente`)
  }
  for (const series of valeDoSinos.territoryPortrait.series) {
    const matches = regras.classificacao.filter(({ regex }) => regex.test(series.seriesId))
    assert.equal(matches.length, 1, `${series.seriesId}: sem regra única`)
    assert.equal(
      matches[0].universo,
      registryById.get(series.seriesId).universo,
      series.seriesId,
    )
  }
})

test('amostra determinística de cinco séries coincide entre registro e pacote', () => {
  const registryById = new Map(registro.series.map((series) => [series.seriesId, series]))
  const sample = deterministicSample(
    valeDoSinos.territoryPortrait.series,
    5,
    0x5EED2026,
  )
  assert.equal(sample.length, 5)

  for (const packageSeries of sample) {
    const registered = registryById.get(packageSeries.seriesId)
    assert.equal(registered.label, packageSeries.label, packageSeries.seriesId)
    assert.equal(registered.unit, packageSeries.unitLabel, packageSeries.seriesId)
    assert.equal(
      registered.evidenceClass,
      packageSeries.evidenceClass,
      packageSeries.seriesId,
    )
  }
})

test('razões calculadas por cem têm numerador e denominador explícitos', () => {
  const ratios = registro.series.filter((series) => (
    series.evidenceClass === 'calculated'
    && series.seriesId.includes('-por-cem-')
  ))
  assert.ok(ratios.length > 0)
  for (const series of ratios) {
    assert.ok(series.ratioOf, `${series.seriesId}.ratioOf`)
    assert.ok(
      series.ratioOf.numeratorLabel.trim().length > 0,
      `${series.seriesId}.ratioOf.numeratorLabel`,
    )
    assert.ok(
      series.ratioOf.denominatorLabel.trim().length > 0,
      `${series.seriesId}.ratioOf.denominatorLabel`,
    )
  }
})

test('P3 bloqueia faixa populacional incompatível com o ensino médio', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-medio',
      territorialSeriesId: 'populacao-de-0-a-14-anos',
      mechanismId: 'M1-coorte-15-17',
    },
    dependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'faixa-etaria-incompativel')
})

test('subgrupo etário é denominador compatível', () => {
  for (const territorialSeriesId of [
    'populacao-de-0-a-3-anos',
    'populacao-de-4-e-5-anos',
  ]) {
    const result = validatePair(
      {
        educationalSeriesId: 'matriculas-na-educacao-infantil',
        territorialSeriesId,
        mechanismId: 'M1-nascimentos-educacao-infantil',
        atendimentoAparente: true,
      },
      dependencies,
    )
    assert.equal(result.allowed, true, territorialSeriesId)
    assert.equal(result.reasonCode, null, territorialSeriesId)
  }
})

test('faixa mais ampla fora de par provisório é bloqueada', () => {
  const syntheticMechanism = {
    id: 'teste-faixa-mais-ampla',
    paresPermitidos: [
      {
        educacional: 'matriculas-no-ensino-fundamental',
        territorial: 'populacao-de-0-a-14-anos',
      },
    ],
  }
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-fundamental',
      territorialSeriesId: 'populacao-de-0-a-14-anos',
      mechanismId: syntheticMechanism.id,
    },
    {
      ...dependencies,
      mecanismos: {
        ...mecanismos,
        mecanismos: [...mecanismos.mecanismos, syntheticMechanism],
      },
    },
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'faixa-etaria-incompativel')
})

test('cadastro social não serve de denominador para EJA', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-na-educacao-de-jovens-e-adultos',
      territorialSeriesId: 'pessoas-inscritas-no-perfil-de-baixa-renda',
      mechanismId: 'M3-eja-publico',
    },
    dependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'cadastro-nao-denominador')
})

test('trabalho juvenil sem recorte etário é bloqueado', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-medio',
      territorialSeriesId: 'vinculos-formais-ativos',
      mechanismId: 'M2-trabalho-juvenil',
    },
    dependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'sem-recorte-de-idade')
})

test('lente mista exige declaração de atendimento aparente', () => {
  const pair = {
    educationalSeriesId: 'matriculas-no-ensino-medio',
    territorialSeriesId: 'populacao-de-15-a-17-anos',
    mechanismId: 'M1-coorte-15-17',
  }
  const undeclared = validatePair(pair, dependencies)
  assert.equal(undeclared.allowed, false)
  assert.equal(undeclared.reasonCode, 'lente-mista-nao-declarada')

  const declared = validatePair(
    { ...pair, atendimentoAparente: true },
    dependencies,
  )
  assert.equal(declared.allowed, true)
  assert.equal(declared.reasonCode, null)
})

test('fotografia censitária é bloqueada antes do default-deny', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-medio',
      territorialSeriesId:
        'saldo-migratorio-aparente-da-coorte-de-15-a-19-anos-no-censo-de-2010',
      mechanismId: 'M1-coorte-15-17',
    },
    dependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'fotografia-nao-serie')
})

test('par inventado é bloqueado pelo default-deny', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-medio',
      territorialSeriesId: 'obitos-por-residencia-60-a-69-anos',
      mechanismId: 'M1-coorte-15-17',
    },
    dependencies,
  )
  assert.equal(result.allowed, false)
  assert.equal(result.reasonCode, 'fora-do-catalogo')
})

test('par provisório é permitido com aproximação e nota declaradas', () => {
  const result = validatePair(
    {
      educationalSeriesId: 'matriculas-no-ensino-fundamental',
      territorialSeriesId: 'populacao-de-0-a-14-anos',
      mechanismId: 'M2-fluxo-fundamental',
    },
    dependencies,
  )
  assert.equal(result.allowed, true)
  assert.equal(result.reasonCode, null)
  assert.ok(result.avisos.includes('aproximacao-declarada'))
  assert.ok(
    result.avisos.includes(
      mecanismos.mecanismos
        .find(({ id }) => id === 'M2-fluxo-fundamental')
        .paresProvisorios[0].nota,
    ),
  )
})

test('gerador confirma que o registro versionado está atualizado', async () => {
  const { stdout, stderr } = await execFileAsync(
    process.execPath,
    ['scripts/generate-vocacoes-pne-registro.mjs', '--check'],
    { cwd: repositoryRoot, encoding: 'utf8' },
  )
  assert.equal(stderr, '')
  assert.match(stdout, /OK: registro-series\.json está atualizado \(101 séries\)\./u)
})
