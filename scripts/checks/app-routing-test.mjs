import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-routing-'))
writeFileSync(path.join(temporaryOutput, 'package.json'), '{"type":"module"}\n')
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
const {
  NAV_GROUPS,
  buildHashPageMap,
  getOwnerGroupId,
} = await import(compiledModule('src/app/navigationRegistry.js'))
const { resolveEducationNavigation } = await import(compiledModule('src/data/educationIndicatorCatalog.js'))
const {
  ANALYTICS_PRODUCTS,
  isPageNavigable,
  isProductEnabledFor,
  resolvePageProduct,
} = await import(compiledModule('src/config/analyticsProducts.js'))
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
  ['#matriz-prioridades', 'matriz-prioridades'],
  ['#matrizprioridades', 'matriz-prioridades'],
  ['#cenarios-da-educacao', 'cenarios-educacao'],
  ['#cenarios-da-educacao?municipio=nova-santa-rita', 'cenarios-educacao'],
  ['#cenarios-educacao', 'cenarios-educacao'],
  ['#pne2014', 'pne2014'],
  ['#pne2014?detalhe=alfabetizacao', 'pne2014'],
  ['#pne2024', 'pne2014'],
  ['#/PNE-2024', 'pne2014'],
  ['#pne2026', 'pne2026'],
  ['#diagnostico', 'diagnostico'],
  ['#educacao', 'educacao'],
  ['#relatorio-tecnico-municipal', 'relatorio-tecnico-municipal'],
  ['#analise-regional', 'analise-regional'],
  ['#analise-regional?municipio=nova-santa-rita', 'analise-regional'],
  ['#regiao', 'analise-regional'],
  ['#vocacoes-da-regiao', 'vocacoes-regiao'],
  ['#vocacoes-da-regiao?municipio=nova-santa-rita', 'vocacoes-regiao'],
  ['#/Analise-Regional', 'analise-regional'],
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
  // Caderno de hipoteses removido em 2026-08-24 (plano de reorganizacao, D7):
  // as rotas aposentadas caem no fallback da pagina inicial, nao ressuscitam.
  ['#caderno', 'home'],
  ['#caderno-de-hipoteses', 'home'],
]

test('resolve todas as rotas e aliases vigentes', () => {
  for (const [hash, expectedPage] of ROUTE_CASES) {
    assert.equal(resolveActivePageFromHash(hash), expectedPage, hash || '(hash vazio)')
  }
})

/*
 * A reorganização pode acrescentar rota, nunca aposentar uma sem decisão
 * registrada. O mapa abaixo é o de antes da reorganização; ele precisa
 * continuar inteiro dentro do mapa atual, e cada rota nova aparece nomeada na
 * lista de acréscimos — quem adicionar uma sem declarar aqui quebra o teste.
 */
test('o registro preserva o mapa de hashes anterior e declara cada acréscimo', () => {
  const FROZEN_MAP = {
    home: 'home',
    pneoverview: 'pne-overview',
    pnelegalgoals: 'pne-legal-goals',
    metaslegais: 'pne-legal-goals',
    matrizprioridades: 'matriz-prioridades',
    cenariosdaeducacao: 'cenarios-educacao',
    cenariosdaeducacaomunicipal: 'cenarios-educacao',
    cenarioseducacao: 'cenarios-educacao',
    pne2014: 'pne2014',
    pne2024: 'pne2014',
    pne2026: 'pne2026',
    diagnostico: 'diagnostico',
    educacao: 'educacao',
    relatoriotecnicomunicipal: 'relatorio-tecnico-municipal',
    financeiros: FINANCIAL_PAGE_KEYS.overview,
    financeirospanorama: FINANCIAL_PAGE_KEYS.panorama,
    panoramafinanceiro: FINANCIAL_PAGE_KEYS.panorama,
    financeirosaplicacaorecursos: FINANCIAL_PAGE_KEYS.application,
    financeirosfundeb: FINANCIAL_PAGE_KEYS.fundeb,
    financeirospnate: FINANCIAL_PAGE_KEYS.pnate,
    financeirosvaar: FINANCIAL_PAGE_KEYS.vaar,
    fundeb: FINANCIAL_PAGE_KEYS.fundeb,
    pnate: FINANCIAL_PAGE_KEYS.pnate,
    siope: FINANCIAL_PAGE_KEYS.application,
    vaar: FINANCIAL_PAGE_KEYS.vaar,
    sistemas: 'educacao',
    escolassistemas: 'educacao',
  }

  // Acréscimos deliberados, na ordem em que entraram.
  const ADDED_ROUTES = {
    // Fase 5 da reorganização: Análise Regional.
    analiseregional: 'analise-regional',
    regiao: 'analise-regional',
    // Fase 6: slot do Vocações da Região, fechado até a pesquisa publicar.
    vocacoesdaregiao: 'vocacoes-regiao',
  }

  const actual = buildHashPageMap()
  for (const [route, page] of Object.entries(FROZEN_MAP)) {
    assert.equal(actual[route], page, `a rota ${route} deixou de resolver`)
  }
  assert.deepEqual(
    Object.keys(actual).filter((route) => !(route in FROZEN_MAP)).sort(),
    Object.keys(ADDED_ROUTES).sort(),
  )
  for (const [route, page] of Object.entries(ADDED_ROUTES)) {
    assert.equal(actual[route], page)
  }
})

