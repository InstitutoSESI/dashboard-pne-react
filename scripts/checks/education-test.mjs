import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'
import { inflateRawSync } from 'node:zlib'
import writeXlsxFile from 'write-excel-file/node'

const output = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-education-'))
execFileSync(process.execPath, [
  path.resolve('node_modules/typescript/bin/tsc'),
  '--project',
  'scripts/checks/tsconfig.education.json',
  '--outDir',
  output,
], { stdio: 'inherit' })
process.on('exit', () => rmSync(output, { force: true, recursive: true }))

const moduleUrl = (relativePath) => pathToFileURL(path.join(output, relativePath)).href
const selectors = await import(moduleUrl('src/features/education/educationSelectors.js'))
const viewModels = await import(moduleUrl('src/features/education/educationViewModels.js'))
const formatters = await import(moduleUrl('src/features/education/educationFormatters.js'))
const attendancePresentation = await import(moduleUrl('src/features/education/educationAttendancePresentation.js'))
const attendanceFilters = await import(moduleUrl('src/features/education/educationAttendanceFilters.js'))
const overviewPresentation = await import(moduleUrl('src/features/education/municipalEducationOverviewPresentation.js'))
const overviewLoader = await import(moduleUrl('src/data/municipalEducationOverview.js'))
const pmeReferenceTable = await import(moduleUrl('src/features/education/pmeReferenceTableViewModel.js'))
const technicalReportWorkbook = await import(moduleUrl('src/features/education/municipalTechnicalReportWorkbook.js'))
const higherEducationValidation = await import(moduleUrl('src/data/higherEducationValidation.js'))
const higherEducationData = await import(moduleUrl('src/data/higherEducationData.js'))
const higherEducationViewModel = await import(moduleUrl('src/features/education/higherEducationViewModel.js'))
const higherEducationCatalog = await import(moduleUrl('src/features/education/higherEducationCatalog.js'))
const higherEducationPresentation = await import(moduleUrl('src/features/education/higherEducationPresentation.js'))
const specialEducationData = await import(moduleUrl('src/data/specialEducation.js'))
const specialEducationTypes = await import(moduleUrl('src/features/education/specialEducationTypes.js'))
const specialEducationViewModel = await import(moduleUrl('src/features/education/specialEducationViewModel.js'))
const schoolInfrastructure = await import(moduleUrl('src/data/schoolInfrastructureContract.js'))
const educationData = await import(moduleUrl('src/data/educationData.js'))
const educationCatalog = await import(moduleUrl('src/data/educationIndicatorCatalog.js'))
const projectionEndLabels = await import(pathToFileURL(path.resolve('src/utils/projectionEndLabels.js')).href)
const pneChartSystem = await import(pathToFileURL(path.resolve('src/utils/pneChartSystem.js')).href)

const specialEducationDataDirectory = path.resolve('public/data/educacao/educacao-especial')

const schoolInfrastructureDocumentsDirectory = path.resolve('public/data/educacao/municipios')
const schoolInfrastructureDocumentFiles = readdirSync(schoolInfrastructureDocumentsDirectory)
  .filter((fileName) => fileName.endsWith('.json'))

function readEducationDocument(fileName = schoolInfrastructureDocumentFiles[0]) {
  return JSON.parse(readFileSync(path.join(schoolInfrastructureDocumentsDirectory, fileName), 'utf8'))
}

function cellValue(cell) {
  return cell && typeof cell === 'object' && 'value' in cell ? cell.value : cell
}

function workbookOverviewFixture() {
  const snapshot = (value = 0, state = 'observed', year = 2025) => ({
    value,
    state,
    year,
    sourceId: 'inep',
    sourceField: 'campo',
  })
  const percentage = (value = 0, state = 'observed', year = 2025) => ({
    value,
    numerator: value == null ? null : 0,
    denominator: value == null ? null : 1,
    state,
    year,
    sourceId: 'inep',
  })
  const breakdown = (value = 0, state = 'observed') => ({
    enrollments: snapshot(value, state),
    share: percentage(value == null ? null : 0, state),
  })
  const stage = (value = 0, state = 'observed') => ({
    total: snapshot(value, state),
    byNetwork: {
      publicSubtotal: breakdown(value, state),
      municipal: breakdown(value, state),
      state: breakdown(value, state),
      federal: breakdown(value, state),
      private: breakdown(value, state),
    },
    bySchoolLocation: {
      urban: breakdown(value, state),
      rural: breakdown(value, state),
    },
  })
  const performance = {
    approval: snapshot(0),
    failure: snapshot(0),
    dropout: snapshot(0),
  }
  const comparison = {
    value2015: snapshot(0, 'observed', 2015),
    value2025: snapshot(0),
    absoluteChange: 0,
    percentageChange: percentage(0),
  }
  const historical = { total: comparison }

  return {
    schemaVersion: 'municipal-education-overview-v1',
    publicationState: 'partial',
    municipality: { idMunicipality: '4300000', name: 'São Borja', slug: 'sao-borja' },
    reference: { year: 2025, generatedAt: '2026-07-27T12:00:00-03:00' },
    universe: {
      territorialBasis: 'school_location',
      locationLabel: 'Localização da escola',
      basicEducationSourceField: 'QT_MAT_BAS',
      methodologyNotes: [],
    },
    basicEducation: { total: snapshot(0) },
    basicEducationComposition: {
      total: snapshot(0),
      components: {
        earlyChildhood: {
          total: snapshot(0),
          details: { creche: snapshot(0), preSchool: snapshot(0) },
        },
        elementary: {
          total: snapshot(0),
          details: { initialYears: snapshot(0), finalYears: snapshot(0) },
        },
        highSchool: {
          total: snapshot(0),
          details: { integratedTechnical: snapshot(0) },
        },
        youthAndAdultEducation: {
          total: snapshot(0),
          details: { elementary: snapshot(0), highSchool: snapshot(0) },
        },
        otherProfessionalOffers: {
          total: snapshot(0),
          details: {
            concomitantTechnical: snapshot(0),
            subsequentTechnical: snapshot(0),
            otherOffers: snapshot(0),
          },
        },
      },
      reconciliation: {
        id: 'total',
        label: 'Total',
        expected: 0,
        observed: 0,
        difference: 0,
        status: 'reconciled',
      },
    },
    specialEducation: {
      total: snapshot(0),
      commonClasses: snapshot(0),
      exclusiveClasses: snapshot(0),
    },
    highSchool: {
      total: stage(0),
      integratedTechnical: {
        total: snapshot(0),
        shareOfHighSchool: percentage(0),
      },
    },
    schoolPerformance: {
      referenceYear: 2025,
      stages: {
        elementary: performance,
        initialYears: performance,
        finalYears: performance,
        highSchool: performance,
      },
      sourceId: 'inep',
    },
    enrollmentComparison: {
      years: [2015, 2025],
      stages: {
        basicEducation: historical,
        earlyChildhood: historical,
        creche: historical,
        preSchool: historical,
        elementary: historical,
        initialYears: historical,
        finalYears: historical,
        highSchool: historical,
        youthAndAdultEducation: historical,
      },
      methodologyNote: 'Comparação histórica.',
    },
    earlyChildhood: {
      total: stage(null, 'unavailable'),
      creche: stage(0),
      preSchool: stage(0),
    },
    elementary: {
      total: stage(0),
      initialYears: stage(0),
      finalYears: stage(0),
    },
    sources: [],
    methodology: [],
    quality: {
      reconciliations: [],
      semanticWarnings: [],
      nullCoreRows: [],
      completeness: {},
      schoolPerformanceChecks: [],
    },
  }
}

function readZipEntry(buffer, entryName) {
  const endOfCentralDirectorySignature = 0x06054b50
  const centralDirectorySignature = 0x02014b50
  const localFileSignature = 0x04034b50
  const earliestOffset = Math.max(0, buffer.length - 65_557)
  let endOfCentralDirectoryOffset = -1

  for (let offset = buffer.length - 22; offset >= earliestOffset; offset -= 1) {
    if (buffer.readUInt32LE(offset) === endOfCentralDirectorySignature) {
      endOfCentralDirectoryOffset = offset
      break
    }
  }

  assert.notEqual(endOfCentralDirectoryOffset, -1, 'diretório central do XLSX não encontrado')
  const entryCount = buffer.readUInt16LE(endOfCentralDirectoryOffset + 10)
  let offset = buffer.readUInt32LE(endOfCentralDirectoryOffset + 16)

  for (let entryIndex = 0; entryIndex < entryCount; entryIndex += 1) {
    assert.equal(buffer.readUInt32LE(offset), centralDirectorySignature)
    const compressionMethod = buffer.readUInt16LE(offset + 10)
    const compressedSize = buffer.readUInt32LE(offset + 20)
    const fileNameLength = buffer.readUInt16LE(offset + 28)
    const extraFieldLength = buffer.readUInt16LE(offset + 30)
    const commentLength = buffer.readUInt16LE(offset + 32)
    const localHeaderOffset = buffer.readUInt32LE(offset + 42)
    const fileName = buffer.subarray(offset + 46, offset + 46 + fileNameLength).toString('utf8')

    if (fileName === entryName) {
      assert.equal(buffer.readUInt32LE(localHeaderOffset), localFileSignature)
      const localFileNameLength = buffer.readUInt16LE(localHeaderOffset + 26)
      const localExtraFieldLength = buffer.readUInt16LE(localHeaderOffset + 28)
      const contentOffset = localHeaderOffset + 30 + localFileNameLength + localExtraFieldLength
      const compressed = buffer.subarray(contentOffset, contentOffset + compressedSize)
      if (compressionMethod === 0) return compressed
      if (compressionMethod === 8) return inflateRawSync(compressed)
      assert.fail(`método de compressão ZIP não suportado no teste: ${compressionMethod}`)
    }

    offset += 46 + fileNameLength + extraFieldLength + commentLength
  }

  assert.fail(`entrada ${entryName} não encontrada no XLSX`)
}

const indicators = [
  { key: 'b', label: 'Zeta', description: 'Atendimento escolar', themeLabel: 'Matrículas' },
  { key: 'a', label: 'Álfa', description: 'Trajetória', categoryLabel: 'Fluxo' },
]

test('runner materializa os tipos compartilhados de Educação Especial', () => {
  assert.equal(specialEducationTypes.SPECIAL_EDUCATION_SCHEMA_VERSION, 'special-education-v1')
  assert.equal(specialEducationTypes.isSpecialEducationIndicatorId('aee'), true)
})

function higherEducationFixture(availability = 'current') {
  const years = [2023, 2024]
  const sources = Object.fromEntries(years.map((year) => [`source-${year}`, {
    year,
    table: '7.1',
    fileName: `source-${year}.xlsx`,
    sha256: 'a'.repeat(64),
    universe: 'graduation',
    territorialReference: 'course_offer_location',
  }]))
  const manifestIndicators = higherEducationCatalog.HIGHER_EDUCATION_INDICATOR_CATALOG.map((item) => ({
    id: item.id,
    universe: item.universe,
    territorialReference: item.territorialReference,
    sourceTable: '7.1',
    coverageByYear: { 2023: 1, 2024: availability === 'current' ? 1 : 0 },
  }))
  const categoryDefinitions = {
    enrollment_dependency: [{ id: 'publica', label: 'Pública' }, { id: 'privada', label: 'Privada' }],
    enrollment_organization: [{ id: 'universidade', label: 'Universidade' }],
    ies_dependency: [{ id: 'publica', label: 'Pública' }],
    ies_organization: [{ id: 'faculdade', label: 'Faculdade' }],
    faculty_education: [{ id: 'Mestrado', label: 'Mestrado' }],
  }
  const manifestBreakdowns = higherEducationCatalog.HIGHER_EDUCATION_BREAKDOWN_CATALOG.map((item) => ({
    id: item.id,
    universe: item.id.startsWith('ies_') ? 'institutions_offering_graduation_or_sequential' : item.id === 'faculty_education' ? 'faculty_in_graduation_or_sequential' : 'graduation',
    territorialReference: item.id.startsWith('ies_') ? 'ies_administrative_headquarters' : item.id === 'faculty_education' ? 'faculty_institution_headquarters' : 'course_offer_location',
    sourceTable: '7.1',
    categories: categoryDefinitions[item.id],
    coverageByYear: { 2023: 1, 2024: availability === 'current' ? 1 : 0 },
  }))
  const manifest = {
    schemaVersion: 1,
    dataVersion: 'fixture-v1',
    firstYear: 2023,
    latestYear: 2024,
    availableYears: years,
    municipalityCount: 1,
    indicators: manifestIndicators,
    breakdowns: manifestBreakdowns,
    sources,
  }
  const unavailable = (year) => ({ year, value: null, status: 'unavailable', sourceId: null })
  const document = {
    schemaVersion: 1,
    municipality: { id: '4300000', name: 'Município teste' },
    availability,
    indicators: Object.fromEntries(manifestIndicators.map((definition, indicatorIndex) => [
      definition.id,
      {
        id: definition.id,
        universe: definition.universe,
        territorialReference: definition.territorialReference,
        series: years.map((year, yearIndex) => availability === 'unavailable' || (availability === 'historical_only' && year === 2024)
          ? unavailable(year)
          : { year, value: indicatorIndex === 1 && yearIndex === 0 ? 0 : (indicatorIndex + 1) * 10 + yearIndex, status: indicatorIndex === 1 && yearIndex === 0 ? 'derived_zero' : 'observed', sourceId: `source-${year}` }),
      },
    ])),
    breakdowns: manifestBreakdowns.flatMap((definition) => years.map((year) => {
      const usable = availability !== 'unavailable' && !(availability === 'historical_only' && year === 2024)
      return {
        id: definition.id,
        year,
        universe: definition.universe,
        territorialReference: definition.territorialReference,
        exhaustive: true,
        status: usable ? 'observed' : 'unavailable',
        sourceId: usable ? `source-${year}` : null,
        categories: definition.categories.map((category, index) => ({
          ...category,
          value: usable ? index + 1 : null,
          status: usable ? 'observed' : 'unavailable',
        })),
      }
    })),
  }
  return { document, manifest }
}

