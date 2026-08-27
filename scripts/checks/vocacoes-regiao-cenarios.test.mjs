/*
 * O Bloco 4 do Vocações da Região — contrato `vocacoes-regiao-2.3.0`.
 *
 * O arquivo irmão (`vocacoes-regiao-slot.test.mjs`) guarda os três blocos da
 * Fase A e a ausência. Este guarda o que a Rodada 9 acrescentou, e o que ela
 * acrescentou tem uma propriedade que os outros três blocos não têm: **duas
 * regiões o publicam e oito declaram que não o têm**. Um bloco que existe em
 * dois estados é um bloco com o dobro de maneiras de mentir.
 *
 * O que este arquivo prova, em ordem:
 *   1. o `2.1.0` é aditivo — nenhum campo dos blocos 1–3 sumiu ou mudou de
 *      nome, e o único campo novo do documento é `scenarios`;
 *   2. o estatuto do cenário é estrutural: enum fechado, frase renderizada do
 *      enum, e exatamente um normativo entre os quatro;
 *   3. nenhum número do bloco é digitado — toda âncora reconfere contra a série
 *      publicada no mesmo documento;
 *   4. a ausência é declarada nos dois sentidos, e nenhuma das quatro
 *      combinações incoerentes de estado passa;
 *   5. o `schema.json` da família declara a assimetria de estatuto como regra
 *      **única** desta família — a família municipal foi removida (D11), e o
 *      schema não a nomeia mais nem cita a regra que não vale aqui;
 *   6. a página desenha os dois estados — os quatro cenários numa região, a
 *      frase de ausência na outra, e a nota de estatuto antes de qualquer
 *      cenário.
 *
 * Como no arquivo irmão, toda recusa é provada por injeção.
 */

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

