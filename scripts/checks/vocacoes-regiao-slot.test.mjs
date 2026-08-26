/*
 * O Vocações da Região publicado — contrato `vocacoes-regiao-2.3.0`.
 *
 * Até a Fase A este arquivo guardava a **ausência**: que o manifesto vazio era
 * um estado declarado e verificável. A ausência continua guardada, e continua
 * importando — só que agora por fixture, e não pelo que está em disco, porque
 * em disco há dez regiões.
 *
 * O que este arquivo prova, em ordem:
 *   1. o que está publicado é exatamente o que o gerador produz, e confere
 *      consigo mesmo (resumo, tamanho, versão de conteúdo, contagem por bloco);
 *   2. o contrato é fechado em todo nível de aninhamento, e as regras que o
 *      plano nomeia (prévia, universo, estimativa, ano futuro, alegação
 *      proibida) recusam o que dizem recusar;
 *   3. o fail-closed é real: pacote adulterado tira a região do conjunto
 *      publicado — ela some do menu e da rota, em vez de virar página em branco;
 *   4. o manifesto vazio segue sendo um estado válido e fechado.
 *
 * Toda recusa é provada por injeção: o teste constrói o defeito e exige que o
 * validador o acuse. Validador que nunca reprovou nada não provou nada.
 */

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

import {
  VOCACOES_PUBLICATION_SCOPE,
  buildEmptyManifest,
  buildPublication,
  computeContentVersion,
  formatPeriodLabel,
  resolveSource,
} from '../generate-vocacoes-regiao.mjs'
import {
  VOCACOES_DOCUMENT_SCHEMA,
  VOCACOES_MANIFEST_PATH,
  VOCACOES_MANIFEST_SCHEMA,
  VOCACOES_REGION_PATH,
  VocacoesLoadError,
  createVocacoesDocumentParser,
  createVocacoesRegiaoLoader,
  parseVocacoesManifest,
  validateRegionIdentity,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoLoader.js'
import {
  EVIDENCE_CLASS_LABELS,
  PROHIBITED_CLAIM_OPENER,
  UNIVERSE_LABELS,
  slugify,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'

/* A politica de visibilidade vive em TypeScript; o teste compila so ela. */
const temporaryOutput = mkdtempSync(path.join(tmpdir(), 'dashboard-pne-vocacoes-'))
writeFileSync(path.join(temporaryOutput, 'package.json'), '{"type":"module"}\n')
execFileSync(
  process.execPath,
  [
    path.resolve('node_modules/typescript/bin/tsc'),
    '--project',
    'scripts/checks/tsconfig.vocacoes.json',
    '--outDir',
    temporaryOutput,
  ],
  { stdio: 'inherit' },
)
process.on('exit', () => rmSync(temporaryOutput, { force: true, recursive: true }))

const { isVocacoesPublished, VOCACOES_PUBLICATION_PENDING } = await import(
  pathToFileURL(path.join(temporaryOutput, 'src/domain/vocacoesRegiaoPublication.js')).href
)

const readRepositoryFile = (relativePath) =>
  readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const publishedManifestRaw = await readRepositoryFile('public/data/vocacoes-regiao/manifest.json')
const publishedManifest = JSON.parse(publishedManifestRaw)
const REFERENCE_SLUG = 'serra'
const publishedRegionRaw = await readRepositoryFile(
  `public/data/vocacoes-regiao/regioes/${REFERENCE_SLUG}.json`,
)
const publishedRegion = JSON.parse(publishedRegionRaw)

const parseDocument = createVocacoesDocumentParser(publishedManifest)

/** Cópia profunda mutável do pacote publicado, para as injeções. */
function draft() {
  return structuredClone(publishedRegion)
}

/*
 * Toda injeção passa por aqui: o teste afirma que o validador recusou, e que
 * recusou pelo motivo que o caso alega. `assert.throws` sem padrão aceitaria
 * qualquer erro — inclusive um `TypeError` acidental do próprio teste.
 */
function refuses(mutate, pattern) {
  const candidate = draft()
  mutate(candidate)
  assert.throws(() => parseDocument(candidate), pattern)
}

/* ================================================================= *
 * 1. O que está publicado
 * ================================================================= */

test('o que está publicado é exatamente o que o gerador produz', () => {
  const publication = buildPublication()
  assert.equal(publication.available, true)
  assert.equal(`${JSON.stringify(publication.manifest, null, 2)}\n`, publishedManifestRaw)
  assert.equal(publication.files.length, publication.manifest.regions.length)

  const generated = new Map(publication.files.map((file) => [file.path, file.serialized]))
  assert.equal(generated.get(`regioes/${REFERENCE_SLUG}.json`), publishedRegionRaw)
})

test('o manifesto publicado declara as dez regiões e passa pelo validador de produção', () => {
  const manifest = parseVocacoesManifest(JSON.parse(publishedManifestRaw))
  assert.equal(manifest.schemaVersion, VOCACOES_MANIFEST_SCHEMA)
  assert.equal(manifest.documentSchemaVersion, VOCACOES_DOCUMENT_SCHEMA)
  assert.equal(manifest.scopeType, 'region')
  assert.equal(manifest.stateCode, 'RS')
  assert.equal(manifest.publicationScope, VOCACOES_PUBLICATION_SCOPE)
  assert.equal(manifest.regions.length, 10)
  assert.equal(new Set(manifest.regions.map((entry) => entry.slug)).size, 10)
  assert.equal(
    manifest.regions.reduce((total, entry) => total + entry.municipalityCount, 0),
    497,
    'as dez regiões precisam particionar os 497 municípios do estado',
  )
})

test('cada região publicada confere com o que o manifesto declara sobre ela', async () => {
  for (const entry of publishedManifest.regions) {
    const raw = await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`)
    const buffer = Buffer.from(raw, 'utf8')
    assert.equal(createHash('sha256').update(buffer).digest('hex'), entry.contentHash, entry.slug)
    assert.equal(buffer.byteLength, entry.byteSize, entry.slug)

    const document = parseDocument(JSON.parse(raw))
    assert.equal(document.region.slug, entry.slug)
    assert.equal(document.region.name, entry.name)
    assert.equal(document.region.municipalityCount, entry.municipalityCount)
    assert.equal(document.contentVersion, entry.contentVersion)
    assert.equal(
      computeContentVersion(document),
      entry.contentVersion,
      `${entry.slug}: a versão de conteúdo precisa ser recomputável a partir do corpo`,
    )
    assert.equal(document.territoryPortrait.series.length, entry.seriesCount)
    assert.equal(document.associations.items.length, entry.associationCount)
    assert.equal(document.temporalPairs.items.length, entry.temporalPairCount)
  }
})

/*
 * As regras que o Aceite da rodada nomeia, conferidas sobre o que foi
 * publicado — e não sobre uma fixture. Fixture prova o validador; o disco prova
 * a publicação.
 */
test('nenhuma prévia chega ao público como observação, e toda prévia está rotulada', async () => {
  let preliminaryPoints = 0
  for (const entry of publishedManifest.regions) {
    const document = JSON.parse(await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`))
    for (const serie of document.territoryPortrait.series) {
      const declared = new Set(serie.preliminaryPeriods)
      for (const point of serie.points) {
        if (declared.has(point.period)) {
          assert.equal(point.evidenceClass, 'preliminary', `${entry.slug}/${serie.seriesId}`)
          preliminaryPoints += 1
        } else {
          assert.notEqual(point.evidenceClass, 'preliminary', `${entry.slug}/${serie.seriesId}`)
        }
      }
    }
  }
  assert.ok(preliminaryPoints > 0, 'sem nenhum ponto de prévia, esta asserção não prova nada')
})