test('contrato de Educação Superior preserva zero e rejeita ausência numérica', () => {
  const { document, manifest } = higherEducationFixture()
  const validatedManifest = higherEducationValidation.validateHigherEducationManifest(manifest)
  assert.equal(higherEducationValidation.validateHigherEducationMunicipalDocument(document, '4300000', validatedManifest).indicators['esup-matriculas-presenciais'].series[0].value, 0)
  const invalid = structuredClone(document)
  invalid.indicators['esup-matriculas-total'].series[0] = { year: 2023, value: 0, status: 'unavailable', sourceId: null }
  assert.throws(() => higherEducationValidation.validateHigherEducationMunicipalDocument(invalid, '4300000', validatedManifest), /não pode ter valor numérico/)
  assert.throws(() => higherEducationValidation.validateHigherEducationMunicipalDocument(document, '9999999', validatedManifest), /não corresponde/)
})

test('validador de Educação Superior rejeita série incompleta, indicador e fonte desconhecidos', () => {
  const { document, manifest } = higherEducationFixture()
  const validatedManifest = higherEducationValidation.validateHigherEducationManifest(manifest)
  const incomplete = structuredClone(document)
  incomplete.indicators['esup-matriculas-total'].series.pop()
  assert.throws(() => higherEducationValidation.validateHigherEducationMunicipalDocument(incomplete, '4300000', validatedManifest), /não possui os 2 anos/)
  const unknownIndicator = structuredClone(document)
  unknownIndicator.indicators.desconhecido = unknownIndicator.indicators['esup-matriculas-total']
  assert.throws(() => higherEducationValidation.validateHigherEducationMunicipalDocument(unknownIndicator, '4300000', validatedManifest), /indicador desconhecido/)
  const unknownSource = structuredClone(document)
  unknownSource.indicators['esup-matriculas-total'].series[0].sourceId = 'fonte-inexistente'
  assert.throws(() => higherEducationValidation.validateHigherEducationMunicipalDocument(unknownSource, '4300000', validatedManifest), /fonte desconhecida/)
})

test('view model de Educação Superior usa anos próprios, variação e composição compatível', () => {
  const { document, manifest } = higherEducationFixture('historical_only')
  const viewModel = higherEducationViewModel.buildHigherEducationViewModel(manifest, document)
  assert.equal(viewModel.availability, 'historical_only')
  assert.equal(viewModel.latestMunicipalUsableYear, 2023)
  assert.equal(viewModel.indicators[0].currentYear, 2023)
  assert.equal(viewModel.indicators[1].firstPoint.value, 0)
  assert.equal(viewModel.indicators[1].percentVariation, null)
  assert.ok(viewModel.effectiveSources.length === 1)
  assert.ok(viewModel.breakdowns.every((item) => item.categories.every((category) => category.share != null)))
})

test('apresentação de Educação Superior preserva os nove indicadores, grupos e estados especiais', () => {
  const currentFixture = higherEducationFixture('current')
  const current = higherEducationViewModel.buildHigherEducationViewModel(
    currentFixture.manifest,
    currentFixture.document,
  )
  assert.equal(current.indicators.length, 9)
  assert.deepEqual(
    current.groups.slice(0, 4).map((group) => group.id),
    ['enrollments', 'institutions', 'access-flow', 'faculty'],
  )
  assert.equal(current.indicators.filter((indicator) => indicator.latestPoint).length, 9)
  assert.equal(current.indicators[1].firstPoint.status, 'derived_zero')
  assert.equal(current.indicators[1].firstPoint.value, 0)

  const unavailableFixture = higherEducationFixture('unavailable')
  const unavailable = higherEducationViewModel.buildHigherEducationViewModel(
    unavailableFixture.manifest,
    unavailableFixture.document,
  )
  assert.equal(unavailable.availability, 'unavailable')
  assert.equal(unavailable.indicators.filter((indicator) => indicator.latestPoint).length, 0)
  assert.equal(unavailable.quickReads.length, 0)
  assert.equal(unavailable.effectiveSources.length, 0)
})

test('apresentação de série distingue zero constante, ponto único e igualdade sem perder derived_zero', () => {
  const zeroSeries = {
    unit: 'matrículas',
    series: [2018, 2019, 2024].map((year) => ({ year, value: 0, status: 'derived_zero' })),
  }
  const zeroPresentation = higherEducationPresentation.analyzeHigherEducationSeries(zeroSeries)
  assert.equal(zeroPresentation.kind, 'constant_zero')
  assert.equal(zeroPresentation.trendLabel, 'Estável')
  assert.equal(zeroPresentation.reading, 'Estabilidade no período')
  assert.equal(zeroPresentation.latestPoint.value, 0)

  const singlePoint = higherEducationPresentation.analyzeHigherEducationSeries({
    unit: 'polos',
    series: [
      { year: 2023, value: null, status: 'unavailable' },
      { year: 2024, value: 1, status: 'observed' },
    ],
  })
  assert.equal(singlePoint.kind, 'single_point')
  assert.equal(singlePoint.reading, 'Série insuficiente para evolução')

  assert.equal(higherEducationPresentation.areHigherEducationSeriesEqual(zeroSeries, structuredClone(zeroSeries)), true)
  assert.equal(higherEducationPresentation.areHigherEducationSeriesEqual(zeroSeries, {
    ...zeroSeries,
    series: zeroSeries.series.map((point, index) => ({ ...point, value: index === 2 ? 1 : 0 })),
  }), false)
})

test('apresentação categórica omite zeros apenas do gráfico e preserva tabelas e não exaustividade', () => {
  const categories = [
    { id: 'federal', label: 'Federal', value: 0, status: 'observed', share: 0 },
    { id: 'private', label: 'Privada', value: 811, status: 'observed', share: 100 },
  ]
  const single = higherEducationPresentation.analyzeHigherEducationBreakdown({ categories, exhaustive: true })
  assert.equal(single.kind, 'single_category')
  assert.equal(single.singleCategory.label, 'Privada')
  assert.equal(single.tableCategories.length, 2)
  assert.equal(single.tableCategories[0].value, 0)

  const nonExhaustive = higherEducationPresentation.analyzeHigherEducationBreakdown({
    categories: categories.map((category) => ({ ...category, share: null })),
    exhaustive: false,
  })
  assert.equal(nonExhaustive.kind, 'bars')
  assert.deepEqual(nonExhaustive.chartRows, [{ label: 'Privada', value: 811 }])
  assert.ok(nonExhaustive.tableCategories.every((category) => category.share == null))
})

test('apoio da Educação Superior exige conteúdo substantivo e não considera nota isolada', () => {
  assert.equal(higherEducationPresentation.hasSubstantiveSupportContent({}), false)
  assert.equal(higherEducationPresentation.hasSubstantiveSupportContent({ breakdownCount: 1 }), true)
  assert.equal(higherEducationPresentation.hasSubstantiveSupportContent({ hasComposition: true }), true)
  assert.equal(higherEducationPresentation.hasSubstantiveSupportContent({ hasUsefulReferenceSeries: true }), true)
})

test('interface pública consolida a fonte e mantém disclosure e impressão da série', () => {
  const componentSource = readFileSync(path.resolve('src/features/education/components/HigherEducationSection.tsx'), 'utf8')
  const cssSource = readFileSync(path.resolve('src/styles/education-pages.css'), 'utf8')
  assert.match(componentSource, /Censo da Educação Superior — INEP/)
  assert.doesNotMatch(componentSource, /Tabela 7\.1|Tabela 7\.3|Tabela 5\.1|sourceId/)
  assert.match(componentSource, /Ver valores da série/)
  assert.match(cssSource, /higher-education-page \.platform-support-disclosure__body[\s\S]*display: block !important/)
  assert.match(cssSource, /higher-education-simple-table\.education-table-wrap[\s\S]*overflow: visible/)
})

test('detalhes de Educação Superior omitem apoio vazio e não duplicam notas específicas', () => {
  const componentSource = readFileSync(path.resolve('src/features/education/components/HigherEducationSection.tsx'), 'utf8')
  assert.match(componentSource, /hasSubstantiveSupportContent/)
  assert.match(componentSource, /\['esup-matriculas-total', 'esup-matriculas-presenciais', 'esup-matriculas-ead'\]/)
  assert.doesNotMatch(componentSource, /if \(indicator\.id === 'esup-matriculas-presenciais'\)[\s\S]{0,200}related\.push\(total\)/)
  assert.match(componentSource, /Como interpretar este indicador/)
  assert.doesNotMatch(componentSource, /Notas do indicador/)
  assert.match(componentSource, /Polo EaD é local de oferta e não equivale a uma Instituição/)
  assert.match(componentSource, /Não é calculada taxa a partir de vagas ou matrículas/)
  assert.match(componentSource, /Não é calculada taxa de conclusão ou relação automática/)
  assert.equal((componentSource.match(/Fonte: Censo da Educação Superior — INEP/g) ?? []).length, 1)
})

test('apresentação refinada preserva métricas compartilhadas, composição e responsividade', () => {
  const componentSource = readFileSync(path.resolve('src/features/education/components/HigherEducationSection.tsx'), 'utf8')
  const cssSource = readFileSync(path.resolve('src/styles/education-pages.css'), 'utf8')
  assert.equal((componentSource.match(/<MetricCard /g) ?? []).length, 4)
  assert.match(componentSource, /educacao-detail-panel--organized/)
  assert.match(componentSource, /hideTitle/)
  assert.match(componentSource, /Participação no total de matrículas/)
  assert.match(componentSource, /higher-education-composition-legend/)
  assert.match(componentSource, /Sem informação municipal/)
  assert.match(cssSource, /@media \(max-width: 1080px\)[\s\S]*higher-education-support-grid/)
  assert.match(cssSource, /higher-education-simple-table \.education-table[\s\S]*table-layout: fixed/)
  assert.match(cssSource, /higher-education-page \.higher-education-unavailable-strip[\s\S]*display: flex !important/)
})