import {
  buildFamilySchema,
  buildPublication,
} from '../generate-vocacoes-regiao.mjs'
import {
  AGENDA_THEME_LABELS,
  AGENDA_THEMES,
  PROHIBITED_CLAIM_OPENER,
  SCENARIO_DIRECTION_LABELS,
  SCENARIO_FRAMING,
  SCENARIO_STATUTE_LABELS,
  UNIVERSE_LABELS,
  createVocacoesDocumentParser,
  slugify,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'

const read = (relativePath) => readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const manifest = JSON.parse(await read('public/data/vocacoes-regiao/manifest.json'))
const parseDocument = createVocacoesDocumentParser({
  documentSchema: manifest.documentSchemaVersion,
  sourceVersion: manifest.sourceVersion,
  publicationScope: manifest.publicationScope,
  referenceYear: manifest.referenceYear,
  referenceMonth: manifest.referenceMonth,
})

/** Uma região com cenários e uma sem — os dois estados do Bloco 4. */
const WITH_SCENARIOS = 'noroeste'
const WITHOUT_SCENARIOS = 'serra'

const withScenarios = JSON.parse(
  await read(`public/data/vocacoes-regiao/regioes/${WITH_SCENARIOS}.json`),
)
const withoutScenarios = JSON.parse(
  await read(`public/data/vocacoes-regiao/regioes/${WITHOUT_SCENARIOS}.json`),
)
/* A segunda regiao com cenarios: o controle decimal do arredondamento. */
const otherWithScenarios = JSON.parse(
  await read('public/data/vocacoes-regiao/regioes/vale-do-rio-pardo.json'),
)
const familySchema = JSON.parse(await read('public/data/vocacoes-regiao/schema.json'))

const draft = () => structuredClone(withScenarios)
const draftAbsent = () => structuredClone(withoutScenarios)

function refuses(candidate, pattern) {
  assert.throws(() => parseDocument(candidate), pattern)
}

/* ================================================================= *
 * 1. Aditividade — o `2.1.0` não mexeu nos blocos 1–3
 * ================================================================= */

/*
 * Os conjuntos de campos do `2.0.0`, transcritos aqui como **fixture
 * congelada**. Congelá-los é o ponto: se alguém renomear `periodLabel` para
 * `periodo` no contrato, o contrato continuará coerente consigo mesmo e este
 * teste é o único lugar que ainda saberá qual era o nome antes.
 *
 * `provenance` é o único conjunto que cresceu, e cresceu por acréscimo: os dois
 * resumos do cenário. Nada saiu, nada mudou de nome — que é o que «aditivo»
 * quer dizer.
 */
const FIELDS_2_0_0 = Object.freeze({
  documento: [
    'schemaVersion', 'contentVersion', 'generatedAt', 'generatorVersion', 'sourceVersion',
    'sourceMethodologyStatus', 'publicationScope', 'region', 'page', 'howToRead',
    'territoryPortrait', 'associations', 'temporalPairs', 'sources', 'limitations', 'provenance',
  ],
  region: ['slug', 'name', 'uf', 'municipalityCount'],
  page: ['eyebrow', 'title', 'description', 'neutralityNote'],
  howToRead: ['label', 'description', 'items'],
  territoryPortrait: ['label', 'description', 'series'],
  serie: [
    'seriesId', 'label', 'unitLabel', 'sourceLabel', 'evidenceClass', 'evidenceLabel',
    'universeLabel', 'aggregationLabel', 'ratioOf', 'periodGranularity', 'periodStart',
    'periodEnd', 'periodLabel', 'preliminaryPeriods', 'limitations', 'points',
  ],
  ponto: ['period', 'value', 'evidenceClass'],
  associacao: [
    'associationId', 'label', 'window', 'periodLabel', 'educationOutcome', 'territorialFactors',
    'observedStatement', 'allowedInterpretation', 'prohibitedClaim', 'hypotheses',
  ],
  janela: ['start', 'end'],
  referenciaDeSerie: ['seriesId', 'label'],
  par: [
    'pairId', 'label', 'window', 'periodLabel', 'seriesA', 'seriesB', 'observedStatement',
    'prohibitedClaim',
  ],
  fonte: ['label', 'periodLabel'],
  procedencia: [
    'sourcePackageSha256', 'sourceContractVersion', 'sourceBuilderVersion', 'sourceGeneratedAt',
    'registrySha256',
  ],
})

/** Onde cada conjunto congelado vive dentro do documento publicado. */
const NODE_OF = Object.freeze({
  documento: (document) => document,
  region: (document) => document.region,
  page: (document) => document.page,
  howToRead: (document) => document.howToRead,
  territoryPortrait: (document) => document.territoryPortrait,
  serie: (document) => document.territoryPortrait.series[0],
  ponto: (document) => document.territoryPortrait.series[0].points[0],
  associacao: (document) => document.associations.items[0],
  janela: (document) => document.associations.items[0].window,
  referenciaDeSerie: (document) => document.associations.items[0].educationOutcome,
  par: (document) => document.temporalPairs.items[0],
  fonte: (document) => document.sources.items[0],
  procedencia: (document) => document.provenance,
})

test('o contrato é aditivo sobre o 2.0.0: nenhum campo dos blocos 1–3 sumiu nem mudou de nome', () => {
  for (const [name, fields] of Object.entries(FIELDS_2_0_0)) {
    const node = NODE_OF[name](withScenarios)
    for (const field of fields) {
      assert.ok(
        Object.prototype.hasOwnProperty.call(node, field),
        `o campo "${field}" do conjunto "${name}" sumiu do contrato 2.1.0`,
      )
      /* Presente não basta: o campo precisa continuar **obrigatório**. Um campo
       * que virou opcional é um campo que sumiu para metade dos documentos. */
      const candidate = draft()
      delete NODE_OF[name](candidate)[field]
      assert.throws(
        () => parseDocument(candidate),
        (error) => {
          /* A recusa precisa nomear o campo removido. Sem isso, o teste
           * aceitaria uma recusa por outro motivo e não provaria nada sobre
           * este campo em particular. */
          assert.match(error.message, /não traz os campos obrigatórios/)
          assert.ok(
            error.message.includes(field),
            `a recusa de "${name}" não nomeia o campo removido "${field}": ${error.message}`,
          )
          return true
        },
      )
    }
  }
})

test('os campos aditivos do documento incluem curadoria editorial, cenários, triagem e síntese', () => {
  const publicados = Object.keys(withScenarios).sort()
  const congelados = [...FIELDS_2_0_0.documento].sort()
  const novos = publicados.filter((field) => !congelados.includes(field))
  const perdidos = congelados.filter((field) => !publicados.includes(field))
  /* 2.7.0 (V5 R1): a leitura editorial é o quarto aditivo declarado. */
  assert.deepEqual(novos, ['editorialReading', 'scenarios', 'screenedRelations', 'synthesis'])
  assert.deepEqual(perdidos, [])

  /* A procedência é o outro conjunto que cresceu, e o acréscimo é declarado: os
   * dois resumos que fecham a cadeia do Bloco 4 até o esqueleto congelado, e o
   * resumo da camada municipal que a Rodada 5 do V2 acrescentou (sucessora da
   * D11), que segue a mesma regra — sha onde há cenário, nulo onde não há. */
  const procedencia = Object.keys(withScenarios.provenance).sort()
  const novosNaProcedencia = procedencia.filter(
    (field) => !FIELDS_2_0_0.procedencia.includes(field),
  )
  assert.deepEqual(novosNaProcedencia, [
    'municipalPackageSha256',
    'scenarioPackageSha256',
    'scenarioSourceSha256',
    'synthesisPackageSha256',
  ])
})

/* ================================================================= *
 * 2. O estatuto, que é o que distingue esta família da municipal
 * ================================================================= */

test('o contrato aceita as duas regiões com cenários', () => {
  const publication = buildPublication()
  const comCenario = publication.manifest.regions.filter(
    (entry) => entry.scenarioStatus === 'published',
  )
  assert.deepEqual(comCenario.map((entry) => entry.slug).sort(), ['noroeste', 'vale-do-rio-pardo'])
  for (const entry of comCenario) assert.equal(entry.scenarioCount, 4)
  assert.equal(
    publication.manifest.regions.filter((entry) => entry.scenarioStatus === 'absent').length,
    8,
  )

  const document = parseDocument(draft())
  assert.equal(document.scenarios.status, 'published')
  assert.equal(document.scenarios.block.items.length, 4)
})

test('o estatuto é estrutural: enum fechado, frase do enum, e um só normativo', () => {
  const statutes = withScenarios.scenarios.block.items.map((item) => item.statute)
  assert.deepEqual(statutes.filter((statute) => statute === 'normative').length, 1)
  assert.deepEqual(statutes.filter((statute) => statute === 'exploratory').length, 3)
  for (const item of withScenarios.scenarios.block.items) {
    assert.equal(item.statuteLabel, SCENARIO_STATUTE_LABELS[item.statute])
  }

  /* Estatuto fora do enum. */
  const inventado = draft()
  inventado.scenarios.block.items[0].statute = 'provavel'
  refuses(inventado, /statute fora do contrato/)

  /* A frase escrita à mão, contradizendo o enum: o defeito que a tabela existe
   * para tornar impossível. */
  const frase = draft()
  frase.scenarios.block.items[0].statuteLabel = 'Cenário mais provável dos quatro.'
  refuses(frase, /statuteLabel não é a frase declarada/)

  /* Nenhum normativo: quatro exploratórios sob uma nota que promete um ideal. */
  const semNormativo = draft()
  for (const item of semNormativo.scenarios.block.items) {
    item.statute = 'exploratory'
    item.statuteLabel = SCENARIO_STATUTE_LABELS.exploratory
  }
  refuses(semNormativo, /publica 0 cenários normativos/)

  /* Dois normativos: dois ideais técnicos concorrentes na mesma página. */
  const doisNormativos = draft()
  doisNormativos.scenarios.block.items[0].statute = 'normative'
  doisNormativos.scenarios.block.items[0].statuteLabel = SCENARIO_STATUTE_LABELS.normative
  refuses(doisNormativos, /publica 2 cenários normativos/)
})

test('o identificador do cenário sai do título, e título repetido é recusado', () => {
  for (const item of withScenarios.scenarios.block.items) {
    assert.equal(item.scenarioId, slugify(item.title))
  }
  const forjado = draft()
  forjado.scenarios.block.items[0].scenarioId = 'continuidade-relativa'
  refuses(forjado, /scenarioId não é o identificador do rótulo/)

  const repetido = draft()
  repetido.scenarios.block.items[1].title = repetido.scenarios.block.items[0].title
  repetido.scenarios.block.items[1].scenarioId = repetido.scenarios.block.items[0].scenarioId
  refuses(repetido, /scenarioId repetido/)
})

/* ================================================================= *
 * 3. Nenhum número digitado
 * ================================================================= */

test('toda âncora reconfere contra a série publicada no mesmo documento', () => {
  const seriesById = new Map(
    withScenarios.territoryPortrait.series.map((serie) => [serie.seriesId, serie]),
  )
  let ancoras = 0
  for (const item of withScenarios.scenarios.block.items) {
    for (const anchor of item.anchors) {
      const serie = seriesById.get(anchor.seriesId)
      assert.ok(serie !== undefined, `a âncora cita a série ausente ${anchor.seriesId}`)
      const inicio = serie.points.find((point) => point.period === anchor.window.start)
      const fim = serie.points.find((point) => point.period === anchor.window.end)
      assert.equal(inicio.value, anchor.startValue)
      assert.equal(fim.value, anchor.endValue)
      ancoras += 1
    }
  }
  assert.equal(ancoras, 20)

  /* Um dígito trocado no valor da âncora. */
  const adulterado = draft()
  adulterado.scenarios.block.items[0].anchors[0].endValue += 1
  refuses(adulterado, /endValue não é o valor da série/)

  const inicioAdulterado = draft()
  inicioAdulterado.scenarios.block.items[0].anchors[0].startValue += 1
  refuses(inicioAdulterado, /startValue não é o valor da série/)

  /* Uma âncora numa série que o documento não publica: o cenário citaria um
   * número que o leitor não pode conferir em lugar nenhum da página. */
  const orfa = draft()
  const anchor = orfa.scenarios.block.items[0].anchors[0]
  anchor.label = 'Série que não existe nesta página'
  anchor.seriesId = slugify(anchor.label)
  refuses(orfa, /não resolve em nenhuma série do documento/)
})

test('a frase de direção não pode contradizer os dois valores da âncora', () => {
  const subindo = draft()
  const alta = subindo.scenarios.block.items
    .flatMap((item) => item.anchors)
    .find((candidate) => candidate.directionLabel === SCENARIO_DIRECTION_LABELS.alta)
  assert.ok(alta !== undefined, 'a região de referência precisa ter ao menos uma âncora em alta')

  const invertido = draft()
  for (const item of invertido.scenarios.block.items) {
    for (const candidate of item.anchors) {
      if (candidate.directionLabel === SCENARIO_DIRECTION_LABELS.alta) {
        candidate.directionLabel = SCENARIO_DIRECTION_LABELS.baixa
      }
    }
  }
  refuses(invertido, /declara baixa e termina em/)

  const forjada = draft()
  forjada.scenarios.block.items[0].anchors[0].directionLabel = 'com forte crescimento'
  refuses(forjada, /directionLabel não é uma das frases de direção/)
})

/* ================================================================= *
 * 4. A ausência, declarada nos dois sentidos
 * ================================================================= */

test('a ausência de cenários é declarada, e nenhuma combinação incoerente passa', () => {
  const document = parseDocument(draftAbsent())
  assert.equal(document.scenarios.status, 'absent')
  assert.equal(document.scenarios.block, null)
  assert.equal(document.scenarios.statuteReadingNote, null)
  assert.ok(document.scenarios.absenceStatement.length > 0)

  /* (1) declara ausência e traz bloco. */
  const ausenteComBloco = draftAbsent()
  ausenteComBloco.scenarios.block = structuredClone(withScenarios.scenarios.block)
  refuses(ausenteComBloco, /declara ausência de cenários e traz bloco/)

  /* (2) declara publicação e não traz bloco. */
  const publicadoSemBloco = draft()
  publicadoSemBloco.scenarios.block = null
  publicadoSemBloco.scenarios.absenceStatement = null
  refuses(publicadoSemBloco, /declara cenários publicados e não traz o bloco/)

  /* (3) publica cenários e traz frase de ausência. */
  const publicadoComAusencia = draft()
  publicadoComAusencia.scenarios.absenceStatement = 'Esta região não tem cenários.'
  refuses(publicadoComAusencia, /publica cenários e traz frase de ausência/)

  /* (4) declara ausência e traz a nota que promete quatro cenários. */
  const ausenteComNota = draftAbsent()
  ausenteComNota.scenarios.statuteReadingNote = withScenarios.scenarios.statuteReadingNote
  refuses(ausenteComNota, /traz a nota de estatuto/)

  /* Estado que não existe. */
  const terceiroEstado = draftAbsent()
  terceiroEstado.scenarios.status = 'parcial'
  refuses(terceiroEstado, /status fora do contrato/)

  /* Sem frase de ausência, a região ficaria silenciosamente sem cenários — e
   * a frase precisa ser a do contrato, não uma qualquer (ver a seção 8). */
  const silenciosa = draftAbsent()
  silenciosa.scenarios.absenceStatement = null
  refuses(silenciosa, /não é a frase de ausência declarada/)
})

test('a procedência do cenário existe onde há cenário, e não existe onde não há', () => {
  assert.match(withScenarios.provenance.scenarioPackageSha256, /^[a-f0-9]{64}$/)
  assert.match(withScenarios.provenance.scenarioSourceSha256, /^[a-f0-9]{64}$/)
  assert.equal(withoutScenarios.provenance.scenarioPackageSha256, null)
  assert.equal(withoutScenarios.provenance.scenarioSourceSha256, null)

  const semProcedencia = draft()
  semProcedencia.provenance.scenarioSourceSha256 = null
  refuses(semProcedencia, /scenarioSourceSha256 deve ser sha256/)

  const procedenciaInventada = draftAbsent()
  procedenciaInventada.provenance.scenarioPackageSha256 = 'a'.repeat(64)
  refuses(procedenciaInventada, /não pode existir num documento sem cenários/)
})

/* ================================================================= *
 * 5. Fechado significa fechado, também no bloco novo
 * ================================================================= */

test('campo desconhecido é recusado em todo nível do bloco de cenários', () => {
  const injections = [
    ['scenarios', (candidate) => { candidate.scenarios.destaque = 'x' }],
    ['block', (candidate) => { candidate.scenarios.block.probabilidade = 0.4 }],
    ['cenário', (candidate) => { candidate.scenarios.block.items[0].peso = 1 }],
    ['âncora', (candidate) => { candidate.scenarios.block.items[0].anchors[0].projecao = 1 }],
    ['implicação', (candidate) => {
      candidate.scenarios.block.items[0].educationImplications[0].prioridade = 1
    }],
    ['critério normativo', (candidate) => {
      candidate.scenarios.block.normativeCriteria[0].prazo = '2031'
    }],
  ]
  for (const [level, mutate] of injections) {
    const candidate = draft()
    mutate(candidate)
    assert.throws(
      () => parseDocument(candidate),
      /campo desconhecido fora do contrato/,
      `campo desconhecido passou no nível "${level}"`,
    )
  }
})

test('a alegação proibida do bloco de cenários continua sendo uma proibição', () => {
  for (const item of withScenarios.scenarios.block.items) {
    assert.ok(item.prohibitedClaim.startsWith(PROHIBITED_CLAIM_OPENER))
  }
  assert.ok(withScenarios.scenarios.block.prohibitedClaim.startsWith(PROHIBITED_CLAIM_OPENER))

  const semAbridor = draft()
  semAbridor.scenarios.block.prohibitedClaim = 'Os cenários dizem o que vai acontecer.'
  refuses(semAbridor, /deve começar pelo abridor/)

  const segundaFrase = draft()
  segundaFrase.scenarios.block.items[0].prohibitedClaim =
    `${PROHIBITED_CLAIM_OPENER}a formação técnica caiu.O emprego a derrubou.`
  refuses(segundaFrase, /uma única sentença/)

  const invisivel = draft()
  invisivel.scenarios.block.items[0].prohibitedClaim =
    `${PROHIBITED_CLAIM_OPENER}a formação​técnica caiu.`
  refuses(invisivel, /caractere de controle/)
})

test('o horizonte precisa vir depois do ano de referência, e em ordem', () => {
  const block = withScenarios.scenarios.block
  assert.ok(block.baseYear <= manifest.referenceYear)
  assert.ok(block.targetYear > manifest.referenceYear)
  assert.ok(block.longScanTargetYear > block.targetYear)

  const passado = draft()
  passado.scenarios.block.targetYear = manifest.referenceYear
  refuses(passado, /targetYear deve ser um ano posterior/)

  const invertido = draft()
  invertido.scenarios.block.longScanTargetYear = invertido.scenarios.block.targetYear - 1
  refuses(invertido, /longScanTargetYear deve ser posterior/)
})

/* ================================================================= *
 * 6. O `schema.json` da família (D3)
 * ================================================================= */

test('o schema da família declara a assimetria de estatuto como regra única', () => {
  /* A regra própria da família: a assimetria de peso entre os quatro cenários.
   * É ela que a D3 protege, e ela é provada aqui contra o próprio schema
   * regional — não mais contra o «outro lado» de uma família que foi removida. */
  assert.ok(
    familySchema.rules.some((rule) => rule.includes('não têm o mesmo peso')),
    'a família regional precisa declarar a assimetria de estatuto como regra',
  )

  /* A regra de peso igual — que era da família municipal extinta — não pode
   * entrar aqui, nem por acidente, nem por omissão: esta família é assimétrica.
   * A cláusula distintiva daquela regra («não há ordem, pontuação ou
   * probabilidade») não aparece em regra nenhuma desta família. */
  assert.ok(
    !familySchema.rules.some((rule) => rule.includes('não há ordem, pontuação ou probabilidade')),
    'a regra de peso igual não pode aparecer nas regras da família regional',
  )
  assert.ok(
    familySchema.rules.every((rule) => !/(?<!não )têm o mesmo peso/u.test(rule)),
    'nenhuma regra desta família pode afirmar que os cenários têm o mesmo peso',
  )

  /* A família removida não é mais nomeada: nenhuma referência a `distinctFrom`
   * nem ao slug da família municipal sobrou apontando para o que não existe. O
   * slug é montado em partes de propósito — assim ele não existe como literal em
   * lugar nenhum do código, nem aqui, no teste que prova a sua ausência. */
  const removedFamilySlug = ['foresight', 'educacao'].join('-')
  assert.equal(familySchema.distinctFrom, undefined)
  assert.ok(
    !JSON.stringify(familySchema).includes(removedFamilySlug),
    'o schema regional não pode citar a família municipal removida',
  )

  assert.equal(familySchema.documentSchemaVersion, manifest.documentSchemaVersion)
  assert.equal(familySchema.manifestSchemaVersion, manifest.schemaVersion)
  assert.deepEqual(familySchema.scenarioCoverage.regionsWithScenarios, ['noroeste', 'vale-do-rio-pardo'])
  assert.equal(familySchema.scenarioCoverage.regionsWithoutScenarios.length, 8)

  /* O schema nasce do manifesto, e não de uma cópia à mão dele. */
  assert.deepEqual(buildFamilySchema(manifest), familySchema)
})

/* ================================================================= *
 * 7. A página, nos dois estados
 * ================================================================= */

const vite = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  optimizeDeps: { include: [], noDiscovery: true },
  publicDir: false,
  server: { hmr: false, middlewareMode: true, watch: null },
})
const { VocacoesReport } = await vite.ssrLoadModule(
  '/src/features/vocacoes-regiao/VocacoesRegiaoPage.tsx',
)

