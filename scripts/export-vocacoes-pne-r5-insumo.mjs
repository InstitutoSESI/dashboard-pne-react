import { createHash } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = fileURLToPath(new URL('../', import.meta.url))
const REGIONS_PATH = path.join(ROOT, 'config', 'regions', 'rs.json')
const MUNICIPALITIES_PATH = path.join(ROOT, 'config', 'municipalities', 'rs.json')
const OVERVIEW_DIRECTORY = path.join(
  ROOT,
  'public',
  'data',
  'educacao',
  'visao-geral-municipal',
)
const DEFAULT_OUTPUT_PATH = path.join(
  ROOT,
  '.tmp',
  'vocacoes-pne',
  'rodada-05',
  'insumo-matriculas-municipais-vale-do-sinos.json',
)

const REGION_SLUG = 'vale-do-sinos'
const YEARS = [2015, 2025]
const STAGES = [
  {
    seriesKey: 'matriculas_educacao_infantil',
    overviewKey: 'earlyChildhood',
    publicLabel: 'Matrículas na educação infantil',
    sourceField: 'QT_MAT_INF',
  },
  {
    seriesKey: 'matriculas_ensino_fundamental',
    overviewKey: 'elementary',
    publicLabel: 'Matrículas no ensino fundamental',
    sourceField: 'QT_MAT_FUND',
  },
  {
    seriesKey: 'matriculas_ensino_medio',
    overviewKey: 'highSchool',
    publicLabel: 'Matrículas no ensino médio',
    sourceField: 'QT_MAT_MED',
  },
]

export class InsumoR5Error extends Error {}