test('toda série do cadastro social declara o universo, e nenhuma vira taxa da população', async () => {
  let cadastral = 0
  for (const entry of publishedManifest.regions) {
    const document = JSON.parse(await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`))
    for (const serie of document.territoryPortrait.series) {
      if (serie.universeLabel !== UNIVERSE_LABELS.cadastral_registry) continue
      cadastral += 1
      const text = `${serie.label} ${serie.unitLabel} ${serie.sourceLabel}`.toLocaleLowerCase('pt-BR')
      for (const forbidden of ['população', 'populacao', 'habitantes', 'taxa', 'percentual', 'per capita']) {
        assert.ok(!text.includes(forbidden), `${entry.slug}/${serie.seriesId} usa "${forbidden}"`)
      }
    }
  }
  assert.ok(cadastral > 0, 'sem nenhuma série cadastral, esta asserção não prova nada')
})

test('a estimativa de migração sai com classe calculada e nota de método', async () => {
  let migration = 0
  for (const entry of publishedManifest.regions) {
    const document = JSON.parse(await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`))
    for (const serie of document.territoryPortrait.series) {
      if (!serie.seriesId.startsWith('saldo-migratorio')) continue
      migration += 1
      assert.equal(serie.evidenceClass, 'calculated', `${entry.slug}/${serie.seriesId}`)
      assert.ok(serie.limitations.length > 0, `${entry.slug}/${serie.seriesId} sem nota de método`)
    }
    const topics = document.limitations.items.join(' ').toLocaleLowerCase('pt-BR')
    assert.ok(
      topics.includes('estimativa indireta'),
      `${entry.slug}: o pacote precisa declarar a natureza de estimativa do saldo`,
    )
  }
  assert.ok(migration > 0, 'sem nenhuma série de migração, esta asserção não prova nada')
})