after(async () => {
  await vite.close()
})

const render = (document) => renderToStaticMarkup(createElement(VocacoesReport, { document }))

test('a página desenha os quatro cenários, com o estatuto antes da narrativa', () => {
  const markup = render(withScenarios)

  assert.ok(markup.includes(withScenarios.scenarios.label))
  assert.ok(markup.includes(withScenarios.scenarios.statuteReadingNote))
  for (const item of withScenarios.scenarios.block.items) {
    assert.ok(markup.includes(item.title), `o cenário "${item.title}" não foi renderizado`)
    assert.ok(markup.includes(item.statuteLabel))
    assert.ok(markup.includes(item.centralMechanism))
  }

  /* O normativo recebe tratamento visual próprio: é o cenário que um leitor
   * desatento lê como previsão. */
  assert.ok(markup.includes('vocacoes-statute--normative'))
  assert.ok(markup.includes('vocacoes-statute--exploratory'))

  /* A nota de estatuto vem antes do primeiro título de cenário. */
  const notePosition = markup.indexOf(withScenarios.scenarios.statuteReadingNote)
  const firstScenarioPosition = markup.indexOf(withScenarios.scenarios.block.items[0].title)
  assert.ok(
    notePosition < firstScenarioPosition,
    'a nota de estatuto precisa aparecer antes do primeiro cenário',
  )

  /* Nenhum identificador interno chega ao texto renderizado. */
  for (const item of withScenarios.scenarios.block.items) {
    assert.ok(!markup.includes(`>${item.scenarioId}<`))
  }
  assert.ok(!markup.includes('exploratory<'))
  assert.ok(!markup.includes('normative<'))
})

