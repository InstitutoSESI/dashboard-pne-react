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

const forbiddenTracked = [
  /^(?:artifacts|outputs|dist|coverage|playwright-report|test-results|screenshots|inspection)\//i,
  /^data_pipeline\/(?:cache|export)\//i,
  /(?:^|\/)(?:debug|screenshots?|inspection)(?:\/|$)/i,
  /\.(?:log|tmp|bak|pyc|pyo)$/i,
]

const violations = tracked.filter((path) => forbiddenTracked.some((pattern) => pattern.test(path)))
assert.deepEqual(violations, [], `Arquivos temporários rastreados:\n${violations.join('\n')}`)

const packageJson = JSON.parse(readFileSync(resolve(repoRoot, 'package.json'), 'utf8'))
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
for (const document of canonicalDocs) {
  const absoluteDocument = resolve(repoRoot, document)
  assert.ok(existsSync(absoluteDocument), `Documento canônico ausente: ${document}`)
  const markdown = readFileSync(absoluteDocument, 'utf8')
  for (const match of markdown.matchAll(/\[[^\]]*]\(([^)]+)\)/g)) {
    const rawTarget = match[1].trim().replace(/^<|>$/g, '').split('#', 1)[0]
    if (!rawTarget || /^(?:https?:|mailto:)/i.test(rawTarget)) continue
    const target = resolve(dirname(absoluteDocument), decodeURIComponent(rawTarget))
    if (!existsSync(target)) brokenLinks.push(`${document}: ${match[1]}`)
  }
}
assert.deepEqual(brokenLinks, [], `Links locais quebrados:\n${brokenLinks.join('\n')}`)

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
for (const municipalityId of municipalityIds) {
  const diagnostic = JSON.parse(
    readFileSync(
      resolve(municipalRoot, municipalityId, 'diagnostico.json'),
      'utf8',
    ),
  )
  assert.equal(
    diagnostic.schemaVersion,
    'municipal-inequality-v1',
    `${municipalityId}: diagnóstico municipal fora do contrato compacto.`,
  )
  assert.deepEqual(
    Object.keys(diagnostic).toSorted(),
    ['generatedAt', 'inequalityPilot', 'municipality', 'schemaVersion'],
    `${municipalityId}: diagnóstico municipal contém blocos obsoletos.`,
  )
  assert.equal(diagnostic.municipality?.id, municipalityId)
}

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
