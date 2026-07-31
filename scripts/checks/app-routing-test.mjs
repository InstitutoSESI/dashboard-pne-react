import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-routing-'))
execFileSync(
  process.execPath,
  [
    path.resolve('node_modules/typescript/bin/tsc'),
    '--project',
    'scripts/checks/tsconfig.app-routing.json',
    '--outDir',
    temporaryOutput,
  ],
  { stdio: 'inherit' },
)

process.on('exit', () => rmSync(temporaryOutput, { force: true, recursive: true }))

const compiledModule = (relativePath) => pathToFileURL(path.join(temporaryOutput, relativePath)).href

const { FINANCIAL_PAGE_KEYS } = await import(compiledModule('src/data/financialPageKeys.js'))
const {
  buildAppHash,
  mergeHashAndSearchParams,
  normalizeRouteValue,
  parseAppHash,
  parseAppLocation,
} = await import(compiledModule('src/app/appHash.js'))
const {
  getActivePageFromLocation,
  getNavigationContextFromLocation,
  resolveActivePage,
  resolveActivePageFromHash,
} = await import(compiledModule('src/app/appRoutes.js'))
const { resolveEducationNavigation } = await import(compiledModule('src/data/educationIndicatorCatalog.js'))
const {
  getHashContext,
  mergeHashContext,
  replaceHashContext,
  setHashContext,
} = await import(compiledModule('src/utils/hashNavigation.js'))

test('merges educational navigation without losing municipality or compatible parameters', () => {
  const fakeLocation = {
    hash: '#educacao?municipio=sapucaia-do-sul&secao=atendimento&detalhe=mat-infantil&tema=matriculas',
  }

  mergeHashContext('educacao', { municipio: 'alto-feliz', detalhe: null }, fakeLocation)
  assert.equal(
    fakeLocation.hash,
    '#educacao?municipio=alto-feliz&secao=atendimento&tema=matriculas',
  )

  replaceHashContext('educacao', { municipio: 'sapucaia-do-sul' }, fakeLocation)
  assert.equal(
    fakeLocation.hash,
    '#educacao?municipio=sapucaia-do-sul&secao=atendimento&tema=matriculas',
  )
})

test('builds detail links with the canonical municipal slug', () => {
  assert.equal(
    buildAppHash('educacao', {
      municipio: 'sapucaia-do-sul',
      secao: 'atendimento',
      detalhe: 'mat-infantil',
    }),
    '#educacao?municipio=sapucaia-do-sul&secao=atendimento&detalhe=mat-infantil',
  )
  assert.equal(
    buildAppHash('educacao', {
      municipio: 'sapucaia-do-sul',
      secao: 'atendimento',
      detalhe: 'mat-fundamental',
    }),
    '#educacao?municipio=sapucaia-do-sul&secao=atendimento&detalhe=mat-fundamental',
  )
})

const ROUTE_CASES = [
  ['', 'home'],
  ['#home', 'home'],
  ['#/Home', 'home'],
  ['#pne-overview', 'pne-overview'],
  ['#pneoverview', 'pne-overview'],
  ['#pne-legal-goals', 'pne-legal-goals'],
  ['#pnelegalgoals', 'pne-legal-goals'],
  ['#metas-legais', 'pne-legal-goals'],
  ['#pne2014', 'pne2014'],
  ['#pne2014?detalhe=alfabetizacao', 'pne2014'],
  ['#pne2024', 'pne2014'],
  ['#/PNE-2024', 'pne2014'],
  ['#pne2026', 'pne2026'],
  ['#diagnostico', 'diagnostico'],
  ['#educacao', 'educacao'],
  ['#relatorio-tecnico-municipal', 'relatorio-tecnico-municipal'],
  ['#financeiros', FINANCIAL_PAGE_KEYS.overview],
  ['#financeiros-panorama', FINANCIAL_PAGE_KEYS.panorama],
  ['#panorama-financeiro', FINANCIAL_PAGE_KEYS.panorama],
  ['#financeiros-aplicacao-recursos', FINANCIAL_PAGE_KEYS.application],
  ['#financeiros-fundeb', FINANCIAL_PAGE_KEYS.fundeb],
  ['#financeiros-pnate', FINANCIAL_PAGE_KEYS.pnate],
  ['#financeiros-vaar', FINANCIAL_PAGE_KEYS.vaar],
  ['#fundeb', FINANCIAL_PAGE_KEYS.fundeb],
  ['#pnate', FINANCIAL_PAGE_KEYS.pnate],
  ['#siope', FINANCIAL_PAGE_KEYS.application],
  ['#vaar', FINANCIAL_PAGE_KEYS.vaar],
  ['#sistemas', 'educacao'],
  ['#escolas-sistemas', 'educacao'],
  ['#rota-inexistente', 'home'],
]