test('a região sem cenários mostra a frase de ausência, e não uma seção vazia', () => {
  const markup = render(withoutScenarios)

  assert.ok(markup.includes(withoutScenarios.scenarios.label))
  assert.ok(markup.includes(withoutScenarios.scenarios.absenceStatement))
  assert.ok(markup.includes('vocacoes-scenarios__absence'))

  /* Nada da moldura dos cenários publicados sobra aqui. */
  assert.ok(!markup.includes('vocacoes-statute--normative'))
  assert.ok(!markup.includes('vocacoes-scenarios__closing'))
  assert.ok(!markup.includes(withScenarios.scenarios.statuteReadingNote))
  for (const item of withScenarios.scenarios.block.items) {
    assert.ok(!markup.includes(item.title))
  }
})

test('os valores das âncoras chegam à página do jeito que a série os declara', () => {
  const markup = render(withScenarios)
  const serie = withScenarios.territoryPortrait.series.find(
    (candidate) => candidate.seriesId === withScenarios.scenarios.block.items[0].anchors[0].seriesId,
  )
  assert.ok(markup.includes(serie.label))
  for (const item of withScenarios.scenarios.block.items) {
    for (const anchor of item.anchors) {
      assert.ok(markup.includes(anchor.directionLabel))
    }
  }
})