function fail(message) {
  throw new InsumoR5Error(message)
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function loadJsonWithBytes(filePath) {
  const bytes = readFileSync(filePath)
  return { bytes, value: JSON.parse(bytes.toString('utf8')) }
}

function assertIbgeCode(value, field) {
  if (typeof value !== 'string' || !/^\d{7}$/u.test(value)) {
    fail(`${field} deve preservar o código IBGE textual de sete dígitos`)
  }
}

function observedValue(stage, year, expectedSourceField, field) {
  const valueField = `value${year}`
  const item = stage?.total?.[valueField]
  if (
    item === null
    || typeof item !== 'object'
    || !Number.isFinite(item.value)
    || item.year !== year
    || !['observed', 'derived_zero'].includes(item.state)
    || item.sourceId !== 'inep_censo_escolar'
    || item.sourceField !== expectedSourceField
  ) {
    fail(`${field}.total.${valueField} não é uma observação INEP válida`)
  }
  return { value: item.value, state: item.state }
}

function canonicalJson(value) {
  return `${JSON.stringify(value, null, 2)}\n`
}

export function buildMunicipalEnrollmentInput() {
  const regionsSource = loadJsonWithBytes(REGIONS_PATH)
  const municipalitiesSource = loadJsonWithBytes(MUNICIPALITIES_PATH)
  const regions = regionsSource.value
  const municipalities = municipalitiesSource.value

  if (
    regions.schemaVersion !== 'regions-config-v1'
    || regions.stateCode !== 'RS'
    || regions.municipalityCount !== 497
  ) {
    fail('config/regions/rs.json não atende ao contrato esperado')
  }
  if (
    municipalities.schemaVersion !== 'municipality-registry-v1'
    || municipalities.stateCode !== 'RS'
    || municipalities.municipalityCount !== 497
  ) {
    fail('config/municipalities/rs.json não atende ao contrato esperado')
  }

  const region = regions.regions.find(({ slug }) => slug === REGION_SLUG)
  if (!region || region.municipalityCount !== 10) {
    fail('Vale do Sinos deve conter exatamente 10 municípios')
  }
  const municipalityByCode = new Map(
    municipalities.municipalities.map((municipality) => {
      assertIbgeCode(municipality.ibgeCode, 'municipalities[].ibgeCode')
      return [municipality.ibgeCode, municipality]
    }),
  )
  const codes = [...region.municipalityIbgeCodes]
  if (new Set(codes).size !== codes.length) fail('códigos municipais duplicados')
  codes.forEach((code, index) => assertIbgeCode(code, `region.codes[${index}]`))

  const sourceFiles = []
  const overviewByCode = new Map()
  for (const code of codes) {
    const canonicalMunicipality = municipalityByCode.get(code)
    if (!canonicalMunicipality) fail(`município ${code} ausente do registro canônico`)
    const filePath = path.join(OVERVIEW_DIRECTORY, `${code}.json`)
    const source = loadJsonWithBytes(filePath)
    const overview = source.value
    if (overview.schemaVersion !== 'municipal-education-overview-v1') {
      fail(`${code}: schema municipal inesperado`)
    }
    if (
      overview.municipality?.idMunicipality !== code
      || overview.municipality?.name !== canonicalMunicipality.name
    ) {
      fail(`${code}: identidade municipal divergente no overview`)
    }
    if (JSON.stringify(overview.enrollmentComparison?.years) !== JSON.stringify(YEARS)) {
      fail(`${code}: janela municipal deve ser 2015–2025`)
    }
    const sourceYears = new Set(
      (overview.sources ?? [])
        .filter(({ id }) => ['inep_censo_escolar_2015', 'inep_censo_escolar'].includes(id))
        .map(({ referenceYear }) => referenceYear),
    )
    if (!YEARS.every((year) => sourceYears.has(year))) {
      fail(`${code}: fontes do Censo Escolar 2015 e 2025 ausentes`)
    }

    overviewByCode.set(code, overview)
    sourceFiles.push({
      path: `public/data/educacao/visao-geral-municipal/${code}.json`,
      sha256: sha256(source.bytes),
      byteSize: source.bytes.length,
    })
  }

  const series = STAGES.map((definition) => ({
    seriesKey: definition.seriesKey,
    publicLabel: definition.publicLabel,
    unit: 'matrículas',
    sourceId: 'censo-escolar-inep',
    sourceField: definition.sourceField,
    municipalities: codes.map((code) => {
      const overview = overviewByCode.get(code)
      const stage = overview.enrollmentComparison?.stages?.[definition.overviewKey]
      const start = observedValue(
        stage,
        YEARS[0],
        definition.sourceField,
        `${code}.${definition.overviewKey}`,
      )
      const end = observedValue(
        stage,
        YEARS[1],
        definition.sourceField,
        `${code}.${definition.overviewKey}`,
      )
      if (stage.total.absoluteChange !== end.value - start.value) {
        fail(`${code}.${definition.overviewKey}: variação absoluta não reconcilia`)
      }
      return {
        ibgeCode: code,
        name: municipalityByCode.get(code).name,
        values: {
          2015: start,
          2025: end,
        },
        absoluteChange: end.value - start.value,
      }
    }),
  }))

  return {
    schemaVersion: 'vocacoes-pne-r5-municipal-enrollments-v1',
    region: {
      slug: region.slug,
      name: region.name,
      stateCode: 'RS',
      municipalityCount: codes.length,
      municipalityIbgeCodes: codes,
    },
    period: { start: YEARS[0], end: YEARS[1], granularity: 'annual' },
    series,
    provenance: {
      exporterVersion: 'export-vocacoes-pne-r5-insumo.mjs v1.0.0',
      generation: {
        deterministic: true,
        clockUsed: false,
        modelUsed: false,
        networkUsed: false,
      },
      identitySources: [
        {
          path: 'config/regions/rs.json',
          sha256: sha256(regionsSource.bytes),
          byteSize: regionsSource.bytes.length,
        },
        {
          path: 'config/municipalities/rs.json',
          sha256: sha256(municipalitiesSource.bytes),
          byteSize: municipalitiesSource.bytes.length,
        },
      ],
      sourceFiles,
      analyticalSources: [
        {
          id: 'censo-escolar-inep',
          label: 'Censo Escolar (INEP)',
          referenceYears: YEARS,
        },
      ],
    },
  }
}

function parseArguments(argv) {
  let check = false
  let outputPath = DEFAULT_OUTPUT_PATH
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--check') {
      check = true
    } else if (argument === '--output') {
      const next = argv[index + 1]
      if (!next) fail('--output requer um caminho')
      outputPath = path.resolve(next)
      index += 1
    } else {
      fail(`argumento desconhecido: ${argument}`)
    }
  }
  return { check, outputPath }
}

function atomicWrite(filePath, content) {
  mkdirSync(path.dirname(filePath), { recursive: true })
  const temporaryPath = `${filePath}.tmp-${process.pid}`
  try {
    writeFileSync(temporaryPath, content, 'utf8')
    renameSync(temporaryPath, filePath)
  } finally {
    if (existsSync(temporaryPath)) rmSync(temporaryPath)
  }
}

export function run(argv = process.argv.slice(2)) {
  const { check, outputPath } = parseArguments(argv)
  const content = canonicalJson(buildMunicipalEnrollmentInput())
  if (check) {
    if (!existsSync(outputPath)) fail(`insumo ausente: ${outputPath}`)
    if (readFileSync(outputPath, 'utf8') !== content) {
      fail(`insumo divergente: execute sem --check para atualizar ${outputPath}`)
    }
    console.log(`OK: insumo municipal R5 idêntico (${outputPath})`)
    return
  }
  atomicWrite(outputPath, content)
  console.log(`OK: insumo municipal R5 escrito (${outputPath})`)
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    run()
  } catch (error) {
    console.error(error instanceof Error ? error.message : error)
    process.exitCode = 1
  }
}