test('nenhum texto público publicado expõe token interno ou chave da camada de pesquisa', async () => {
  const forbiddenTokens = ['fiergs', 'senai', 'sesi', 'csv-dashboard', 'manifesto_datasets', 'regiao_fiergs']
  const internalKey = /\b[a-z0-9]+(?:_[a-z0-9]+){2,}\b/u
  for (const entry of publishedManifest.regions) {
    const document = JSON.parse(await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`))
    for (const text of publicTexts(document)) {
      const normalized = text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR')
      for (const token of forbiddenTokens) {
        assert.ok(!normalized.includes(token), `${entry.slug}: "${token}" em "${text}"`)
      }
      assert.equal(internalKey.exec(text), null, `${entry.slug}: chave interna em "${text}"`)
    }
  }
})

test('nenhum período publicado ultrapassa o ano de referência do manifesto', async () => {
  const { referenceYear } = publishedManifest
  for (const entry of publishedManifest.regions) {
    const document = JSON.parse(await readRepositoryFile(`public/data/vocacoes-regiao/${entry.path}`))
    for (const serie of document.territoryPortrait.series) {
      for (const point of serie.points) {
        const year = serie.periodGranularity === 'annual'
          ? point.period
          : Math.floor(point.period / 100)
        assert.ok(year <= referenceYear, `${entry.slug}/${serie.seriesId}: período ${point.period}`)
      }
    }
  }
})

/** Todo texto que o leitor vê, na ordem do documento. */
function publicTexts(document) {
  const texts = [
    document.region.name,
    ...Object.values(document.page),
    document.howToRead.label,
    document.howToRead.description,
    ...document.howToRead.items,
    document.territoryPortrait.label,
    document.territoryPortrait.description,
    document.associations.label,
    document.associations.description,
    document.temporalPairs.label,
    document.temporalPairs.description,
    document.sources.label,
    document.sources.description,
    document.limitations.label,
    document.limitations.description,
    ...document.limitations.items,
  ]
  for (const serie of document.territoryPortrait.series) {
    texts.push(serie.label, serie.unitLabel, serie.sourceLabel, serie.periodLabel, ...serie.limitations)
    if (serie.universeLabel !== null) texts.push(serie.universeLabel)
    if (serie.ratioOf !== null) texts.push(serie.ratioOf.numeratorLabel, serie.ratioOf.denominatorLabel)
  }
  for (const association of document.associations.items) {
    texts.push(
      association.label,
      association.periodLabel,
      association.observedStatement,
      association.allowedInterpretation,
      association.prohibitedClaim,
      association.educationOutcome.label,
      ...association.territorialFactors.map((factor) => factor.label),
      ...association.hypotheses,
    )
  }
  for (const pair of document.temporalPairs.items) {
    texts.push(
      pair.label,
      pair.periodLabel,
      pair.observedStatement,
      pair.prohibitedClaim,
      pair.seriesA.label,
      pair.seriesB.label,
    )
  }
  for (const item of document.sources.items) texts.push(item.label, item.periodLabel)
  return texts
}

/* ================================================================= *
 * 2. O contrato, provado por injeção
 * ================================================================= */

test('o contrato 2.1.0 aceita o pacote publicado', () => {
  const document = parseDocument(draft())
  assert.equal(document.schemaVersion, VOCACOES_DOCUMENT_SCHEMA)
  assert.ok(document.territoryPortrait.series.length > 0)
  assert.ok(document.associations.items.length > 0)
  assert.ok(document.temporalPairs.items.length > 0)
})

/*
 * A Rodada 5 guardava aqui que o esquema `1.0.0`, que trazia cenários
 * transpostos do municipal, deixara de ser aceito. A recusa continua valendo, e
 * o que mudou é o outro lado: o `2.1.0` tem bloco de cenários, com forma
 * própria — a lista solta do esquema antigo continua sendo recusada.
 *
 * A região de referência deste arquivo é uma das oito **sem** cenário, e é isso
 * que ela prova: a ausência é declarada em campo obrigatório, e é contável no
 * manifesto sem abrir o documento.
 */
test('o esquema antigo, com cenários em lista solta, segue recusado', () => {
  refuses((candidate) => { candidate.schemaVersion = 'vocacoes-regiao-1.0.0' }, /esquema do pacote desconhecido/)
  refuses((candidate) => { candidate.scenarios = [] }, /pacote\.scenarios deve ser um objeto/)
  assert.equal(publishedRegion.scenarios.status, 'absent')
  assert.equal(publishedRegion.scenarios.block, null)
  assert.equal(publishedRegion.scenarios.statuteReadingNote, null)
  assert.ok(publishedRegion.scenarios.absenceStatement.length > 0)

  const entry = publishedManifest.regions.find((region) => region.slug === REFERENCE_SLUG)
  assert.equal(entry.scenarioStatus, 'absent')
  assert.equal(entry.scenarioCount, 0)
})

/*
 * Fechamento em todo nível de aninhamento. Cada linha é um lugar onde um campo
 * novo poderia entrar sem ninguém validar — e alguém renderizar.
 */
test('campo desconhecido é recusado em todo nível do documento', () => {
  const injections = [
    ['documento', (candidate) => { candidate.observacao = 'x' }],
    ['region', (candidate) => { candidate.region.populacao = 1 }],
    ['page', (candidate) => { candidate.page.subtitulo = 'x' }],
    ['howToRead', (candidate) => { candidate.howToRead.nota = 'x' }],
    ['territoryPortrait', (candidate) => { candidate.territoryPortrait.nota = 'x' }],
    ['series', (candidate) => { candidate.territoryPortrait.series[0].chaveInterna = 'x' }],
    ['series.ratioOf', (candidate) => {
      const serie = candidate.territoryPortrait.series.find((item) => item.ratioOf !== null)
      serie.ratioOf.formula = 'x'
    }],
    ['point', (candidate) => { candidate.territoryPortrait.series[0].points[0].nota = 'x' }],
    ['associations', (candidate) => { candidate.associations.nota = 'x' }],
    ['association', (candidate) => { candidate.associations.items[0].peso = 1 }],
    ['association.window', (candidate) => { candidate.associations.items[0].window.meio = 2020 }],
    ['educationOutcome', (candidate) => { candidate.associations.items[0].educationOutcome.chave = 'x' }],
    ['territorialFactor', (candidate) => { candidate.associations.items[0].territorialFactors[0].chave = 'x' }],
    ['temporalPairs', (candidate) => { candidate.temporalPairs.nota = 'x' }],
    ['temporalPair', (candidate) => { candidate.temporalPairs.items[0].peso = 1 }],
    ['temporalPair.seriesA', (candidate) => { candidate.temporalPairs.items[0].seriesA.chave = 'x' }],
    ['sources', (candidate) => { candidate.sources.nota = 'x' }],
    ['sources.item', (candidate) => { candidate.sources.items[0].url = 'x' }],
    ['limitations', (candidate) => { candidate.limitations.nota = 'x' }],
    ['provenance', (candidate) => { candidate.provenance.caminho = 'x' }],
  ]
  for (const [level, mutate] of injections) {
    const candidate = draft()
    mutate(candidate)
    assert.throws(
      () => parseDocument(candidate),
      /campo desconhecido/,
      `o nível "${level}" aceitou um campo fora do contrato`,
    )
  }
  assert.equal(injections.length, 20)
})

test('campo obrigatório que sumiu é recusado, não tratado como ausência', () => {
  refuses((candidate) => { delete candidate.provenance }, /campos obrigatórios/)
  refuses((candidate) => { delete candidate.territoryPortrait.series[0].universeLabel }, /campos obrigatórios/)
  refuses((candidate) => { delete candidate.associations.items[0].prohibitedClaim }, /campos obrigatórios/)
})

test('prévia não passa como observação, e observação não passa como prévia', () => {
  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.preliminaryPeriods.length > 0)
    const period = serie.preliminaryPeriods[0]
    serie.points.find((point) => point.period === period).evidenceClass = 'observed'
  }, /período de prévia e não pode ter classe observed/)

  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series[0]
    serie.points[0].evidenceClass = 'preliminary'
  }, /classe de prévia sem que o período conste/)

  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.preliminaryPeriods.length > 0)
    serie.preliminaryPeriods = [...serie.preliminaryPeriods, serie.periodEnd + 1]
  }, /fora da janela declarada|sem ponto correspondente/)
})

test('a frase de classe e a de universo não podem contradizer o que a série declara', () => {
  refuses((candidate) => {
    candidate.territoryPortrait.series[0].evidenceLabel = EVIDENCE_CLASS_LABELS.calculated
  }, /não é a frase declarada para a classe/)

  refuses((candidate) => {
    candidate.territoryPortrait.series[0].universeLabel = 'Todas as pessoas do território regional.'
  }, /não é null nem uma das frases de universo/)
})

test('número em período futuro é recusado', () => {
  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.periodGranularity === 'annual')
    serie.periodEnd = publishedManifest.referenceYear + 4
    serie.points.push({
      period: publishedManifest.referenceYear + 4,
      value: 1234,
      evidenceClass: 'observed',
    })
  }, /ultrapassa o período de referência/)
})

test('a alegação proibida precisa continuar sendo uma proibição', () => {
  refuses((candidate) => {
    candidate.associations.items[0].prohibitedClaim = 'A demografia determinou a matrícula.'
  }, /abridor de proibição/)

  refuses((candidate) => {
    candidate.associations.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}uma coisa moveu a outra. Mas moveu.`
  }, /única sentença/)

  refuses((candidate) => {
    candidate.temporalPairs.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}uma​coisa moveu a outra.`
  }, /caractere de controle/)

  refuses((candidate) => {
    candidate.temporalPairs.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}uma coisa moveu a outra.`
  }, /caractere de controle/)
})