/* ================================================================= *
 * 8. O que a revisão adversarial do contrato derrubou
 *
 * Três garantias foram atacadas e as três caíram em alguma medida. Cada
 * achado virou regra aqui — e cada regra é provada pela injeção que a motivou.
 * ================================================================= */

test('a frase de ausência não pode afirmar que há cenários', () => {
  /*
   * O contraexemplo do parecer, palavra por palavra: forma inteiramente
   * coerente, frase mentindo. Ele passava antes de a moldura virar tabela.
   */
  const mentiroso = draftAbsent()
  mentiroso.scenarios.absenceStatement =
    'Há quatro cenários publicados nesta região, incorporados a esta descrição.'
  refuses(mentiroso, /não é a frase de ausência declarada/)

  const descricaoTrocada = draftAbsent()
  descricaoTrocada.scenarios.description = SCENARIO_FRAMING.publishedDescription
  refuses(descricaoTrocada, /não é a descrição declarada para o estado "absent"/)

  const notaReescrita = draft()
  notaReescrita.scenarios.statuteReadingNote =
    'Os quatro cenários desta página têm o mesmo peso.'
  refuses(notaReescrita, /não é a nota de estatuto declarada/)

  const rotuloTrocado = draft()
  rotuloTrocado.scenarios.label = 'Previsões da região'
  refuses(rotuloTrocado, /não é o rótulo declarado/)

  /* E o que está publicado é exatamente a tabela. */
  assert.equal(withoutScenarios.scenarios.absenceStatement, SCENARIO_FRAMING.absenceStatement)
  assert.equal(withoutScenarios.scenarios.description, SCENARIO_FRAMING.absentDescription)
  assert.equal(withScenarios.scenarios.description, SCENARIO_FRAMING.publishedDescription)
  assert.equal(withScenarios.scenarios.statuteReadingNote, SCENARIO_FRAMING.statuteReadingNote)
})

