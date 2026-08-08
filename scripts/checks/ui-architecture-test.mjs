import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const sourceRoot = path.join(repositoryRoot, 'src')
const stylesRoot = path.join(sourceRoot, 'styles')

const CSS_TOTAL_SOFT_LIMIT_BYTES = 1_385_000
const CSS_FILE_SOFT_LIMIT_BYTES = Object.freeze({
  'src/App.css': 286_000,
  'src/styles/quick-reading-list.css': 3_000,
  'src/styles/education-pages.css': 800,
  'src/styles/education-pages-base.css': 2_500,
  'src/styles/education-higher-education.css': 24_000,
  'src/styles/education-page-shell.css': 19_000,
  'src/styles/education-demand.css': 11_500,
  'src/styles/education-methodology.css': 25_000,
  'src/styles/education-sistema-s.css': 5_500,
  'src/styles/education-detail-layout.css': 27_000,
  'src/styles/education-indicator-support-data.css': 11_000,
  'src/styles/education-attendance-summary.css': 2_500,
  'src/styles/education-compact-entry.css': 16_000,
  'src/styles/education-overview.css': 52_000,
  'src/styles/education-landing.css': 8_000,
  'src/styles/education-technical-report.css': 130_000,
  'src/styles/education-school-infrastructure-report.css': 4_000,
  'src/styles/education-school-infrastructure.css': 30_000,
  'src/styles/education-pages-refinements.css': 20_000,
  'src/styles/financial-pages.css': 209_000,
  'src/styles/institutional-refresh.css': 213_000,
})
const TYPECHECK_DEBT_ALLOWLIST = Object.freeze([
  'src/features/education/educationViewModels.ts',
])
const APP_STYLE_ORDER = [
  './App.css',
  './styles/chart-system.css',
  './styles/pne-cycle-experience.css',
  './styles/platform-ui.css',
  './styles/quick-reading-list.css',
  './styles/financial-pages.css',
  './styles/navigation-shell.css',
  './styles/home-page.css',
  './styles/state-publication-status.css',
]
const MAIN_STYLE_ORDER = [
  './index.css',
  './styles/institutional-refresh.css',
  './styles/typography-system.css',
]
const EDUCATION_STYLE_ORDER = [
  './education-pages-base.css',
  './education-higher-education.css',
  './education-page-shell.css',
  './education-demand.css',
  './education-methodology.css',
  './education-sistema-s.css',
  './education-detail-layout.css',
  './education-indicator-support-data.css',
  './education-attendance-summary.css',
  './education-compact-entry.css',
  './education-overview.css',
  './education-landing.css',
  './education-technical-report.css',
  './education-school-infrastructure-report.css',
  './education-school-infrastructure.css',
  './education-pages-refinements.css',
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

function cssDependencies(source) {
  return [...source.matchAll(/^@import\s+['"]([^'"]+\.css)['"];?$/gm)]
    .map((match) => match[1])
    .filter((specifier) => specifier.startsWith('.'))
}

function relativePath(file) {
  return path.relative(repositoryRoot, file).split(path.sep).join('/')
}

function normalizedByteLength(source) {
  return Buffer.byteLength(source.replace(/\r\n/g, '\n'), 'utf8')
}

const parsedSourceFiles = new Map()

function parseSourceFile(file) {
  if (parsedSourceFiles.has(file)) return parsedSourceFiles.get(file)
  const extension = path.extname(file)
  const scriptKind = extension === '.tsx'
    ? ts.ScriptKind.TSX
    : extension === '.ts'
      ? ts.ScriptKind.TS
      : extension === '.jsx'
        ? ts.ScriptKind.JSX
        : ts.ScriptKind.JS
  const parsed = ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    scriptKind,
  )
  parsedSourceFiles.set(file, parsed)
  return parsed
}

function callableNames(file) {
  const names = new Set()
  const sourceFile = parseSourceFile(file)
  const visit = (node) => {
    if (ts.isFunctionDeclaration(node) && node.name) names.add(node.name.text)
    if (
      ts.isVariableDeclaration(node)
      && ts.isIdentifier(node.name)
      && node.initializer
      && (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    ) {
      names.add(node.name.text)
    }
    ts.forEachChild(node, visit)
  }
  visit(sourceFile)
  return names
}

function staticTextFragments(node) {
  if (ts.isStringLiteralLike(node)) return [node.text]
  if (ts.isTemplateExpression(node)) {
    return [
      node.head.text,
      ...node.templateSpans.flatMap((span) => [
        ...staticTextFragments(span.expression),
        span.literal.text,
      ]),
    ]
  }
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    return [...staticTextFragments(node.left), ...staticTextFragments(node.right)]
  }
  if (ts.isConditionalExpression(node)) {
    return [...staticTextFragments(node.whenTrue), ...staticTextFragments(node.whenFalse)]
  }
  return []
}

