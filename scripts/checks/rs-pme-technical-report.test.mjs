import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import test, { after, before } from 'node:test'
import { tmpdir } from 'node:os'
import { fileURLToPath, pathToFileURL } from 'node:url'
import ts from 'typescript'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
let temporaryDirectory
let buildPmeTechnicalReportData
let resolvePmeTechnicalReportDiagnostic
let validatePmeTechnicalReportIdentity

before(async () => {
  temporaryDirectory = await mkdtemp(path.join(tmpdir(), 'rs-pme-technical-report-'))
  const source = await readFile(path.join(root, 'src/experiences/pme/pmeTechnicalReportData.ts'), 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const runnable = compiled
    .replace(/import \{[^}]*SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION[^}]*\} from ['"][^'"]+['"];?\r?\n/, "const SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION = 'school-infrastructure-v2';\n")
    .replace(/import \{[^}]*buildEducationModel[^}]*buildPneComplementaryTheme[^}]*\} from ['"][^'"]+['"];?\r?\n/, `
      let modelInput; let complementaryInput;
      const buildEducationModel = (blocos) => { modelInput = blocos; return { items: [{ key: 'mat-integral' }] }; };
      const buildPneComplementaryTheme = (input) => { complementaryInput = input; return { items: [{ key: 'internet' }, { key: 'special-item' }] }; };
      export const __captured = () => ({ modelInput, complementaryInput });
    `)
    .replace(/import \{[^}]*isSpecialEducationIndicatorId[^}]*\} from ['"][^'"]+['"];?\r?\n/, "const isSpecialEducationIndicatorId = (key) => key === 'special-item';\n")
  const output = path.join(temporaryDirectory, 'pmeTechnicalReportData.mjs')
  await writeFile(output, runnable, 'utf8')
  const module = await import(pathToFileURL(output).href)
  buildPmeTechnicalReportData = module.buildPmeTechnicalReportData
  buildPmeTechnicalReportData.__captured = module.__captured
  resolvePmeTechnicalReportDiagnostic = module.resolvePmeTechnicalReportDiagnostic
  validatePmeTechnicalReportIdentity = module.validatePmeTechnicalReportIdentity
})

after(async () => { if (temporaryDirectory) await rm(temporaryDirectory, { recursive: true, force: true }) })

test('4313375 mantém a composição de entradas do relatório técnico da Educação', () => {
  const infrastructure = { contractVersion: 'school-infrastructure-v2', referenceYear: 2025 }
  const blocos = { rede_escolar: { infraestrutura: infrastructure }, aprendizagem: { fixture: true } }
  const indicadores = { generated_at: '2026-09-07' }
  const results = { internet: { valor: 91 } }
  const planningScenarios = { population: 'published' }
  const projections = { year: 2036 }
  const output = buildPmeTechnicalReportData({
    education: { id_municipio: '4313375', municipio: 'Nova Santa Rita', blocos },
    indicadores,
    municipioData: {
      id_municipio: '4313375',
      municipio: { populacao: 0 },
      pne_2026_2036: { indicadores: results, cenarios_planejamento: planningScenarios, projecoes: projections },
    },
    specialEducationItems: [{ key: 'special-education' }],
  })
  const captured = buildPmeTechnicalReportData.__captured()

  assert.equal(captured.modelInput, blocos)
  assert.deepEqual(captured.complementaryInput, { indicadores, rede: blocos.rede_escolar, results })
  assert.deepEqual(output.educationItems.map((item) => item.key), ['mat-integral', 'internet', 'special-education'])
  assert.equal(output.schoolInfrastructure, infrastructure)
  assert.equal(output.municipalityPopulation, 0)
  assert.deepEqual(output.pmeReferenceData, { planningScenarios, projections })
  const suppliedDiagnostic = { municipalityId: '4313375', pne2026PublicDiagnostic: { indicators: [] } }
  const loadedDiagnostic = { municipalityId: '4313375', pne2026PublicDiagnostic: { indicators: ['local'] } }
  assert.equal(resolvePmeTechnicalReportDiagnostic(suppliedDiagnostic, loadedDiagnostic), suppliedDiagnostic)
  assert.equal(resolvePmeTechnicalReportDiagnostic(null, loadedDiagnostic), null)
  assert.equal(resolvePmeTechnicalReportDiagnostic(undefined, loadedDiagnostic), loadedDiagnostic)
  assert.equal(validatePmeTechnicalReportIdentity({
    municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' },
    education: { id_municipio: '4313375', municipio: 'Nova Santa Rita', blocos },
    municipioData: { id_municipio: '4313375' },
  }), null)
  assert.match(validatePmeTechnicalReportIdentity({
    municipality: { ibgeCode: '4313375', name: 'Nova Santa Rita', slug: 'nova-santa-rita', stateCode: 'RS' },
    education: { id_municipio: '4314902', municipio: 'Porto Alegre', blocos },
    municipioData: { id_municipio: '4313375' },
  }), /não corresponde/)
})

