import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { after, before, test } from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

let buildFinancialQuickReadingItems
let compiledModuleDirectory
let EducationIndicatorQuickReading
let FinancialQuickReading
let QuickReadingList

async function compileModule(sourcePath, outputName, rewriteImports = (source) => source) {
  const absoluteSourcePath = path.join(repositoryRoot, sourcePath)
  const source = await readFile(absoluteSourcePath, 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: absoluteSourcePath,
  }).outputText
  const outputPath = path.join(compiledModuleDirectory, outputName)
  await writeFile(outputPath, rewriteImports(compiled), 'utf8')
  return outputPath
}

before(async () => {
  compiledModuleDirectory = await mkdtemp(path.join(repositoryRoot, 'node_modules', '.quick-reading-render-'))
  await compileModule('src/components/QuickReadingHeading.jsx', 'QuickReadingHeading.mjs')
  const sharedModulePath = await compileModule(
    'src/components/QuickReadingList.tsx',
    'QuickReadingList.mjs',
    (source) => source.replace(
      /from ['"]\.\/QuickReadingHeading['"]/,
      "from './QuickReadingHeading.mjs'",
    ),
  )
  await compileModule(
    'src/components/EducationQuickReading.tsx',
    'EducationQuickReading.mjs',
    (source) => source.replace(
      /from ['"]\.\/QuickReadingList['"]/,
      "from './QuickReadingList.mjs'",
    ),
  )
  const educationAdapterPath = await compileModule(
    'src/features/education/components/EducationIndicatorQuickReading.tsx',
    'EducationIndicatorQuickReading.mjs',
    (source) => source.replace(
      /from ['"]\.\.\/\.\.\/\.\.\/components\/EducationQuickReading['"]/,
      "from './EducationQuickReading.mjs'",
    ),
  )
  const financialAdapterPath = await compileModule(
    'src/components/FinancialQuickReading.tsx',
    'FinancialQuickReading.mjs',
    (source) => source.replace(
      /from ['"]\.\/QuickReadingList['"]/,
      "from './QuickReadingList.mjs'",
    ),
  )
  ;({ QuickReadingList } = await import(pathToFileURL(sharedModulePath).href))
  ;({ EducationIndicatorQuickReading } = await import(pathToFileURL(educationAdapterPath).href))
  ;({ buildFinancialQuickReadingItems, FinancialQuickReading } = await import(pathToFileURL(financialAdapterPath).href))
})

after(async () => {
  if (compiledModuleDirectory) await rm(compiledModuleDirectory, { force: true, recursive: true })
})

test('shared quick reading preserves zero and omits non-renderable content', () => {
  const html = renderToStaticMarkup(createElement(QuickReadingList, {
    items: [
      { key: 'zero', label: 'Zero observado', text: 0 },
      { key: 'false', label: 'Booleano', text: false },
      { key: 'empty', label: 'Vazio', text: '' },
      { key: 'spaces', label: 'Espaços', text: '   ' },
      { key: 'null', label: 'Nulo', text: null },
      { key: 'undefined', label: 'Indefinido', text: undefined },
      { key: 'warning', label: 'Com alerta', text: 'Conteúdo', warning: 0 },
    ],
  }))

  assert.equal((html.match(/<li(?:>|\s)/g) ?? []).length, 2)
  assert.match(html, /class="interpretation-box platform-quick-reading"/)
  assert.match(html, /Zero observado/)
  assert.match(html, /<p>0<\/p>/)
  assert.match(html, /<small>0<\/small>/)
  assert.doesNotMatch(html, /Booleano|Vazio|Espaços|Nulo|Indefinido/)
})

test('education adapter renders a valid cut-only quick reading', () => {
  const html = renderToStaticMarkup(createElement(EducationIndicatorQuickReading, {
    cutLabel: 'Total do município',
  }))

  assert.equal((html.match(/<li(?:>|\s)/g) ?? []).length, 1)
  assert.match(html, /platform-quick-reading education-quick-reading/)
  assert.match(html, /Recorte exibido/)
  assert.match(html, /<strong>Total do município<\/strong>/)
})

test('financial adapter renders fallbacks, zero and the preserved cut icon', () => {
  const props = {
    description: 'Descrição de fallback',
    indicator: {
      currentYear: 2024,
      initialYear: 2022,
      quickReading: 'Leitura do modelo',
    },
    metadata: { measures: 'Descrição dos metadados' },
    readingGuide: { oQueMede: 'Descrição do guia' },
    text: 0,
  }
  const items = buildFinancialQuickReadingItems(props)
  const html = renderToStaticMarkup(createElement(FinancialQuickReading, props))

  assert.equal(items[1].text, 'Descrição do guia')
  assert.equal(items[2].icon, 'cut')
  assert.equal((html.match(/<li(?:>|\s)/g) ?? []).length, 3)
  assert.match(html, /aria-label="Leitura rápida do indicador"/)
  assert.match(html, /platform-quick-reading financial-quick-reading/)
  assert.doesNotMatch(html, /education-quick-reading/)
  assert.match(html, /<p>0<\/p>/)
  assert.match(html, /Descrição do guia/)
  assert.doesNotMatch(html, /Descrição dos metadados|Descrição de fallback/)
  assert.match(html, /<strong>2022 a 2024<\/strong>/)
  assert.match(html, /lucide-list-filter/)
})
