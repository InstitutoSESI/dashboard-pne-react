import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../src/experiences/pme/pmeRoutes.ts', import.meta.url), 'utf8')
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText
const { buildPmeHash, parsePmeHash, pmeLink, PME_PAGES } = await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`)

test('PME inicia sem município e não restaura rotas ou conteúdo de outra experiência', () => {
  const route = parsePmeHash('')
  assert.equal(route.page, 'apresentacao')
  assert.equal(route.municipalityId, null)
  assert.equal(route.error, null)
  assert.ok(parsePmeHash('#pne2026?municipio=nova-santa-rita').error)
  assert.doesNotMatch(source, /localStorage|sessionStorage/)
  assert.equal(parsePmeHash('#inicio?municipio=4313375').page, 'inicio', 'o link do panorama existente permanece válido')
})

test('links diretos de todas as páginas mantêm IBGE e filtros públicos na recarga', () => {
  for (const page of Object.keys(PME_PAGES)) {
    const hash = buildPmeHash(page, { municipalityId: '4313375', objectiveId: '19', themeId: 'financiamento', reportKind: 'caderno', evidenceFilter: 'lacunas' })
    const route = parsePmeHash(hash)
    assert.equal(route.error, null)
    assert.equal(route.page, page)
    assert.equal(route.municipalityId, '4313375')
    assert.equal(route.objectiveId, '19')
    assert.equal(route.themeId, 'financiamento')
    assert.equal(route.reportKind, 'caderno')
    assert.equal(route.evidenceFilter, 'lacunas')
    assert.equal(buildPmeHash(page, route), hash)
  }
})

test('troca de município preserva objetivo e filtro sem carregar ID anterior ou slug', () => {
  const original = parsePmeHash('#objetivo?municipio=4313375&objetivo=9&tema=modalidades')
  const next = parsePmeHash(pmeLink(original, 'objetivo', { municipalityId: '4314902' }))
  assert.equal(next.municipalityId, '4314902')
  assert.equal(next.objectiveId, '9')
  assert.equal(next.themeId, 'modalidades')
  assert.equal(next.error, null)
  assert.equal(parsePmeHash(pmeLink(next, 'inicio', { municipalityId: null })).municipalityId, null)
})

test('identidade, objetivo e seleções ambíguas falham explicitamente', () => {
  for (const hash of [
    '#objetivo?municipio=4313375', '#objetivo?objetivo=20', '#objetivo?objetivo=0',
    '#inicio?municipio=2700102', '#inicio?municipio=nova-santa-rita', '#inicio?municipio=4313375.0',
    '#inicio?municipio=4313375&municipio=4314902', '#relatorios?relatorio=editor',
    '#evidencias?situacao=inventada', '#evidencias?relacao=../dados',
  ]) assert.ok(parsePmeHash(hash).error, hash)
})

test('navegar da evidência à ficha mantém município e limpa somente a relação específica', () => {
  const route = parsePmeHash('#evidencias?municipio=4313375&objetivo=1&relacao=relation.1.a.creche')
  assert.equal(route.relationId, 'relation.1.a.creche')
  const sheet = parsePmeHash(pmeLink(route, 'objetivo'))
  assert.equal(sheet.municipalityId, '4313375')
  assert.equal(sheet.objectiveId, '1')
  assert.equal(sheet.relationId, null)
})
