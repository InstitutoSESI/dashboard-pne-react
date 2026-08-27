import {
  existsSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import path from 'node:path'
import { isDeepStrictEqual } from 'node:util'
import { fileURLToPath } from 'node:url'

const PUBLIC_PACKAGES_DIRECTORY = new URL(
  '../public/data/vocacoes-regiao/regioes/',
  import.meta.url,
)
const REGRAS_PATH = new URL(
  './checks/fixtures/vocacoes-pne/regras-universo.json',
  import.meta.url,
)
const FLUXO_PATH = new URL(
  './checks/fixtures/vocacoes-pne/fluxo-series-pesquisa.json',
  import.meta.url,
)
const OUTPUT_PATH = new URL(
  './checks/fixtures/vocacoes-pne/registro-series.json',
  import.meta.url,
)

const PLATFORM_METADATA_FIELDS = [
  'label',
  'unitLabel',
  'sourceLabel',
  'evidenceClass',
  'universeLabel',
  'aggregationLabel',
  'ratioOf',
  'periodGranularity',
]

function fail(message) {
  throw new Error('Falha ao gerar o registro de séries Vocações × PNE: ' + message)
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function readJson(filePath, label) {
  try {
    return JSON.parse(readFileSync(filePath, 'utf8'))
  } catch (error) {
    throw new Error('Não foi possível ler ' + label, { cause: error })
  }
}

function sortedJsonFiles(directoryUrl) {
  const directory = fileURLToPath(directoryUrl)
  return readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .sort()
}

function stableJson(value) {
  return JSON.stringify(value, null, 2) + '\n'
}

function writeGeneratedFile(fileUrl, contents) {
  const target = fileURLToPath(fileUrl)
  if (existsSync(target) && readFileSync(target, 'utf8') === contents) {
    return false
  }

  const suffix = process.pid + '-' + Date.now()
  const temporary = target + '.' + suffix + '.tmp'
  const backup = target + '.' + suffix + '.bak'
  writeFileSync(temporary, contents, 'utf8')

  try {
    if (!existsSync(target)) {
      renameSync(temporary, target)
      return true
    }

    renameSync(target, backup)
    try {
      renameSync(temporary, target)
    } catch (error) {
      renameSync(backup, target)
      throw error
    }
    rmSync(backup)
    return true
  } catch (error) {
    if (existsSync(temporary)) rmSync(temporary)
    if (existsSync(backup) && !existsSync(target)) renameSync(backup, target)
    throw error
  }
}

function requireArray(value, label) {
  if (!Array.isArray(value)) fail(label + ' deve ser um array')
  return value
}

function requireIntegerOrNull(value, label) {
  if (value !== null && !Number.isInteger(value)) {
    fail(label + ' deve ser inteiro ou null')
  }
}

function clone(value) {
  if (Array.isArray(value)) return value.map(clone)
  if (!isRecord(value)) return value
  return Object.fromEntries(
    Object.entries(value).map(([key, child]) => [key, clone(child)]),
  )
}

function compileClassifiers(regras) {
  const classifiers = requireArray(regras.classificacao, 'regras.classificacao')
    .map((rule, index) => {
      if (!isRecord(rule)) {
        fail('regras.classificacao[' + index + '] deve ser objeto')
      }
      if (!Number.isInteger(rule.ordem)) {
        fail('regras.classificacao[' + index + '].ordem deve ser inteiro')
      }
      if (typeof rule.pattern !== 'string' || rule.pattern.length === 0) {
        fail('regras.classificacao[' + index + '].pattern deve ser string não vazia')
      }
      if (!isRecord(regras.universos?.[rule.universo])) {
        fail(
          'universo desconhecido na classificação '
          + rule.ordem
          + ': '
          + rule.universo,
        )
      }
      try {
        return { ...rule, regex: new RegExp(rule.pattern, 'u') }
      } catch (error) {
        throw new Error(
          'Regex inválida na classificação ' + rule.ordem + ': ' + rule.pattern,
          { cause: error },
        )
      }
    })
    .sort((left, right) => left.ordem - right.ordem)

  const orders = new Set()
  for (const classifier of classifiers) {
    if (orders.has(classifier.ordem)) {
      fail('ordem duplicada na classificação: ' + classifier.ordem)
    }
    orders.add(classifier.ordem)
  }
  return classifiers
}

function classifySeries(seriesId, classifiers) {
  const matches = classifiers.filter(({ regex }) => regex.test(seriesId))
  if (matches.length === 0) {
    fail('série publicada sem regra de classificação: ' + seriesId)
  }
  if (matches.length > 1) {
    fail(
      'série publicada casa com mais de uma regra: '
      + seriesId
      + ' (ordens '
      + matches.map(({ ordem }) => ordem).join(', ')
      + ')',
    )
  }
  return matches[0]
}

function faixaEtariaFromId(seriesId, classifier) {
  if (Array.isArray(classifier.faixaEtaria)) return clone(classifier.faixaEtaria)
  if (classifier.faixaEtariaRegra !== 'faixa_no_id') return null

  const closedRange = seriesId.match(/(?:^|-)(\d+)-a-(\d+)-anos(?:-|$)/u)
  if (closedRange) return [Number(closedRange[1]), Number(closedRange[2])]
  if (seriesId.includes('menor-1-ano')) return [0, 0]

  const openRange = seriesId.match(/(?:^|-)(\d+)-anos-e-mais(?:-|$)/u)
  if (openRange) return [Number(openRange[1]), null]
  return null
}

function platformSeriesById(files) {
  if (files.length !== 10) {
    fail('esperados 10 pacotes públicos regionais, encontrados ' + files.length)
  }

  const collected = new Map()
  let referenceIds = null
  let referenceFile = null

  for (const fileName of files) {
    const fileUrl = new URL(fileName, PUBLIC_PACKAGES_DIRECTORY)
    const packageData = readJson(fileUrl, 'pacote público ' + fileName)
    const series = requireArray(
      packageData?.territoryPortrait?.series,
      fileName + '.territoryPortrait.series',
    )
    const regionIds = new Set()

    for (const [index, item] of series.entries()) {
      if (
        !isRecord(item)
        || typeof item.seriesId !== 'string'
        || item.seriesId.length === 0
      ) {
        fail(
          fileName
          + '.territoryPortrait.series['
          + index
          + '] não tem seriesId válido',
        )
      }
      if (regionIds.has(item.seriesId)) {
        fail(fileName + ' contém seriesId duplicado: ' + item.seriesId)
      }
      regionIds.add(item.seriesId)

      for (const field of PLATFORM_METADATA_FIELDS) {
        if (!Object.hasOwn(item, field)) {
          fail(fileName + ': ' + item.seriesId + '.' + field + ' ausente')
        }
      }
      requireIntegerOrNull(
        item.periodStart,
        fileName + ': ' + item.seriesId + '.periodStart',
      )
      requireIntegerOrNull(
        item.periodEnd,
        fileName + ': ' + item.seriesId + '.periodEnd',
      )
      const preliminaryPeriods = requireArray(
        item.preliminaryPeriods,
        fileName + ': ' + item.seriesId + '.preliminaryPeriods',
      )
      if (!preliminaryPeriods.every(Number.isInteger)) {
        fail(
          fileName
          + ': '
          + item.seriesId
          + '.preliminaryPeriods deve conter inteiros',
        )
      }

      if (!collected.has(item.seriesId)) {
        collected.set(item.seriesId, {
          metadata: Object.fromEntries(
            PLATFORM_METADATA_FIELDS.map((field) => [field, clone(item[field])]),
          ),
          starts: [],
          ends: [],
          preliminaryPeriods: new Set(),
        })
      } else {
        const reference = collected.get(item.seriesId).metadata
        for (const field of PLATFORM_METADATA_FIELDS) {
          if (!isDeepStrictEqual(item[field], reference[field])) {
            fail(
              'metadado divergente para '
              + item.seriesId
              + '.'
              + field
              + ' em '
              + fileName
              + ': '
              + JSON.stringify(item[field])
              + ' != '
              + JSON.stringify(reference[field]),
            )
          }
        }
      }

      const aggregate = collected.get(item.seriesId)
      if (item.periodStart !== null) aggregate.starts.push(item.periodStart)
      if (item.periodEnd !== null) aggregate.ends.push(item.periodEnd)
      for (const period of preliminaryPeriods) {
        aggregate.preliminaryPeriods.add(period)
      }
    }

    const currentIds = [...regionIds].sort()
    if (referenceIds === null) {
      referenceIds = currentIds
      referenceFile = fileName
    } else if (!isDeepStrictEqual(currentIds, referenceIds)) {
      const expected = new Set(referenceIds)
      const missing = referenceIds.filter((seriesId) => !regionIds.has(seriesId))
      const extra = currentIds.filter((seriesId) => !expected.has(seriesId))
      fail(
        'conjunto de séries divergente em '
        + fileName
        + ' contra '
        + referenceFile
        + '; ausentes=['
        + missing.join(', ')
        + '], extras=['
        + extra.join(', ')
        + ']',
      )
    }
  }

  if (collected.size !== 71) {
    fail('esperadas 71 séries publicadas, encontradas ' + collected.size)
  }
  return collected
}

function populationReferenceFor(seriesId, regras) {
  const reference = regras.populacaoReferenciaMatriculas?.[seriesId]
  return reference === undefined ? null : clone(reference)
}

function createPlatformEntries(regras, classifiers) {
  const files = sortedJsonFiles(PUBLIC_PACKAGES_DIRECTORY)
  const collected = platformSeriesById(files)

  return [...collected.entries()].map(([seriesId, aggregate]) => {
    const classifier = classifySeries(seriesId, classifiers)
    const universe = regras.universos[classifier.universo]
    return {
      seriesId,
      label: aggregate.metadata.label,
      unit: aggregate.metadata.unitLabel,
      source: aggregate.metadata.sourceLabel,
      evidenceClass: aggregate.metadata.evidenceClass,
      universo: classifier.universo,
      lente: universe.lente,
      faixaEtaria: faixaEtariaFromId(seriesId, classifier),
      populacaoReferencia: populationReferenceFor(seriesId, regras),
      ratioOf: clone(aggregate.metadata.ratioOf),
      periodStart: aggregate.starts.length === 0
        ? null
        : Math.min(...aggregate.starts),
      periodEnd: aggregate.ends.length === 0
        ? null
        : Math.max(...aggregate.ends),
      periodGranularity: aggregate.metadata.periodGranularity,
      preliminaryPeriods: [...aggregate.preliminaryPeriods].sort((a, b) => a - b),
      rede: 'todas',
      status: 'disponivel_plataforma',
    }
  })
}

function fluxoEtapa(seriesId) {
  if (seriesId.endsWith('_fundamental_anos_iniciais')) {
    return 'ensino_fundamental_anos_iniciais'
  }
  if (seriesId.endsWith('_fundamental_anos_finais')) {
    return 'ensino_fundamental_anos_finais'
  }
  if (seriesId.endsWith('_fundamental')) return 'ensino_fundamental'
  if (seriesId.endsWith('_medio')) return 'ensino_medio'
  fail('não foi possível derivar a etapa da série de fluxo: ' + seriesId)
}

function createResearchEntries(regras, classifiers) {
  const snapshot = readJson(FLUXO_PATH, 'snapshot de séries de fluxo')
  if (snapshot?.status !== 'disponivel_pesquisa') {
    fail('fluxo-series-pesquisa.json deve ter status disponivel_pesquisa')
  }
  const series = requireArray(snapshot.series, 'fluxo-series-pesquisa.json.series')
  if (series.length !== 16) {
    fail('esperadas 16 séries de pesquisa, encontradas ' + series.length)
  }

  const seen = new Set()
  return series.map((item, index) => {
    if (
      !isRecord(item)
      || typeof item.seriesId !== 'string'
      || item.seriesId.length === 0
    ) {
      fail(
        'fluxo-series-pesquisa.json.series['
        + index
        + '] não tem seriesId válido',
      )
    }
    if (seen.has(item.seriesId)) {
      fail('série de pesquisa duplicada: ' + item.seriesId)
    }
    seen.add(item.seriesId)
    const classifier = classifySeries(item.seriesId, classifiers)
    if (classifier.universo !== 'fluxo_rendimento') {
      fail(item.seriesId + ' deve ser classificada como fluxo_rendimento')
    }
    const universe = regras.universos[classifier.universo]
    requireIntegerOrNull(item.periodStart, item.seriesId + '.periodStart')
    requireIntegerOrNull(item.periodEnd, item.seriesId + '.periodEnd')
    const preliminaryPeriods = requireArray(
      item.preliminaryPeriods,
      item.seriesId + '.preliminaryPeriods',
    )
    if (!preliminaryPeriods.every(Number.isInteger)) {
      fail(item.seriesId + '.preliminaryPeriods deve conter inteiros')
    }

    return {
      seriesId: item.seriesId,
      label: item.label,
      unit: item.unit,
      source: item.source,
      evidenceClass: item.evidenceClass,
      universo: classifier.universo,
      lente: universe.lente,
      faixaEtaria: null,
      populacaoReferencia: { etapa: fluxoEtapa(item.seriesId) },
      ratioOf: null,
      periodStart: item.periodStart,
      periodEnd: item.periodEnd,
      periodGranularity: item.periodGranularity,
      preliminaryPeriods: clone(preliminaryPeriods),
      rede: 'todas',
      status: 'disponivel_pesquisa',
    }
  })
}

function createPendingEntries(regras) {
  const pending = requireArray(regras.seriesPendentes, 'regras.seriesPendentes')
  if (pending.length !== 14) {
    fail('esperadas 14 séries pendentes, encontradas ' + pending.length)
  }

  const seen = new Set()
  return pending.map((item, index) => {
    if (
      !isRecord(item)
      || typeof item.seriesId !== 'string'
      || item.seriesId.length === 0
    ) {
      fail('regras.seriesPendentes[' + index + '] não tem seriesId válido')
    }
    if (seen.has(item.seriesId)) {
      fail('série pendente duplicada: ' + item.seriesId)
    }
    seen.add(item.seriesId)
    if (!['pendente_r3', 'pendente_r4'].includes(item.status)) {
      fail(item.seriesId + ' tem status pendente inválido: ' + item.status)
    }
    const universe = regras.universos?.[item.universo]
    if (!isRecord(universe) || typeof universe.lente !== 'string') {
      fail(item.seriesId + ' referencia universo inválido: ' + item.universo)
    }

    return {
      seriesId: item.seriesId,
      label: item.label,
      unit: null,
      source: item.fonteDesejavel,
      evidenceClass: null,
      universo: item.universo,
      lente: universe.lente,
      faixaEtaria: clone(item.faixaEtaria),
      populacaoReferencia: populationReferenceFor(item.seriesId, regras),
      ratioOf: null,
      periodStart: null,
      periodEnd: null,
      periodGranularity: null,
      preliminaryPeriods: [],
      rede: 'todas',
      status: item.status,
    }
  })
}

function assertUniqueSeries(entries) {
  const seen = new Set()
  for (const entry of entries) {
    if (seen.has(entry.seriesId)) {
      fail('seriesId repetido entre as fontes do registro: ' + entry.seriesId)
    }
    seen.add(entry.seriesId)
  }
}

export function buildRegistro() {
  const regras = readJson(REGRAS_PATH, 'regras de universo')
  if (!isRecord(regras.universos)) fail('regras.universos deve ser objeto')
  const classifiers = compileClassifiers(regras)
  const entries = [
    ...createPlatformEntries(regras, classifiers),
    ...createResearchEntries(regras, classifiers),
    ...createPendingEntries(regras),
  ]
  assertUniqueSeries(entries)

  if (entries.length !== 101) {
    fail('esperadas 101 entradas no registro, encontradas ' + entries.length)
  }
  entries.sort((left, right) => (
    left.seriesId < right.seriesId ? -1 : left.seriesId > right.seriesId ? 1 : 0
  ))

  return {
    version: '1.0.0',
    generatedFrom: {
      plataforma: 'public/data/vocacoes-regiao/regioes/*.json',
      pesquisa: 'scripts/checks/fixtures/vocacoes-pne/fluxo-series-pesquisa.json',
      pendentes: 'scripts/checks/fixtures/vocacoes-pne/regras-universo.json#seriesPendentes',
      note: 'Registro gerado deterministicamente, sem timestamp.',
    },
    series: entries,
  }
}

function main() {
  const args = process.argv.slice(2)
  if (
    args.some((arg) => arg !== '--check')
    || args.filter((arg) => arg === '--check').length > 1
  ) {
    fail('argumentos não reconhecidos: ' + args.join(' '))
  }

  const registro = buildRegistro()
  const contents = stableJson(registro)
  const output = fileURLToPath(OUTPUT_PATH)

  if (args.includes('--check')) {
    if (!existsSync(output)) {
      fail('arquivo gerado ausente: ' + output)
    }
    const current = readFileSync(output, 'utf8')
    if (current !== contents) {
      fail('registro-series.json está desatualizado (comparação byte a byte falhou)')
    }
    console.log(
      'OK: registro-series.json está atualizado ('
      + registro.series.length
      + ' séries).',
    )
    return
  }

  const changed = writeGeneratedFile(OUTPUT_PATH, contents)
  console.log(
    (changed ? 'Gerado' : 'Sem alterações')
    + ': scripts/checks/fixtures/vocacoes-pne/registro-series.json ('
    + registro.series.length
    + ' séries).',
  )
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : null
if (invokedPath === fileURLToPath(import.meta.url)) {
  main()
}