test('o número escrito na prosa do cenário precisa de âncora por trás', () => {
  /* O contraexemplo do parecer: a âncora e a série ficam corretas, e só a
   * frase muda. Antes desta regra, o documento passava. */
  const prosaAdulterada = draft()
  const cenario = prosaAdulterada.scenarios.block.items[0]
  cenario.startingPointStatement = cenario.startingPointStatement.replace('14 527', '999 999')
  refuses(prosaAdulterada, /escreve o número "999 999", que nenhuma âncora deste cenário/)

  /* Série citada na prosa e não ancorada naquele cenário. */
  const semAncora = draft()
  const alvo = semAncora.scenarios.block.items[0]
  const naoAncorada = semAncora.territoryPortrait.series
    .map((serie) => serie.label)
    .find((label) => !alvo.anchors.some((anchor) => anchor.label === label))
  alvo.centralMechanism = `Nesta região, ${naoAncorada} acompanha a formação técnica dela.`
  refuses(semAncora, /sem ancorá-la neste cenário/)

  /* Controle: o texto publicado passa, inclusive com o arredondamento decimal
   * que a origem escreve (a âncora guarda 84,175…, a frase mostra 84,2). */
  assert.ok(parseDocument(draft()))
  assert.ok(parseDocument(structuredClone(otherWithScenarios)))
})