test('rotas do relatório PME preservam o contexto municipal e objetivo', async () => {
  const routeSource = await readFile(path.join(root, 'src/experiences/pme/PmeTechnicalReport.tsx'), 'utf8')
  const sharedReportSource = await readFile(path.join(root, 'src/features/education/components/MunicipalTechnicalReport.tsx'), 'utf8')
  assert.match(routeSource, /section === 'metodologia' \? 'transparencia' : 'evidencias'/)
  assert.match(routeSource, /financialHref: \(\) => pmeLink\(route, 'financiamento'\)/)
  assert.match(routeSource, /useMunicipioDiagnostic\(diagnostic === undefined \? idMunicipality : null\)/)
  assert.match(routeSource, /pmeDiagnostic=\{resolvedDiagnostic\?\.pne2026PublicDiagnostic \?\? null\}/)
  assert.match(sharedReportSource, /linkOverrides\?: \{[\s\S]*educationHref\?: \(section: string\) => string/)
  assert.match(sharedReportSource, /buildAppHash\('educacao', \{ municipio: municipalitySlug \|\| undefined, secao: section \}\)/)
  assert.match(sharedReportSource, /buildAppHash\(page, \{ municipio: municipalitySlug \|\| undefined \}\)/)

  const pmeRoutes = await readFile(path.join(root, 'src/experiences/pme/pmeRoutes.ts'), 'utf8')
  const compiled = ts.transpileModule(pmeRoutes, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText
  const output = path.join(temporaryDirectory, 'pmeRoutes.mjs')
  await writeFile(output, compiled, 'utf8')
  const { buildPmeHash } = await import(`${pathToFileURL(output).href}?routes`)
  assert.equal(buildPmeHash('financiamento', { municipalityId: '4313375', objectiveId: '8' }), '#financiamento?municipio=4313375&objetivo=8')
})

test('o relatório aceita os slugs históricos sem transformá-los em identidade', async () => {
  const registry = JSON.parse(await readFile(path.join(root, 'config/municipalities/rs.json'), 'utf8'))
  const compatibility = JSON.parse(await readFile(path.join(root, 'config/compatibility/education-municipality-routes/rs.json'), 'utf8'))
  const municipality = registry.municipalities.find((item) => item.ibgeCode === '4300034')
  const historical = JSON.stringify(compatibility)
  assert.match(historical, /aceguá/)
  const input = {
    municipality,
    education: { id_municipio: '4300034', municipio: municipality.name },
    municipioData: { id_municipio: '4300034' },
    specialEducation: { municipality: { code: '4300034', name: municipality.name, slug: 'aceguá' } },
  }
  assert.equal(validatePmeTechnicalReportIdentity(input), null)
  input.specialEducation.municipality.code = '4313375'
  assert.match(validatePmeTechnicalReportIdentity(input), /Educação Especial não corresponde/)
})