test('relatório técnico omite colunas de situação e fonte detalhada da Educação Superior', () => {
  const reportSource = readFileSync(path.resolve('src/features/education/components/MunicipalTechnicalReport.tsx'), 'utf8')
  const layoutSource = readFileSync(path.resolve('src/features/education/components/MunicipalTechnicalReportLayout.tsx'), 'utf8')
  const pmeSource = readFileSync(path.resolve('src/features/education/components/PmeReferenceIndicatorsTable.tsx'), 'utf8')
  const catalogSource = readFileSync(path.resolve('src/features/education/municipalTechnicalReportCatalog.ts'), 'utf8')
  const cssSource = readFileSync(path.resolve('src/styles/education-pages.css'), 'utf8')
  assert.doesNotMatch(reportSource, /<th[^>]*>\s*Situação\s*<\/th>/)
  assert.doesNotMatch(reportSource, /municipal-technical-report__table-col-status/)
  assert.doesNotMatch(reportSource, /INEP · Sinopse Estatística · tabela/)
  assert.doesNotMatch(cssSource, /municipal-technical-report__pme-table-scroll\s*\{\s*max-height:\s*min\(/)
  assert.match(cssSource, /municipal-technical-report__pme-table-scroll\s*\{[\s\S]*?max-height:\s*none;[\s\S]*?overflow-x:\s*auto;/)
  assert.doesNotMatch(reportSource, /item\.label \?\? item\.key/)
  assert.doesNotMatch(reportSource, /Dados integrados|Dados não integrados|Situação da base/)
  assert.doesNotMatch(`${reportSource}${layoutSource}${pmeSource}`, /Não calculável com os dados atualmente disponíveis|Meta já alcançada|Meta atingida|Meta cumprida|Meta não atingida/)
  assert.match(layoutSource, /Evidências públicas disponíveis/)
  assert.match(pmeSource, /Situação atual em relação à referência/)
  assert.equal((catalogSource.match(/officialTitle:/g) ?? []).length, 19)
  assert.equal((catalogSource.match(/id: 'capitulo-/g) ?? []).length, 6)
  assert.match(catalogSource, /Expansão das matrículas em cursos técnicos subsequentes/)
  assert.match(cssSource, /--technical-report-canvas-max:\s*1120px/)
  assert.match(reportSource, /Baixar Excel/)
  assert.match(reportSource, /getDiagnosticItems\('educacao_ambiental'\)/)
  assert.match(reportSource, /getDiagnosticItems\('adequacao_ai', 'adequacao_af', 'adequacao_em', 'pos_graduacao', 'temporarios'\)/)
  assert.match(reportSource, /getDiagnosticItems\('conselho_escolar'\)/)
  assert.match(reportSource, /getDiagnosticItems\('salas_climatizadas', 'salas_acessiveis'\)/)
})

test('workbook municipal usa rótulos humanos, preserva estados e gera XLSX válido', async () => {
  const environmentalEducationResult = pmeResult({
    goalId: '6.a',
    indicatorId: 'educacao_ambiental',
    order: 1,
    themeId: 'sustentabilidade',
    currentValue: 0,
  })
  environmentalEducationResult.publicName = 'Escolas que promovem educação ambiental'
  environmentalEducationResult.publicDescription = 'Participação das escolas que declaram promover ações de educação ambiental.'
  const fullTimeResult = pmeResult({
    goalId: '5.a',
    indicatorId: 'basico_integral',
    order: 2,
    themeId: 'sustentabilidade',
    currentValue: 0,
  })
  fullTimeResult.publicName = 'Alunos em jornada integral na rede pública'
  fullTimeResult.publicDescription = 'Participação dos alunos em jornada integral na rede pública.'
  const diagnostic = {
    sources: [{
      id: 'inep_censo_escolar',
      organization: 'Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)',
      publicTitle: 'Censo Escolar',
      period: '2025',
      officialUrl: 'https://example.test/inep',
    }],
    presentation: {
      themes: [{ id: 'sustentabilidade', order: 1, label: 'Sustentabilidade socioambiental' }],
      resultDefinitions: [],
    },
    goals: [{
      goalId: '6.a',
      title: 'Meta 6',
      order: 1,
      results: [environmentalEducationResult, fullTimeResult],
    }],
  }
  const input = {
    educationItems: [
      {
        key: 'mat-eja',
        label: 'matriculas_eja',
        currentValue: 42,
        currentDisplay: '42',
        currentYear: 2025,
        unit: 'matriculas',
        source: 'censo_escolar',
      },
      {
        key: 'docentes-total',
        label: 'docentes_total',
        currentValue: null,
        currentDisplay: '—',
        currentYear: 2025,
        unit: 'docentes',
        source: 'censo_escolar',
      },
    ],
    emissionDate: '27/07/2026',
    higherEducation: null,
    municipalityId: '4300000',
    municipalityName: 'São Borja',
    municipalityPopulation: 59_000,
    municipalitySlug: 'São Borja',
    overview: null,
    pmeDiagnostic: diagnostic,
    pmeReferenceData: {
      planningScenarios: {
        basico_integral: {
          indicatorKey: 'basico_integral',
          historical: [{ year: 2025, numerator: 0, denominator: 120 }],
        },
      },
    },
    schoolInfrastructure: {
      referenceYear: 2025,
      years: [],
    },
    specialEducation: null,
  }

  const workbook = technicalReportWorkbook.buildMunicipalTechnicalReportWorkbook(input)
  assert.equal(workbook.fileName, 'relatorio-tecnico-municipal-sao-borja-2025.xlsx')
  assert.deepEqual(
    workbook.sheets.map((sheet) => sheet.sheet),
    [
      'Orientações',
      'Acompanhamento',
      'Referências PNE',
      'Matrículas por rede',
      'Rendimento escolar',
      'Série histórica',
      'Infraestrutura',
      'Educação Especial',
      'Educação Superior',
      'Fontes e metodologia',
    ],
  )

  const trackingSheet = workbook.sheets.find((sheet) => sheet.sheet === 'Acompanhamento')
  assert.ok(trackingSheet)
  const headers = trackingSheet.data[2].map(cellValue)
  assert.deepEqual(headers.slice(-5), [
    'Meta municipal (preencher)',
    'Prazo municipal (preencher)',
    'Responsável pelo acompanhamento (preencher)',
    'Periodicidade de revisão (preencher)',
    'Observações da gestão (preencher)',
  ])
  assert.ok(headers.every((header) => typeof header === 'string' && !/[a-z]+_[a-z]+/.test(header)))

  const rows = trackingSheet.data.slice(3)
  const environmentalEducation = rows.find(
    (row) => cellValue(row[2]) === 'Escolas que promovem educação ambiental',
  )
  assert.ok(environmentalEducation)
  assert.equal(environmentalEducation[3].value, 0)
  assert.equal(environmentalEducation[3].type, Number)
  assert.equal(environmentalEducation[3].format, '0.00%')
  assert.equal(cellValue(environmentalEducation[11]), 'Disponível')

  const unavailableTeachers = rows.find((row) => cellValue(row[2]) === 'Total de docentes')
  assert.ok(unavailableTeachers)
  assert.equal(unavailableTeachers[3], null)
  assert.equal(cellValue(unavailableTeachers[11]), 'Dado indisponível')

  const eja = rows.find(
    (row) => cellValue(row[2]) === 'Matrículas na Educação de Jovens e Adultos',
  )
  assert.ok(eja)
  assert.equal(cellValue(eja[3]), 42)
  assert.ok(eja.slice(-5).every((cell) =>
    cellValue(cell) === '' && cell.backgroundColor === '#FEF3C7'))

  const pneSheet = workbook.sheets.find((sheet) => sheet.sheet === 'Referências PNE')
  assert.ok(pneSheet)
  const pneHeaders = pneSheet.data[2].map(cellValue)
  assert.ok(pneHeaders.includes('Numerador'))
  assert.ok(pneHeaders.includes('Unidade do numerador'))
  assert.ok(pneHeaders.includes('Denominador'))
  assert.ok(pneHeaders.includes('Unidade do denominador'))
  const numeratorIndex = pneHeaders.indexOf('Numerador')
  const numeratorUnitIndex = pneHeaders.indexOf('Unidade do numerador')
  const denominatorIndex = pneHeaders.indexOf('Denominador')
  const denominatorUnitIndex = pneHeaders.indexOf('Unidade do denominador')
  const fullTimeReference = pneSheet.data.slice(3).find(
    (row) => cellValue(row[2]) === 'Alunos do público-alvo da Educação em Tempo Integral em jornada integral na rede pública',
  )
  assert.ok(fullTimeReference)
  assert.equal(fullTimeReference[numeratorIndex].value, 0)
  assert.equal(fullTimeReference[numeratorIndex].type, Number)
  assert.equal(cellValue(fullTimeReference[numeratorUnitIndex]), 'matrículas')
  assert.equal(fullTimeReference[denominatorIndex].value, 120)
  assert.equal(cellValue(fullTimeReference[denominatorUnitIndex]), 'matrículas')
  const environmentalReference = pneSheet.data.slice(3).find(
    (row) => cellValue(row[2]) === 'Escolas que promovem educação ambiental',
  )
  assert.ok(environmentalReference)
  assert.equal(environmentalReference[numeratorIndex], null)
  assert.equal(environmentalReference[denominatorIndex], null)

  const visibleText = workbook.sheets
    .flatMap((sheet) => sheet.data)
    .flatMap((row) => row)
    .map(cellValue)
    .filter((value) => typeof value === 'string')
    .join('\n')
  assert.doesNotMatch(
    visibleText,
    /matriculas_eja|docentes_total|censo_escolar|mat-eja|docentes-total|educacao_ambiental/,
  )

  const buffer = await writeXlsxFile(workbook.sheets, {
    fontFamily: 'Arial',
    fontSize: 10,
  }).toBuffer()
  assert.equal(buffer.subarray(0, 4).toString('hex'), '504b0304')

  const workbookXml = readZipEntry(buffer, 'xl/workbook.xml').toString('utf8')
  const sharedStringsXml = readZipEntry(buffer, 'xl/sharedStrings.xml').toString('utf8')
  assert.match(workbookXml, /name="Orientações"/)
  assert.match(workbookXml, /name="Acompanhamento"/)
  assert.match(workbookXml, /name="Fontes e metodologia"/)
  assert.match(sharedStringsXml, /Meta municipal \(preencher\)/)
  assert.match(sharedStringsXml, /Escolas que promovem educação ambiental/)

  const zoomScales = workbook.sheets.map((_, index) => {
    const sheetXml = readZipEntry(buffer, `xl/worksheets/sheet${index + 1}.xml`).toString('utf8')
    const zoomScale = /zoomScale="(\d+)"/.exec(sheetXml)
    assert.ok(zoomScale, `aba ${index + 1} deve declarar uma escala de zoom`)
    return Number(zoomScale[1])
  })
  assert.deepEqual(zoomScales, [90, 85, 85, 85, 85, 85, 85, 85, 85, 85])
  assert.ok(zoomScales.every((zoomScale) => zoomScale >= 10 && zoomScale <= 400))
})

test('workbook não publica participação total quando o total da etapa está indisponível', () => {
  const workbook = technicalReportWorkbook.buildMunicipalTechnicalReportWorkbook({
    educationItems: [],
    emissionDate: '27/07/2026',
    higherEducation: null,
    municipalityId: '4300000',
    municipalityName: 'São Borja',
    municipalitySlug: 'sao-borja',
    overview: workbookOverviewFixture(),
    pmeDiagnostic: null,
    schoolInfrastructure: null,
    specialEducation: null,
  })
  const networkSheet = workbook.sheets.find((sheet) => sheet.sheet === 'Matrículas por rede')
  assert.ok(networkSheet)
  const unavailableTotal = networkSheet.data.slice(3).find(
    (row) => cellValue(row[0]) === 'Educação Infantil' && cellValue(row[1]) === 'Total',
  )
  assert.ok(unavailableTotal)
  assert.equal(unavailableTotal[2], null)
  assert.equal(unavailableTotal[3], null)
  assert.equal(cellValue(unavailableTotal[5]), 'Dado indisponível')
})

test('loader de Educação Superior deduplica requisições simultâneas e limpa cache', async () => {
  const { document, manifest } = higherEducationFixture()
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async (url) => {
    requests.push(String(url))
    return new Response(JSON.stringify(String(url).endsWith('index.json') ? manifest : document), { status: 200 })
  }
  try {
    higherEducationData.clearHigherEducationDataCache()
    const [first, second] = await Promise.all([
      higherEducationData.loadHigherEducationMunicipality('4300000'),
      higherEducationData.loadHigherEducationMunicipality('4300000'),
    ])
    assert.equal(first, second)
    assert.equal(requests.filter((url) => url.endsWith('index.json')).length, 1)
    assert.equal(requests.filter((url) => url.endsWith('4300000.json')).length, 1)
  } finally {
    higherEducationData.clearHigherEducationDataCache()
    globalThis.fetch = originalFetch
  }
})

test('contrato de Educação Especial valida casos positivo, zero e parcial', () => {
  const manifest = specialEducationData.validateSpecialEducationManifest(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'index.json'), 'utf8')),
  )
  const documents = ['4300406', '4300034', '4314407'].map((municipalityId) =>
    specialEducationData.validateSpecialEducationMunicipalDocument(
      JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'municipios', `${municipalityId}.json`), 'utf8')),
      municipalityId,
      manifest,
    ))
  const positiveLatest = documents[0].years[documents[0].years.length - 1].cuts.total
  assert.equal(positiveLatest.specialEducation.enrollments.value, 1056)
  assert.equal(positiveLatest.aee.schoolsOfferingAee.value, 17)
  assert.equal(documents[1].years.at(-1).cuts.total.bilingualDeafEducation.enrollments.value, 0)
  const partialInterpreter = documents[2].years.at(-1).cuts.total.bilingualDeafEducation.interpreterAssignments
  assert.equal(partialInterpreter.state, 'partial')
  assert.equal(partialInterpreter.value, 10)
})