function jsxClassTokens(file) {
  const tokens = new Set()
  const sourceFile = parseSourceFile(file)
  const visit = (node) => {
    if (
      ts.isJsxAttribute(node)
      && node.name.text === 'className'
      && node.initializer
    ) {
      const fragments = ts.isStringLiteral(node.initializer)
        ? [node.initializer.text]
        : ts.isJsxExpression(node.initializer) && node.initializer.expression
          ? staticTextFragments(node.initializer.expression)
          : []
      for (const fragment of fragments) {
        for (const token of fragment.split(/\s+/).filter(Boolean)) tokens.add(token)
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(sourceFile)
  return tokens
}

assert.deepEqual(cssImports(read('src/App.tsx')), APP_STYLE_ORDER, 'App.tsx: ordem canônica dos estilos foi alterada')
assert.deepEqual(cssImports(read('src/main.jsx')), MAIN_STYLE_ORDER, 'main.jsx: ordem canônica dos estilos foi alterada')

assert.deepEqual(
  cssDependencies(read('src/styles/education-pages.css')),
  EDUCATION_STYLE_ORDER,
  'education-pages.css: ordem dos módulos não pode alterar a cascata do domínio',
)
assert.doesNotMatch(
  read('src/styles/education-pages.css'),
  /[{}]/,
  'education-pages.css deve permanecer apenas como manifesto de módulos',
)

const educationSupportStyles = read('src/styles/education-indicator-support-data.css')
const educationInfrastructureStyles = read('src/styles/education-school-infrastructure.css')
const educationInfrastructureReportStyles = read('src/styles/education-school-infrastructure-report.css')
assert.match(educationSupportStyles, /^\.educacao-page--detail \.education-detail-view \.education-support-data--organized\s*\{/)
assert.match(educationSupportStyles, /\.education-compact-comparison\s*\{/)
assert.match(educationInfrastructureStyles, /\.school-infrastructure-composite-card\s*\{/)
assert.match(educationInfrastructureStyles, /\.school-infrastructure-panorama__support \.infra-panorama-grid\s*\{/)
assert.match(educationInfrastructureReportStyles, /^\.school-infrastructure-canonical-group\s*\{/)
assert.match(educationInfrastructureReportStyles, /\.municipal-technical-report__table--school-infrastructure\s*\{/)

const sourceFiles = walk(sourceRoot, (file) => /\.(?:css|[cm]?[jt]sx?)$/.test(file))
const scriptFiles = sourceFiles.filter((file) => !file.endsWith('.css'))
const sourceCorpus = sourceFiles.map((file) => fs.readFileSync(file, 'utf8')).join('\n')
const cssFiles = sourceFiles.filter((file) => file.endsWith('.css'))
const cssSizes = cssFiles.map((file) => ({
  bytes: normalizedByteLength(fs.readFileSync(file, 'utf8')),
  file: relativePath(file),
}))
const oversizedCssFiles = cssSizes.filter(({ bytes, file }) => (
  CSS_FILE_SOFT_LIMIT_BYTES[file] && bytes > CSS_FILE_SOFT_LIMIT_BYTES[file]
))
assert.deepEqual(
  oversizedCssFiles,
  [],
  `CSS canônico ultrapassou o baseline; consolide regras antes de ampliar:\n${oversizedCssFiles.map(({ bytes, file }) => `${file}: ${bytes.toLocaleString('pt-BR')} bytes`).join('\n')}`,
)
const totalCssBytes = cssSizes.reduce((total, { bytes }) => total + bytes, 0)
assert.ok(
  totalCssBytes <= CSS_TOTAL_SOFT_LIMIT_BYTES,
  `CSS total ultrapassou ${CSS_TOTAL_SOFT_LIMIT_BYTES.toLocaleString('pt-BR')} bytes normalizados; reduza duplicações antes de adicionar novas regras`,
)
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
const typecheckDisabledFiles = typedCoreFiles
  .filter((file) => /^\s*\/\/\s*@ts-nocheck\b/m.test(fs.readFileSync(file, 'utf8')))
  .map(relativePath)
  .sort()
assert.deepEqual(
  typecheckDisabledFiles,
  [...TYPECHECK_DEBT_ALLOWLIST].sort(),
  'A dívida de @ts-nocheck deve apenas diminuir; remova o arquivo da allowlist ao tipá-lo e não adicione novas exceções',
)
const explicitAny = /\b(?:as|satisfies)\s+any\b|:\s*any\b|<any>/g
const unsafeTypeHits = typedCoreFiles.flatMap((file) => {
  const relativePath = path.relative(repositoryRoot, file)
  return [...fs.readFileSync(file, 'utf8').matchAll(explicitAny)].map(() => relativePath)
})
assert.deepEqual(unsafeTypeHits, [], `Tipos any explícitos na camada TypeScript central: ${unsafeTypeHits.join(', ')}`)

for (const [componentName, expectedOwner] of [
  ['InfraDetailPanel', 'src/features/education/components/SchoolInfrastructureDetail.jsx'],
  ['SchoolInfrastructureCombinedDetail', 'src/features/education/components/SchoolInfrastructureDetail.jsx'],
  ['SchoolInfrastructureIndicatorDetail', 'src/features/education/components/SchoolInfrastructureDetail.jsx'],
  ['IndicatorSegmentedControl', 'src/features/education/components/EducationIndicatorSegmentedControl.tsx'],
  ['EducationSourceNotes', 'src/features/education/components/EducationSourceNotes.tsx'],
  ['dataSourceContextForEducation', 'src/features/education/components/EducationSourceNotes.tsx'],
  ['EducationIndicatorBreakdown', 'src/features/education/components/EducationIndicatorSupportData.jsx'],
  ['ExploreItem', 'src/features/education/components/EducationIndicatorSupportData.jsx'],
  ['EducationCompactComparison', 'src/features/education/components/EducationIndicatorSupportData.jsx'],
  ['AgeRangeDetail', 'src/features/education/components/EducationDemographicDetails.jsx'],
  ['ModalityDetail', 'src/features/education/components/EducationDemographicDetails.jsx'],
  ['ColorRaceDetail', 'src/features/education/components/EducationDemographicDetails.jsx'],
]) {
  const owners = scriptFiles
    .filter((file) => callableNames(file).has(componentName))
    .map(relativePath)
  assert.deepEqual(
    owners,
    [expectedOwner],
    `${componentName} deve permanecer no módulo responsável pela respectiva fronteira visual`,
  )
}

assert.doesNotMatch(
  read('src/features/education/components/EducationIndicatorDetailView.tsx'),
  /function\s+(?:InfraDetailPanel|SchoolInfrastructureCombinedDetail|SchoolInfrastructureIndicatorDetail|EducationIndicatorBreakdown|ExploreItem|AgeRangeDetail|ModalityDetail|ColorRaceDetail)\b/,
  'EducationIndicatorDetailView deve orquestrar, não reimplementar, infraestrutura ou dados de apoio',
)

const quickReadingOwners = scriptFiles
  .filter((file) => callableNames(file).has('QuickReadingList'))
  .map(relativePath)
assert.deepEqual(
  quickReadingOwners,
  ['src/components/QuickReadingList.tsx'],
  'QuickReadingList deve ter uma única implementação visual compartilhada',
)

const quickReadingMarkupOwners = scriptFiles
  .filter((file) => jsxClassTokens(file).has('platform-quick-reading'))
  .map(relativePath)
assert.deepEqual(
  quickReadingMarkupOwners,
  ['src/components/QuickReadingList.tsx'],
  'A marcação visual de QuickReadingList deve existir somente na primitiva compartilhada',
)

for (const [componentName, expectedOwner] of [
  ['EducationQuickReading', 'src/components/EducationQuickReading.tsx'],
  ['FinancialQuickReading', 'src/components/FinancialQuickReading.tsx'],
]) {
  const owners = scriptFiles
    .filter((file) => callableNames(file).has(componentName))
    .map(relativePath)
  assert.deepEqual(
    owners,
    [expectedOwner],
    `${componentName} deve permanecer como adaptador único do respectivo domínio`,
  )
}

assert.doesNotMatch(
  sourceCorpus,
  /education-quick-reading__(?:icon|list)/,
  'Classes internas legadas de Educação não devem reaparecer na primitiva de plataforma',
)
assert.doesNotMatch(
  read('src/App.css'),
  /\.(?:education|financial)-quick-reading\b/,
  'Estilos de leitura rápida dos domínios pertencem aos respectivos CSS, não ao App.css',
)
assert.doesNotMatch(
  read('src/components/FinancialIndicatorPrimitives.jsx'),
  /EducationQuickReading/,
  'Primitivas financeiras não devem depender do adaptador visual de Educação',
)

assert.doesNotMatch(
  read('src/components/MetaCard.jsx'),
  /from\s+['"]\.\/IndicatorDetail(?:\.jsx)?['"]/,
  'MetaCard não deve depender do componente de detalhe para decisões puras de apresentação',
)

for (const helperName of [
  'formatApproximateDifference',
  'formatApproximatePercent',
  'isApproximateIndicator',
  'isComparableIndicator',
]) {
  const owners = scriptFiles
    .filter((file) => callableNames(file).has(helperName))
    .map(relativePath)
  assert.deepEqual(
    owners,
    ['src/utils/pneIndicatorPresentation.js'],
    `${helperName} deve permanecer centralizado na apresentação pura de PNE`,
  )
}

console.log('UI architecture validation passed: cascata, budgets de CSS, primitivas compartilhadas e dívida tipada.')