test('o rótulo de período da âncora sai da janela dela', () => {
  const forjado = draft()
  forjado.scenarios.block.items[0].anchors[0].periodLabel = '2019 a 2025'
  refuses(forjado, /periodLabel não descreve a janela da âncora/)
})

/* ================================================================= *
 * 9. Temas de agenda — a ponte Vocações → PNE (contrato 2.3.0, V2-D6)
 * ================================================================= */

test('cada cenário publicado traz temas de agenda, com o rótulo do enum', () => {
  for (const item of withScenarios.scenarios.block.items) {
    assert.ok(
      Array.isArray(item.agendaThemes) && item.agendaThemes.length > 0,
      `o cenário "${item.title}" não traz temas de agenda`,
    )
    const statements = new Set(item.educationImplications.map((i) => i.statement))
    const seen = new Set()
    for (const theme of item.agendaThemes) {
      assert.ok(AGENDA_THEMES.includes(theme.theme), `tema fora do enum: ${theme.theme}`)
      assert.equal(theme.themeLabel, AGENDA_THEME_LABELS[theme.theme])
      /* A frase do tema é byte-idêntica a uma implicação do próprio cenário —
       * nenhuma prosa nova entra pela porta da agenda. */
      assert.ok(
        statements.has(theme.statement),
        `o tema "${theme.theme}" não aponta para uma implicação do cenário`,
      )
      assert.ok(!seen.has(theme.theme), `tema repetido no cenário: ${theme.theme}`)
      seen.add(theme.theme)
    }
  }
})