test('loader de Educação Especial usa manifesto uma vez e deduplica município por hash', async () => {
  const manifest = JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'index.json'), 'utf8'))
  const document = JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'municipios', '4300406.json'), 'utf8'))
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async (url) => {
    requests.push(String(url))
    return new Response(JSON.stringify(String(url).endsWith('index.json') ? manifest : document), { status: 200 })
  }
  try {
    specialEducationData.clearSpecialEducationDataCache()
    const [first, second] = await Promise.all([
      specialEducationData.loadSpecialEducationMunicipality('4300406'),
      specialEducationData.loadSpecialEducationMunicipality('4300406'),
    ])
    assert.equal(first, second)
    assert.equal(requests.filter((url) => url.endsWith('index.json')).length, 1)
    assert.equal(requests.filter((url) => url.endsWith('4300406.json')).length, 1)
  } finally {
    specialEducationData.clearSpecialEducationDataCache()
    globalThis.fetch = originalFetch
  }
})

test('view model preserva oito recortes, lacunas e retrato bilíngue somente em 2025', () => {
  const manifest = specialEducationData.validateSpecialEducationManifest(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'index.json'), 'utf8')),
  )
  const document = specialEducationData.validateSpecialEducationMunicipalDocument(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'municipios', '4300406.json'), 'utf8')),
    '4300406',
    manifest,
  )
  assert.deepEqual(
    specialEducationViewModel.SPECIAL_EDUCATION_CUT_OPTIONS.map((item) => item.key),
    ['total', 'publica', 'municipal', 'estadual', 'federal', 'privada', 'urbana', 'rural'],
  )
  const bilingual = specialEducationViewModel.buildIndicatorSeries(document, 'educacao-bilingue-surdos', 'total')
  assert.deepEqual(bilingual.filter((point) => point.valor != null).map((point) => point.ano), [2025])
  assert.equal(bilingual.find((point) => point.ano === 2024).valor, null)
  const viewModel = specialEducationViewModel.buildSpecialEducationViewModel(document)
  const items = viewModel.items
  assert.deepEqual(items.map((item) => item.key), [
    'educacao-especial-matriculas',
    'educacao-especial-inclusao-classes-comuns',
    'aee',
    'educacao-bilingue-surdos',
  ])
  assert.equal(items.find((item) => item.key === 'aee').unit, 'escolas')
  assert.match(items.find((item) => item.key === 'educacao-especial-matriculas').statusLabel, /Alta|Queda|Estável/)
  assert.equal(items.find((item) => item.key === 'educacao-bilingue-surdos').statusLabel, 'Retrato 2025')
  assert.equal(items.find((item) => item.key === 'educacao-bilingue-surdos').cardReading, 'Retrato disponível em 2025')
  const enrollments = items.find((item) => item.key === 'educacao-especial-matriculas')
  assert.equal(enrollments.series.length, 12)
  assert.deepEqual(enrollments.series.map((point) => point.ano), [
    2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025,
  ])
  assert.deepEqual(
    enrollments.series.filter((point) => point.ano >= 2022).map((point) => point.valor),
    [736, 931, 1015, 1056],
  )
  assert.equal(enrollments.currentYear, 2025)
  assert.equal(enrollments.currentValue, 1056)
  assert.equal(viewModel.latestYear, 2025)
  assert.equal(viewModel.allItems.length, 4)
})

test('ticks responsivos reduzem rótulos sem remover os doze dados anuais', () => {
  const points = Array.from({ length: 12 }, (_, index) => ({
    ano: 2014 + index,
    year: 2014 + index,
    valor: index,
  }))
  const ticks = pneChartSystem.selectPneYearTicks(points, 7)
  assert.equal(points.length, 12)
  assert.ok(ticks.length <= 7)
  assert.equal(ticks[0].year, 2014)
  assert.equal(ticks.at(-1).year, 2025)
})

test('publicação especial exige o total de 2025 e preserva zero observado', () => {
  const manifest = specialEducationData.validateSpecialEducationManifest(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'index.json'), 'utf8')),
  )
  const readDocument = (municipalityId) => specialEducationData.validateSpecialEducationMunicipalDocument(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'municipios', `${municipalityId}.json`), 'utf8')),
    municipalityId,
    manifest,
  )
  const zeroModel = specialEducationViewModel.buildSpecialEducationViewModel(readDocument('4300034'))
  const bilingualZero = zeroModel.items.find((item) => item.key === 'educacao-bilingue-surdos')
  assert.equal(bilingualZero.currentValue, 0)
  assert.equal(bilingualZero.currentDisplay, '0')
  assert.equal(bilingualZero.snapshotOnly, true)
  assert.equal(bilingualZero.variationRaw, null)
  assert.equal(bilingualZero.series.filter((point) => point.valor != null).length, 1)

  const saoLeopoldoModel = specialEducationViewModel.buildSpecialEducationViewModel(readDocument('4318705'))
  assert.deepEqual(
    saoLeopoldoModel.items.map((item) => item.key),
    ['educacao-especial-matriculas', 'educacao-especial-inclusao-classes-comuns', 'aee', 'educacao-bilingue-surdos'],
  )
  const observedEnrollment = saoLeopoldoModel.allItems.find((item) => item.key === 'educacao-especial-matriculas')
  assert.equal(observedEnrollment.availableInReferenceYear, true)
  assert.equal(observedEnrollment.currentYear, 2025)
  assert.equal(observedEnrollment.currentValue, 2692)
  assert.equal(observedEnrollment.currentDisplay, '2.692')
  assert.equal(observedEnrollment.series.find((point) => point.ano === 2025).valor, 2692)
  assert.equal(observedEnrollment.series.find((point) => point.ano === 2021).valor, 1468)

  const partialDocument = structuredClone(readDocument('4300034'))
  partialDocument.years.at(-1).cuts.total.specialEducation.enrollments = {
    missingSchools: 1,
    observedSchools: 4,
    reason: 'test-partial',
    sourceId: 'test-partial',
    state: 'partial',
    value: 12,
  }
  const partialModel = specialEducationViewModel.buildSpecialEducationViewModel(partialDocument)
  const partialEnrollment = partialModel.items.find((item) => item.key === 'educacao-especial-matriculas')
  assert.equal(partialEnrollment.currentValue, 12)
  assert.equal(partialEnrollment.currentDisplay, '12')
  assert.equal(partialEnrollment.referencePointState, 'partial')

  const derivedZeroDocument = structuredClone(readDocument('4300034'))
  derivedZeroDocument.years.at(-1).cuts.total.aee.schoolsOfferingAee = {
    sourceId: 'test-derived-zero',
    state: 'derived_zero',
    value: 0,
  }
  const derivedZeroModel = specialEducationViewModel.buildSpecialEducationViewModel(derivedZeroDocument)
  assert.equal(derivedZeroModel.items.find((item) => item.key === 'aee').currentValue, 0)

  const notApplicableDocument = structuredClone(readDocument('4300034'))
  notApplicableDocument.years.at(-1).cuts.total.aee.schoolsOfferingAee = {
    reason: 'test-not-applicable',
    sourceId: 'test-not-applicable',
    state: 'not_applicable',
    value: null,
  }
  const notApplicableModel = specialEducationViewModel.buildSpecialEducationViewModel(notApplicableDocument)
  assert.equal(notApplicableModel.items.some((item) => item.key === 'aee'), false)
  assert.equal(notApplicableModel.allItems.find((item) => item.key === 'aee').currentValue, null)
})

test('os oito recortes mantêm 2025 como referência sem converter indisponibilidade em zero', () => {
  const manifest = specialEducationData.validateSpecialEducationManifest(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'index.json'), 'utf8')),
  )
  const document = specialEducationData.validateSpecialEducationMunicipalDocument(
    JSON.parse(readFileSync(path.join(specialEducationDataDirectory, 'municipios', '4318705.json'), 'utf8')),
    '4318705',
    manifest,
  )
  specialEducationViewModel.SPECIAL_EDUCATION_CUT_OPTIONS.forEach(({ key }) => {
    const series = specialEducationViewModel.buildIndicatorSeries(
      document,
      'educacao-especial-inclusao-classes-comuns',
      key,
    )
    assert.equal(series.length, 12)
    assert.equal(series.at(-1).ano, 2025)
    if (series.at(-1).state === 'partial' || series.at(-1).state === 'unavailable') {
      assert.equal(series.at(-1).valor, null)
    }
  })
})

test('interface especial reutiliza o shell educacional, integra o recorte ao cabeçalho e preserva fonte e impressão', () => {
  const detailSource = readFileSync('src/features/education/components/SpecialEducationDetailView.tsx', 'utf8')
  const headerSource = readFileSync('src/features/education/components/EducationCompactHeader.tsx', 'utf8')
  const shellSource = readFileSync('src/features/education/components/EducationIndicatorDetailShell.tsx', 'utf8')
  const loaderSource = readFileSync('src/data/specialEducation.ts', 'utf8')
  const styles = readFileSync('src/styles/education-pages.css', 'utf8')
  assert.match(detailSource, /EducationIndicatorDetailShell/)
  assert.match(detailSource, /EducationMetricSummary/)
  assert.match(detailSource, /EducationSupportDataSection/)
  assert.match(shellSource, /education-primary-analysis/)
  assert.doesNotMatch(detailSource, /SegmentedControl|special-education-cut-selector/)
  assert.match(detailSource, /resolvedPoints\.length >= 2/)
  assert.match(detailSource, /Situação do indicador em/)
  assert.match(detailSource, /Este indicador não possui valor disponível para 2025 neste município\./)
  assert.match(detailSource, /special-education-reference-state/)
  assert.match(detailSource, /Variação de 2014 a 2025/)
  assert.match(detailSource, /currentYear=\{SPECIAL_EDUCATION_REFERENCE_YEAR\}/)
  assert.match(detailSource, /earlyChildhood:\s*'Educação Infantil'/)
  assert.match(detailSource, /elementary:\s*'Ensino Fundamental'/)
  assert.match(detailSource, /finalYears:\s*'Anos Finais'/)
  assert.match(detailSource, /highSchool:\s*'Ensino Médio'/)
  assert.match(detailSource, /initialYears:\s*'Anos Iniciais'/)
  assert.match(detailSource, /preSchool:\s*'Pré-escola'/)
  assert.match(detailSource, /professional:\s*'Educação Profissional'/)
  assert.match(detailSource, /youthAndAdult:\s*'Educação de Jovens e Adultos'/)
  assert.doesNotMatch(detailSource, /latestResolved/)
  assert.doesNotMatch(detailSource, /source_column_absent|zero_denominator|sourceVariable|normalizedTable/)
  assert.match(detailSource, /Censo Escolar da Educação Básica — INEP/)
  assert.match(headerSource, /aria-haspopup="menu"/)
  assert.match(headerSource, /event\.key !== 'Escape'/)
  assert.match(loaderSource, /contentHash.*normalizedId/)
  assert.match(styles, /education-context-chip__menu-trigger:focus-visible/)
  assert.match(styles, /@media print[\s\S]*education-context-chip__menu[\s\S]*display:\s*none/)
  assert.match(styles, /@media print[\s\S]*education-support-data__item[\s\S]*break-inside:\s*avoid/)
  assert.doesNotMatch(styles, /special-education-cut-control|special-education-cut-selector/)
})