test('referência de série que não resolve, ou que renomeia a série, é recusada', () => {
  refuses((candidate) => {
    candidate.associations.items[0].educationOutcome = {
      seriesId: 'serie-que-nao-existe',
      label: 'Serie que nao existe',
    }
  }, /não resolve em nenhuma série/)

  /*
   * Renomear a referência agora esbarra antes na derivação do identificador: o
   * `seriesId` deixa de ser o slug do rótulo novo. As duas guardas apontam o
   * mesmo defeito, e a primeira a falar é a mais específica.
   */
  refuses((candidate) => {
    candidate.associations.items[0].territorialFactors[0].label = 'Outro nome qualquer'
  }, /não é o identificador do rótulo|diverge do rótulo da série/)

  refuses((candidate) => {
    const first = candidate.temporalPairs.items[0]
    first.seriesB = { ...first.seriesA }
  }, /compara uma série com ela mesma/)
})

test('identificador público não aceita a chave interna da camada de pesquisa', () => {
  refuses((candidate) => {
    candidate.territoryPortrait.series[0].seriesId = 'cadastro_social_familias_inscritas'
  }, /identificador público derivado do rótulo/)

  /* Identificador e rótulo repetidos: os dois caem, cada um pelo seu motivo. */
  refuses((candidate) => {
    const [first, second] = candidate.territoryPortrait.series
    second.seriesId = first.seriesId
    second.label = first.label
  }, /seriesId repetido|label repetido/)
})

