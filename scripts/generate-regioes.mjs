/*
 * Publica o painel regional em `public/data/regioes/`.
 *
 * O gerador é determinístico e não fala com banco: ele agrega o que a própria
 * plataforma já publicou por município. As regras centrais são:
 *
 *  - matrículas (`public/data/educacao/municipios/<ibge>.json`): contagens
 *    absolutas, somadas;
 *  - cobertura por idade (`public/data/municipios/<ibge>/index.json`):
 *    numerador e denominador anuais, somados separadamente e só então
 *    divididos.
 *
 *  - PNE 2026–2036: taxa regional somente para os quatro indicadores cujo
 *    numerador e denominador estão publicados; os demais usam mediana municipal
 *    explicitamente rotulada e comparada à mesma estatística estadual;
 *  - fluxo, aprendizagem e organização: mediana municipal, nunca taxa regional;
 *  - estrutura, oferta, educação indígena e Sistema S: contagens somadas.
 *
 * Nenhum ano é publicado como total completo quando falta município. A geração
 * ocorre em staging, é validada integralmente e só então promovida com rollback.
 *
 * Uso:
 *   node scripts/generate-regioes.mjs            publica
 *   node scripts/generate-regioes.mjs --check    confere sem escrever
 */

import { createHash, randomUUID } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { loadRegionsConfig } from './lib/state-build-profile.mjs'
import {
  buildRegionalEducationBlock,
  buildRegionalPneBlock,
} from './lib/regional-panorama.mjs'
import {
  parseRegiaoDocument,
  parseRegioesManifest,
} from '../src/features/regional/regionalLoader.js'

const REPOSITORY_ROOT = new URL('../', import.meta.url)
const STATE_CODE = 'RS'

export const REGIOES_MANIFEST_SCHEMA = 'regioes-manifest-v1'
export const REGIOES_DOCUMENT_SCHEMA = 'regioes-2.0.0'
export const REGIOES_GENERATOR_VERSION = 'regioes-generator-v2'

/*
 * Os recortes de matrícula publicados no painel regional. Todos são contagem
 * absoluta no artefato municipal, então a soma é exata.
 */
const ENROLLMENT_BREAKDOWNS = Object.freeze([
  { key: 'por_etapa', dimension: 'etapa_ensino' },
  { key: 'por_dependencia', dimension: 'dependencia' },
  { key: 'por_localizacao', dimension: 'localizacao' },
])

/** O município publica este recorte? Dimensão declarada e não retirada. */
const dimensionAvailable = (dimension) => (block) =>
  (block.dimensoes_disponiveis ?? []).includes(dimension)
  && !(block.campos_indisponiveis ?? []).includes(dimension)

const AGE_COVERAGE_KEYS = Object.freeze([
  'creche',
  'pre_escola',
  'infantil_0_5',
  'escolar_6_14',
  'basico_6_17',
  'basico_15_17',
  'obrigatoria_4_17',
])

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function readJson(relativePath) {
  const target = fileURLToPath(new URL(relativePath, REPOSITORY_ROOT))
  return JSON.parse(fs.readFileSync(target, 'utf8'))
}