test('loader distingue documento inexistente de conteúdo inválido', async () => {
  const originalFetch = globalThis.fetch
  try {
    higherEducationData.clearHigherEducationDataCache()
    globalThis.fetch = async () => new Response('', { status: 404 })
    await assert.rejects(higherEducationData.loadHigherEducationManifest(), (error) => error instanceof higherEducationData.HigherEducationDataNotFoundError)
    higherEducationData.clearHigherEducationDataCache()
    globalThis.fetch = async () => new Response('{}', { status: 200 })
    await assert.rejects(higherEducationData.loadHigherEducationManifest(), (error) => error instanceof higherEducationData.HigherEducationInvalidDataError)
  } finally {
    higherEducationData.clearHigherEducationDataCache()
    globalThis.fetch = originalFetch
  }
})

test('contratos reais selecionados de Educação Superior passam na validação frontend', () => {
  const manifest = higherEducationValidation.validateHigherEducationManifest(
    JSON.parse(readFileSync('public/data/educacao/superior/index.json', 'utf8')),
  )
  for (const municipalityId of ['4300604', '4300109', '4300034', '4300059']) {
    const document = JSON.parse(readFileSync(`public/data/educacao/superior/municipios/${municipalityId}.json`, 'utf8'))
    assert.equal(
      higherEducationValidation.validateHigherEducationMunicipalDocument(document, municipalityId, manifest).municipality.id,
      municipalityId,
    )
  }
})

test('visão geral municipal preserva zero, ausência e contrato ampliado', () => {
  const base = { year: 2025, sourceId: 'inep', sourceField: 'campo' }
  assert.equal(overviewPresentation.formatSchoolPerformanceRate({ ...base, state: 'observed', value: 0 }), '0,0%')
  assert.equal(overviewPresentation.formatSchoolPerformanceRate({ ...base, state: 'unavailable', value: null }), '—')
  assert.equal(overviewPresentation.formatSchoolPerformanceRate({ ...base, state: 'not_applicable', value: null }), '—')
  assert.equal(overviewLoader.isMunicipalEducationOverviewDocument({
    schemaVersion: 'municipal-education-overview-v1',
    municipality: { idMunicipality: '4319356', name: 'São Pedro da Serra', slug: 'sao-pedro-da-serra' },
    reference: { year: 2025, generatedAt: '2026-07-22T12:00:00-03:00' },
    basicEducationComposition: { components: {} },
    highSchool: { total: { byNetwork: {}, bySchoolLocation: {} }, integratedTechnical: {} },
    specialEducation: {},
    schoolPerformance: { referenceYear: 2025 },
    enrollmentComparison: { years: [2015, 2025], stages: {} },
  }, '4319356'), true)
})

test('agrupa itens na ordem declarada da seção', () => {
  assert.deepEqual(
    selectors.selectEducationSectionItems(indicators, { key: 'x', indicatorKeys: ['a', 'b', 'inexistente'] }).map((item) => item.key),
    ['a', 'b'],
  )
  assert.deepEqual(
    selectors.selectEducationVisibleGroups([{ key: 'g', indicatorKeys: ['b', 'inexistente'] }], indicators)[0].items.map((item) => item.key),
    ['b'],
  )
})

test('busca normalizada, filtragem e ordenação preservam o contrato', () => {
  assert.equal(selectors.normalizeEducationSearch('  ÁLFA  '), 'álfa')
  assert.deepEqual(selectors.filterEducationIndicators(indicators, 'trajetória').map((item) => item.key), ['a'])
  assert.deepEqual(selectors.sortEducationIndicators(indicators).map((item) => item.key), ['a', 'b'])
})

test('indisponibilidade, zero e seleção de detalhe são distintos', () => {
  assert.equal(selectors.isEducationIndicatorAvailable(0), true)
  assert.equal(selectors.isEducationIndicatorAvailable(null), false)
  assert.equal(selectors.isEducationIndicatorAvailable(undefined), false)
  assert.equal(selectors.selectActiveEducationIndicator(indicators, 'a')?.label, 'Álfa')
  assert.equal(selectors.selectActiveEducationIndicator(indicators, 'inexistente'), null)
})

test('view model resolve seção e resumo sem alterar dados', () => {
  const sections = { overview: 'overview', demand: 'demand', methodology: 'methodology' }
  assert.deepEqual(
    viewModels.buildEducationPageViewModel({ indicatorCount: 0, selectedSectionKey: 'demand', sectionKeys: sections }),
    { contextScope: 'Cenários de atendimento escolar', isDemandSection: true, isMethodologySection: false, isOverviewSection: false },
  )
  assert.equal(
    viewModels.buildEducationPageViewModel({ indicatorCount: 1, selectedSectionKey: 'overview', sectionKeys: sections }).contextScope,
    '1 indicador',
  )
})

test('retrato indígena preserva cobertura e os quatro totais oficiais, inclusive zero', () => {
  const items = viewModels.buildIndigenousEducationIndicators({
    ultimo_ano: 2025,
    resumo_ultimo_ano: {
      matriculas: 0,
      estabelecimentos: 0,
      docentes: 0,
      turmas: 0,
    },
    series_totais: {
      matriculas: [{ ano: 2023, valor: 6 }, { ano: 2024, valor: 0 }, { ano: 2025, valor: 0 }],
      estabelecimentos: [{ ano: 2023, valor: 1 }, { ano: 2024, valor: 0 }, { ano: 2025, valor: 0 }],
      docentes: [{ ano: 2023, valor: 1 }, { ano: 2024, valor: 0 }, { ano: 2025, valor: 0 }],
      turmas: [{ ano: 2023, valor: 3 }, { ano: 2024, valor: 0 }, { ano: 2025, valor: 0 }],
    },
    coberturaEstimada: {
      series: {
        2023: { percentage: 12.5, status: 'available' },
        2024: { percentage: 0, status: 'available' },
        2025: { percentage: 0, status: 'available' },
      },
    },
  })

  assert.deepEqual(items.map((item) => item.label), [
    'Cobertura estimada da educação escolar indígena — 4 a 17 anos',
    'Matrículas na educação escolar indígena',
    'Estabelecimentos com oferta de educação escolar indígena',
    'Docentes da educação escolar indígena',
    'Turmas da educação escolar indígena',
  ])
  assert.deepEqual(items.map((item) => item.currentValue), [0, 0, 0, 0, 0])
  assert.equal(items[0].currentDisplay, '0,0%')
  assert.ok(items.slice(1).every((item) => item.currentDisplay === '0'))
  assert.ok(items.every((item) => item.neutralTrend === true))
})

test('indicadores de infraestrutura expõem recortes por rede e localização', () => {
  const rede = {
    infraestrutura: {
      por_rede: [
        { ano: 2025, dependencia: 'municipal', perc_tablet_aluno: 38.2 },
        { ano: 2025, dependencia: 'estadual', perc_tablet_aluno: 51.4 },
      ],
      por_localizacao: [
        { ano: 2025, localizacao: 'urbana', perc_tablet_aluno: 40.1 },
        { ano: 2025, localizacao: 'rural', perc_tablet_aluno: 87.5 },
      ],
    },
  }
  const theme = viewModels.buildPneComplementaryTheme({
    indicadores: null,
    results: {
      tablet_aluno: {
        end_value: 42.5,
        end_year: 2025,
        series: [{ ano: 2019, valor: 16 }, { ano: 2025, valor: 42.5 }],
        value_mode: 'percent',
      },
    },
    rede,
  })
  const tablet = theme?.items.find((item) => item.key === 'tablet_aluno')

  assert.deepEqual(tablet?.explore.map((item) => item.key), [
    'tablet_aluno-por-rede',
    'tablet_aluno-por-localizacao',
  ])
  assert.deepEqual(tablet?.explore.map((item) => item.chartSize), ['large', 'large'])
  assert.equal(tablet?.statusLabel, 'Crescimento')
  assert.equal(tablet?.statusDetail, 'Aumento entre 2019 e 2025')
  assert.deepEqual(tablet?.explore[0].data, [
    { label: 'Municipal', value: 38.2, year: 2025 },
    { label: 'Estadual', value: 51.4, year: 2025 },
  ])
  assert.deepEqual(tablet?.explore[1].data, [
    { label: 'Urbana', value: 40.1, year: 2025 },
    { label: 'Rural', value: 87.5, year: 2025 },
  ])
})

test('contrato canônico de infraestrutura valida os 497 documentos promovidos', () => {
  assert.equal(schoolInfrastructureDocumentFiles.length, 497)
  for (const fileName of schoolInfrastructureDocumentFiles) {
    const document = readEducationDocument(fileName)
    const contract = schoolInfrastructure.getSchoolInfrastructureContractFromDocument(document)
    assert.ok(contract, `${fileName} deve conter o contrato canônico`)
    assert.equal(contract.referenceYear, 2025)
  }
})