test('pontos fora de ordem, repetidos ou fora da janela são recusados', () => {
  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series[0]
    const [first, second] = serie.points
    serie.points[0] = second
    serie.points[1] = first
  }, /fora de ordem|repetido/)

  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series[0]
    serie.points = [...serie.points, { ...serie.points[0] }]
  }, /repetido|fora de ordem/)

  refuses((candidate) => {
    candidate.territoryPortrait.series[0].points[0].value = 'muito'
  }, /número finito/)
})

test('a janela de uma associação precisa alcançar as séries que ela cita', () => {
  refuses((candidate) => {
    candidate.associations.items[0].window = { start: 1900, end: 1901 }
  }, /não cabe na série/)
})

test('a identidade regional substitui a municipal sem afrouxar o contrato', () => {
  assert.throws(() => validateRegionIdentity({ slug: 'serra' }, 'regiao'), /campos obrigatórios/)
  assert.throws(
    () => validateRegionIdentity({ slug: 'Serra', name: 'Serra', uf: 'RS', municipalityCount: 42 }, 'regiao'),
    /slug/,
  )
  assert.throws(
    () => validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'rs', municipalityCount: 42 }, 'regiao'),
    /uf/,
  )
  assert.throws(
    () => validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'RS', municipalityCount: 0 }, 'regiao'),
    /municipalityCount/,
  )
  assert.ok(validateRegionIdentity({ slug: 'serra', name: 'Serra', uf: 'RS', municipalityCount: 42 }, 'regiao'))
})

test('as funções derivadas do gerador fazem o que a transposição promete', () => {
  assert.equal(slugify('Matrículas no ensino médio'), 'matriculas-no-ensino-medio')
  assert.equal(slugify('População de 0 a 14 anos'), 'populacao-de-0-a-14-anos')
  assert.throws(() => slugify('—'), /identificador público/)
  assert.equal(formatPeriodLabel(2006, 2025, 'annual'), '2006 a 2025')
  assert.equal(formatPeriodLabel(2022, 2022, 'annual'), '2022')
  assert.equal(formatPeriodLabel(201505, 202608, 'monthly'), 'maio de 2015 a agosto de 2026')
})

/* ================================================================= *
 * 3. Fail-closed por mutação
 * ================================================================= */

/** Um leitor sobre um manifesto e um corpo escolhidos pelo teste. */
function loaderOver({ manifest = publishedManifestRaw, region = publishedRegionRaw } = {}) {
  const regionPath = VOCACOES_REGION_PATH.replace('{regionSlug}', REFERENCE_SLUG)
  return createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (requested) => {
      if (requested === VOCACOES_MANIFEST_PATH) return manifest
      if (requested === regionPath) return region
      throw new Error(`caminho não publicado: ${requested}`)
    },
  })
}

