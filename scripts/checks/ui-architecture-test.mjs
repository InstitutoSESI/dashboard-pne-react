import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const sourceRoot = path.join(repositoryRoot, 'src')
const stylesRoot = path.join(sourceRoot, 'styles')

const APP_CSS_SOFT_LIMIT_BYTES = 440_000
const APP_STYLE_ORDER = [
  './App.css',
  './styles/chart-system.css',
  './styles/pne-cycle-experience.css',
  './styles/platform-ui.css',
  './styles/financial-pages.css',
  './styles/navigation-shell.css',
  './styles/home-page.css',
]
const MAIN_STYLE_ORDER = [
  './index.css',
  './styles/institutional-refresh.css',
  './styles/typography-system.css',
]

function read(relativePath) {
  return fs.readFileSync(path.join(repositoryRoot, relativePath), 'utf8')
}

function walk(directory, predicate = () => true) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = path.join(directory, entry.name)
    if (entry.isDirectory()) return walk(absolutePath, predicate)
    return predicate(absolutePath) ? [absolutePath] : []
  })
}

function cssImports(source) {
  return [...source.matchAll(/^import\s+['"]([^'"]+\.css)['"]/gm)]
    .map((match) => match[1])
    .filter((specifier) => specifier.startsWith('.'))
}

assert.deepEqual(cssImports(read('src/App.tsx')), APP_STYLE_ORDER, 'App.tsx: ordem canônica dos estilos foi alterada')
assert.deepEqual(cssImports(read('src/main.jsx')), MAIN_STYLE_ORDER, 'main.jsx: ordem canônica dos estilos foi alterada')

const appCssPath = path.join(sourceRoot, 'App.css')
assert.ok(
  fs.statSync(appCssPath).size <= APP_CSS_SOFT_LIMIT_BYTES,
  `App.css ultrapassou o teto de ${APP_CSS_SOFT_LIMIT_BYTES.toLocaleString('pt-BR')} bytes; novos padrões pertencem às camadas canônicas`,
)

const sourceFiles = walk(sourceRoot, (file) => /\.(?:css|[cm]?[jt]sx?)$/.test(file))
const sourceCorpus = sourceFiles.map((file) => fs.readFileSync(file, 'utf8')).join('\n')
const styleFiles = walk(stylesRoot, (file) => file.endsWith('.css'))
const missingStyleImports = styleFiles
  .map((file) => path.basename(file))
  .filter((fileName) => !sourceCorpus.includes(fileName))
assert.deepEqual(missingStyleImports, [], `CSS sem importador: ${missingStyleImports.join(', ')}`)

const sharedChartSelector = /(^|\n)\s*\.(chart-tooltip(?:__[\w-]+)?|chart-legend(?:__[\w-]+)?)(?=[\s,.:>{])/g
const chartSelectorLeaks = walk(sourceRoot, (file) => file.endsWith('.css') && !file.endsWith('chart-system.css'))
  .flatMap((file) => {
    const relativePath = path.relative(repositoryRoot, file)
    return [...fs.readFileSync(file, 'utf8').matchAll(sharedChartSelector)]
      .map((match) => `${relativePath}: .${match[2]}`)
  })
assert.deepEqual(
  chartSelectorLeaks,
  [],
  `Primitivas canônicas de tooltip/legenda de gráfico fora de chart-system.css:\n${chartSelectorLeaks.join('\n')}`,
)

const typedCoreFiles = [
  ...walk(path.join(sourceRoot, 'app'), (file) => /\.tsx?$/.test(file)),
  ...walk(path.join(sourceRoot, 'features', 'education'), (file) => /\.tsx?$/.test(file)),
]
const explicitAny = /\b(?:as|satisfies)\s+any\b|:\s*any\b|<any>/g
const unsafeTypeHits = typedCoreFiles.flatMap((file) => {
  const relativePath = path.relative(repositoryRoot, file)
  return [...fs.readFileSync(file, 'utf8').matchAll(explicitAny)].map(() => relativePath)
})
assert.deepEqual(unsafeTypeHits, [], `Tipos any explícitos na camada TypeScript central: ${unsafeTypeHits.join(', ')}`)

console.log('UI architecture validation passed: cascata, CSS canônico, teto legado e tipos centrais.')