test('loader rejeita contrato inválido, remove a falha do cache e aceita nova resposta válida', async () => {
  const validDocument = readEducationDocument()
  const invalidDocument = structuredClone(validDocument)
  invalidDocument.blocos.rede_escolar.infraestrutura.years[0].cuts.total.indicators.internet.denominator = -1
  const originalFetch = globalThis.fetch
  let attempts = 0
  globalThis.fetch = async () => {
    attempts += 1
    return new Response(JSON.stringify(attempts === 1 ? invalidDocument : validDocument), { status: 200 })
  }
  try {
    await assert.rejects(
      educationData.loadEducationMunicipio('fixture-invalid-then-valid'),
      /school-infrastructure-v2 inválido/,
    )
    const loaded = await educationData.loadEducationMunicipio('fixture-invalid-then-valid')
    assert.equal(
      loaded.blocos.rede_escolar.infraestrutura.contractVersion,
      schoolInfrastructure.SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION,
    )
    assert.equal(attempts, 2)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('catálogo de infraestrutura separa 18 indicadores de 14 conteúdos navegáveis', () => {
  const groups = educationCatalog.EDUCATION_SECTION_GROUPS[
    educationCatalog.EDUCATION_SECTION_KEYS.infrastructure
  ]
  const section = educationCatalog.EDUCATION_SECTION_CATALOG.find(
    ({ key }) => key === educationCatalog.EDUCATION_SECTION_KEYS.infrastructure,
  )
  assert.deepEqual(groups.map((group) => group.indicatorKeys.length), [1, 9, 4])
  assert.deepEqual(groups.map((group) => group.indicatorCount), [5, 9, 4])
  assert.equal(groups.flatMap((group) => group.indicatorKeys).length, 14)
  assert.equal(section.indicatorCount, 18)
  assert.equal(section.navigableContentCount, 14)
  assert.deepEqual(groups[0].indicatorKeys, ['infraestrutura-basica'])
  assert.equal(
    groups.flatMap((group) => group.indicatorKeys)
      .some((key) => educationCatalog.SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.includes(key)),
    false,
  )
  assert.equal(
    groups.flatMap((group) => group.indicatorKeys).filter((key) => key === 'internet').length,
    1,
  )

  const sequence = groups.flatMap((group) => group.indicatorKeys)
  assert.equal(new Set(sequence).size, 14)
  assert.deepEqual(sequence, [
    'infraestrutura-basica',
    'internet',
    'internet_alunos',
    'internet_aprendizagem',
    'internet_comunidade',
    'acesso_internet_computador',
    'acesso_internet_disp_pessoais',
    'rede_local',
    'rede_wireless',
    'banda_larga',
    'proposta_pedagogica',
    'desktop_aluno',
    'comp_portatil_aluno',
    'tablet_aluno',
  ])
  assert.equal(sequence.includes('rede-infraestrutura'), false)
  assert.deepEqual(
    educationCatalog.EDUCATION_INDICATOR_CATALOG
      .find(({ key }) => key === 'rede-infraestrutura')
      .sections,
    [],
  )
  assert.equal(
    educationCatalog.resolveEducationNavigation({
      route: 'educacao',
      hashParams: 'secao=infraestrutura&detalhe=rede-infraestrutura',
    }).detailKey,
    'rede-infraestrutura',
  )
  assert.equal(
    sequence.some((key) => educationCatalog.SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.includes(key)),
    false,
  )

  const contents = sequence.map((key) => ({ key, label: key }))
  sequence.forEach((key, index) => {
    const forward = selectors.selectEducationDetailSequence(contents, key)
    assert.equal(forward.activeIndex, index)
    assert.equal(forward.previousItem?.key ?? null, sequence[index - 1] ?? null)
    assert.equal(forward.nextItem?.key ?? null, sequence[index + 1] ?? null)
  })
  ;[...sequence].reverse().forEach((key, reverseIndex) => {
    const backward = selectors.selectEducationDetailSequence(contents, key)
    assert.equal(backward.activeIndex, sequence.length - reverseIndex - 1)
  })
})

test('view model canônico cria o conteúdo composto e preserva Internet histórica', () => {
  const document = readEducationDocument()
  const contract = schoolInfrastructure.getSchoolInfrastructureContractFromDocument(document)
  const theme = viewModels.buildPneComplementaryTheme({
    indicadores: null,
    rede: document.blocos.rede_escolar,
    results: {
      internet: {
        end_value: 10,
        end_year: 2025,
        series: [
          { ano: 2014, valor: 20 },
          { ano: 2024, valor: 30 },
          { ano: 2025, valor: 10 },
        ],
        value_mode: 'percent',
      },
    },
  })
  const canonicalItems = theme.items.filter((item) => item.schoolInfrastructureKey)
  const composite = theme.items.find((item) => item.key === 'infraestrutura-basica')
  const internet = canonicalItems.find((item) => item.key === 'internet')
  const snapshots = canonicalItems.filter((item) => item.key !== 'internet')
  const canonicalInternet = schoolInfrastructure.selectSchoolInfrastructureResult(contract, 'internet')

  assert.equal(canonicalItems.length, 6)
  assert.equal(snapshots.length, 5)
  assert.equal(composite.cardVariant, 'school-infrastructure-composite')
  assert.equal(composite.schoolInfrastructureDimensions.length, 5)
  assert.deepEqual(
    composite.schoolInfrastructureDimensions.map(({ key }) => key),
    educationCatalog.SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER,
  )
  assert.ok(snapshots.every((item) => item.snapshotOnly && item.series.length === 0))
  assert.ok(snapshots.every((item) => item.statusLabel === 'Situação em 2025'))
  assert.deepEqual(internet.series.map((point) => point.ano), [2014, 2024, 2025])
  assert.equal(internet.series.at(-1).valor, canonicalInternet.percentage)
  assert.equal(internet.currentValue, canonicalInternet.percentage)
  assert.equal(canonicalItems.filter((item) => item.key === 'internet').length, 1)
})

test('seletores e formatação preservam recortes, zero real e estados sem denominador', () => {
  const document = readEducationDocument()
  const contract = schoolInfrastructure.getSchoolInfrastructureContractFromDocument(document)
  for (const cut of schoolInfrastructure.SCHOOL_INFRASTRUCTURE_CUT_ORDER) {
    assert.ok(schoolInfrastructure.selectSchoolInfrastructureResult(contract, 'internet', cut))
  }

  const zero = {
    numerator: 0,
    denominator: 2,
    percentage: 0,
    totalActiveSchools: 2,
    observedSchools: 2,
    missingSchools: 0,
    status: 'published',
  }
  const notApplicable = {
    numerator: 0,
    denominator: 0,
    percentage: null,
    totalActiveSchools: 0,
    observedSchools: 0,
    missingSchools: 0,
    status: 'unavailable',
  }
  const unavailable = {
    ...notApplicable,
    totalActiveSchools: 2,
    missingSchools: 2,
  }
  assert.equal(schoolInfrastructure.formatSchoolInfrastructurePercentage(zero), '0,0%')
  assert.equal(schoolInfrastructure.formatSchoolInfrastructureQuantity(zero), '0 de 2')
  assert.equal(schoolInfrastructure.formatSchoolInfrastructureReportCell(zero), '0 de 2 · 0,0%')
  assert.equal(schoolInfrastructure.formatSchoolInfrastructureReportCell(notApplicable), 'Não se aplica')
  assert.equal(schoolInfrastructure.formatSchoolInfrastructureReportCell(unavailable), 'Não disponível')
})

test('interface de infraestrutura usa card composto, página conjunta e apoio responsivo', () => {
  const detailSource = readFileSync(
    path.resolve('src/features/education/components/EducationIndicatorDetailView.tsx'),
    'utf8',
  )
  const cardSource = readFileSync(path.resolve('src/components/EducationIndicatorCard.jsx'), 'utf8')
  const cssSource = readFileSync(path.resolve('src/styles/education-pages.css'), 'utf8')
  const pageSource = readFileSync(path.resolve('src/features/education/EducationPage.tsx'), 'utf8')
  const viewModelSource = readFileSync(path.resolve('src/features/education/educationViewModels.ts'), 'utf8')
  const combinedDetailSource = detailSource.slice(
    detailSource.indexOf('function SchoolInfrastructureCombinedDetail'),
    detailSource.indexOf('function SchoolInfrastructureSupportChart'),
  )

  assert.doesNotMatch(detailSource, /SchoolInfrastructureSnapshotChart/)
  assert.doesNotMatch(detailSource, /SchoolInfrastructureStandardSupportData/)
  assert.doesNotMatch(detailSource, /Com água potável|Sem água potável/)
  assert.match(detailSource, /SchoolInfrastructureCombinedDetail/)
  assert.match(detailSource, /SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER\.map/)
  assert.doesNotMatch(combinedDetailSource, /Dimensão selecionada/)
  assert.doesNotMatch(combinedDetailSource, /aria-pressed|onSelectDimension|selectedDimension/)
  assert.match(detailSource, /Panorama da infraestrutura básica — \$\{contract\.referenceYear\}/)
  assert.match(detailSource, /As cinco dimensões apresentam o mesmo resultado no recorte selecionado\./)
  assert.match(detailSource, /Por rede/)
  assert.match(detailSource, /Por localização/)
  assert.match(detailSource, /school-infrastructure-comparison-table/)
  assert.match(detailSource, /school-infrastructure-comparison-cards/)
  assert.match(detailSource, /Não se aplica/)
  assert.match(detailSource, /Não disponível/)
  assert.match(detailSource, /SchoolInfrastructureSupportData/)
  assert.match(detailSource, /Resultado por rede — \$\{contract\.referenceYear\}/)
  assert.match(detailSource, /Resultado por localização — \$\{contract\.referenceYear\}/)
  assert.match(detailSource, /title="Evolução do indicador"/)
  assert.match(detailSource, /SchoolInfrastructurePanoramaChart results=\{panoramaAvailableResults\}/)
  assert.match(detailSource, /school-infrastructure-panorama-row__label/)
  assert.match(detailSource, /formatSchoolInfrastructureQuantity\(result\)/)
  assert.match(detailSource, /highest = availableResults\.filter/)
  assert.match(detailSource, /lowest = availableResults\.filter/)
  assert.match(detailSource, /value=\{panoramaCoveragePercentage == null \? EM : formatInfrastructureValue\(panoramaCoveragePercentage\)\}/)
  assert.match(detailSource, /Histórico de conectividade e condições escolares/)
  assert.match(cardSource, /SchoolInfrastructureCompositeCard/)
  assert.match(cardSource, /school-infrastructure-composite-card__metrics/)
  assert.match(cardSource, /Abrir panorama/)
  assert.doesNotMatch(cardSource, /onDimensionSelect|aria-pressed/)
  assert.match(cardSource, /indicator\.groupKey === 'equipamentos-recursos'/)
  assert.match(cardSource, /hideContext: isExploratory \|\| isPedagogicalResource/)
  assert.match(cardSource, /modifier: isExploratory[\s\S]*\['panorama-entry', 'panorama-feature'\][\s\S]*isPedagogicalResource[\s\S]*'compact-copy'/)
  assert.equal(
    cardSource.includes('Condições básicas, espaços escolares, conectividade e equipamentos disponíveis nas escolas.'),
    true,
  )
  assert.equal(
    cardSource.includes('Escolas públicas com projeto político-pedagógico'),
    true,
  )
  assert.equal(
    cardSource.includes('Escolas públicas com projeto político-pedagógico ou proposta pedagógica.'),
    true,
  )
  assert.equal(cardSource.includes("'Recursos pedagógicos'"), true)
  assert.match(cssSource, /education-indicator-group--infraestrutura-basica \.education-indicator-card-grid\s*\{[\s\S]*grid-template-columns: minmax\(0, 1fr\)/)
  assert.match(cssSource, /school-infrastructure-composite-card__metrics[\s\S]*repeat\(5/)
  assert.match(cssSource, /school-infrastructure-composite-card__value[\s\S]*font-size: var\(--font-size-3xl\)[\s\S]*tabular-nums/)
  assert.match(cssSource, /school-infrastructure-summary-card > strong[\s\S]*font-size: 30px/)
  assert.match(cssSource, /school-infrastructure-comparison-table-wrap[\s\S]*width: 100%/)
  assert.match(cssSource, /school-infrastructure-comparison-cards[\s\S]*display: none/)
  assert.match(cssSource, /education-indicator-group--rede-escolar \.education-indicator-card-grid[\s\S]*minmax\(0, 1fr\)/)
  assert.match(cssSource, /education-indicator-card--panorama-feature[\s\S]*min-height: 112px !important/)
  assert.match(cssSource, /education-indicator-card--panorama-feature[\s\S]*grid-template-columns: repeat\(12/)
  assert.match(cssSource, /education-indicator-group--equipamentos-recursos \.education-indicator-card-grid[\s\S]*repeat\(4/)
  assert.match(cssSource, /@media \(max-width: 1440px\)[\s\S]*education-indicator-group--equipamentos-recursos[\s\S]*repeat\(3/)
  assert.match(cssSource, /education-indicator-card--compact-copy[\s\S]*font-size: var\(--font-size-sm\)[\s\S]*-webkit-line-clamp: unset/)
  assert.match(cssSource, /education-indicator-card--compact-copy \.indicator-card-shell__description[\s\S]*line-height: 1\.4[\s\S]*-webkit-line-clamp: unset/)
  assert.match(cssSource, /education-indicator-card--compact-copy \.indicator-card-shell__value-row[\s\S]*align-items: flex-start !important[\s\S]*justify-content: flex-start !important/)
  assert.match(cssSource, /education-indicator-card--compact-copy \.indicator-card-shell__value-row strong[\s\S]*max-width: none !important[\s\S]*font-size: var\(--font-size-3xl\) !important[\s\S]*text-overflow: clip !important/)
  assert.match(cssSource, /school-infrastructure-support \.education-support-data__grid[\s\S]*minmax\(0, 3fr\)[\s\S]*minmax\(280px, 2fr\)/)
  assert.match(cssSource, /school-infrastructure-panorama__support \.infra-panorama-grid[\s\S]*repeat\(12/)
  assert.match(cssSource, /infra-panel-group:nth-child\(1\)[\s\S]*span 3/)
  assert.match(cssSource, /infra-panel-group:nth-child\(2\)[\s\S]*span 4/)
  assert.match(cssSource, /infra-panel-group:nth-child\(3\)[\s\S]*span 5/)
  assert.match(cssSource, /@media \(max-width: 1180px\)[\s\S]*school-infrastructure-composite-card__metrics[\s\S]*repeat\(3/)
  assert.match(cssSource, /@media \(max-width: 1180px\)[\s\S]*education-indicator-group--equipamentos-recursos[\s\S]*repeat\(2/)
  assert.match(cssSource, /@media \(max-width: 700px\)[\s\S]*education-indicator-group--infraestrutura-basica[\s\S]*minmax\(0, 1fr\)/)
  assert.match(cssSource, /@media \(max-width: 700px\)[\s\S]*education-indicator-group--equipamentos-recursos[\s\S]*minmax\(0, 1fr\)/)
  assert.match(cssSource, /@media \(max-width: 700px\)[\s\S]*school-infrastructure-comparison-table-wrap[\s\S]*display: none/)
  assert.match(cssSource, /@media \(max-width: 700px\)[\s\S]*school-infrastructure-comparison-cards[\s\S]*display: grid/)
  assert.match(viewModelSource, /key: 'rede-infraestrutura'[\s\S]*mainCutLabel: 'Total'/)
  assert.doesNotMatch(viewModelSource, /key: 'rede-infraestrutura'[\s\S]{0,1400}mainCutLabel: 'Escolas com internet'/)
  assert.match(pageSource, /activeIndicator\.cardVariant === 'exploratory'[\s\S]*activeIndicator\.cardTitle/)
  assert.match(pageSource, /replaceHashContext[\s\S]*detalhe: isLegacyInfrastructureAlias \? 'infraestrutura-basica' : requestedDetailKey[\s\S]*dimensao: null/)
  assert.doesNotMatch(pageSource, /selectedInfrastructureDimension|setSelectedInfrastructureDimension/)
  assert.doesNotMatch(detailSource, /variationStatusLabel/)

  const panoramaSource = detailSource.slice(
    detailSource.indexOf('function InfraDetailPanel'),
    detailSource.indexOf('function applyStageOption'),
  )
  assert.equal((panoramaSource.match(/education-support-data__footer/g) ?? []).length, 1)
})

test('panorama preserva a ordem e os seis rótulos canônicos de infraestrutura básica', () => {
  assert.deepEqual(schoolInfrastructure.SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER, [
    'agua_potavel',
    'energia_eletrica',
    'internet',
    'biblioteca_sala_leitura',
    'quadra_esportes',
    'esgoto_rede_publica',
  ])
  assert.deepEqual(
    schoolInfrastructure.SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.map(
      (key) => schoolInfrastructure.SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].shortLabel,
    ),
    [
      'Água potável',
      'Energia elétrica',
      'Internet',
      'Biblioteca ou sala de leitura',
      'Quadra de esportes',
      'Rede pública de esgoto',
    ],
  )
})

test('relatório usa o contrato canônico, seis linhas e os recortes total e municipal', () => {
  const reportTableSource = readFileSync(
    path.resolve('src/features/education/components/SchoolInfrastructureReportTable.tsx'),
    'utf8',
  )
  const detailSource = readFileSync(
    path.resolve('src/features/education/components/EducationIndicatorDetailView.tsx'),
    'utf8',
  )
  assert.match(reportTableSource, /SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER\.map/)
  assert.match(reportTableSource, /indicatorKey, 'total'/)
  assert.match(reportTableSource, /indicatorKey, 'municipal'/)
  assert.match(reportTableSource, /Bloco C — Infraestrutura/)
  assert.doesNotMatch(`${reportTableSource}${detailSource}`, />\s*(sourceVariable|contractVersion|numerator|denominator)\s*</)
  assert.doesNotMatch(detailSource, /SchoolInfrastructureSnapshotChart|SchoolInfrastructureStandardSupportData/)
  assert.doesNotMatch(reportTableSource, /numerator|denominator/)
})

test('indicadores contextuais descrevem o movimento observado da série', () => {
  const theme = viewModels.buildPneComplementaryTheme({
    indicadores: null,
    results: {
      internet: { end_value: 98.8, end_year: 2025, series: [{ ano: 2015, valor: 91.4 }, { ano: 2025, valor: 98.8 }], value_mode: 'percent' },
      rede_local: { end_value: 80, end_year: 2025, series: [{ ano: 2019, valor: 90 }, { ano: 2025, valor: 80 }], value_mode: 'percent' },
      rede_wireless: { end_value: 60, end_year: 2025, series: [{ ano: 2019, valor: 60 }, { ano: 2025, valor: 60 }], value_mode: 'percent' },
      tablet_aluno: { end_value: 42.5, end_year: 2025, series: [{ ano: 2025, valor: 42.5 }], value_mode: 'percent' },
    },
  })
  const statusByKey = Object.fromEntries(theme?.items.map((item) => [item.key, item.statusLabel]) ?? [])

  assert.equal(statusByKey.internet, 'Crescimento')
  assert.equal(statusByKey.rede_local, 'Redução')
  assert.equal(statusByKey.rede_wireless, 'Estabilidade')
  assert.equal(statusByKey.tablet_aluno, 'Série disponível')
  assert.equal(theme?.items.some((item) => item.statusLabel === 'Contexto'), false)
})

test('navegação educacional resolve seção, detalhe e vizinhança compartilhada', () => {
  assert.deepEqual(
    selectors.getInitialEducationNavigation({
      route: 'educacao',
      hashParams: 'secao=trajetoria&detalhe=fluxo-aprovacao',
      searchParams: '',
    }),
    {
      panoramaTheme: 'fluxo',
      section: 'trajetoria',
      detailKey: 'fluxo-aprovacao',
      shouldApplyTheme: true,
    },
  )
  assert.deepEqual(
    selectors.getInitialEducationNavigation({
      route: 'educacao',
      hashParams: 'secao=modalidades&detalhe=educacao-indigena',
      searchParams: '',
    }),
    {
      panoramaTheme: 'oferta',
      section: 'modalidades',
      detailKey: 'educacao-indigena',
      shouldApplyTheme: true,
    },
  )
  assert.deepEqual(
    selectors.getInitialEducationNavigation({ route: 'outra-rota' }),
    {
      panoramaTheme: 'matriculas',
      section: 'visao-geral',
      detailKey: '',
      shouldApplyTheme: false,
    },
  )

  assert.deepEqual(
    selectors.getInitialEducationNavigation({
      route: 'educacao',
      hashParams: 'secao=infraestrutura&detalhe=agua_potavel',
      searchParams: '',
    }),
    {
      panoramaTheme: 'pne_complementares',
      section: 'infraestrutura',
      detailKey: 'infraestrutura-basica',
      shouldApplyTheme: true,
    },
  )

  const sequence = selectors.selectEducationDetailSequence(indicators, 'a')
  assert.equal(sequence.activeIndex, 1)
  assert.equal(sequence.previousItem?.key, 'b')
  assert.equal(sequence.nextItem, null)
})

test('cards principais preservam zero, ausência, percentuais e série insuficiente', () => {
  const zero = viewModels.createIndicator({
    key: 'fixture-zero',
    label: 'Zero observado',
    themeKey: 'matriculas',
    categories: ['todos'],
    series: [{ ano: 2025, valor: 0 }],
    currentValue: 0,
    formatType: 'number',
  })
  assert.equal(zero.currentDisplay, '0')
  assert.equal(zero.statusLabel, 'Com dados')
  assert.equal(zero.series.length, 1)

  const missing = viewModels.createIndicator({
    key: 'fixture-missing',
    label: 'Ausente',
    themeKey: 'matriculas',
    categories: ['todos'],
    series: [],
    currentValue: null,
    formatType: 'number',
  })
  assert.equal(missing.currentDisplay, '—')
  assert.equal(missing.statusLabel, 'Sem dados')

  const percent = viewModels.createIndicator({
    key: 'fixture-percent',
    label: 'Percentual',
    themeKey: 'fluxo',
    categories: ['todos'],
    series: [{ ano: 2020, valor: 10 }, { ano: 2025, valor: 12 }],
    currentValue: 12,
    formatType: 'percent',
  })
  assert.equal(percent.currentDisplay, '12,0%')
  assert.equal(percent.variationDisplay, '+2 p.p.')
  assert.equal(percent.statusLabel, 'Alta')
})

test('projeção preserva alinhamento entre ano, ausência e população', () => {
  const incompleteProjection = {
    historical_years: [2022, 2023, 2024],
    historical_percent: [51.2, 103.4, null],
    historical_population: [1000, 1010, 1020],
  }

  assert.deepEqual(
    viewModels.buildProjectionHistory({
      historical_years: [2022, 2023, 2024],
      historical_percent: [51.2, null, 54.8],
      historical_population: [1000, 1010, 1020],
    }),
    [
      { year: 2022, value: 51.2, population: 1000 },
      { year: 2023, value: null, population: 1010 },
      { year: 2024, value: 54.8, population: 1020 },
    ],
  )
  assert.deepEqual(
    viewModels.getLatestProjectionObservation(incompleteProjection),
    { year: 2023, value: 103.4, population: 1010 },
  )
  assert.equal(
    viewModels.getLatestProjectionObservation({
      historical_years: [2023, 2024],
      historical_percent: [null, null],
      historical_population: [1010, 1020],
    }),
    null,
  )
  assert.deepEqual(viewModels.buildProjectionHistory(null), [])
})

test('formatadores educacionais preservam fontes, períodos e nomes oficiais', () => {
  assert.equal(formatters.formatIndicatorCount(0), '0 indicadores')
  assert.equal(formatters.formatIndicatorCount(1), '1 indicador')
  assert.equal(formatters.formatSourceYears([]), 'Não disponível para o município')
  assert.equal(formatters.formatSourceYears([2019]), '2019')
  assert.equal(formatters.formatSourceYears([2019, 2021, 2023]), '2019–2023')
  assert.equal(formatters.normalizeEducationIndicatorLabel('Matrículas na EJA'), 'Matrículas na Educação de Jovens e Adultos')
  assert.equal(formatters.normalizeMethodologyId('Como interpretar'), 'como-interpretar')
})

test('busca considera caixa e acentuação declarada sem alterar a ordem de seção', () => {
  assert.deepEqual(selectors.filterEducationIndicators(indicators, '  TRAJETÓRIA ').map((item) => item.key), ['a'])
  assert.deepEqual(
    selectors.selectEducationSectionItems(indicators, { key: 'x', indicatorKeys: ['b', 'a'] }).map((item) => item.key),
    ['b', 'a'],
  )
})

test('regra de publicação usa valores brutos e exclui manutenção, constância e histórico isolado', () => {
  const indicator = {
    kind: 'age_coverage',
    observed: { year: 2025, numerator: 120, denominator: 100, rawValue: 120 },
    historical: [
      { year: 2024, numerator: 110, denominator: 100, rawValue: 110 },
      { year: 2025, numerator: 120, denominator: 100, rawValue: 120 },
    ],
    scenario: {
      type: 'trend_scenario',
      method: 'municipal_base_times_rs_age_factor',
      status: 'available',
      projected: [
        { year: 2026, numerator: 121, denominator: 100, rawValue: 121 },
        { year: 2036, numerator: 130, denominator: 100, rawValue: 130 },
      ],
    },
    reference: { value: 100, year: 2036 },
    diagnostics: { warnings: ['bases distintas'] },
  }

  assert.equal(attendancePresentation.isDisplayableProjection(indicator), true)
  assert.deepEqual(attendancePresentation.toProjectionView(indicator).projected_percent, [100, 100])
  assert.deepEqual(attendancePresentation.toProjectionView(indicator).raw_projected_percent, [121, 130])

  const constant = {
    ...indicator,
    scenario: {
      ...indicator.scenario,
      projected: [
        { year: 2026, rawValue: 120 },
        { year: 2036, rawValue: 120 },
      ],
    },
  }
  assert.equal(attendancePresentation.isDisplayableProjection(constant), false)
  assert.equal(attendancePresentation.isDisplayableProjection({
    ...indicator,
    scenario: { ...indicator.scenario, model: 'last_value' },
  }), false)
  assert.equal(attendancePresentation.isDisplayableProjection({
    ...indicator,
    scenario: { ...indicator.scenario, type: 'maintenance' },
  }), false)
  assert.equal(attendancePresentation.isDisplayableProjection({
    ...indicator,
    scenario: { ...indicator.scenario, projected: [] },
  }), false)
})

test('adaptador preserva projeção, meta explícita e diferença na unidade percentual', () => {
  const view = attendancePresentation.toProjectionView({
    kind: 'age_coverage',
    observed: { year: 2025, rawValue: 70 },
    historical: [{ year: 2024, rawValue: 65 }, { year: 2025, rawValue: 70 }],
    scenario: {
      type: 'trend_scenario',
      method: 'fixture',
      status: 'available',
      projected: [{ year: 2026, rawValue: 72 }, { year: 2036, rawValue: 85 }],
    },
    reference: { value: 90, year: 2036 },
    diagnostics: { warnings: [] },
  })
  assert.equal(view.available, true)
  assert.equal(view.projected_end_year, 2036)
  assert.equal(view.target_percent, 90)
  assert.equal(view.target_year, 2036)
  assert.equal(view.distance_to_target_2036, -5)
})

test('percentual de apresentação trata limite, piso, ausência e valor regular', () => {
  assert.deepEqual(attendancePresentation.toDisplayPercentage(102), {
    displayValue: 100,
    displayWasCapped: true,
    rawValue: 102,
  })
  assert.deepEqual(attendancePresentation.toDisplayPercentage(130.5), {
    displayValue: 100,
    displayWasCapped: true,
    rawValue: 130.5,
  })
  assert.deepEqual(attendancePresentation.toDisplayPercentage(-4), {
    displayValue: 0,
    displayWasCapped: false,
    rawValue: -4,
  })
  assert.deepEqual(attendancePresentation.toDisplayPercentage(null), {
    displayValue: null,
    displayWasCapped: false,
    rawValue: null,
  })
  assert.deepEqual(attendancePresentation.toDisplayPercentage(68.4), {
    displayValue: 68.4,
    displayWasCapped: false,
    rawValue: 68.4,
  })
})

function projectedAttendanceIndicator(indicatorKey, overrides = {}) {
  return {
    indicatorKey,
    kind: 'age_coverage',
    observed: { year: 2025, rawValue: 70 },
    historical: [{ year: 2024, rawValue: 68 }, { year: 2025, rawValue: 70 }],
    scenario: {
      type: 'trend_scenario',
      method: 'fixture',
      status: 'available',
      projected: [{ year: 2026, rawValue: 71 }, { year: 2036, rawValue: 80 }],
    },
    reference: null,
    diagnostics: { warnings: [] },
    ...overrides,
  }
}

test('tempo integral publicável mantém filtro e bloco derivados da mesma coleção', () => {
  const integral = projectedAttendanceIndicator('basico_integral', {
    kind: 'integral_coverage',
    reference: {
      targets: [{ type: 'configured_reference', value: 50, year: 2036 }],
      trajectory: [{ year: 2031, value: 35 }, { year: 2036, value: 50 }],
    },
    scenario: {
      type: 'maintenance',
      method: 'last_components',
      status: 'available',
      projected: [{ year: 2036, rawValue: 70 }],
    },
  })
  const payload = { ageCoverage: {}, integral: { overall: integral } }
  const items = attendanceFilters.getDisplayableAttendanceItems(payload)

  assert.equal(attendancePresentation.isDisplayableProjection(integral), true)
  assert.deepEqual(attendancePresentation.toProjectionView(integral).raw_projected_percent, [35, 50])
  assert.deepEqual(attendanceFilters.getAvailableIndicatorTypes(items), ['integral'])
  assert.equal(attendanceFilters.getVisibleAttendanceItems(items, 'integral', 'overall').length, 1)
})

test('recortes usam ordem fixa e faixas combinadas substituem abrangência geral', () => {
  const keys = [
    'obrigatoria_4_17',
    'basico_15_17',
    'escolar_6_14',
    'creche',
    'basico_6_17',
    'pre_escola',
    'infantil_0_5',
  ]
  const payload = {
    ageCoverage: Object.fromEntries(keys.map((key) => [key, projectedAttendanceIndicator(key)])),
    integral: { overall: null },
  }
  const items = attendanceFilters.getDisplayableAttendanceItems(payload)

  assert.deepEqual(attendanceFilters.getAvailableCuts(items, 'coverage'), [
    'all',
    'infantil',
    'fundamental',
    'medio',
    'combined',
  ])
  assert.equal(attendanceFilters.CUT_LABELS.combined, 'Faixas combinadas')
  assert.deepEqual(
    attendanceFilters.getVisibleAttendanceItems(items, 'coverage', 'combined').map((item) => item.indicator.indicatorKey),
    ['obrigatoria_4_17', 'basico_6_17'],
  )
})

test('grade de métricas acompanha uma, duas, três e quatro células reais', () => {
  assert.equal(attendanceFilters.getMetricGridClass(1), 'metric-grid--one')
  assert.equal(attendanceFilters.getMetricGridClass(2), 'metric-grid--two')
  assert.equal(attendanceFilters.getMetricGridClass(3), 'metric-grid--three')
  assert.equal(attendanceFilters.getMetricGridClass(4), 'metric-grid--four')
})

test('rótulos finais combinam somente pontos brutos coincidentes e afastam os demais', () => {
  const base = {
    chartHeight: 264,
    chartWidth: 640,
    lastProjectedPoint: { value: 100, x: 572, y: 38, year: 2036 },
    metaLine: { labelY: 52, value: 100, y: 38 },
    padding: { bottom: 44, left: 64, right: 68, top: 38 },
  }
  const combined = projectionEndLabels.buildProjectionEndLabelLayout({
    ...base,
    projectedRawValue: 100,
    targetRawValue: 100,
    targetYear: 2036,
  })
  assert.equal(combined.combined, true)
  assert.equal(combined.meta.hidden, true)

  const sameValueDifferentYear = projectionEndLabels.buildProjectionEndLabelLayout({
    ...base,
    projectedRawValue: 100,
    targetRawValue: 100,
    targetYear: 2035,
  })
  assert.equal(sameValueDifferentYear.combined, false)
  assert.ok(Math.abs(sameValueDifferentYear.projected.y - sameValueDifferentYear.meta.y) >= 22)

  const differentValueSameYear = projectionEndLabels.buildProjectionEndLabelLayout({
    ...base,
    projectedRawValue: 100.000001,
    targetRawValue: 100,
    targetYear: 2036,
  })
  assert.equal(differentValueSameYear.combined, false)
  assert.ok(Math.abs(differentValueSameYear.projected.y - differentValueSameYear.meta.y) >= 22)

  const withoutTarget = projectionEndLabels.buildProjectionEndLabelLayout({
    ...base,
    metaLine: null,
    projectedRawValue: 80,
    targetRawValue: null,
    targetYear: null,
  })
  assert.equal(withoutTarget.combined, false)
  assert.equal(withoutTarget.meta, null)
  assert.ok(withoutTarget.projected.x <= base.chartWidth - base.padding.right)
})

test('comparação do PME exige valor, referência e direção válidos', () => {
  const base = {
    kind: 'percentage',
    direction: 'at_least',
    currentValue: 40,
    targetValue: 60,
    numerator: 40,
    denominator: 100,
    effortUnit: 'matrículas',
  }

  assert.equal(
    pmeReferenceTable.calculatePmeEffort({ ...base, targetValue: null }).text,
    pmeReferenceTable.PME_COMPARISON_UNAVAILABLE,
  )
  assert.equal(
    pmeReferenceTable.calculatePmeEffort({ ...base, currentValue: null }).text,
    pmeReferenceTable.PME_COMPARISON_UNAVAILABLE,
  )
  assert.equal(
    pmeReferenceTable.calculatePmeEffort({ ...base, direction: null }).text,
    pmeReferenceTable.PME_COMPARISON_UNAVAILABLE,
  )
})

test('comparação percentual informa diferença em pontos percentuais', () => {
  const effort = pmeReferenceTable.calculatePmeEffort({
    kind: 'percentage',
    direction: 'at_least',
    currentValue: 0,
    targetValue: 33.4,
    numerator: 0,
    denominator: 10,
    effortUnit: 'matrículas',
  })

  assert.equal(effort.text, 'Abaixo da referência — 33,4 pontos percentuais abaixo do valor de referência.')
  assert.equal(effort.quantitativeCalculable, true)
})

test('comparação com direção de redução nomeia o limite máximo', () => {
  const effort = pmeReferenceTable.calculatePmeEffort({
    kind: 'percentage',
    direction: 'at_most',
    currentValue: 40,
    targetValue: 30,
    numerator: 41,
    denominator: 100,
    effortUnit: 'docentes',
  })

  assert.equal(effort.text, 'Acima da referência — 10 pontos percentuais acima do limite de referência.')
  assert.equal(effort.atOrBeyondReference, false)
})

test('valor igual é distinguido de comparação indisponível sem encerrar o ciclo', () => {
  const effort = pmeReferenceTable.calculatePmeEffort({
    kind: 'percentage',
    direction: 'at_least',
    currentValue: 60,
    targetValue: 60,
    numerator: null,
    denominator: null,
  })

  assert.equal(effort.text, pmeReferenceTable.PME_REFERENCE_EQUAL)
  assert.equal(effort.atOrBeyondReference, true)
  assert.equal(effort.quantitativeCalculable, true)
})

test('indicadores qualitativos usam acompanhamento descritivo', () => {
  assert.equal(
    pmeReferenceTable.calculatePmeEffort({
      kind: 'qualitative',
      direction: null,
      currentValue: null,
      targetValue: null,
      qualitativeAchieved: true,
    }).text,
    pmeReferenceTable.PME_DESCRIPTIVE_MONITORING,
  )
  assert.equal(
    pmeReferenceTable.calculatePmeEffort({
      kind: 'qualitative',
      direction: null,
      currentValue: null,
      targetValue: null,
      qualitativeAchieved: false,
    }).text,
    pmeReferenceTable.PME_DESCRIPTIVE_MONITORING,
  )
})

function pmeResult({
  goalId,
  indicatorId,
  order,
  relationshipType = 'direct',
  themeId,
  currentValue = 0,
}) {
  return {
    resultOrder: order,
    goalId,
    indicatorId,
    themeId,
    tier: 'essential',
    priorityOrder: null,
    publicName: `Descrição ${indicatorId}`,
    publicDescription: `Descrição pública ${indicatorId}`,
    relationshipType,
    relationshipReading: '',
    direction: 'at_least',
    current: {
      value: currentValue,
      displayValue: currentValue,
      displayText: `${currentValue.toLocaleString('pt-BR')}%`,
      year: 2025,
      unit: 'percent',
    },
    indicatorReference: {
      value: 60,
      year: 2036,
      direction: 'at_least',
    },
    legalGoal: { deadline: 2036 },
    classification: 'advance',
    remainingGap: 60 - currentValue,
    favorableDifference: currentValue - 60,
    distance: 60 - currentValue,
    sourceIds: ['inep_censo_escolar'],
  }
}

test('tabela do PME agrupa na ordem oficial sem exibir identificadores internos', () => {
  const diagnostic = {
    sources: [{
      id: 'inep_censo_escolar',
      organization: 'Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)',
      publicTitle: 'Censo Escolar',
      period: '2025',
      officialUrl: 'https://example.test/inep',
    }],
    presentation: {
      themes: [
        { id: 'tema-b', order: 2, label: 'Tema B' },
        { id: 'tema-a', order: 1, label: 'Tema A' },
      ],
      resultDefinitions: [],
    },
    goals: [
      { goalId: '2.a', title: 'Meta 2', order: 2, results: [
        pmeResult({ goalId: '2.a', indicatorId: 'segundo', order: 2, themeId: 'tema-b' }),
      ] },
      { goalId: '1.a', title: 'Meta 1', order: 1, results: [
        pmeResult({
          goalId: '1.a',
          indicatorId: 'primeiro',
          order: 1,
          relationshipType: 'partial_component',
          themeId: 'tema-a',
          currentValue: 0,
        }),
      ] },
    ],
  }

  const model = pmeReferenceTable.buildPmeReferenceTableModel(diagnostic, {
    projections: {
      primeiro: {
        historical_years: [2025],
        historical_numerator: [0],
        historical_population: [10],
      },
    },
  })

  assert.deepEqual(model.groups.map((group) => group.label), ['Tema A', 'Tema B'])
  assert.equal(model.groups[0].rows[0].goalLabel, 'Meta 1.a')
  assert.equal(model.groups[0].rows[0].indicatorLabel, 'Descrição primeiro')
  assert.equal(model.groups[0].rows[0].numerator, '0 matrículas')
  assert.equal(model.groups[0].rows[0].relationshipLabel, 'Componente parcial da meta')
})

test('relações contextuais são sinalizadas sem renomear metas do PNE', () => {
  const diagnostic = {
    sources: [],
    presentation: {
      themes: [{ id: 'tema', order: 1, label: 'Tema' }],
      resultDefinitions: [],
    },
    goals: [{
      goalId: '4.a',
      title: 'Meta 4',
      order: 1,
      results: [
        pmeResult({
          goalId: '4.a',
          indicatorId: 'contexto',
          order: 1,
          relationshipType: 'contextual_proxy',
          themeId: 'tema',
        }),
      ],
    }],
  }

  const row = pmeReferenceTable.buildPmeReferenceTableModel(diagnostic).groups[0].rows[0]
  assert.equal(row.relationshipLabel, 'Indicador contextual')
  assert.equal(row.effort.text, pmeReferenceTable.PME_DESCRIPTIVE_MONITORING)
})