test('região publicada é lida, conferida e navegável', async () => {
  const loader = loaderOver()
  const slugs = await loader.listPublishedRegionSlugs()
  assert.equal(slugs.length, 10)
  assert.ok(slugs.includes(REFERENCE_SLUG))

  const loaded = await loader.loadRegion(REFERENCE_SLUG)
  assert.equal(loaded.document.region.slug, REFERENCE_SLUG)
  assert.equal(loaded.entry.contentHash, publishedManifest.regions.find(
    (entry) => entry.slug === REFERENCE_SLUG,
  ).contentHash)

  const publication = { publishedSlugs: new Set(slugs), ready: true }
  assert.equal(isVocacoesPublished(publication, REFERENCE_SLUG), true)
})

/*
 * O teste que o Aceite pede: pacote adulterado **some do menu e da rota**. Cada
 * eixo do contrato é mutado em separado, e cada um precisa produzir a mesma
 * consequência — recusa, retratação, região fora do conjunto publicado.
 */
test('pacote adulterado tira a região do menu e da rota, em vez de virar página em branco', async () => {
  const mutations = [
    ['identidade', (candidate) => { candidate.region.name = 'Serra Gaúcha' }],
    ['versão de conteúdo', (candidate) => { candidate.contentVersion = 'f'.repeat(64) }],
    ['campo fora do contrato', (candidate) => { candidate.observacao = 'fora do contrato' }],
    ['bloco removido', (candidate) => { candidate.associations.items = [] }],
    ['prévia promovida a observação', (candidate) => {
      const serie = candidate.territoryPortrait.series.find((item) => item.preliminaryPeriods.length > 0)
      const period = serie.preliminaryPeriods[0]
      serie.points.find((point) => point.period === period).evidenceClass = 'observed'
    }],
    ['proibição virada afirmação', (candidate) => {
      candidate.associations.items[0].prohibitedClaim = 'A demografia determinou a matrícula.'
    }],
  ]

  for (const [name, mutate] of mutations) {
    const candidate = draft()
    mutate(candidate)
    const loader = loaderOver({ region: `${JSON.stringify(candidate, null, 2)}\n` })

    assert.ok(
      (await loader.listPublishedRegionSlugs()).includes(REFERENCE_SLUG),
      `${name}: antes da leitura, o manifesto ainda promete a região`,
    )

    await assert.rejects(loader.loadRegion(REFERENCE_SLUG), (error) => {
      assert.ok(error instanceof VocacoesLoadError, name)
      assert.equal(error.code, 'invalid_payload', name)
      assert.equal(error.regionSlug, REFERENCE_SLUG, name)
      return true
    })

    const afterwards = await loader.listPublishedRegionSlugs()
    assert.ok(!afterwards.includes(REFERENCE_SLUG), `${name}: a região precisa sair do conjunto publicado`)
    assert.equal(afterwards.length, 9, name)
    assert.equal(
      isVocacoesPublished({ publishedSlugs: new Set(afterwards), ready: true }, REFERENCE_SLUG),
      false,
      `${name}: a navegação precisa fechar a rota`,
    )

    await assert.rejects(loader.loadRegion(REFERENCE_SLUG), (error) => {
      assert.equal(error.code, 'region_not_published', `${name}: a retratação não pode ser reversível`)
      return true
    })
  }
  assert.equal(mutations.length, 6)
})

test('a retratação avisa a navegação em vez de esperar a próxima leitura', async () => {
  const candidate = draft()
  candidate.region.name = 'Serra Gaúcha'
  const loader = loaderOver({ region: `${JSON.stringify(candidate, null, 2)}\n` })

  let notifications = 0
  const unsubscribe = loader.subscribe(() => { notifications += 1 })
  await assert.rejects(loader.loadRegion(REFERENCE_SLUG))
  assert.equal(notifications, 1)
  unsubscribe()

  await assert.rejects(loader.loadRegion(REFERENCE_SLUG))
  assert.equal(notifications, 1, 'quem cancelou a inscrição não recebe mais avisos')
})

test('arquivo de região ausente também retrata a região', async () => {
  const loader = createVocacoesRegiaoLoader({
    logger: () => {},
    fetchText: async (requested) => {
      if (requested === VOCACOES_MANIFEST_PATH) return publishedManifestRaw
      throw new Error('HTTP 404')
    },
  })
  await assert.rejects(loader.loadRegion(REFERENCE_SLUG), (error) => {
    assert.equal(error.code, 'region_unavailable')
    return true
  })
  assert.ok(!(await loader.listPublishedRegionSlugs()).includes(REFERENCE_SLUG))
})

