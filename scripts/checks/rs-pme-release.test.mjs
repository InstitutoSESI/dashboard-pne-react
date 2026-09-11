import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { compareRsExperienceDataDirectories } from './rs-experience-data-parity.mjs'

test('a ficha de publicação aponta para o comando RS PME e deixa campos externos pendentes', async () => {
  const preparation = JSON.parse(await readFile(new URL('../../config/hosting/rs-pme-pages.json', import.meta.url), 'utf8'))
  const manifest = JSON.parse(await readFile(new URL('../../package.json', import.meta.url), 'utf8'))
  assert.equal(preparation.status, 'proposed_not_provisioned')
  assert.deepEqual(preparation.fixedCliProfile, { state: 'RS', experience: 'pme' })
  assert.equal(preparation.buildCommand, 'npm run build:cloudflare:rs-pme')
  assert.equal(preparation.outputDirectory, 'dist')
  assert.equal(preparation.rootDirectory, '.')
  assert.match(manifest.scripts['build:cloudflare:rs-pme'], /build RS pme --outDir dist$/)
  assert.ok(Object.values(preparation.externalProvisioning).every((value) => value === null))
})

test('gate de release compara bytes e conjunto de arquivos, rejeitando vazio, raiz igual e lote parcial', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'rs-pme-release-'))
  try {
    const current = path.join(temporary, 'rs', 'data')
    const pme = path.join(temporary, 'rs-pme', 'data')
    await Promise.all([mkdir(current, { recursive: true }), mkdir(pme, { recursive: true })])
    await assert.rejects(compareRsExperienceDataDirectories(current, pme), /vazia/)
    const document = '{"id_municipio":"4313375","value":0}\n'
    await Promise.all([writeFile(path.join(current, 'index.json'), document), writeFile(path.join(pme, 'index.json'), document)])
    const result = await compareRsExperienceDataDirectories(current, pme)
    assert.equal(result.fileCount, 1)
    assert.equal(result.totalBytes, Buffer.byteLength(document))
    assert.match(result.sha256, /^[a-f0-9]{64}$/)
    await assert.rejects(compareRsExperienceDataDirectories(current, current), /mesma raiz/)
    await writeFile(path.join(pme, 'index.json'), document.replace('"value":0', '"value":null'))
    await assert.rejects(compareRsExperienceDataDirectories(current, pme), /Dados RS divergentes/)
    await writeFile(path.join(pme, 'index.json'), document)
    await writeFile(path.join(pme, 'extra.json'), '{}')
    await assert.rejects(compareRsExperienceDataDirectories(current, pme), /extra.json/)
    await assert.rejects(compareRsExperienceDataDirectories(current, path.join(temporary, 'missing')), /ENOENT/)
  } finally {
    assert.ok(path.resolve(temporary).startsWith(path.resolve(os.tmpdir()) + path.sep))
    assert.ok(path.basename(temporary).startsWith('rs-pme-release-'))
    await rm(temporary, { recursive: true, force: true })
  }
})