function fail(message) {
  throw new Error(`Painel regional: ${message}`)
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

/** Arredonda para uma casa, sem carregar o ruído binário adiante. */
function round1(value) {
  return Math.round(value * 10) / 10
}

function round2(value) {
  return Math.round(value * 100) / 100
}

/*
 * Soma uma série anual município a município. O ano só recebe valor quando
 * todos os municípios da região contribuíram: cobertura parcial vira null com
 * a contagem exposta, nunca um total que parece completo e não é.
 */
function sumAnnualSeries(perMunicipality, municipalityCount, readValue) {
  const totals = new Map()
  for (const entries of perMunicipality) {
    for (const entry of entries) {
      const year = entry.ano
      if (!Number.isInteger(year)) fail(`ano inválido em série anual: ${JSON.stringify(entry)}.`)
      const value = readValue(entry)
      if (!isFiniteNumber(value)) continue
      const bucket = totals.get(year) ?? { total: 0, municipalitiesWithData: 0 }
      bucket.total += value
      bucket.municipalitiesWithData += 1
      totals.set(year, bucket)
    }
  }
  return [...totals.entries()]
    .toSorted(([left], [right]) => left - right)
    .map(([year, bucket]) => ({
      ano: year,
      valor: bucket.municipalitiesWithData === municipalityCount ? bucket.total : null,
      municipiosComDado: bucket.municipalitiesWithData,
    }))
}

/*
 * Recorte de um total já conhecido. Aqui a ausência de uma categoria em um ano
 * significa zero, não dado faltante: o município que não tem escola rural
 * simplesmente não publica a série rural, e o total daquele ano continua
 * inteiro. O que de fato invalidaria o ano é o município não publicar o
 * recorte — e aí ele não contribui, deixando o ano regional nulo.
 *
 * `isAvailable` é quem decide isso, e decide de forma diferente conforme o
 * recorte: os recortes por dimensão declarada consultam
 * `dimensoes_disponiveis`; a série de tempo integral não pertence a dimensão
 * alguma do contrato municipal, então o que a habilita é ela própria existir.
 */
function sumBreakdownSeries(blocks, municipalityCount, isAvailable, selectSeries) {
  const totals = new Map()
  for (const block of blocks) {
    if (!isAvailable(block)) continue
    const observed = new Map(
      (selectSeries(block) ?? [])
        .filter((entry) => isFiniteNumber(entry.valor))
        .map((entry) => [entry.ano, entry.valor]),
    )
    for (const entry of block.series?.total ?? []) {
      if (!isFiniteNumber(entry.valor)) continue
      const bucket = totals.get(entry.ano) ?? { total: 0, municipalitiesWithData: 0 }
      bucket.total += observed.get(entry.ano) ?? 0
      bucket.municipalitiesWithData += 1
      totals.set(entry.ano, bucket)
    }
  }
  return [...totals.entries()]
    .toSorted(([left], [right]) => left - right)
    .map(([year, bucket]) => ({
      ano: year,
      valor: bucket.municipalitiesWithData === municipalityCount ? bucket.total : null,
      municipiosComDado: bucket.municipalitiesWithData,
    }))
}

/*
 * Cobertura por idade: numerador e denominador somam separadamente e o
 * percentual nasce da divisão dos totais. O ano com cobertura parcial não
 * publica percentual — publicá-lo seria comparar regiões por universos
 * diferentes.
 */
function aggregateAgeCoverage(perMunicipality, municipalityCount) {
  const totals = new Map()
  for (const historical of perMunicipality) {
    for (const entry of historical) {
      const year = entry.year
      if (!Number.isInteger(year)) {
        fail(`ano inválido em cobertura por idade: ${JSON.stringify(entry)}.`)
      }
      const bucket = totals.get(year) ?? { numerator: 0, denominator: 0, municipalitiesWithData: 0 }
      totals.set(year, bucket)
      if (!isFiniteNumber(entry.numerator) || !isFiniteNumber(entry.denominator)) continue
      bucket.numerator += entry.numerator
      bucket.denominator += entry.denominator
      bucket.municipalitiesWithData += 1
    }
  }
  return [...totals.entries()]
    .toSorted(([left], [right]) => left - right)
    .map(([year, bucket]) => {
      const complete = bucket.municipalitiesWithData === municipalityCount && bucket.denominator > 0
      return {
        ano: year,
        numerador: complete ? bucket.numerator : null,
        denominador: complete ? bucket.denominator : null,
        valor: complete ? round2((bucket.numerator / bucket.denominator) * 100) : null,
        municipiosComDado: bucket.municipalitiesWithData,
      }
    })
}

function lastAvailable(series) {
  for (let index = series.length - 1; index >= 0; index -= 1) {
    if (series[index].valor !== null) return series[index]
  }
  return null
}

function loadMunicipalSource(identity) {
  const ibgeCode = identity.ibgeCode
  const education = readJson(`public/data/educacao/municipios/${ibgeCode}.json`)
  const index = readJson(`public/data/municipios/${ibgeCode}/index.json`)
  if (education.id_municipio !== ibgeCode) {
    fail(`artefato educacional de ${ibgeCode} declara outro município.`)
  }
  if (index.id_municipio !== ibgeCode) {
    fail(`índice municipal de ${ibgeCode} declara outro município.`)
  }
  if (typeof education.updated_at !== 'string' || !ISO_DATE_PATTERN.test(education.updated_at)) {
    fail(`artefato educacional de ${ibgeCode} não declara updated_at em ISO.`)
  }
  const coverage = index.educacao?.atendimento_cenarios?.ageCoverage
  if (coverage === undefined || coverage === null) {
    fail(`índice municipal de ${ibgeCode} não publica cobertura por idade.`)
  }
  const pne2026 = index.pne_2026_2036
  if (pne2026 === undefined || pne2026 === null || typeof pne2026.indicadores !== 'object') {
    fail(`índice municipal de ${ibgeCode} não publica o ciclo PNE 2026–2036.`)
  }
  return { identity, education, coverage, pne2026, updatedAt: education.updated_at }
}

function loadAllMunicipalSources(registry) {
  return registry.municipalities.map((identity) => loadMunicipalSource(identity))
}

function selectRegionalSources(region, sourcesByCode) {
  return region.municipalityIbgeCodes.map((ibgeCode) => {
    const source = sourcesByCode.get(ibgeCode)
    if (source === undefined) fail(`município ${ibgeCode} fora do registro de ${STATE_CODE}.`)
    return source
  })
}

function buildEnrollmentBlock(sources, municipalityCount) {
  const blocks = sources.map((source) => {
    const block = source.education.blocos?.matriculas
    if (block === undefined || block === null) {
      fail(`artefato educacional de ${source.identity.ibgeCode} não publica matrículas.`)
    }
    return block
  })

  const total = sumAnnualSeries(
    blocks.map((block) => block.series?.total ?? []),
    municipalityCount,
    (entry) => entry.valor,
  )
  const integralCounts = sumBreakdownSeries(
    blocks,
    municipalityCount,
    (block) => Array.isArray(block.series?.integral),
    (block) => block.series?.integral,
  )
  const totalByYear = new Map(total.map((entry) => [entry.ano, entry.valor]))
  const integral = integralCounts.map((entry) => {
    const reference = totalByYear.get(entry.ano) ?? null
    return {
      ...entry,
      // Percentual recalculado dos totais somados, nunca média de percentuais.
      percentual:
        entry.valor !== null && reference !== null && reference > 0
          ? round1((entry.valor / reference) * 100)
          : null,
    }
  })

  const breakdowns = {}
  for (const { key, dimension } of ENROLLMENT_BREAKDOWNS) {
    const categories = new Set()
    for (const block of blocks) {
      for (const category of Object.keys(block.series?.[key] ?? {})) categories.add(category)
    }
    const aggregated = {}
    for (const category of [...categories].toSorted()) {
      aggregated[category] = sumBreakdownSeries(
        blocks,
        municipalityCount,
        dimensionAvailable(dimension),
        (block) => block.series?.[key]?.[category],
      )
    }
    breakdowns[key] = aggregated
  }

  const latestTotal = lastAvailable(total)
  return {
    label: 'Matrículas da educação básica',
    descricao: 'Soma das matrículas informadas por cada município da região no Censo Escolar.',
    ultimoAno: latestTotal === null ? null : latestTotal.ano,
    totalUltimoAno: latestTotal === null ? null : latestTotal.valor,
    series: {
      total,
      integral,
      ...breakdowns,
    },
  }
}

function buildCoverageBlock(sources, municipalityCount) {
  const indicators = AGE_COVERAGE_KEYS.map((key) => {
    const entries = sources.map((source) => {
      const indicator = source.coverage[key]
      if (indicator === undefined || indicator === null) {
        fail(`município ${source.identity.ibgeCode} não publica a cobertura "${key}".`)
      }
      return indicator
    })
    const reference = entries[0]
    for (const entry of entries) {
      if (entry.title !== reference.title || entry.ageRange !== reference.ageRange) {
        fail(`a cobertura "${key}" tem contrato divergente entre municípios da região.`)
      }
    }
    const series = aggregateAgeCoverage(
      entries.map((entry) => entry.historical ?? []),
      municipalityCount,
    )
    const latest = lastAvailable(series)
    return {
      chave: key,
      titulo: reference.title,
      faixaEtaria: reference.ageRange,
      unidade: 'percent',
      baseTerritorial: {
        numerador: reference.territorialBasis.numerator,
        denominador: reference.territorialBasis.denominator,
      },
      campos: {
        numerador: reference.fields.numerator,
        denominador: reference.fields.denominator,
      },
      ultimoAno: latest === null ? null : latest.ano,
      valorUltimoAno: latest === null ? null : latest.valor,
      series,
    }
  })

  return {
    label: 'Atendimento por faixa etária',
    descricao:
      'Matrículas somadas da região sobre a população residente somada da região, ano a ano.',
    indicadores: indicators,
  }
}

export function buildRegionDocument({
  region,
  sources,
  stateSources,
  pneCatalog,
  stateCoverage,
}) {
  const municipalityCount = region.municipalityCount
  if (sources.length !== municipalityCount) {
    fail(`região ${region.slug} carregou ${sources.length} de ${municipalityCount} municípios.`)
  }
  const updatedAt = sources.map((source) => source.updatedAt).toSorted().at(-1)
  const coverage = buildCoverageBlock(sources, municipalityCount)

  return {
    schemaVersion: REGIOES_DOCUMENT_SCHEMA,
    generatorVersion: REGIOES_GENERATOR_VERSION,
    generatedAt: updatedAt,
    stateCode: STATE_CODE,
    regiao: {
      slug: region.slug,
      nome: region.name,
      totalMunicipios: municipalityCount,
      municipios: sources.map((source) => ({
        ibgeCode: source.identity.ibgeCode,
        nome: source.identity.name,
        slug: source.identity.slug,
      })),
    },
    pagina: {
      eyebrow: 'Análise regional',
      titulo: `Região ${region.name}`,
      descricao:
        `Leitura agregada dos ${municipalityCount} municípios da região, `
        + 'construída a partir dos dados publicados de cada um deles.',
    },
    atendimento: coverage,
    matriculas: buildEnrollmentBlock(sources, municipalityCount),
    educacao: buildRegionalEducationBlock({
      regionalSources: sources,
      stateSources,
    }),
    pne2026: buildRegionalPneBlock({
      regionalSources: sources,
      stateSources,
      catalog: pneCatalog,
      regionalCoverage: coverage,
      stateCoverage,
    }),
    metodologia: [
      'Contagens são somadas município a município.',
      'Taxas com numerador e denominador publicados são recalculadas a partir dos totais somados. Nos demais indicadores, o painel usa a mediana municipal e a identifica explicitamente.',
      'Somas e taxas regionais só recebem valor quando há componentes para a região inteira; medianas usam os resultados municipais disponíveis e declaram quantos entraram.',
      'As etapas de ensino não formam uma divisão do total: o ensino fundamental aparece também nos anos iniciais e finais, e uma parte das matrículas é informada em mais de uma etapa. Somar as etapas dá mais do que o total.',
      'Quando o contrato municipal não publica numerador e denominador suficientes para recompor uma taxa regional, o painel mostra a mediana dos municípios e a identifica explicitamente; isso se aplica, entre outros, a fluxo escolar, IDEB, SAEB e INSE.',
      'Metas e referências do PNE 2026–2036 vêm do contrato canônico do ciclo; resultado observado, zero e indisponibilidade permanecem distintos.',
      'null significa dado ausente, não zero.',
    ],
    fontes: [
      {
        nome: 'INEP - Censo Escolar',
        uso: 'matrículas e numeradores de cobertura por faixa etária',
      },
      {
        nome: 'Painel populacional municipal por faixa etária',
        uso: 'denominadores de cobertura por faixa etária',
      },
      {
        nome: 'INEP - Taxas de Rendimento Escolar, SAEB, IDEB, INSE e Alfabetização',
        uso: 'trajetória e aprendizagem na distribuição dos municípios',
      },
      {
        nome: 'IBGE - Censo Demográfico',
        uso: 'indicadores de escolaridade da população',
      },
      {
        nome: 'Contrato canônico do PNE 2026–2036',
        uso: 'metas, referências, direção e vínculo dos indicadores do ciclo',
      },
      {
        nome: 'VAAR/FUNDEB',
        uso: 'condicionalidades e componentes do exercício mais recente',
      },
    ],
  }
}

/** Serialização canônica: chaves ordenadas, para que o hash só mude com o dado. */
export function serializeForContentVersion(value) {
  if (Array.isArray(value)) return `[${value.map(serializeForContentVersion).join(',')}]`
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value)
      .toSorted()
      .map((key) => `${JSON.stringify(key)}:${serializeForContentVersion(value[key])}`)
      .join(',')}}`
  }
  return JSON.stringify(value ?? null)
}

function sha256(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex')
}

export function buildPublication() {
  const repoRoot = fileURLToPath(REPOSITORY_ROOT)
  const registry = readJson('config/municipalities/rs.json')
  const regionsConfig = loadRegionsConfig({
    repoRoot,
    stateCode: STATE_CODE,
    municipalityRegistry: registry,
  })
  if (regionsConfig === null) fail(`não há mapa regional para ${STATE_CODE}.`)

  const stateSources = loadAllMunicipalSources(registry)
  const sourcesByCode = new Map(
    stateSources.map((source) => [source.identity.ibgeCode, source]),
  )
  const pneCatalog = readJson('public/data/indicadores.json').cycles?.pne_2026_2036
  if (pneCatalog === undefined || pneCatalog === null) {
    fail('o catálogo público não contém o ciclo PNE 2026–2036.')
  }
  const stateCoverage = buildCoverageBlock(stateSources, registry.municipalityCount)
  const files = []
  for (const region of regionsConfig.regions) {
    const sources = selectRegionalSources(region, sourcesByCode)
    const document = buildRegionDocument({
      region,
      sources,
      stateSources,
      pneCatalog,
      stateCoverage,
    })
    const contentVersion = sha256(serializeForContentVersion(document))
    const published = { ...document, contentVersion }
    const serialized = `${JSON.stringify(published, null, 2)}\n`
    files.push({
      region,
      document: published,
      serialized,
      contentVersion,
      contentHash: sha256(serialized),
      byteSize: Buffer.byteLength(serialized, 'utf8'),
    })
  }

  const generatedAt = files.map((file) => file.document.generatedAt).toSorted().at(-1)
  const manifest = {
    schemaVersion: REGIOES_MANIFEST_SCHEMA,
    documentSchemaVersion: REGIOES_DOCUMENT_SCHEMA,
    generatorVersion: REGIOES_GENERATOR_VERSION,
    generatedAt,
    stateCode: STATE_CODE,
    regionFilePattern: '{regionSlug}.json',
    regionCount: files.length,
    municipalityCount: regionsConfig.municipalityCount,
    regions: files.map((file) => ({
      slug: file.region.slug,
      name: file.region.name,
      path: `${file.region.slug}.json`,
      municipalityCount: file.region.municipalityCount,
      contentHash: file.contentHash,
      contentVersion: file.contentVersion,
      byteSize: file.byteSize,
    })),
  }
  return { manifest, files }
}

function publicationOutputs(publication) {
  return [
    {
      relativePath: 'manifest.json',
      contents: `${JSON.stringify(publication.manifest, null, 2)}\n`,
    },
    ...publication.files.map((file) => ({
      relativePath: `${file.region.slug}.json`,
      contents: file.serialized,
    })),
  ]
}

function assertChildPath(root, target, label) {
  const relative = path.relative(path.resolve(root), path.resolve(target))
  if (relative === '' || relative.startsWith('..') || path.isAbsolute(relative)) {
    fail(`${label} precisa ficar dentro de ${root}.`)
  }
}

function writeFileAtomic(target, contents) {
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const temporary = path.join(
    path.dirname(target),
    `.${path.basename(target)}.${process.pid}.${randomUUID()}.tmp`,
  )
  const descriptor = fs.openSync(temporary, 'w')
  try {
    fs.writeFileSync(descriptor, contents, 'utf8')
    fs.fsyncSync(descriptor)
  } finally {
    fs.closeSync(descriptor)
  }
  try {
    fs.renameSync(temporary, target)
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary)
  }
}

function jsonFiles(directory) {
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .toSorted()
}

export function validatePublicationDirectory(directory) {
  const manifestPath = path.join(directory, 'manifest.json')
  if (!fs.existsSync(manifestPath)) fail('o staging não contém manifest.json.')
  const manifestRaw = fs.readFileSync(manifestPath, 'utf8')
  const manifest = parseRegioesManifest(JSON.parse(manifestRaw))
  const expectedFiles = ['manifest.json', ...manifest.regions.map((entry) => entry.path)].toSorted()
  const actualFiles = jsonFiles(directory)
  if (JSON.stringify(actualFiles) !== JSON.stringify(expectedFiles)) {
    fail(`o staging contém ${actualFiles.join(', ')}, mas deveria conter ${expectedFiles.join(', ')}.`)
  }

  for (const entry of manifest.regions) {
    const target = path.join(directory, entry.path)
    const raw = fs.readFileSync(target, 'utf8')
    if (Buffer.byteLength(raw, 'utf8') !== entry.byteSize) {
      fail(`${entry.path} diverge do byteSize declarado.`)
    }
    if (sha256(raw) !== entry.contentHash) {
      fail(`${entry.path} diverge do contentHash declarado.`)
    }
    const payload = JSON.parse(raw)
    const { contentVersion, ...withoutVersion } = payload
    if (
      contentVersion !== entry.contentVersion
      || sha256(serializeForContentVersion(withoutVersion)) !== entry.contentVersion
    ) {
      fail(`${entry.path} diverge da versão de conteúdo declarada.`)
    }
    const document = parseRegiaoDocument(payload)
    if (
      document.regiao.slug !== entry.slug
      || document.regiao.nome !== entry.name
      || document.regiao.totalMunicipios !== entry.municipalityCount
      || document.schemaVersion !== manifest.documentSchemaVersion
      || document.generatorVersion !== manifest.generatorVersion
      || document.stateCode !== manifest.stateCode
    ) {
      fail(`${entry.path} diverge da identidade ou origem declarada no manifesto.`)
    }
  }
  return manifest
}

/**
 * Promove o lote regional somente depois da validação integral do staging.
 * Arquivos idênticos são preservados; qualquer falha restaura todo o conjunto.
 */
export function publishPublicationTransactionally(
  publication,
  {
    outputRoot = fileURLToPath(new URL('public/data/regioes/', REPOSITORY_ROOT)),
    stagingRoot = fileURLToPath(new URL('data_pipeline/.staging/regioes/', REPOSITORY_ROOT)),
    afterTargetPromoted = null,
  } = {},
) {
  const outputs = publicationOutputs(publication)
  const runRoot = path.join(stagingRoot, `run-${randomUUID()}`)
  const candidateRoot = path.join(runRoot, 'candidate')
  const backupRoot = path.join(runRoot, 'backup')
  assertChildPath(stagingRoot, runRoot, 'o run regional')
  fs.mkdirSync(candidateRoot, { recursive: true })

  for (const output of outputs) {
    const target = path.join(candidateRoot, output.relativePath)
    assertChildPath(candidateRoot, target, 'o arquivo de staging')
    writeFileAtomic(target, output.contents)
  }
  validatePublicationDirectory(candidateRoot)

  fs.mkdirSync(outputRoot, { recursive: true })
  const expected = new Set(outputs.map((output) => output.relativePath))
  const managed = [...new Set([...jsonFiles(outputRoot), ...expected])].toSorted()
  const existed = new Set()
  for (const relativePath of managed) {
    const current = path.join(outputRoot, relativePath)
    if (!fs.existsSync(current)) continue
    existed.add(relativePath)
    const backup = path.join(backupRoot, relativePath)
    assertChildPath(backupRoot, backup, 'o backup regional')
    fs.mkdirSync(path.dirname(backup), { recursive: true })
    fs.copyFileSync(current, backup)
  }

  const report = { created: [], updated: [], preserved: [], removed: [] }
  let rollbackFailure = null
  try {
    for (const output of outputs) {
      const target = path.join(outputRoot, output.relativePath)
      assertChildPath(outputRoot, target, 'o arquivo regional promovido')
      const current = fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : null
      if (current === output.contents) {
        report.preserved.push(output.relativePath)
      } else {
        writeFileAtomic(target, output.contents)
        report[existed.has(output.relativePath) ? 'updated' : 'created'].push(output.relativePath)
        afterTargetPromoted?.(output.relativePath, report)
      }
    }
    for (const relativePath of managed) {
      if (expected.has(relativePath)) continue
      const target = path.join(outputRoot, relativePath)
      assertChildPath(outputRoot, target, 'o órfão regional')
      if (fs.existsSync(target)) {
        fs.unlinkSync(target)
        report.removed.push(relativePath)
        afterTargetPromoted?.(relativePath, report)
      }
    }
    validatePublicationDirectory(outputRoot)
  } catch (error) {
    try {
      for (const relativePath of managed) {
        const target = path.join(outputRoot, relativePath)
        const backup = path.join(backupRoot, relativePath)
        if (existed.has(relativePath)) {
          writeFileAtomic(target, fs.readFileSync(backup, 'utf8'))
        } else if (fs.existsSync(target)) {
          fs.unlinkSync(target)
        }
      }
    } catch (rollbackError) {
      rollbackFailure = rollbackError
    }
    if (rollbackFailure !== null) {
      throw new AggregateError(
        [error, rollbackFailure],
        `Painel regional: promoção falhou e o rollback também falhou; preserve ${runRoot}.`,
      )
    }
    fs.rmSync(runRoot, { recursive: true, force: true })
    throw error
  }

  fs.rmSync(runRoot, { recursive: true, force: true })
  return report
}

function main(argv) {
  const checkOnly = argv.includes('--check')
  const publication = buildPublication()
  const outputRoot = fileURLToPath(new URL('public/data/regioes/', REPOSITORY_ROOT))
  const outputs = publicationOutputs(publication)

  if (checkOnly) {
    let drift = 0
    for (const output of outputs) {
      const target = path.join(outputRoot, output.relativePath)
      const current = fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : null
      if (current !== output.contents) {
        drift += 1
        process.stderr.write(`divergente: ${path.relative(fileURLToPath(REPOSITORY_ROOT), target)}\n`)
      }
    }
    if (drift > 0) {
      process.exitCode = 1
      return
    }
    process.stdout.write(
      `Painel regional: ${publication.files.length} regiões conferidas, sem divergência.\n`,
    )
    return
  }

  const report = publishPublicationTransactionally(publication, { outputRoot })
  process.stdout.write(
    `Painel regional publicado: ${publication.files.length} regiões, `
    + `${publication.manifest.municipalityCount} municípios (${publication.manifest.generatedAt}); `
    + `${report.created.length} criados, ${report.updated.length} atualizados, `
    + `${report.preserved.length} preservados e ${report.removed.length} removidos.\n`,
  )
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1] ?? '')) {
  main(process.argv.slice(2))
}