test('manifesto quebrado fecha a divisão inteira, em vez de virar publicação parcial', async () => {
  const broken = JSON.parse(publishedManifestRaw)
  broken.scopeType = 'municipality'
  assert.throws(() => parseVocacoesManifest(broken), /escopo territorial/)

  const extra = JSON.parse(publishedManifestRaw)
  extra.observacao = 'fora do contrato'
  assert.throws(() => parseVocacoesManifest(extra), /fora do contrato/)

  const stale = JSON.parse(publishedManifestRaw)
  stale.regions[0] = { ...stale.regions[0], cenarioDestaque: 'x' }
  assert.throws(() => parseVocacoesManifest(stale), /fora do contrato/)

  /* Os dois campos do Bloco 4 no manifesto precisam concordar: contar cenário
   * numa região que declara ausência é o manifesto mentindo sobre o bloco. */
  const mismatched = JSON.parse(publishedManifestRaw)
  mismatched.regions[0] = { ...mismatched.regions[0], scenarioCount: 4 }
  assert.throws(() => parseVocacoesManifest(mismatched), /não concordam/)

  const loader = loaderOver({ manifest: `${JSON.stringify(broken, null, 2)}\n` })
  await assert.rejects(loader.loadManifest(), (error) => {
    assert.equal(error.code, 'invalid_manifest')
    return true
  })
  assert.deepEqual(await loader.listPublishedRegionSlugs(), [])
})

/* ================================================================= *
 * 4. A ausência, que continua sendo um estado válido
 * ================================================================= */

test('o manifesto vazio segue válido e fechado — agora por fixture', async () => {
  const empty = buildEmptyManifest()
  const manifest = parseVocacoesManifest(structuredClone(empty))
  assert.deepEqual(manifest.regions, [])
  assert.equal(manifest.documentSchemaVersion, VOCACOES_DOCUMENT_SCHEMA)

  const raw = `${JSON.stringify(empty, null, 2)}\n`
  const loader = loaderOver({ manifest: raw })
  assert.deepEqual(await loader.listPublishedRegionSlugs(), [])
  await assert.rejects(loader.loadRegion(REFERENCE_SLUG), (error) => {
    assert.ok(error instanceof VocacoesLoadError)
    assert.equal(error.code, 'region_not_published')
    return true
  })
})

test('a decisão de visibilidade fecha antes e depois do manifesto', () => {
  assert.equal(isVocacoesPublished(VOCACOES_PUBLICATION_PENDING, REFERENCE_SLUG), false)
  const empty = { publishedSlugs: new Set(), ready: true }
  assert.equal(isVocacoesPublished(empty, REFERENCE_SLUG), false)
  const published = { publishedSlugs: new Set([REFERENCE_SLUG]), ready: true }
  assert.equal(isVocacoesPublished(published, REFERENCE_SLUG), true)
  assert.equal(isVocacoesPublished(published, null), false)
})

test('origem sem aprovação do contrato público: manifesto vazio com recusa registrada', () => {
  const semOrigem = resolveSource('caminho/que/nao/existe')
  assert.equal(semOrigem.available, false)
  assert.equal(semOrigem.refusal, null)

  const semAprovacao = resolveSource('scripts')
  assert.equal(semAprovacao.available, false)
  assert.match(semAprovacao.refusal, /ainda não foi aprovado/)

  const publication = buildPublication({ sourceRoot: 'scripts' })
  assert.deepEqual(publication.manifest.regions, [])
  assert.deepEqual(publication.files, [])
  assert.match(publication.refusal, /não transpõe\s+nada por conta própria/)
})

