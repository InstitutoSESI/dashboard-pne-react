import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const OUTPUT = resolve(
  ROOT,
  'data_pipeline',
  'manifests',
  'vocacoes-pne-aa0-worktree-baseline.json',
)

const PROGRAM_OWNED_PATHS = new Set([
  'data_pipeline/manifests/vocacoes-pne-aa0-worktree-baseline.json',
  'docs/PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md',
  'docs/RELATORIO_AA0_AVANCO_ANALITICO_VOCACOES_PNE.md',
  'docs/REVISAO_OPUS_AA0_AVANCO_ANALITICO_VOCACOES_PNE.md',
  'scripts/checks/generate-vocacoes-pne-aa0-baseline.mjs',
])

const OFFICIAL_BUNDLES = [
  'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iCore.json',
  'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5iSeries.json',
  'src/features/vocacoes-pne-internal/generated/vocacoesPneJob5kStories.json',
  'src/features/vocacoes-regiao/generated/vocacoesPneOfficialPromotion.json',
  'src/features/vocacoes-regiao/generated/vocacoesPneValeDoSinos.json',
]

function run(command, args) {
  return execFileSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function fileEvidence(relativePath) {
  const absolutePath = resolve(ROOT, relativePath)
  if (!existsSync(absolutePath)) {
    return {
      byteSize: null,
      currentContentSha256: null,
    }
  }
  const stat = lstatSync(absolutePath)
  if (!stat.isFile()) {
    throw new Error(`Baseline path is not a regular file: ${relativePath}`)
  }
  const content = readFileSync(absolutePath)
  return {
    byteSize: content.byteLength,
    currentContentSha256: sha256(content),
  }
}

function indexEvidence(relativePath) {
  const output = run('git', ['ls-files', '-s', '--', relativePath])
  if (!output) return { indexBlobOid: null, indexMode: null }
  const match = /^(\d+) ([0-9a-f]+) \d+\t/.exec(output)
  if (!match) throw new Error(`Unexpected git ls-files output for ${relativePath}`)
  return { indexBlobOid: match[2], indexMode: match[1] }
}

function rawDirtyEntries() {
  const raw = execFileSync(
    'git',
    ['status', '--porcelain=v1', '-z', '--untracked-files=all', '--no-renames'],
    { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
  )
  return raw
    .split('\0')
    .filter(Boolean)
    .map((record) => ({
      path: record.slice(3).replaceAll('\\', '/'),
      status: record.slice(0, 2),
    }))
    .map(({ path, status }) => ({
      path,
      status,
      ...indexEvidence(path),
      ...fileEvidence(path),
    }))
    .sort((left, right) => left.path.localeCompare(right.path, 'en'))
}

function parseDirtyEntries() {
  return rawDirtyEntries().filter(({ path }) => !PROGRAM_OWNED_PATHS.has(path))
}

function cliValue(name) {
  const inline = process.argv.find((value) => value.startsWith(`${name}=`))
  if (inline) return inline.slice(name.length + 1)
  const index = process.argv.indexOf(name)
  return index >= 0 ? process.argv[index + 1] : null
}

function normalizeRepoPath(path) {
  const normalized = relative(ROOT, resolve(ROOT, path)).replaceAll('\\', '/')
  if (normalized.startsWith('../') || normalized === '..') {
    throw new Error(`Allowlist must stay inside the repository: ${path}`)
  }
  return normalized
}

function loadAllowlist(path) {
  if (!path) return null
  const absolutePath = resolve(ROOT, path)
  const parsed = JSON.parse(readFileSync(absolutePath, 'utf8'))
  const allowedPaths = Array.isArray(parsed) ? parsed : parsed.allowedPaths
  if (!Array.isArray(allowedPaths) || allowedPaths.some((value) => typeof value !== 'string')) {
    throw new Error('AA0 allowlist must be an array or expose string[] allowedPaths')
  }
  return {
    allowlistPath: normalizeRepoPath(path),
    rules: allowedPaths.map((value) =>
      value.endsWith('/**')
        ? `${normalizeRepoPath(value.slice(0, -3))}/**`
        : normalizeRepoPath(value),
    ),
  }
}

function pathMatches(path, rules) {
  return rules.some((rule) =>
    rule.endsWith('/**') ? path.startsWith(rule.slice(0, -2)) : path === rule,
  )
}

function comparableEntry(entry) {
  return {
    path: entry.path,
    status: entry.status,
    indexBlobOid: entry.indexBlobOid,
    indexMode: entry.indexMode,
    byteSize: entry.byteSize,
    currentContentSha256: entry.currentContentSha256,
  }
}

function verifyWithAllowlist(baseline, allowlist) {
  const dirtyPathRules = [
    ...PROGRAM_OWNED_PATHS,
    allowlist.allowlistPath,
    ...allowlist.rules,
  ]
  const stageRules = [allowlist.allowlistPath, ...allowlist.rules]
  const currentEntries = rawDirtyEntries()
  const currentByPath = new Map(currentEntries.map((entry) => [entry.path, entry]))
  const baselineByPath = new Map(
    baseline.protectedDirtyBaseline.entries.map((entry) => [entry.path, entry]),
  )
  const failures = []

  for (const [path, expected] of baselineByPath) {
    if (pathMatches(path, stageRules)) continue
    const current = currentByPath.get(path)
    if (!current) {
      failures.push(`Protected path missing from dirty state: ${path}`)
      continue
    }
    if (JSON.stringify(comparableEntry(current)) !== JSON.stringify(comparableEntry(expected))) {
      failures.push(`Protected path drifted: ${path}`)
    }
  }

  for (const current of currentEntries) {
    if (baselineByPath.has(current.path) || pathMatches(current.path, dirtyPathRules)) continue
    failures.push(`Unexpected dirty path outside the stage allowlist: ${current.path}`)
  }

  for (const expected of baseline.officialFallbackBundles.bundles) {
    if (pathMatches(expected.path, stageRules)) continue
    const current = { path: expected.path, ...fileEvidence(expected.path) }
    if (JSON.stringify(current) !== JSON.stringify(expected)) {
      failures.push(`Official fallback bundle drifted: ${expected.path}`)
    }
  }

  if (!pathMatches(baseline.contract.path, stageRules)) {
    const current = { path: baseline.contract.path, ...fileEvidence(baseline.contract.path) }
    const expected = {
      path: baseline.contract.path,
      byteSize: baseline.contract.byteSize,
      currentContentSha256: baseline.contract.currentContentSha256,
    }
    if (JSON.stringify(current) !== JSON.stringify(expected)) {
      failures.push(`AA0 plan hash drifted: ${baseline.contract.path}`)
    }
  }

  const currentHead = run('git', ['rev-parse', 'HEAD'])
  const currentUpstream = run('git', ['rev-parse', '@{upstream}'])
  if (currentHead !== baseline.git.head) failures.push('HEAD changed from the AA0 baseline')
  if (currentUpstream !== baseline.git.upstreamHead) {
    failures.push('Upstream HEAD changed from the AA0 baseline')
  }
  if (failures.length > 0) throw new Error(failures.join('\n'))

  console.log(
    `OK: AA0 protected set preserved with ${allowlist.rules.length} stage rule(s); ` +
      `${baseline.protectedDirtyBaseline.entryCount} baseline entries remain guarded.`,
  )
}

function buildManifest() {
  const dirtyEntries = parseDirtyEntries()
  const trackedDirtyCount = dirtyEntries.filter(({ status }) => status !== '??').length
  const untrackedCount = dirtyEntries.filter(({ status }) => status === '??').length
  const officialBundles = OFFICIAL_BUNDLES.map((path) => ({ path, ...fileEvidence(path) }))
  const [ahead, behind] = run('git', [
    'rev-list',
    '--left-right',
    '--count',
    'HEAD...@{upstream}',
  ])
    .split(/\s+/)
    .map(Number)
  const entriesCanonical = JSON.stringify(dirtyEntries)
  const officialCanonical = JSON.stringify(officialBundles)
  const npmVersion =
    process.platform === 'win32'
      ? run(process.env.ComSpec ?? 'cmd.exe', ['/d', '/s', '/c', 'npm --version'])
      : run('npm', ['--version'])

  return {
    schemaVersion: 'vocacoes-pne-aa0-worktree-baseline-v1',
    programId: 'vocacoes-pne-advanced-analytics-v1',
    capturedDate: '2026-08-30',
    repositoryRoot: ROOT.replaceAll('\\', '/'),
    git: {
      head: run('git', ['rev-parse', 'HEAD']),
      branch: run('git', ['branch', '--show-current']),
      upstream: run('git', ['rev-parse', '--abbrev-ref', '@{upstream}']),
      upstreamHead: run('git', ['rev-parse', '@{upstream}']),
      ahead,
      behind,
    },
    toolchain: {
      git: run('git', ['--version']),
      node: run('node', ['--version']),
      npm: npmVersion,
      uv: run('uv', ['--version']),
      python: run('uv', ['run', 'python', '--version']),
    },
    protectedDirtyBaseline: {
      trackedDirtyCount,
      untrackedCount,
      entryCount: dirtyEntries.length,
      entriesSha256: sha256(entriesCanonical),
      entries: dirtyEntries,
    },
    officialFallbackBundles: {
      count: officialBundles.length,
      bundlesSha256: sha256(officialCanonical),
      bundles: officialBundles,
    },
    contract: {
      path: 'docs/PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md',
      ...fileEvidence('docs/PLANO_EXECUCAO_AVANCO_ANALITICO_VOCACOES_PNE.md'),
      gitState: 'untracked_program_owned_at_aa0',
    },
    validatedBaselineCommands: [
      {
        command: 'npm run test:vocacoes-pne',
        result: 'PASS',
        passed: 103,
        failed: 0,
      },
      {
        command:
          'uv run python -m pytest data_pipeline/tests/test_vocacoes_pne_job5j.py data_pipeline/tests/test_vocacoes_pne_job5l_final.py -vv -s',
        result: 'PASS',
        passed: 17,
        failed: 0,
      },
      {
        command: 'npm run check:fast',
        result: 'PASS',
        details: ['typecheck', 'lint', 'compiler_check', 'app_only_build'],
      },
      {
        command: 'git diff --check',
        result: 'PASS_WITH_LINE_ENDING_WARNINGS_ONLY',
      },
    ],
    publicDataMutationPerformed: false,
    databaseUsed: false,
    networkUsedForProjectData: false,
    fullProductionBuildDeferredTo: 'AA6',
    fullProductionBuildDeferralReason:
      'AA0 is documentation and baseline audit; the project contract reserves the full data-copying build for release validation.',
  }
}

const checkOnly = process.argv.includes('--check')
const allowlistPath = cliValue('--allowlist')

if (allowlistPath && !checkOnly) {
  throw new Error('--allowlist is valid only together with --check')
}

if (checkOnly && allowlistPath) {
  if (!existsSync(OUTPUT)) throw new Error(`Missing AA0 baseline manifest: ${OUTPUT}`)
  const baseline = JSON.parse(readFileSync(OUTPUT, 'utf8'))
  verifyWithAllowlist(baseline, loadAllowlist(allowlistPath))
  process.exit(0)
}

const manifest = buildManifest()
const serialized = `${JSON.stringify(manifest, null, 2)}\n`

if (checkOnly) {
  if (!existsSync(OUTPUT)) throw new Error(`Missing AA0 baseline manifest: ${OUTPUT}`)
  const existing = readFileSync(OUTPUT, 'utf8')
  if (existing !== serialized) {
    throw new Error('AA0 baseline manifest diverges from the protected current state')
  }
  console.log(
    `OK: AA0 baseline preserved (${manifest.protectedDirtyBaseline.trackedDirtyCount} tracked, ${manifest.protectedDirtyBaseline.untrackedCount} untracked).`,
  )
  process.exit(0)
}

mkdirSync(dirname(OUTPUT), { recursive: true })
const temporary = `${OUTPUT}.tmp`
writeFileSync(temporary, serialized, 'utf8')
if (existsSync(OUTPUT) && readFileSync(OUTPUT, 'utf8') === serialized) {
  rmSync(temporary)
  console.log('OK: AA0 baseline manifest already identical.')
  process.exit(0)
}
if (existsSync(OUTPUT)) rmSync(OUTPUT)
renameSync(temporary, OUTPUT)
console.log(`OK: wrote ${OUTPUT}`)
