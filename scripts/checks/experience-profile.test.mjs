import assert from 'node:assert/strict'
import { existsSync, readFileSync, realpathSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import {
  DEFAULT_PLATFORM_EXPERIENCE,
  loadExperienceBuildProfile,
  normalizePlatformExperience,
} from '../lib/experience-build-profile.mjs'
import { parseStateViteArguments } from '../run-state-vite.mjs'
import { createViteConfig } from '../../vite.config.js'

const repoRoot = fileURLToPath(new URL('../..', import.meta.url))

test('a matriz UF × experiência aceita RS atual, RS PME e AL atual', () => {
  const rsCurrent = loadExperienceBuildProfile({ repoRoot, stateCode: 'RS', experience: 'atual' })
  const rsPme = loadExperienceBuildProfile({ repoRoot, stateCode: 'RS', experience: 'pme' })
  const alCurrent = loadExperienceBuildProfile({ repoRoot, stateCode: 'AL', experience: 'atual' })

  assert.equal(rsCurrent.experience, 'atual')
  assert.equal(rsCurrent.entryModule, 'src/main.jsx')
  assert.equal(rsPme.experience, 'pme')
  assert.equal(rsPme.entryModule, 'src/main-pme.tsx')
  assert.equal(alCurrent.experience, 'atual')
  assert.equal(alCurrent.entryModule, 'src/main.jsx')
})

test('a experiência atual é o default e combinações inválidas falham sem fallback', () => {
  assert.equal(normalizePlatformExperience(), DEFAULT_PLATFORM_EXPERIENCE)
  assert.equal(normalizePlatformExperience(' ATUAL '), 'atual')
  assert.throws(() => normalizePlatformExperience('desconhecida'), /PLATFORM_EXPERIENCE inválida/)
  assert.throws(
    () => loadExperienceBuildProfile({ repoRoot, stateCode: 'AL', experience: 'pme' }),
    /PME está disponível somente para a UF RS/,
  )
})

test('o alias seleciona estaticamente uma única entrada por perfil', () => {
  const currentConfig = createViteConfig(
    { command: 'build', mode: 'app-only' },
    { PLATFORM_STATE: 'RS', PLATFORM_EXPERIENCE: 'atual' },
  )
  const pmeConfig = createViteConfig(
    { command: 'build', mode: 'app-only' },
    { PLATFORM_STATE: 'RS', PLATFORM_EXPERIENCE: 'pme' },
  )

  assert.equal(currentConfig.resolve.alias['@platform-entry'], path.join(repoRoot, 'src', 'main.jsx'))
  assert.equal(pmeConfig.resolve.alias['@platform-entry'], path.join(repoRoot, 'src', 'main-pme.tsx'))
  assert.notEqual(
    currentConfig.resolve.alias['@platform-entry'],
    pmeConfig.resolve.alias['@platform-entry'],
  )
  assert.equal(existsSync(currentConfig.resolve.alias['@platform-entry']), true)
  assert.notEqual(currentConfig.cacheDir, pmeConfig.cacheDir)
  assert.match(pmeConfig.cacheDir.replaceAll('\\', '/'), /\.tmp\/vite\/rs-pme$/)
  const alConfig = createViteConfig({ command: 'build', mode: 'app-only' }, { PLATFORM_STATE: 'AL', PLATFORM_EXPERIENCE: 'atual' })
  assert.notEqual(alConfig.cacheDir, currentConfig.cacheDir)
})

test('a entrada comum e o HTML não importam aplicações em runtime', () => {
  assert.equal(
    readFileSync(path.join(repoRoot, 'src', 'main-entry.ts'), 'utf8').trim(),
    "import '@platform-entry'",
  )
  assert.match(
    readFileSync(path.join(repoRoot, 'index.html'), 'utf8'),
    /<script type="module" src="\/src\/main-entry\.ts"><\/script>/,
  )
})

test('o servidor permite fontes de dependências compartilhadas sem liberar a pasta pai do checkout', () => {
  const config = createViteConfig({ command: 'serve', mode: 'development' }, { PLATFORM_STATE: 'RS', PLATFORM_EXPERIENCE: 'pme' })
  const dependencyRoot = path.join(repoRoot, 'node_modules')
  const expected = [path.resolve(repoRoot), ...(existsSync(dependencyRoot) ? [realpathSync(dependencyRoot)] : [])]
  assert.deepEqual(config.server.fs.allow.map((entry) => path.resolve(entry)), expected)
  assert.ok(!config.server.fs.allow.some((entry) => path.resolve(entry) === path.dirname(path.resolve(repoRoot))))
})

test('a CLI fixa UF e experiência antes de iniciar o Vite', () => {
  assert.deepEqual(
    parseStateViteArguments(['build', 'rs', 'pme', '--outDir', 'dist']),
    {
      command: 'build',
      stateCode: 'RS',
      experience: 'pme',
      viteArguments: ['--outDir', 'dist'],
    },
  )
  assert.throws(
    () => parseStateViteArguments(['build', 'RS', 'invalida']),
    /PLATFORM_EXPERIENCE inválida/,
  )
  assert.deepEqual(
    parseStateViteArguments(['build', 'AL', '--outDir', 'dist/al']),
    {
      command: 'build',
      stateCode: 'AL',
      experience: 'atual',
      viteArguments: ['--outDir', 'dist/al'],
    },
  )
})

test('os comandos explícitos usam saídas isoladas e não herdam a experiência do shell', () => {
  const packageJson = JSON.parse(readFileSync(path.join(repoRoot, 'package.json'), 'utf8'))
  assert.equal(packageJson.scripts['dev:rs-pme'], 'node scripts/run-state-vite.mjs serve RS pme --port 5189')
  assert.equal(
    packageJson.scripts['build:app:rs-pme'],
    'node scripts/run-state-vite.mjs build RS pme --mode app-only --outDir dist/app-only-rs-pme',
  )
  assert.equal(packageJson.scripts['build:rs-pme'], 'node scripts/run-state-vite.mjs build RS pme --outDir dist/rs-pme')
  assert.equal(
    packageJson.scripts['preview:rs-pme'],
    'node scripts/run-state-vite.mjs preview RS pme --outDir dist/rs-pme --port 4189',
  )
  assert.equal(packageJson.scripts['build:cloudflare:rs-pme'], 'node scripts/run-state-vite.mjs build RS pme --outDir dist')
  assert.match(packageJson.scripts['dev:rs'], /serve RS atual/)
  assert.match(packageJson.scripts['dev:al'], /serve AL atual/)
  assert.match(packageJson.scripts['build:rs'], /build RS atual/)
  assert.match(packageJson.scripts['build:al'], /build AL atual/)
})