test('aprovação de uma versão de contrato que o gerador não implementa é erro alto', async () => {
  const { mkdtemp, writeFile: writeTempFile, rm } = await import('node:fs/promises')
  const { join } = await import('node:path')
  const dir = await mkdtemp(join(tmpdir(), 'vocacoes-regiao-aprovacao-'))
  try {
    await writeTempFile(
      join(dir, 'CONTRATO_PUBLICO_APROVADO.json'),
      `${JSON.stringify({ publicContractVersion: 'vocacoes-regiao-9.9.9' })}\n`,
      'utf8',
    )
    assert.throws(() => resolveSource(dir), /esta versão do gerador implementa/)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
})

/* ================================================================= *
 * 5. Corpus adversarial — fixture permanente (§5.5, C24)
 * ================================================================= */

/*
 * O corpus mede as duas defesas desta camada em separado, e o resultado é
 * declarado como é. Quatro ataques passam: três construções causais de classe
 * aberta do vetor 3 e o futuro implícito sem ano nenhum — o item `B4` do
 * backlog, herdado da Rodada 4 e ainda não fechado. Fingir que a guarda os pega
 * seria pior do que a guarda não pegá-los.
 *
 * Para comparação, o instrumento da Rodada 4 media, sobre o pacote de pesquisa,
 * 14 ataques fechados e 6 textos honestos recusados. Esta camada fecha 15 e não
 * recusa nenhum honesto.
 */
test('o corpus adversarial: 15 dos 19 ataques recusados, 4 furos declarados, 0 falso positivo', async () => {
  const { ATAQUES, HONESTOS, DECLARED_GAPS } = await import('./fixtures/vocacoes-regiao-corpus.mjs')
  const { createPublicLanguageGuard, scanPublicDocument, assertPublicationRules } = await import(
    '../lib/vocacoes-public-language.mjs'
  )
  const { DEFAULT_SOURCE_ROOT, RESEARCH_CONTRACT_FILE } = await import(
    '../generate-vocacoes-regiao.mjs'
  )
  const { readFileSync } = await import('node:fs')
  const { join } = await import('node:path')

  const researchContract = JSON.parse(
    readFileSync(join(DEFAULT_SOURCE_ROOT, RESEARCH_CONTRACT_FILE), 'utf8'),
  )
  const guard = createPublicLanguageGuard(researchContract)
  guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

  const refused = (mutate) => {
    const candidate = draft()
    mutate(candidate)
    try {
      scanPublicDocument(candidate, guard)
      assertPublicationRules(candidate, { cadastralUniverseLabel: guard.cadastralUniverseLabel })
    } catch {
      return true
    }
    try {
      parseDocument(structuredClone(candidate))
    } catch {
      return true
    }
    return false
  }

  assert.equal(ATAQUES.length, 19)
  assert.equal(HONESTOS.length, 6)

  const open = ATAQUES.filter(([, , mutate]) => !refused(mutate)).map(([id]) => id)
  assert.deepEqual(
    open,
    DECLARED_GAPS,
    'os furos abertos precisam ser exatamente os declarados — nem mais, nem menos',
  )

  const falsePositives = HONESTOS.filter(([, mutate]) => refused(mutate)).map(([id]) => id)
  assert.deepEqual(falsePositives, [], 'texto honesto recusado é defeito tão grave quanto ataque aceito')
})

/* ================================================================= *
 * 6. Os quatro defeitos que a revisão adversarial encontrou
 * ================================================================= */

/*
 * Cada um destes casos passava pelo contrato antes da revisão. Eles ficam aqui
 * como regressão nomeada: o instrumento que reprova é o mesmo, e o caso diz
 * qual furo ele fechou.
 */
test('o corte mensal usa o mês de referência, não dezembro', () => {
  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.periodGranularity === 'monthly')
    const december = publishedManifest.referenceYear * 100 + 12
    serie.periodEnd = december
    serie.points.push({ period: december, value: 1, evidenceClass: 'observed' })
  }, /ultrapassa o período de referência/)
})

test('a janela precisa caber na série, não apenas encostar nela', () => {
  refuses((candidate) => {
    const association = candidate.associations.items[0]
    association.window = { start: association.window.start, end: publishedManifest.referenceYear + 73 }
  }, /ultrapassa o ano de referência/)

  refuses((candidate) => {
    const association = candidate.associations.items[0]
    association.window = { start: 1900, end: association.window.end }
  }, /não cabe na série/)
})

test('uma segunda frase emendada na alegação proibida é recusada', () => {
  refuses((candidate) => {
    candidate.associations.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}a matrícula caiu.O emprego subiu.`
  }, /única sentença/)

  refuses((candidate) => {
    candidate.temporalPairs.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}uma coisa é a outra; a segunda moveu a primeira.`
  }, /única sentença/)

  refuses((candidate) => {
    candidate.temporalPairs.items[0].prohibitedClaim =
      `${PROHIBITED_CLAIM_OPENER}uma coisa moveu a outra`
  }, /terminar em ponto final/)
})

test('razão entre somas e ratioOf precisam concordar nos dois sentidos', () => {
  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.ratioOf === null)
    serie.aggregationLabel = 'Soma dos numeradores dividida pela soma dos denominadores.'
  }, /precisam concordar/)

  refuses((candidate) => {
    const serie = candidate.territoryPortrait.series.find((item) => item.ratioOf !== null)
    serie.ratioOf = null
  }, /precisam concordar/)
})

test('o identificador público precisa ser o slug do rótulo que ele nomeia', () => {
  refuses((candidate) => {
    /* Kebab-case perfeito, e ainda assim a chave interna transcodificada. */
    candidate.territoryPortrait.series[0].seriesId = 'cadastro-social-familias-inscritas'
  }, /não é o identificador do rótulo/)

  refuses((candidate) => {
    candidate.temporalPairs.items[0].pairId = 'regiao-fiergs-demografia-e-matriculas'
  }, /nome institucional "fiergs"/)

  refuses((candidate) => {
    const association = candidate.associations.items[0]
    association.associationId = slugify(`${association.label} e outra coisa qualquer`)
  }, /não é o identificador do resultado educacional/)
})

test('o identificador de toda série e de todo par publicado sai do rótulo', () => {
  for (const serie of publishedRegion.territoryPortrait.series) {
    assert.equal(serie.seriesId, slugify(serie.label), serie.label)
  }
  for (const pair of publishedRegion.temporalPairs.items) {
    assert.equal(pair.pairId, slugify(pair.label), pair.label)
  }
})
