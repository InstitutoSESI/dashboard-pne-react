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
const expectedUvPythonScripts = [
  'test:python',
  'check:python-deps',
  'update:education-data',
  'update:indigenous-coverage',
  'update:data',
  'update:data:skip-build',
  'verify:indicator',
  'validate:details',
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
assert.equal(municipalityIds.length, 497, 'Publicação municipal deve conter 497 municípios.')
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
const municipalContract = updateSource.match(
  /MUNICIPAL_STATIC_FILES\s*=\s*frozenset\(\s*\{([\s\S]*?)\}\s*\)/,
)
assert.ok(municipalContract, 'Contrato municipal estático não encontrado no sincronizador.')
assert.doesNotMatch(
  municipalContract[1],
  /diagnostico\.json/,
  'O contrato municipal administrado não pode voltar a exigir diagnostico.json.',
)

const forbiddenReferences = [
  ['data_pipeline/app.py', /data_pipeline\/app\.py/],
  ['src.views', /\bsrc\.views\b/],
  ['src/views', /(?:^|[^/])src\/views(?:\/|$)/m],
  ['scripts/export_education_indicators.py', /(?:^|[^/])scripts\/export_education_indicators\.py\b/m],
]
const staleReferences = []
for (const path of tracked.filter((item) => ['.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'].includes(extname(item)))) {
  if (path === 'scripts/checks/repository-hygiene-test.mjs') continue
  if (!existsSync(resolve(repoRoot, path))) continue
  const text = readFileSync(resolve(repoRoot, path), 'utf8')
  for (const [label, pattern] of forbiddenReferences) {
    if (pattern.test(text)) staleReferences.push(`${path}: ${label}`)
  }
}
assert.deepEqual(staleReferences, [], `Referências removidas ainda presentes:\n${staleReferences.join('\n')}`)

console.log(
  `Higiene permanente validada: ${tracked.length} arquivos rastreados, `
  + `${canonicalDocs.length} documentos canônicos e ${Object.keys(packageJson.scripts).length} scripts npm.`,
)