test('resolve todas as rotas e aliases vigentes', () => {
  for (const [hash, expectedPage] of ROUTE_CASES) {
    assert.equal(resolveActivePageFromHash(hash), expectedPage, hash || '(hash vazio)')
  }
})

test('preserva acesso direto ao detalhe de alfabetizacao no ciclo encerrado', () => {
  const parsed = parseAppHash('#pne2014?detalhe=alfabetizacao')
  assert.equal(parsed.route, 'pne2014')
  assert.equal(parsed.params.get('detalhe'), 'alfabetizacao')
})

test('normaliza letras, acentos e caracteres especiais', () => {
  assert.equal(normalizeRouteValue('Aplicação de Recursos'), 'aplicacaoderecursos')
  assert.equal(resolveActivePageFromHash('#/FINANCEIROS—FUNDEB'), FINANCIAL_PAGE_KEYS.fundeb)
  assert.deepEqual(
    {
      route: parseAppHash('#/Educação?secao=trajetoria').route,
      section: parseAppHash('#/Educação?secao=trajetoria').params.get('secao'),
    },
    { route: 'educacao', section: 'trajetoria' },
  )
})

test('resolve módulos financeiros no hash', () => {
  for (const [hash, expectedPage] of [
    ['#financeiros?modulo=fundeb', FINANCIAL_PAGE_KEYS.fundeb],
    ['#financeiros?module=pnate', FINANCIAL_PAGE_KEYS.pnate],
    ['#financeiros?modulo=vaar', FINANCIAL_PAGE_KEYS.vaar],
    ['#financeiros?modulo=complementacao-vaar', FINANCIAL_PAGE_KEYS.vaar],
    ['#financeiros?module=siope', FINANCIAL_PAGE_KEYS.application],
    ['#financeiros?modulo=siope', FINANCIAL_PAGE_KEYS.application],
    ['#financeiros?module=aplicacao-recursos', FINANCIAL_PAGE_KEYS.application],
    ['#financeiros?modulo=FUNDEB', FINANCIAL_PAGE_KEYS.fundeb],
    ['#financeiros?modulo=desconhecido', FINANCIAL_PAGE_KEYS.overview],
  ]) {
    assert.equal(resolveActivePageFromHash(hash), expectedPage, hash)
  }
})

test('combina parâmetros com prioridade do hash e constrói hashes sem vazios', () => {
  const location = { hash: '#educacao?secao=trajetoria&tema=fluxo', search: '?secao=oferta&detalhe=indicador-a&module=fundeb' }
  const context = getNavigationContextFromLocation(location)
  assert.equal(context.params.get('secao'), 'trajetoria')
  assert.equal(context.params.get('tema'), 'fluxo')
  assert.equal(context.params.get('detalhe'), 'indicador-a')
  assert.equal(context.params.get('module'), 'fundeb')
  assert.equal(resolveActivePage(context), 'educacao')
  assert.equal(buildAppHash('educacao', { detalhe: '', secao: 'trajetoria', tema: null, theme: 'fluxo' }), '#educacao?secao=trajetoria&theme=fluxo')
  assert.deepEqual(
    [...mergeHashAndSearchParams('secao=trajetoria', 'secao=oferta&detalhe=x').entries()],
    [['secao', 'trajetoria'], ['detalhe', 'x']],
  )
})

test('preserva município e contexto educacional na rota do panorama financeiro', () => {
  const hash = buildAppHash(FINANCIAL_PAGE_KEYS.panorama, {
    municipio: 'agudo',
    indicatorId: 'creche,alfabetizacao',
    programId: 'salario_educacao_qsem,fundeb_vaar',
  })
  const parsed = parseAppHash(hash)
  assert.equal(resolveActivePage(parsed), FINANCIAL_PAGE_KEYS.panorama)
  assert.equal(parsed.params.get('municipio'), 'agudo')
  assert.equal(parsed.params.get('indicatorId'), 'creche,alfabetizacao')
  assert.equal(parsed.params.get('programId'), 'salario_educacao_qsem,fundeb_vaar')
})

