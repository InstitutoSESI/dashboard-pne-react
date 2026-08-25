/*
 * Publica o Vocações da Região em `public/data/vocacoes-regiao/`.
 *
 * O gerador existe antes do conteúdo, e é honesto sobre isso: enquanto a
 * camada de pesquisa (`SESI\PNE\foresight`) não publicar o contrato de origem
 * "vocacoes-regiao v0.1", não há candidato algum a projetar, e o manifesto
 * publicado é o manifesto vazio — válido, verificável e sem nenhuma região.
 *
 * Nada aqui inventa cenário, transpõe o pacote municipal para a região nem
 * reaproveita narrativa de outro escopo. Quando a origem existir, o passo que
 * falta é ler o pacote regional aprovado e projetá-lo com a mesma disciplina
 * do gerador municipal: hash do arquivo, versão de conteúdo canônica, guarda
 * de linguagem pública e escrita atômica.
 *
 * Uso:
 *   node scripts/generate-vocacoes-regiao.mjs            publica
 *   node scripts/generate-vocacoes-regiao.mjs --check    confere sem escrever
 *   node scripts/generate-vocacoes-regiao.mjs --source <dir>   origem explícita
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  VOCACOES_DOCUMENT_SCHEMA,
  VOCACOES_MANIFEST_SCHEMA,
  VOCACOES_REGION_FILE_PATTERN,
  VOCACOES_SCOPE_TYPE,
  parseVocacoesManifest,
} from '../src/features/vocacoes-regiao/vocacoesRegiaoLoader.js'

const REPOSITORY_ROOT = new URL('../', import.meta.url)
const OUTPUT_ROOT = new URL('public/data/vocacoes-regiao/', REPOSITORY_ROOT)

export const VOCACOES_GENERATOR_VERSION = 'vocacoes-regiao-generator-v1'
export const STATE_CODE = 'RS'

/*
 * Enquanto não houver contrato de origem, estes são os valores que o manifesto
 * vazio declara. Eles não descrevem conteúdo publicado: descrevem a ausência
 * dele, de um jeito que o leitor consegue validar.
 */
export const EMPTY_MANIFEST_SOURCE_VERSION = 'nao-publicado'
export const EMPTY_MANIFEST_METHODOLOGY_STATUS = 'contrato_de_origem_pendente'
export const EMPTY_MANIFEST_PUBLICATION_SCOPE = 'none'
export const EMPTY_MANIFEST_GENERATED_AT = '2026-08-24'

/** Origem canônica do pacote regional, ainda inexistente por decisão de escopo. */
export const DEFAULT_SOURCE_ROOT = 'C:/Users/rnbirck/PROJETOS/SESI/PNE/foresight/vocacoes-regiao'

export function buildEmptyManifest() {
  return {
    schemaVersion: VOCACOES_MANIFEST_SCHEMA,
    documentSchemaVersion: VOCACOES_DOCUMENT_SCHEMA,
    scopeType: VOCACOES_SCOPE_TYPE,
    generatedAt: EMPTY_MANIFEST_GENERATED_AT,
    generatorVersion: VOCACOES_GENERATOR_VERSION,
    sourceVersion: EMPTY_MANIFEST_SOURCE_VERSION,
    sourceMethodologyStatus: EMPTY_MANIFEST_METHODOLOGY_STATUS,
    publicationScope: EMPTY_MANIFEST_PUBLICATION_SCOPE,
    regionFilePattern: VOCACOES_REGION_FILE_PATTERN,
    stateCode: STATE_CODE,
    regions: [],
  }
}

/*
 * Recusa registrada, não exceção: a origem existir sem contrato público
 * aprovado é o estado projetado das Rodadas 1–4 do plano Vocações da Região.
 * O gerador publica o manifesto vazio e registra a recusa — o mesmo padrão do
 * município lido e recusado no foresight. Só é erro alto o estado inesperado:
 * aprovação presente sem transposição implementada.
 */
export const PUBLIC_CONTRACT_APPROVAL_FILE = 'CONTRATO_PUBLICO_APROVADO.json'

export function resolveSource(sourceRoot) {
  const resolved = path.resolve(sourceRoot ?? DEFAULT_SOURCE_ROOT)
  if (!fs.existsSync(resolved)) {
    return { available: false, root: resolved, refusal: null }
  }
  if (fs.existsSync(path.join(resolved, PUBLIC_CONTRACT_APPROVAL_FILE))) {
    throw new Error(
      'Vocações da Região: a origem em '
      + `${resolved} declara contrato público aprovado, mas a transposição ainda não está `
      + 'implementada nesta versão do gerador. Implemente a transposição (Rodada 5) antes '
      + 'de aprovar o contrato público.',
    )
  }
  return {
    available: false,
    root: resolved,
    refusal:
      `a origem existe em ${resolved}, mas o contrato público "vocacoes-regiao v0.1" `
      + 'ainda não foi aprovado; o gerador publica o manifesto vazio e não transpõe '
      + 'nada por conta própria.',
  }
}

export function buildPublication({ sourceRoot } = {}) {
  const source = resolveSource(sourceRoot)
  const manifest = buildEmptyManifest()
  // O manifesto vazio passa pelo mesmo validador que o leitor usa em produção.
  parseVocacoesManifest(structuredClone(manifest))
  return {
    manifest,
    files: [],
    origin: source.root,
    available: source.available,
    refusal: source.refusal,
  }
}

function writeFileAtomic(targetUrl, contents) {
  const target = fileURLToPath(targetUrl)
  fs.mkdirSync(path.dirname(target), { recursive: true })
  const temporary = `${target}.tmp`
  fs.writeFileSync(temporary, contents, 'utf8')
  fs.renameSync(temporary, target)
}

function main(argv) {
  const checkOnly = argv.includes('--check')
  const sourceIndex = argv.indexOf('--source')
  const sourceRoot = sourceIndex >= 0 ? argv[sourceIndex + 1] : undefined

  const publication = buildPublication({ sourceRoot })
  const outputs = [
    {
      contents: `${JSON.stringify(publication.manifest, null, 2)}\n`,
      url: new URL('manifest.json', OUTPUT_ROOT),
    },
    ...publication.files.map((file) => ({
      contents: file.serialized,
      url: new URL(file.path, OUTPUT_ROOT),
    })),
  ]

  if (checkOnly) {
    let drift = 0
    for (const output of outputs) {
      const target = fileURLToPath(output.url)
      const current = fs.existsSync(target) ? fs.readFileSync(target, 'utf8') : null
      if (current !== output.contents) {
        drift += 1
        process.stderr.write(`divergente: ${path.relative(fileURLToPath(REPOSITORY_ROOT), target)}\n`)
      }
    }
    if (drift > 0) {
      process.exitCode = 1
      return
    }
    process.stdout.write(
      `Vocações da Região: manifesto conferido, ${publication.manifest.regions.length} regiões publicadas.\n`,
    )
    if (publication.refusal) {
      process.stdout.write(`Vocações da Região: recusa registrada — ${publication.refusal}\n`)
    }
    return
  }

  for (const output of outputs) writeFileAtomic(output.url, output.contents)
  if (publication.refusal) {
    process.stdout.write(
      `Vocações da Região: manifesto vazio publicado. Recusa registrada — ${publication.refusal}\n`,
    )
  } else {
    process.stdout.write(
      'Vocações da Região: manifesto vazio publicado — nenhuma região tem pacote, '
      + `o contrato de origem ainda não existe em ${publication.origin}.\n`,
    )
  }
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1] ?? '')) {
  main(process.argv.slice(2))
}