test('Panorama educacional permanece apenas no grupo canônico de indicadores', () => {
  const reportsGroup = NAV_GROUPS.find((group) => group.id === 'relatorios')
  const educationGroup = NAV_GROUPS.find((group) => group.id === 'educacao')

  assert.ok(reportsGroup)
  assert.ok(educationGroup)
  assert.equal(
    reportsGroup.items.some((item) => item.target === 'educacao?secao=panorama'),
    false,
  )
  assert.equal(educationGroup.dynamicItems, 'education-sections')
  assert.equal(getOwnerGroupId('educacao'), 'educacao')
})

/*
 * Análise Regional é o primeiro grupo cuja existência depende de configuração
 * de UF, e não de publicação de produto. O gate vive no cabeçalho, marcado no
 * registro como condição do item: uma UF sem mapa regional não vê o item, e o
 * grupo desaparece junto quando sobra vazio.
 */
test('o grupo Análise Regional reúne o panorama e os cenários, cada um com seu gate', () => {
  const group = NAV_GROUPS.find((candidate) => candidate.id === 'analise-regional')
  assert.ok(group)
  assert.deepEqual(
    group.items.map((item) => [item.key, item.target, item.condition]),
    [
      ['analise-regional', 'analise-regional', 'regional'],
      ['cenarios-educacao', 'cenarios-da-educacao', 'foresight'],
      ['vocacoes-regiao', 'vocacoes-da-regiao', 'vocacoes'],
    ],
  )
  assert.equal(getOwnerGroupId('analise-regional'), 'analise-regional')
  assert.equal(getOwnerGroupId('cenarios-educacao'), 'analise-regional')

  const pneGroup = NAV_GROUPS.find((candidate) => candidate.id === 'pne')
  assert.equal(pneGroup.items.some((item) => item.key === 'cenarios-educacao'), false)

  const header = readFileSync(new URL('../../src/components/Header.jsx', import.meta.url), 'utf8')
  assert.match(header, /item\.condition === 'regional' && !REGIONAL_ANALYSIS_AVAILABLE/)
  assert.match(header, /\.filter\(\(block\) => block\.items\.length > 0\)/)
  assert.match(header, /withVocacoesItem\(block, vocacoesVisible\)/)
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

test('cada página analítica pertence a exatamente um produto declarado', () => {
  assert.deepEqual([...ANALYTICS_PRODUCTS], ['pne', 'educacao', 'financiamento'])
  assert.equal(resolvePageProduct('home'), null)
  assert.equal(resolvePageProduct('pne2026'), 'pne')
  assert.equal(resolvePageProduct('diagnostico'), 'pne')
  assert.equal(resolvePageProduct('matriz-prioridades'), 'pne')
  assert.equal(resolvePageProduct('cenarios-educacao'), 'pne')
  assert.equal(resolvePageProduct('educacao'), 'educacao')
  assert.equal(resolvePageProduct('relatorio-tecnico-municipal'), 'educacao')
  assert.equal(resolvePageProduct('analise-regional'), 'educacao')
  assert.equal(resolvePageProduct('vocacoes-regiao'), 'educacao')
  for (const pageKey of Object.values(FINANCIAL_PAGE_KEYS)) {
    assert.equal(resolvePageProduct(pageKey), 'financiamento')
  }
})

test('publicação completa libera todos os produtos', () => {
  for (const product of ANALYTICS_PRODUCTS) {
    assert.equal(isProductEnabledFor('complete', null, product), true)
  }
  assert.equal(isPageNavigable('financeiros-fundeb', 'complete', null), true)
})

test('publicação identity-only não libera produto algum', () => {
  for (const product of ANALYTICS_PRODUCTS) {
    assert.equal(isProductEnabledFor('identity-only', null, product), false)
  }
  assert.equal(isPageNavigable('educacao', 'identity-only', null), false)
  assert.equal(isPageNavigable('home', 'identity-only', null), true)
})

test('publicação parcial navega o produto declarado e barra os demais', () => {
  const enabled = ['educacao']
  assert.equal(isProductEnabledFor('partial', enabled, 'educacao'), true)
  assert.equal(isProductEnabledFor('partial', enabled, 'pne'), false)
  assert.equal(isProductEnabledFor('partial', enabled, 'financiamento'), false)

  assert.equal(isPageNavigable('home', 'partial', enabled), true)
  assert.equal(isPageNavigable('educacao', 'partial', enabled), true)
  assert.equal(isPageNavigable('relatorio-tecnico-municipal', 'partial', enabled), true)
  assert.equal(isPageNavigable('pne2026', 'partial', enabled), false)
  assert.equal(isPageNavigable('diagnostico', 'partial', enabled), false)
  assert.equal(isPageNavigable('cenarios-educacao', 'partial', enabled), false)
  assert.equal(isPageNavigable(FINANCIAL_PAGE_KEYS.panorama, 'partial', enabled), false)

  // Uma rota barrada continua resolvendo para a mesma página: o aviso de
  // indisponibilidade é do roteador, não do parser de hash.
  assert.equal(resolveActivePageFromHash('#pne2026?municipio=maceio'), 'pne2026')
})

test('publicação parcial sem lista não libera nada', () => {
  for (const product of ANALYTICS_PRODUCTS) {
    assert.equal(isProductEnabledFor('partial', null, product), false)
    assert.equal(isProductEnabledFor('partial', [], product), false)
  }
})
