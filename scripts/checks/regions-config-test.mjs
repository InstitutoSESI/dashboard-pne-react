/*
 * Contrato do mapa regional (`config/regions/<uf>.json`).
 *
 * O mapa é a única fonte do recorte regional da plataforma. Este teste congela
 * três coisas: que ele particiona o registro municipal da UF sem sobra nem
 * duplicata, que o parser recusa cada forma de mapa quebrado em vez de aceitar
 * um recorte parcial, e que o nome da instituição que mantém o recorte não
 * vaza para nenhum texto público — nem em rótulo, nem em slug, nem na
 * proveniência.
 *
 * A ausência de mapa é comportamento declarado, não falha: uma UF sem arquivo
 * simplesmente não tem análise regional.
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import {
  REGIONS_CONFIG_SCHEMA_VERSION,
  loadRegionsConfig,
  parseRegionsConfig,
  regionsConfigPath,
} from '../lib/state-build-profile.mjs'

const repoRoot = path.resolve(fileURLToPath(new URL('../..', import.meta.url)))

const readJson = (relativePath) =>
  JSON.parse(readFileSync(path.join(repoRoot, relativePath), 'utf8'))

const rsRegistry = readJson('config/municipalities/rs.json')
const rsRegions = readJson('config/regions/rs.json')
const clone = () => structuredClone(rsRegions)

test('o mapa do RS particiona o registro municipal sem sobra nem duplicata', () => {
  const parsed = parseRegionsConfig(rsRegions, 'RS', rsRegistry)
  assert.equal(parsed.schemaVersion, REGIONS_CONFIG_SCHEMA_VERSION)
  assert.equal(parsed.stateCode, 'RS')
  assert.equal(parsed.municipalityCount, rsRegistry.municipalityCount)

  const owners = new Map()
  for (const region of parsed.regions) {
    assert.equal(region.municipalityCount, region.municipalityIbgeCodes.length)
    for (const code of region.municipalityIbgeCodes) {
      assert.equal(owners.has(code), false, `município ${code} em mais de uma região`)
      owners.set(code, region.slug)
    }
  }
  const registryCodes = rsRegistry.municipalities.map(({ ibgeCode }) => ibgeCode).toSorted()
  assert.deepEqual([...owners.keys()].toSorted(), registryCodes)
})

test('cada município do RS resolve exatamente uma região', () => {
  const parsed = parseRegionsConfig(rsRegions, 'RS', rsRegistry)
  for (const { ibgeCode } of rsRegistry.municipalities) {
    const matches = parsed.regions.filter((region) =>
      region.municipalityIbgeCodes.includes(ibgeCode),
    )
    assert.equal(matches.length, 1, `município ${ibgeCode} não resolve uma única região`)
  }
})

test('nenhum texto público do recorte carrega o nome institucional', () => {
  const raw = readFileSync(path.join(repoRoot, 'config/regions/rs.json'), 'utf8')
  const normalized = raw
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('pt-BR')
  for (const token of ['fiergs', 'senai', 'sesi']) {
    assert.equal(normalized.includes(token), false, `o mapa regional expõe "${token}"`)
  }
})

test('o parser recusa nome ou slug com o nome institucional', () => {
  const withName = clone()
  withName.regions[0].name = 'Região SENAI Serra'
  assert.throws(() => parseRegionsConfig(withName, 'RS', rsRegistry), /nome institucional/)

  const withSlug = clone()
  withSlug.regions[0].slug = 'fiergs-central'
  assert.throws(() => parseRegionsConfig(withSlug, 'RS', rsRegistry), /nome institucional/)

  const withProvenance = clone()
  withProvenance.provenance = 'Recorte mantido pelo Sesi.'
  assert.throws(() => parseRegionsConfig(withProvenance, 'RS', rsRegistry), /nome institucional/)
})

test('o parser recusa mapa que não cobre o registro municipal', () => {
  const missing = clone()
  const dropped = missing.regions[0].municipalityIbgeCodes.pop()
  missing.regions[0].municipalityCount -= 1
  missing.municipalityCount -= 1
  assert.throws(
    () => parseRegionsConfig(missing, 'RS', rsRegistry),
    new RegExp(`municípios sem região: .*${dropped}`),
  )
})

test('o parser recusa município repetido entre regiões', () => {
  const duplicated = clone()
  const shared = duplicated.regions[0].municipalityIbgeCodes[0]
  duplicated.regions[1].municipalityIbgeCodes.push(shared)
  duplicated.regions[1].municipalityCount += 1
  duplicated.municipalityCount += 1
  assert.throws(() => parseRegionsConfig(duplicated, 'RS', rsRegistry), /aparece em/)
})

test('o parser recusa município fora do registro estadual', () => {
  const foreign = clone()
  foreign.regions[0].municipalityIbgeCodes.push('3550308')
  foreign.regions[0].municipalityCount += 1
  foreign.municipalityCount += 1
  assert.throws(
    () => parseRegionsConfig(foreign, 'RS', rsRegistry),
    /fora do registro estadual: 3550308/,
  )
})

test('o parser recusa contagem, esquema, UF e campos divergentes', () => {
  const badCount = clone()
  badCount.municipalityCount += 1
  assert.throws(() => parseRegionsConfig(badCount, 'RS', rsRegistry), /municipalityCount/)

  const badRegionCount = clone()
  badRegionCount.regionCount += 1
  assert.throws(() => parseRegionsConfig(badRegionCount, 'RS', rsRegistry), /regionCount/)

  const badSchema = clone()
  badSchema.schemaVersion = 'regions-config-v2'
  assert.throws(() => parseRegionsConfig(badSchema, 'RS', rsRegistry), /schemaVersion/)

  const badState = clone()
  assert.throws(() => parseRegionsConfig(badState, 'AL', rsRegistry), /stateCode diverge/)

  const extraField = clone()
  extraField.observacao = 'nota fora do contrato'
  assert.throws(() => parseRegionsConfig(extraField, 'RS', rsRegistry), /campos divergentes/)
})

test('UF sem mapa não tem análise regional e não quebra o build', () => {
  assert.equal(loadRegionsConfig({ repoRoot, stateCode: 'AL' }), null)
  assert.equal(regionsConfigPath(repoRoot, 'AL'), path.join(repoRoot, 'config', 'regions', 'al.json'))
  assert.notEqual(loadRegionsConfig({ repoRoot, stateCode: 'RS' }), null)
})