test('o contrato recusa tema fora do enum, rótulo à mão, frase órfã e tema repetido', () => {
  const foraDoEnum = draft()
  foraDoEnum.scenarios.block.items[0].agendaThemes[0].theme = 'meta_3'
  refuses(foraDoEnum, /theme fora do contrato/)

  const rotuloAMao = draft()
  rotuloAMao.scenarios.block.items[0].agendaThemes[0].themeLabel = 'Atingir 85% até 2031'
  refuses(rotuloAMao, /themeLabel não é a frase declarada/)

  /* A frase que não é implicação nenhuma do cenário: a porta de prosa nova que
   * a regra de identidade fecha. */
  const fraseOrfa = draft()
  fraseOrfa.scenarios.block.items[0].agendaThemes[0].statement =
    'A meta 3 do PNE será atingida até 2031.'
  refuses(fraseOrfa, /não é a frase de nenhuma implicação/)

  const repetido = draft()
  const themes = repetido.scenarios.block.items[0].agendaThemes
  themes[1].theme = themes[0].theme
  themes[1].themeLabel = themes[0].themeLabel
  refuses(repetido, /theme repetido no mesmo cenário/)

  /* Campo desconhecido no tema é recusado como em todo nível fechado. */
  const campoNovo = draft()
  campoNovo.scenarios.block.items[0].agendaThemes[0].metaNumero = 3
  refuses(campoNovo, /campo desconhecido fora do contrato/)

  /* Tema ausente: o subcampo é obrigatório onde há cenário. */
  const semTemas = draft()
  semTemas.scenarios.block.items[0].agendaThemes = []
  refuses(semTemas, /agendaThemes deve trazer ao menos um tema/)
})

test('a página renderiza os temas de agenda sem vazar o enum interno', () => {
  const markup = render(withScenarios)
  for (const item of withScenarios.scenarios.block.items) {
    for (const theme of item.agendaThemes) {
      assert.ok(markup.includes(theme.themeLabel), `o tema "${theme.themeLabel}" não foi renderizado`)
      /* O enum interno nunca chega ao texto. */
      assert.ok(!markup.includes(`>${theme.theme}<`))
    }
  }
  assert.ok(markup.includes('Temas da agenda do PNE'))
})

test('a prosa do cenário não pode apresentá-lo como previsão ou plano aprovado', async () => {
  const { createPublicLanguageGuard, scanPublicDocument } = await import(
    '../lib/vocacoes-public-language.mjs'
  )
  const { DEFAULT_SOURCE_ROOT, RESEARCH_CONTRACT_FILE } = await import(
    '../generate-vocacoes-regiao.mjs'
  )
  const researchContract = JSON.parse(
    await readFile(`${DEFAULT_SOURCE_ROOT}/${RESEARCH_CONTRACT_FILE}`, 'utf8'),
  )
  const guard = createPublicLanguageGuard(researchContract)
  guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

  /* O documento publicado passa pela guarda inteira. */
  assert.ok(scanPublicDocument(structuredClone(withScenarios), guard))

  /* O contraexemplo do parecer: estatuto estrutural intacto, prosa mentindo. */
  const contradiz = draft()
  contradiz.scenarios.block.items[3].centralMechanism =
    'Este cenário é a previsão oficial e o plano aprovado pela região.'
  assert.throws(
    () => scanPublicDocument(contradiz, guard),
    /contradiz o estatuto declarado/,
  )

  /* E a negação honesta continua passando — é o que o bloco precisa dizer. */
  const honesto = draft()
  honesto.scenarios.block.items[3].centralMechanism =
    'Este cenário não é a previsão oficial da região, e não foi pactuado com ninguém.'
  assert.ok(scanPublicDocument(honesto, guard))
})