test('mantém parse → build → parse e o adaptador compatível', () => {
  const built = buildAppHash('financeiros', { detalhe: 'receitas', modulo: 'fundeb' })
  const parsed = parseAppHash(built)
  assert.equal(parsed.route, 'financeiros')
  assert.equal(parsed.params.get('modulo'), 'fundeb')
  assert.equal(parsed.params.get('detalhe'), 'receitas')

  const fakeLocation = { hash: '#educacao?tema=matriculas', search: '?secao=oferta' }
  const legacyContext = getHashContext(fakeLocation)
  assert.equal(legacyContext.route, 'educacao')
  assert.equal(legacyContext.params.get('tema'), 'matriculas')
  assert.equal(legacyContext.params.get('secao'), 'oferta')
  setHashContext('educacao', { detalhe: '', secao: 'trajetoria', tema: 'fluxo' }, fakeLocation)
  assert.equal(fakeLocation.hash, '#educacao?secao=trajetoria&tema=fluxo')
})

test('resolve Educação sem acesso a window', () => {
  const education = resolveEducationNavigation({
    route: 'educacao',
    hashParams: new URLSearchParams('detalhe=taxa_aprovacao&secao=oferta&tema=aprendizagem'),
    searchParams: new URLSearchParams('detalhe=matriculas&secao=trajetoria&theme=fluxo'),
  })
  assert.equal(education.detailKey, 'taxa_aprovacao')
  assert.equal(education.section, 'modalidades')
  assert.equal(education.requestedTheme, 'aprendizagem')

  const systems = resolveEducationNavigation({ route: 'escolas-sistemas' })
  assert.equal(systems.section, 'modalidades')
  assert.equal(systems.hasSystemTheme, true)
  assert.equal(resolveEducationNavigation({ route: 'pne2014' }), null)
})

test('resolve visão geral, panorama, aliases históricos e relatório técnico', () => {
  const resolveSection = (secao) => resolveEducationNavigation({
    route: 'educacao',
    hashParams: new URLSearchParams(`secao=${secao}`),
  }).section

  assert.equal(resolveSection('visao-geral'), 'visao-geral')
  assert.equal(resolveSection('panorama'), 'panorama')
  assert.equal(resolveSection('panorama-educacional'), 'panorama')
  assert.equal(resolveSection('visao-geral-municipal'), 'panorama')
  assert.equal(resolveSection('educacao-superior'), 'educacao-superior')
  assert.equal(resolveSection('superior'), 'educacao-superior')
  assert.equal(resolveSection('ensino-superior'), 'educacao-superior')
  assert.equal(resolveSection('relatorio-tecnico-municipal'), 'relatorio-tecnico-municipal')

  const technicalReport = resolveEducationNavigation({
    route: 'relatorio-tecnico-municipal',
    hashParams: new URLSearchParams('municipio=porto-alegre'),
  })
  assert.equal(technicalReport.section, 'relatorio-tecnico-municipal')

  const higherEducationDetail = resolveEducationNavigation({
    route: 'educacao',
    hashParams: new URLSearchParams('secao=educacao-superior&detalhe=esup-docentes&municipio=porto-alegre'),
  })
  assert.equal(higherEducationDetail.section, 'educacao-superior')
  assert.equal(higherEducationDetail.detailKey, 'esup-docentes')

  const aeeDetail = resolveEducationNavigation({
    route: 'educacao',
    hashParams: new URLSearchParams('detalhe=aee&municipio=alegrete'),
  })
  assert.equal(aeeDetail.section, 'modalidades')
  assert.equal(aeeDetail.detailKey, 'aee')

  for (const alias of ['quadra_esportes', 'esgoto_rede_publica']) {
    const legacyInfrastructure = resolveEducationNavigation({
      route: 'educacao',
      hashParams: new URLSearchParams(`secao=infraestrutura&detalhe=${alias}&dimensao=${alias}`),
    })
    assert.equal(legacyInfrastructure.section, 'infraestrutura')
    assert.equal(legacyInfrastructure.detailKey, 'infraestrutura-basica')
    assert.equal('dimensionKey' in legacyInfrastructure, false)
  }
})

test('adapta location e mantém o fallback da página inicial', () => {
  assert.equal(getActivePageFromLocation({ hash: '#pne2026' }), 'pne2026')
  assert.equal(getActivePageFromLocation(null), 'home')
  assert.deepEqual(parseAppLocation(), {
    hashParams: new URLSearchParams(),
    params: new URLSearchParams(),
    rawRoute: '',
    route: '',
    searchParams: new URLSearchParams(),
  })
})
