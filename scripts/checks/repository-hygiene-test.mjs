import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { dirname, extname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const tracked = execFileSync('git', ['ls-files', '-z'], {
  cwd: repoRoot,
  encoding: 'utf8',
  maxBuffer: 16 * 1024 * 1024,
}).split('\0').filter(Boolean)

const pythonProjectPath = resolve(repoRoot, 'data_pipeline/pyproject.toml')
const pythonLockPath = resolve(repoRoot, 'data_pipeline/uv.lock')
const retiredRequirementsPath = resolve(repoRoot, 'data_pipeline/requirements.txt')
assert.ok(existsSync(pythonProjectPath), 'Contrato Python ausente: data_pipeline/pyproject.toml.')
assert.ok(existsSync(pythonLockPath), 'Lock Python ausente: data_pipeline/uv.lock.')
assert.ok(
  !existsSync(retiredRequirementsPath),
  'data_pipeline/requirements.txt foi aposentado; use pyproject.toml e uv.lock.',
)

const trackedPythonEnvironments = tracked.filter((path) => (
  /(?:^|\/)(?:\.venv|venv|\.uv-cache|uv-cache|__pycache__|\.pytest_cache)(?:\/|$)/i.test(path)
  || /\.py[co]$/i.test(path)
))
assert.deepEqual(
  trackedPythonEnvironments,
  [],
  `Ambientes ou caches Python/uv rastreados:\n${trackedPythonEnvironments.join('\n')}`,
)

const misplacedPythonContracts = tracked.filter((path) => (
  /^(?:public\/data|data_pipeline\/data)\//.test(path)
  && /(?:^|\/)(?:pyproject\.toml|uv\.lock|requirements\.txt)$/.test(path)
))
assert.deepEqual(
  misplacedPythonContracts,
  [],
  `Contratos do ambiente Python não pertencem às árvores de dados:\n${misplacedPythonContracts.join('\n')}`,
)

const retiredFinanceContractName = ['MunicipalFinance', 'PrototypeDocumentV1'].join('')
const retiredFinanceMethodology = ['municipal-finance', 'p5a-v1'].join('-')
const retiredOperationalResearchPaths = [
  ['data_pipeline', 'scripts', 'audit_pne_director_selection.py'].join('/'),
  ['data_pipeline', 'scripts', 'audit_pne_inec_connectivity.py'].join('/'),
  ['data_pipeline', 'src', 'education_attendance_projection_experiment.py'].join('/'),
  ['data_pipeline', 'scripts', 'run_education_attendance_projection_experiment.py'].join('/'),
]

const forbiddenTracked = [
  /^(?:artifacts|outputs|dist|coverage|playwright-report|test-results|screenshots|inspection)\//i,
  /^data_pipeline\/(?:cache|export)\//i,
  /(?:^|\/)(?:debug|screenshots?|inspection)(?:\/|$)/i,
  /\.(?:log|tmp|bak|pyc|pyo)$/i,
]

const violations = tracked.filter((path) => forbiddenTracked.some((pattern) => pattern.test(path)))
assert.deepEqual(violations, [], `Arquivos temporários rastreados:\n${violations.join('\n')}`)

assert.ok(
  !existsSync(resolve(repoRoot, 'public/data/municipios.json')),
  'O agregado municipal interno não pode voltar ao contrato público.',
)

const productionCodeFiles = tracked.filter((path) => (
  (
    path.startsWith('src/')
    || path.startsWith('data_pipeline/src/')
    || path.startsWith('data_pipeline/scripts/')
    || path.startsWith('scripts/checks/')
  )
  && ['.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'].includes(extname(path))
  && path !== 'scripts/checks/repository-hygiene-test.mjs'
))
const repositoryCodeFiles = tracked.filter((path) => (
  ['.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'].includes(extname(path))
  && path !== 'scripts/checks/repository-hygiene-test.mjs'
))
const retiredFinanceContractReferences = repositoryCodeFiles.filter((path) => {
  const source = readFileSync(resolve(repoRoot, path), 'utf8')
  return source.includes(retiredFinanceContractName)
    || source.includes(retiredFinanceMethodology)
})
assert.deepEqual(
  retiredFinanceContractReferences,
  [],
  `Contrato financeiro P5-A aposentado voltou ao código de produção:\n${retiredFinanceContractReferences.join('\n')}`,
)

const trackedRetiredResearchPaths = retiredOperationalResearchPaths.filter((path) => (
  tracked.includes(path)
))
assert.deepEqual(
  trackedRetiredResearchPaths,
  [],
  `Caminhos operacionais aposentados voltaram a ser rastreados:\n${trackedRetiredResearchPaths.join('\n')}`,
)

const researchDependencyPattern = /(?:\b(?:from|import)\s+(?:data_pipeline\.)?research\b|\b(?:data_pipeline\.)?research\.(?:projections|audits)\b|(?:data_pipeline[\\/])?research[\\/](?:projections|audits)\b)/m
const productionResearchReferences = productionCodeFiles.filter((path) => (
  researchDependencyPattern.test(readFileSync(resolve(repoRoot, path), 'utf8'))
))
assert.deepEqual(
  productionResearchReferences,
  [],
  `Produção não pode importar nem executar código de pesquisa:\n${productionResearchReferences.join('\n')}`,
)

const researchFileNames = new Set([
  'audit_pne_director_selection.py',
  'audit_pne_inec_connectivity.py',
  'education_attendance_projection_experiment.py',
  'run_education_attendance_projection_experiment.py',
])
const publicResearchFiles = tracked.filter((path) => (
  path.startsWith('public/data/')
  && (
    /(?:^|\/)research(?:\/|$)/.test(path)
    || researchFileNames.has(path.split('/').at(-1))
  )
))
assert.deepEqual(
  publicResearchFiles,
  [],
  `Arquivos de pesquisa não podem ser publicados em public/data:\n${publicResearchFiles.join('\n')}`,
)

const productionSourceFiles = tracked.filter(
  (path) => path.startsWith('src/') && ['.js', '.jsx', '.ts', '.tsx'].includes(extname(path)),
)

const municipalityIdentityPaths = [
  'src/config/stateConfig.ts',
  'src/context/MunicipalityContext.tsx',
  'src/domain/municipalityRegistry.ts',
  'src/domain/municipalityRouting.ts',
  'src/domain/municipalitySelectorModel.ts',
  'src/domain/municipalityStorage.ts',
  'src/hooks/useInitialAppData.ts',
  'src/hooks/useMunicipioData.ts',
  'src/components/MunicipalitySelector.tsx',
]
for (const path of municipalityIdentityPaths) {
  assert.ok(existsSync(resolve(repoRoot, path)), `Módulo da identidade municipal ausente: ${path}.`)
}

const stateConfigPath = resolve(repoRoot, 'config/states/rs.json')
assert.ok(existsSync(stateConfigPath), 'Configuração estadual canônica ausente: config/states/rs.json.')
const stateConfig = JSON.parse(readFileSync(stateConfigPath, 'utf8'))
assert.deepEqual(
  stateConfig,
  {
    schemaVersion: 'state-config-v1',
    stateCode: 'RS',
    stateName: 'Rio Grande do Sul',
    municipalityIbgePrefix: '43',
    expectedMunicipalityCount: 497,
    locale: 'pt-BR',
  },
  'A configuração estadual do RS divergiu do contrato state-config-v1.',
)

const municipalityRegistryPath = resolve(repoRoot, 'config/municipalities/rs.json')
assert.ok(
  existsSync(municipalityRegistryPath),
  'Registro municipal canônico ausente: config/municipalities/rs.json.',
)
const municipalityRegistry = JSON.parse(readFileSync(municipalityRegistryPath, 'utf8'))
assert.deepEqual(
  Object.keys(municipalityRegistry).toSorted(),
  ['municipalities', 'municipalityCount', 'schemaVersion', 'stateCode'],
  'Registro municipal canônico contém campos inesperados.',
)
assert.equal(municipalityRegistry.schemaVersion, 'municipality-registry-v1')
assert.equal(municipalityRegistry.stateCode, stateConfig.stateCode)
assert.equal(municipalityRegistry.municipalityCount, stateConfig.expectedMunicipalityCount)
assert.ok(Array.isArray(municipalityRegistry.municipalities))
assert.equal(
  municipalityRegistry.municipalities.length,
  municipalityRegistry.municipalityCount,
)
const registryIds = []
const registrySlugs = []
for (const [index, municipality] of municipalityRegistry.municipalities.entries()) {
  assert.deepEqual(
    Object.keys(municipality).toSorted(),
    ['ibgeCode', 'name', 'slug'],
    `Registro municipal na posição ${index + 1} contém campos inesperados.`,
  )
  assert.match(
    municipality.ibgeCode,
    new RegExp(`^${stateConfig.municipalityIbgePrefix}\\d{5}$`),
    `Código IBGE inválido no registro: ${municipality.ibgeCode}.`,
  )
  assert.equal(typeof municipality.name, 'string')
  assert.ok(municipality.name.trim(), `Nome municipal vazio em ${municipality.ibgeCode}.`)
  assert.equal(typeof municipality.slug, 'string')
  assert.ok(municipality.slug.trim(), `Slug municipal vazio em ${municipality.ibgeCode}.`)
  registryIds.push(municipality.ibgeCode)
  registrySlugs.push(municipality.slug.toLocaleLowerCase('pt-BR'))
}
assert.equal(new Set(registryIds).size, municipalityRegistry.municipalityCount)
assert.equal(new Set(registrySlugs).size, municipalityRegistry.municipalityCount)

const publicMunicipalityIndexPath = resolve(repoRoot, 'public/data/municipios_index.json')
const publicMunicipalityIndex = JSON.parse(
  readFileSync(publicMunicipalityIndexPath, 'utf8'),
)
assert.deepEqual(
  publicMunicipalityIndex,
  {
    generated_at: publicMunicipalityIndex.generated_at,
    total_municipios: municipalityRegistry.municipalityCount,
    municipios: municipalityRegistry.municipalities.map((municipality) => ({
      nome: municipality.name,
      id_municipio: municipality.ibgeCode,
      slug: municipality.slug,
      path: `/data/municipios/${municipality.ibgeCode}/index.json`,
    })),
  },
  'municipios_index.json deve ser exatamente a projeção pública do registro canônico.',
)

const educationRouteCompatibilityPath = resolve(
  repoRoot,
  'config/compatibility/education-municipality-routes/rs.json',
)
assert.ok(
  existsSync(educationRouteCompatibilityPath),
  'A compatibilidade versionada das rotas municipais da Educação não pode desaparecer.',
)
const educationRouteCompatibility = JSON.parse(
  readFileSync(educationRouteCompatibilityPath, 'utf8'),
)
assert.deepEqual(
  Object.keys(educationRouteCompatibility).toSorted(),
  ['schemaVersion', 'slugOverrides', 'stateCode'],
  'A compatibilidade educacional não pode incorporar cadastro ou dados analíticos.',
)
assert.equal(
  educationRouteCompatibility.schemaVersion,
  'education-municipality-route-compat-v1',
)
assert.equal(educationRouteCompatibility.stateCode, stateConfig.stateCode)
assert.equal(typeof educationRouteCompatibility.slugOverrides, 'object')
assert.ok(!Array.isArray(educationRouteCompatibility.slugOverrides))

const publicEducationMunicipalityIndex = JSON.parse(
  readFileSync(resolve(repoRoot, 'public/data/educacao/municipios_index.json'), 'utf8'),
)
assert.deepEqual(
  Object.keys(publicEducationMunicipalityIndex),
  ['municipios'],
  'O índice educacional não pode voltar a definir um cadastro paralelo.',
)
assert.equal(
  publicEducationMunicipalityIndex.municipios.length,
  municipalityRegistry.municipalityCount,
)
const registryById = new Map(
  municipalityRegistry.municipalities.map((municipality) => [
    municipality.ibgeCode,
    municipality,
  ]),
)
const expectedEducationOverrides = publicEducationMunicipalityIndex.municipios
  .filter((municipality) => (
    registryById.get(municipality.id_municipio)?.slug !== municipality.slug
  ))
  .map((municipality) => [municipality.id_municipio, municipality.slug])
  .toSorted(([left], [right]) => left.localeCompare(right))
const configuredEducationOverrides = Object.entries(
  educationRouteCompatibility.slugOverrides,
).toSorted(([left], [right]) => left.localeCompare(right))
assert.equal(expectedEducationOverrides.length, 182)
assert.deepEqual(
  configuredEducationOverrides,
  expectedEducationOverrides,
  'Os overrides devem coincidir exatamente com as divergências públicas atuais.',
)
for (const [municipalityId, publicSlug] of configuredEducationOverrides) {
  assert.match(municipalityId, /^\d{7}$/, 'Código de override deve permanecer texto.')
  const canonical = registryById.get(municipalityId)
  assert.ok(canonical, `Override órfão: ${municipalityId}.`)
  assert.equal(typeof publicSlug, 'string')
  assert.ok(publicSlug.trim(), `Override vazio: ${municipalityId}.`)
  assert.notEqual(publicSlug, canonical.slug, `Override redundante: ${municipalityId}.`)
}
const resultingEducationSlugs = municipalityRegistry.municipalities.map((municipality) => (
  educationRouteCompatibility.slugOverrides[municipality.ibgeCode] ?? municipality.slug
)).map((slug) => slug.toLocaleLowerCase('pt-BR'))
assert.equal(
  new Set(resultingEducationSlugs).size,
  municipalityRegistry.municipalityCount,
  'Slugs públicos educacionais resultantes devem ser únicos.',
)
for (const [position, municipality] of publicEducationMunicipalityIndex.municipios.entries()) {
  assert.deepEqual(
    Object.keys(municipality),
    ['id_municipio', 'municipio', 'slug', 'caminho'],
    `Índice educacional na posição ${position + 1} contém aliases ou campos inesperados.`,
  )
  const canonical = registryById.get(municipality.id_municipio)
  assert.ok(canonical, `Índice educacional contém código desconhecido: ${municipality.id_municipio}.`)
  assert.equal(municipality.municipio, canonical.name)
  assert.equal(
    municipality.caminho,
    `educacao/municipios/${municipality.id_municipio}.json`,
  )
}

const municipalityContextSource = readFileSync(
  resolve(repoRoot, 'src/context/MunicipalityContext.tsx'),
  'utf8',
)
assert.doesNotMatch(
  municipalityContextSource,
  /\b(?:MunicipioName|selectedMunicipio|setSelectedMunicipio)\b/,
  'MunicipalityContext não pode voltar a armazenar ou selecionar pelo nome.',
)
assert.match(
  municipalityContextSource,
  /selectedMunicipalityId\s*:\s*MunicipalityId\s*\|\s*null/,
  'MunicipalityContext deve manter o código IBGE como identidade da seleção.',
)

const municipalityStorageSource = readFileSync(
  resolve(repoRoot, 'src/domain/municipalityStorage.ts'),
  'utf8',
)
const municipalityFrontendSourceFiles = Array.from(new Set([
  ...productionSourceFiles,
  ...municipalityIdentityPaths,
]))
const legacyMunicipalityStorageReferences = municipalityFrontendSourceFiles.filter((path) => (
  existsSync(resolve(repoRoot, path))
  && readFileSync(resolve(repoRoot, path), 'utf8').includes('pne_dashboard_municipio')
))
assert.deepEqual(
  legacyMunicipalityStorageReferences,
  ['src/domain/municipalityStorage.ts'],
  'A chave municipal antiga só pode ser referenciada pelo módulo de migração.',
)
assert.doesNotMatch(
  municipalityStorageSource,
  /(?:safeSet|setItem)\s*\(\s*(?:storage\s*,\s*)?LEGACY_MUNICIPALITY_STORAGE_KEY/,
  'A aplicação não pode voltar a gravar na chave municipal antiga.',
)
assert.match(
  municipalityStorageSource,
  /JSON\.stringify\([\s\S]*stateCode[\s\S]*municipalityId/,
  'O armazenamento municipal versionado deve serializar stateCode e municipalityId.',
)

const useMunicipioDataSource = readFileSync(
  resolve(repoRoot, 'src/hooks/useMunicipioData.ts'),
  'utf8',
)
assert.doesNotMatch(
  useMunicipioDataSource,
  /\bmunicipiosIndex\b|\bMunicipioName\b|\.nome\b/,
  'useMunicipioData deve carregar diretamente pelo código, sem lookup por nome.',
)
assert.match(
  useMunicipioDataSource,
  /loadMunicipioData\(selectedMunicipalityId\)/,
  'useMunicipioData deve determinar o arquivo pelo código IBGE selecionado.',
)

const municipalitySelectorSource = readFileSync(
  resolve(repoRoot, 'src/components/MunicipalitySelector.tsx'),
  'utf8',
)
assert.doesNotMatch(
  municipalitySelectorSource,
  /\bselectedMunicipio\b|\bmunicipios\s*:/,
  'MunicipalitySelector não pode expor o contrato antigo baseado em nomes.',
)
assert.match(
  municipalitySelectorSource,
  /onChange\(municipality\.ibgeCode\)/,
  'MunicipalitySelector deve retornar código IBGE.',
)
assert.ok(
  !tracked.includes('src/components/MunicipalitySelector.jsx')
  && !existsSync(resolve(repoRoot, 'src/components/MunicipalitySelector.jsx')),
  'MunicipalitySelector.jsx foi movido e não pode voltar a ser rastreado.',
)

const initialAppDataSource = readFileSync(resolve(repoRoot, 'src/hooks/useInitialAppData.ts'), 'utf8')
const initialAppDataTypesSource = readFileSync(resolve(repoRoot, 'src/types/data.ts'), 'utf8')
const initialAppDataContractSource = initialAppDataTypesSource.split('export type InitialAppData', 2)[1] ?? ''
assert.doesNotMatch(
  `${initialAppDataSource}\n${initialAppDataContractSource}`,
  /\b(?:municipios|municipiosIndex)\s*:/,
  'InitialAppData não pode manter listas municipais paralelas.',
)

const identityCountDuplicates = municipalityIdentityPaths.filter((path) => (
  /\b497\b/.test(readFileSync(resolve(repoRoot, path), 'utf8'))
))
assert.deepEqual(
  identityCountDuplicates,
  [],
  'A camada frontend de identidade deve obter a quantidade municipal da configuração estadual.',
)

const municipalityNumberCoercions = municipalityFrontendSourceFiles.filter((path) => (
  /(?:Number|parseInt)\s*\([^)]*\b(?:id_municipio|municipalityId|ibgeCode)\b/.test(
    readFileSync(resolve(repoRoot, path), 'utf8'),
  )
))
assert.deepEqual(
  municipalityNumberCoercions,
  [],
  `Código municipal convertido para number no frontend:\n${municipalityNumberCoercions.join('\n')}`,
)

const retiredMunicipalityLoaderReferences = productionSourceFiles.filter((path) => (
  /\/data\/municipios\.json/.test(readFileSync(resolve(repoRoot, path), 'utf8'))
))
assert.deepEqual(
  retiredMunicipalityLoaderReferences,
  [],
  `Código de produção carrega /data/municipios.json:\n${retiredMunicipalityLoaderReferences.join('\n')}`,
)

const retiredInequalityLoaderReferences = productionSourceFiles.filter((path) => {
  const source = readFileSync(resolve(repoRoot, path), 'utf8')
  return /\bloadMunicipioInequality\b/.test(source)
    || /\/data\/municipios\/[^\s'"`]+\/diagnostico\.json/.test(source)
})
assert.deepEqual(
  retiredInequalityLoaderReferences,
  [],
  `Código de produção usa o loader municipal de desigualdade aposentado:\n${retiredInequalityLoaderReferences.join('\n')}`,
)

const cyclePageSource = readFileSync(resolve(repoRoot, 'src/pages/CyclePage.jsx'), 'utf8')
assert.match(
  cyclePageSource,
  /municipioDetails\?\._shared\?\.municipal_inequality/,
  'CyclePage deve obter o piloto do details.json já carregado.',
)
assert.match(
  cyclePageSource,
  /inequalityPilotLoading[\s\S]*municipioDetailsLoading/,
  'O piloto deve reutilizar o estado de carregamento de details.json.',
)
const indicatorDetailSource = readFileSync(
  resolve(repoRoot, 'src/components/IndicatorDetail.jsx'),
  'utf8',
)
assert.match(
  indicatorDetailSource,
  /item\?\.key === 'basico_integral'[\s\S]*InequalityPilotSection/,
  'basico_integral deve continuar renderizando os estados do piloto.',
)

const packageJsonSource = readFileSync(resolve(repoRoot, 'package.json'), 'utf8')
const packageJsonWithoutCurrentCatalog = packageJsonSource.replaceAll('municipios_index.json', '')
assert.doesNotMatch(
  packageJsonWithoutCurrentCatalog,
  /municipios\.json/,
  'package.json não pode declarar municipios.json como catálogo público.',
)
const packageJson = JSON.parse(packageJsonSource)
assert.equal(
  packageJson.scripts?.['test:municipality-identity'],
  'node --test --test-concurrency=1 scripts/checks/municipality-identity.test.mjs',
  'A suíte permanente de identidade municipal deve permanecer exposta no package.json.',
)
const expectedUvPythonScripts = [
  'test:python',
  'check:python-deps',
  'update:education-data',
  'update:education-data:fingerprint-shadow',
  'update:education-data:incremental',
  'update:indigenous-coverage',
  'update:data',
  'update:data:skip-build',
  'verify:indicator',
  'validate:details',
  'test:pipeline-state-config',
  'test:pipeline-education-state',
  'test:pipeline-education-fingerprint',
]
for (const name of expectedUvPythonScripts) {
  const command = String(packageJson.scripts?.[name] ?? '')
  assert.ok(command, `Script Python obrigatório ausente: ${name}.`)
  const pythonSegments = command.split(/\s*&&\s*/).filter((segment) => /\bpython(?:\.exe)?\b/.test(segment))
  assert.ok(pythonSegments.length > 0, `${name} deve executar Python pelo ambiente uv.`)
  for (const segment of pythonSegments) {
    assert.match(
      segment,
      /^uv\s+run\s+--project\s+data_pipeline(?:\s+--(?:group\s+\S+|frozen|locked|no-default-groups))*\s+python(?:\.exe)?\b/,
      `${name} contém comando Python operacional fora de uv run --project data_pipeline.`,
    )
  }
}
assert.match(
  String(packageJson.scripts?.['python:sync'] ?? ''),
  /^uv\s+sync\s+--project\s+data_pipeline\s+--group\s+test\s+--frozen$/,
  'python:sync deve sincronizar o grupo test sem alterar o lock.',
)
assert.match(
  String(packageJson.scripts?.['python:lock:check'] ?? ''),
  /^uv\s+lock\s+--project\s+data_pipeline\s+--check$/,
  'python:lock:check deve validar o lock canônico.',
)
const directOperationalPython = Object.entries(packageJson.scripts ?? {})
  .filter(([, command]) => /(?:^|\s)(?:python(?:\.exe)?|py(?:\.exe)?)(?=\s)/i.test(String(command)))
  .flatMap(([name, command]) => String(command).split(/\s*&&\s*/)
    .filter((segment) => /(?:^|\s)(?:python(?:\.exe)?|py(?:\.exe)?)(?=\s)/i.test(segment))
    .filter((segment) => !/^uv\s+run\s+--project\s+data_pipeline\b/.test(segment))
    .map((segment) => `${name}: ${segment}`))
assert.deepEqual(
  directOperationalPython,
  [],
  `Comandos Python operacionais fora do uv no package.json:\n${directOperationalPython.join('\n')}`,
)
const researchUpdateScripts = Object.entries(packageJson.scripts ?? {})
  .filter(([name, command]) => (
    /^update(?::|$)/.test(name)
    && researchDependencyPattern.test(String(command))
  ))
  .map(([name]) => name)
assert.deepEqual(
  researchUpdateScripts,
  [],
  `Scripts de atualização do package.json não podem executar pesquisa:\n${researchUpdateScripts.join('\n')}`,
)
const missingScriptFiles = []
for (const [name, command] of Object.entries(packageJson.scripts ?? {})) {
  const candidates = String(command).match(/[A-Za-z0-9_./-]+\.(?:cjs|mjs|js|py)(?=\s|$)/g) ?? []
  for (const candidate of candidates) {
    const absolute = resolve(repoRoot, candidate)
    if (!existsSync(absolute)) missingScriptFiles.push(`${name}: ${candidate}`)
  }
}
assert.deepEqual(
  missingScriptFiles,
  [],
  `Scripts do package.json apontam para arquivos ausentes:\n${missingScriptFiles.join('\n')}`,
)

const canonicalDocs = [
  'README.md',
  'PRODUCT.md',
  'docs/ARQUITETURA.md',
  'docs/DESIGN.md',
  'docs/METODOLOGIA.md',
  'docs/OPERACAO.md',
]
const brokenLinks = []
const retiredCatalogDocDeclarations = []
for (const document of canonicalDocs) {
  const absoluteDocument = resolve(repoRoot, document)
  assert.ok(existsSync(absoluteDocument), `Documento canônico ausente: ${document}`)
  const markdown = readFileSync(absoluteDocument, 'utf8')
  for (const paragraph of markdown.split(/\r?\n\s*\r?\n/)) {
    const withoutCurrentCatalog = paragraph.replaceAll('municipios_index.json', '')
    if (!/municipios\.json/i.test(withoutCurrentCatalog)) continue
    if (!/(?:staging|agregado interno|catálogo interno|não faz parte do contrato público)/i.test(paragraph)) {
      retiredCatalogDocDeclarations.push(document)
    }
  }
  for (const match of markdown.matchAll(/\[[^\]]*]\(([^)]+)\)/g)) {
    const rawTarget = match[1].trim().replace(/^<|>$/g, '').split('#', 1)[0]
    if (!rawTarget || /^(?:https?:|mailto:)/i.test(rawTarget)) continue
    const target = resolve(dirname(absoluteDocument), decodeURIComponent(rawTarget))
    if (!existsSync(target)) brokenLinks.push(`${document}: ${match[1]}`)
  }
}
assert.deepEqual(brokenLinks, [], `Links locais quebrados:\n${brokenLinks.join('\n')}`)
assert.deepEqual(
  retiredCatalogDocDeclarations,
  [],
  `Documentos canônicos tratam municipios.json como catálogo público:\n${retiredCatalogDocDeclarations.join('\n')}`,
)

const pnePublicationRoot = resolve(repoRoot, 'public/data/pne2026-diagnostic-v3')
const activePointer = JSON.parse(
  readFileSync(resolve(pnePublicationRoot, 'current.json'), 'utf8'),
)
const releaseNames = readdirSync(resolve(pnePublicationRoot, 'releases'), {
  withFileTypes: true,
})
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .toSorted()
assert.deepEqual(
  releaseNames,
  [activePointer.releaseId],
  'A publicação PNE deve manter somente a release ativa.',
)

const municipalRoot = resolve(repoRoot, 'public/data/municipios')
const municipalityIds = readdirSync(municipalRoot, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && /^\d{7}$/.test(entry.name))
  .map((entry) => entry.name)
  .toSorted()
assert.deepEqual(
  municipalityIds,
  registryIds.toSorted(),
  'Diretórios municipais públicos devem coincidir exatamente com o registro canônico.',
)
const trackedMunicipalDiagnostics = tracked.filter((path) => (
  /^public\/data\/municipios\/\d{7}\/diagnostico\.json$/.test(path)
  && existsSync(resolve(repoRoot, path))
))
assert.deepEqual(
  trackedMunicipalDiagnostics,
  [],
  `diagnostico.json municipal aposentado ainda está rastreado:\n${trackedMunicipalDiagnostics.join('\n')}`,
)
for (const municipalityId of municipalityIds) {
  assert.ok(
    !existsSync(resolve(municipalRoot, municipalityId, 'diagnostico.json')),
    `${municipalityId}: diagnostico.json municipal aposentado ainda existe.`,
  )
  const details = JSON.parse(
    readFileSync(resolve(municipalRoot, municipalityId, 'details.json'), 'utf8'),
  )
  assert.ok(
    details._shared?.privadas_conveniadas,
    `${municipalityId}: _shared.privadas_conveniadas ausente.`,
  )
  const diagnostic = details._shared?.municipal_inequality
  assert.equal(
    diagnostic?.schemaVersion,
    'municipal-inequality-v1',
    `${municipalityId}: desigualdade municipal incorporada fora do contrato.`,
  )
  assert.deepEqual(
    Object.keys(diagnostic).toSorted(),
    ['generatedAt', 'inequalityPilot', 'municipality', 'schemaVersion'],
    `${municipalityId}: documento municipal incorporado contém blocos inesperados.`,
  )
  assert.equal(diagnostic.municipality?.id, municipalityId)
  assert.ok(diagnostic.municipality?.name)
  assert.equal(diagnostic.inequalityPilot?.indicatorId, 'basico_integral')
}

const partitionSource = readFileSync(
  resolve(repoRoot, 'data_pipeline/scripts/partition_static_data.py'),
  'utf8',
)
assert.doesNotMatch(
  partitionSource,
  /diagnostico\.json|desigualdade_por_municipio\.json|build_partitioned_inequality_document/,
  'O particionamento não pode recriar o artefato municipal aposentado.',
)
assert.doesNotMatch(
  partitionSource,
  /extract_fundeb_id|\bslugify\b|\bunique_slugs\b|\bcanonical_id\b/,
  'O particionamento não pode descobrir identidade pelo Fundeb nem recriar slug municipal.',
)

const exportSource = readFileSync(
  resolve(repoRoot, 'data_pipeline/scripts/export_static_data.py'),
  'utf8',
)
assert.doesNotMatch(
  exportSource,
  /desigualdade_por_municipio\.json|_export_inequality_documents/,
  'O exportador não pode recriar o placeholder municipal aposentado.',
)

const updateSource = readFileSync(
  resolve(repoRoot, 'data_pipeline/scripts/update_static_data.py'),
  'utf8',
)
assert.doesNotMatch(
  updateSource,
  researchDependencyPattern,
  'update_static_data.py não pode importar nem executar código de pesquisa.',
)

const migratedPipelineSources = new Map([
  ['data_pipeline/src/pne_macro_ingestion.py', readFileSync(
    resolve(repoRoot, 'data_pipeline/src/pne_macro_ingestion.py'),
    'utf8',
  )],
  ['data_pipeline/scripts/partition_static_data.py', partitionSource],
  ['data_pipeline/scripts/update_static_data.py', updateSource],
  ['data_pipeline/scripts/validate_static_details.py', readFileSync(
    resolve(repoRoot, 'data_pipeline/scripts/validate_static_details.py'),
    'utf8',
  )],
  ['data_pipeline/scripts/materialize_municipal_inequality.py', readFileSync(
    resolve(repoRoot, 'data_pipeline/scripts/materialize_municipal_inequality.py'),
    'utf8',
  )],
])
for (const [path, source] of migratedPipelineSources) {
  assert.doesNotMatch(
    source,
    /\bEXPECTED_MUNICIPALIT(?:Y_COUNT|IES)\s*=/,
    `${path} voltou a declarar cardinalidade municipal literal na fundação migrada.`,
  )
  assert.doesNotMatch(
    source,
    /\b(?:int|float)\s*\([^\n)]*\bid_municipio\b/,
    `${path} converte código IBGE municipal para número.`,
  )
}
assert.doesNotMatch(
  migratedPipelineSources.get('data_pipeline/src/pne_macro_ingestion.py'),
  /municipios_index\.json|MUNICIPALITY_INDEX/,
  'PNE macro não pode voltar a usar municipios_index.json como universo canônico.',
)
assert.doesNotMatch(
  migratedPipelineSources.get('data_pipeline/scripts/materialize_municipal_inequality.py'),
  /municipios_index\.json/,
  'Materializador de desigualdade não pode usar o índice público como registro.',
)

const migratedEducationPaths = [
  'data_pipeline/scripts/export_education_indicators.py',
  'data_pipeline/src/education_municipality_routes.py',
  'data_pipeline/src/municipal_education_overview.py',
  'data_pipeline/scripts/materialize_municipal_education_overview.py',
  'data_pipeline/src/higher_education.py',
  'data_pipeline/src/higher_education_materialization.py',
  'data_pipeline/scripts/sync_higher_education_from_sinopse.py',
  'data_pipeline/scripts/materialize_special_education.py',
  'data_pipeline/src/special_education_materialization.py',
  'data_pipeline/scripts/validate_special_education.py',
  'data_pipeline/scripts/audit_special_education_completeness.py',
]
const migratedEducationSources = new Map(migratedEducationPaths.map((path) => [
  path,
  readFileSync(resolve(repoRoot, path), 'utf8'),
]))
for (const [path, source] of migratedEducationSources) {
  assert.doesNotMatch(
    source,
    /\bEXPECTED_MUNICIPALIT(?:Y_COUNT|IES)\s*=/,
    `${path} voltou a declarar cardinalidade municipal literal na Educação migrada.`,
  )
  assert.doesNotMatch(
    source,
    /\b(?:int|float|str)\s*\([^\n)]*\b(?:id_municipio|municipality_id|ibgeCode)\b|\bid_municipio\b[^\n]*\.astype\(str\)|\.astype\(str\)[^\n]*\bid_municipio\b/,
    `${path} converte código IBGE municipal para número ou texto após a leitura.`,
  )
  assert.doesNotMatch(
    source,
    /(?:startswith\(\s*['"]43['"]\)|\[:2\]\s*==\s*['"]43['"])/,
    `${path} voltou a usar o prefixo 43 como validação central.`,
  )
  assert.doesNotMatch(
    source,
    /(?:sigla_uf|SG_UF|unidade_da_federacao|uf)\s*(?:==|=)\s*['"]RS['"]/i,
    `${path} voltou a fixar RS em filtro estadual de produção.`,
  )
  assert.doesNotMatch(
    source,
    /slugify\s*\([^\n]*(?:municipio|municipality|name)/i,
    `${path} voltou a derivar slug municipal para definir identidade.`,
  )
}

for (const path of migratedEducationPaths.slice(1)) {
  assert.doesNotMatch(
    migratedEducationSources.get(path),
    /municipios_index\.json/,
    `${path} voltou a usar índice educacional publicado como identidade.`,
  )
}
assert.doesNotMatch(
  migratedEducationSources.get('data_pipeline/scripts/export_education_indicators.py'),
  /\b(?:MUNICIPAL_INDEX|REGISTRY_PATH)\b/,
  'O exportador geral não pode usar índice publicado como registro municipal.',
)
const routeCompatibilitySource = migratedEducationSources.get(
  'data_pipeline/src/education_municipality_routes.py',
)
assert.match(
  routeCompatibilitySource,
  /def resolve_education_public_slug\s*\(/,
  'O resolvedor testável da rota educacional deve permanecer explícito.',
)
const educationRouteBoundaries = [
  'data_pipeline/scripts/export_education_indicators.py',
  'data_pipeline/scripts/materialize_special_education.py',
  'data_pipeline/scripts/validate_special_education.py',
]
for (const path of educationRouteBoundaries) {
  const source = migratedEducationSources.get(path)
  assert.match(
    source,
    /(?:build_education_municipalities_index_payload|resolve_education_public_slug)\s*\(/,
    `${path} deve projetar o slug histórico pelo resolvedor de compatibilidade.`,
  )
  assert.doesNotMatch(
    source,
    /['"]slug['"]\s*:\s*record\.slug/,
    `${path} não pode publicar record.slug diretamente na fronteira histórica.`,
  )
}
const embeddedEducationOverrides = migratedEducationPaths.filter((path) => (
  /['"]\d{7}['"]\s*:\s*['"][\p{L}\d-]+['"]/u.test(
    migratedEducationSources.get(path),
  )
))
assert.deepEqual(
  embeddedEducationOverrides,
  [],
  `Overrides municipais não podem ser embutidos em Python:\n${embeddedEducationOverrides.join('\n')}`,
)
const municipalSlugAsInternalKey = migratedEducationPaths.filter((path) => {
  const source = migratedEducationSources.get(path)
  return /(?:groupby|set_index|merge|join)\s*\([^\n)]*(?:record\.slug|municipality[^\n)]*slug|municipio[^\n)]*slug)/i.test(source)
    || /\[\s*(?:record\.slug|municipality\[['"]slug['"]\])\s*\]/.test(source)
    || /f['"][^'"\n]*\{(?:record\.slug|municipality\[['"]slug['"]\])\}[^'"\n]*['"]/.test(source)
})
assert.deepEqual(
  municipalSlugAsInternalKey,
  [],
  `Slug municipal não pode ser diretório, join ou chave interna:\n${municipalSlugAsInternalKey.join('\n')}`,
)

const educationEntrypoints = new Map([
  ['data_pipeline/scripts/export_education_indicators.py', '_get_education_engine()'],
  ['data_pipeline/scripts/materialize_municipal_education_overview.py', 'get_local_postgres_engine()'],
  ['data_pipeline/scripts/sync_higher_education_from_sinopse.py', 'parse_higher_education_sources('],
  ['data_pipeline/scripts/materialize_special_education.py', 'load_special_education_school_source_data('],
  ['data_pipeline/scripts/validate_special_education.py', 'load_special_education_school_source_data('],
  ['data_pipeline/scripts/audit_special_education_completeness.py', 'load_special_education_school_source_data('],
])
for (const [path, firstEffect] of educationEntrypoints) {
  const source = migratedEducationSources.get(path)
  const main = source.slice(source.search(/\ndef main\s*\(/))
  assert.match(source, /['"]--state['"]/, `${path} perdeu o parâmetro --state.`)
  assert.match(main, /load_state_config\(/, `${path} não carrega StateConfig no entrypoint.`)
  assert.match(
    main,
    /load_municipality_registry\(/,
    `${path} não carrega MunicipalityRegistry no entrypoint.`,
  )
  assert.ok(
    main.indexOf('load_state_config(') < main.indexOf(firstEffect),
    `${path} executa ${firstEffect} antes de validar o estado.`,
  )
}
for (const [path, firstEffect] of [
  ['data_pipeline/scripts/export_education_indicators.py', '_get_education_engine()'],
  ['data_pipeline/scripts/materialize_special_education.py', 'load_special_education_school_source_data('],
  ['data_pipeline/scripts/validate_special_education.py', 'load_special_education_school_source_data('],
]) {
  const main = migratedEducationSources.get(path).slice(
    migratedEducationSources.get(path).search(/\ndef main\s*\(/),
  )
  assert.ok(
    main.indexOf('load_state_config(')
      < main.indexOf('load_education_municipality_route_compatibility('),
    `${path} deve validar StateConfig antes da compatibilidade de rota.`,
  )
  assert.ok(
    main.indexOf('load_education_municipality_route_compatibility(')
      < main.indexOf(firstEffect),
    `${path} deve validar compatibilidade antes do primeiro efeito externo.`,
  )
}

const educationCommand = updateSource.match(
  /education_command\s*=\s*\[([\s\S]*?)\n\s*\]/,
)
assert.ok(educationCommand, 'Comando central de Educação não encontrado.')
assert.match(
  educationCommand[1],
  /['"]--state['"][\s\S]*state_config\.state_code/,
  'update_static_data.py deve propagar --state para a Educação.',
)
assert.equal(
  packageJson.scripts?.['test:pipeline-education-state'],
  'uv run --project data_pipeline --group test --frozen python -m pytest data_pipeline/tests/test_pipeline_education_state.py data_pipeline/tests/test_export_education_indicators_matriculas.py data_pipeline/tests/test_municipal_education_overview.py data_pipeline/tests/test_materialize_municipal_education_overview.py data_pipeline/tests/test_higher_education.py data_pipeline/tests/test_special_education_materialization.py',
  'A suíte focada de parametrização estadual da Educação deve permanecer exposta.',
)
const municipalContract = updateSource.match(
  /MUNICIPAL_STATIC_FILES\s*=\s*frozenset\(\s*\{([\s\S]*?)\}\s*\)/,
)
assert.ok(municipalContract, 'Contrato municipal estático não encontrado no sincronizador.')
assert.doesNotMatch(
  municipalContract[1],
  /diagnostico\.json/,
  'O contrato municipal administrado não pode voltar a exigir diagnostico.json.',
)

const retiredEducationExporterPath = 'scripts/export_education_indicators.py'
const currentEducationExporterPath = `data_pipeline/${retiredEducationExporterPath}`

function referencesRetiredEducationExporter(text) {
  const normalized = text.replaceAll('\\', '/')
  const pathPattern = /(?:\.\/)?(?:[A-Za-z0-9_.-]+\/)*scripts\/export_education_indicators\.py\b/g
  const dataPipelineRootNames = new Set(
    Array.from(
      normalized.matchAll(
        /\b([A-Z][A-Z0-9_]*)\s*=\s*[^\r\n]*\/\s*['"]data_pipeline['"]/g,
      ),
      (match) => match[1],
    ),
  )

  for (const match of normalized.matchAll(pathPattern)) {
    const candidate = match[0].replace(/^\.\//, '')
    if (candidate.endsWith(currentEducationExporterPath)) continue

    const prefix = normalized.slice(Math.max(0, match.index - 80), match.index)
    const rootExpression = prefix.match(/\b([A-Z][A-Z0-9_]*)\s*\/\s*['"]$/)
    const isDataPipelineRelative = (
      candidate === retiredEducationExporterPath
      && rootExpression
      && dataPipelineRootNames.has(rootExpression[1])
    )
    if (isDataPipelineRelative) continue

    return true
  }
  return false
}

for (const source of [
  retiredEducationExporterPath,
  `./${retiredEducationExporterPath}`,
  `uv run python ${retiredEducationExporterPath}`,
  'python .\\scripts\\export_education_indicators.py',
]) {
  assert.equal(
    referencesRetiredEducationExporter(source),
    true,
    `Referência ao exportador aposentado deveria ser proibida: ${source}`,
  )
}
for (const source of [
  currentEducationExporterPath,
  'PIPELINE_ROOT = REPO_ROOT / "data_pipeline"\n'
    + 'PIPELINE_ROOT / "scripts" / "export_education_indicators.py"',
  'PIPELINE_ROOT = REPO_ROOT / "data_pipeline"\n'
    + '(PIPELINE_ROOT / "scripts/export_education_indicators.py").read_text()',
]) {
  assert.equal(
    referencesRetiredEducationExporter(source),
    false,
    `Referência legítima ao exportador atual deveria ser permitida: ${source}`,
  )
}

const forbiddenReferences = [
  ['data_pipeline/app.py', /data_pipeline\/app\.py/],
  ['src.views', /\bsrc\.views\b/],
  ['src/views', /(?:^|[^/])src\/views(?:\/|$)/m],
  [retiredEducationExporterPath, referencesRetiredEducationExporter],
]
const staleReferences = []
for (const path of tracked.filter((item) => ['.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'].includes(extname(item)))) {
  if (path === 'scripts/checks/repository-hygiene-test.mjs') continue
  if (!existsSync(resolve(repoRoot, path))) continue
  const text = readFileSync(resolve(repoRoot, path), 'utf8')
  for (const [label, matcher] of forbiddenReferences) {
    const matches = typeof matcher === 'function' ? matcher(text) : matcher.test(text)
    if (matches) staleReferences.push(`${path}: ${label}`)
  }
}
assert.deepEqual(staleReferences, [], `Referências removidas ainda presentes:\n${staleReferences.join('\n')}`)

console.log(
  `Higiene permanente validada: ${tracked.length} arquivos rastreados, `
  + `${canonicalDocs.length} documentos canônicos e ${Object.keys(packageJson.scripts).length} scripts npm.`,
)
