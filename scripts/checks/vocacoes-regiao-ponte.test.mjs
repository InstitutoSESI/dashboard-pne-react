/*
 * A ponte PNE ↔ Vocações — contrato `vocacoes-regiao-2.3.0`, Rodada 4 do V2.
 *
 * Este arquivo guarda a costura que a rodada acrescentou, nos dois sentidos:
 *
 *   1. **Vocações → PNE**: os temas de agenda e a guarda de linguagem nova do
 *      bloco ponte — número de meta e causalidade município←região —, medida
 *      contra um corpus bilateral (`fixtures/vocacoes-bridge-corpus.mjs`).
 *   2. **PNE → Vocações**: o bloco "Contexto territorial da região" na matriz
 *      municipal, que aparece quando há pacote regional e **some** quando não há
 *      — fail-closed por ausência, com `LoadedMatrizPage` puro.
 *
 * Como nos arquivos irmãos, toda recusa é provada por injeção.
 */

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test, { after } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

import {
  ATTACKS,
  DECLARED_GAPS,
  HONEST,
} from './fixtures/vocacoes-bridge-corpus.mjs'
import {
  AGENDA_THEME_LABELS,
  UNIVERSE_LABELS,
} from '../../src/features/vocacoes-regiao/vocacoesRegiaoContract.js'
import {
  createPublicLanguageGuard,
} from '../lib/vocacoes-public-language.mjs'
import {
  DEFAULT_SOURCE_ROOT,
  RESEARCH_CONTRACT_FILE,
} from '../generate-vocacoes-regiao.mjs'

const read = (relativePath) => readFile(new URL(`../../${relativePath}`, import.meta.url), 'utf8')

const researchContract = JSON.parse(
  await readFile(`${DEFAULT_SOURCE_ROOT}/${RESEARCH_CONTRACT_FILE}`, 'utf8'),
)
const guard = createPublicLanguageGuard(researchContract)
guard.cadastralUniverseLabel = UNIVERSE_LABELS.cadastral_registry

/* ================================================================= *
 * 1. A guarda nova do bloco ponte, contra o corpus bilateral
 * ================================================================= */

test('a guarda do bloco ponte recusa todos os ataques do corpus', () => {
  for (const [id, text] of ATTACKS) {
    assert.throws(
      () => guard.checkBridgeText(text, `corpus.${id}`),
      (error) => {
        assert.equal(error.name, 'PublicLanguageError')
        return true
      },
      `o ataque ${id} passou pela guarda: "${text}"`,
    )
  }
})

test('a guarda do bloco ponte aceita todos os textos honestos do corpus', () => {
  for (const [id, text] of HONEST) {
    assert.doesNotThrow(
      () => guard.checkBridgeText(text, `corpus.${id}`),
      `o texto honesto ${id} foi barrado indevidamente: "${text}"`,
    )
  }
})

test('os furos de classe aberta estão declarados, e o teste os documenta como abertos', () => {
  /* Um furo declarado é um ataque que a guarda ainda NÃO fecha. O teste afirma
   * que ele passa — se um dia fechar, este assert quebra e o furo sai da lista,
   * em vez de a lista mentir que ele está fechado. */
  for (const [id, text] of DECLARED_GAPS) {
    assert.doesNotThrow(
      () => guard.checkBridgeText(text, `gap.${id}`),
      `o furo declarado ${id} passou a ser fechado; remova-o de DECLARED_GAPS: "${text}"`,
    )
  }
})

test('todo rótulo do vocabulário de temas passa a guarda: sem número de meta, sem ano futuro', () => {
  for (const [theme, label] of Object.entries(AGENDA_THEME_LABELS)) {
    assert.doesNotThrow(
      () => {
        guard.checkGoalNumber(label, `agendaThemeLabel.${theme}`)
        guard.checkFutureYear(label, `agendaThemeLabel.${theme}`)
        guard.checkCausal(label, `agendaThemeLabel.${theme}`)
      },
      `o rótulo do tema "${theme}" não passa a guarda: "${label}"`,
    )
  }
})

test('checkGoalNumber recusa número de meta e aceita texto sem número de meta', () => {
  assert.throws(() => guard.checkGoalNumber('A meta 3 do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('estratégia 9.2', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A meta número 3 do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A meta n.º 3 do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A estratégia N° 3.1 do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A meta-3 do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A Meta Ⅲ do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A meta três do PNE.', 'x'), /número de uma meta/)
  assert.throws(() => guard.checkGoalNumber('A terceira meta do PNE.', 'x'), /número de uma meta/)
  /* "metade" e "metas de aprendizagem" não são número de meta. */
  assert.doesNotThrow(() => guard.checkGoalNumber('A metade da rede rural.', 'x'))
  assert.doesNotThrow(() => guard.checkGoalNumber('As metas de aprendizagem da região.', 'x'))
  assert.doesNotThrow(() => guard.checkGoalNumber('A estratégia foi analisada em três municípios.', 'x'))
  assert.doesNotThrow(() => guard.checkGoalNumber('A estratégia civil de educação.', 'x'))
})

test('checkAgendaTheme aplica a fronteira ao rótulo e à frase de sustentação', () => {
  const honestLabel = AGENDA_THEME_LABELS.ensino_medio
  const honestStatement = 'A permanência no ensino médio é um tema da agenda educacional.'

  assert.throws(
    () => guard.checkAgendaTheme('Ensino médio — Meta N° 3', honestStatement, 'agenda'),
    /número de uma meta/,
  )
  assert.throws(
    () => guard.checkAgendaTheme(honestLabel, 'A terceira meta do PNE orienta este tema.', 'agenda'),
    /número de uma meta/,
  )
  assert.doesNotThrow(() => guard.checkAgendaTheme(honestLabel, honestStatement, 'agenda'))
})

/* ================================================================= *
 * 2. As frases de moldura do bloco territorial passam a guarda
 * ================================================================= */

const vite = await createServer({
  appType: 'custom',
  logLevel: 'silent',
  optimizeDeps: { include: [], noDiscovery: true },
  publicDir: false,
  server: { hmr: false, middlewareMode: true, watch: null },
})

after(async () => {
  await vite.close()
})

const {
  buildMatrizTerritorialContext,
  buildTerritorialIntro,
  TERRITORIAL_READING_NOTE,
} = await vite.ssrLoadModule('/src/features/matriz/matrizTerritorialContext.ts')
const { LoadedMatrizPage } = await vite.ssrLoadModule('/src/features/matriz/MatrizPage.tsx')

const regionDocument = JSON.parse(
  await read('public/data/vocacoes-regiao/regioes/vale-do-rio-pardo.json'),
)
const matriz = JSON.parse(
  await read('public/data/pne2026-matriz/municipios/4313375.json'),
)

test('a moldura do bloco territorial passa a guarda do bloco ponte', () => {
  const intro = buildTerritorialIntro(regionDocument.region.name, regionDocument.region.municipalityCount)
  assert.doesNotThrow(() => guard.checkBridgeText(intro, 'territorial.intro'))
  assert.doesNotThrow(() => guard.checkBridgeText(TERRITORIAL_READING_NOTE, 'territorial.note'))

  /* A ressalva nega a causalidade município←região, e a negação honesta precisa
   * passar — é justamente o que o bloco tem de poder dizer. */
  assert.ok(/não explicam o resultado do município/u.test(TERRITORIAL_READING_NOTE))
})

/* ================================================================= *
 * 3. O bloco territorial na página, e o fail-closed por ausência
 * ================================================================= */

const render = (props) => renderToStaticMarkup(createElement(LoadedMatrizPage, props))

test('a matriz mostra o bloco territorial quando há pacote regional', () => {
  const territorialContext = buildMatrizTerritorialContext(regionDocument, matriz.municipality.ibge7)
  const markup = render({ matriz, territorialContext })

  assert.ok(markup.includes('Contexto territorial da região'))
  assert.ok(markup.includes(regionDocument.region.name))
  assert.ok(markup.includes('matriz-territorio'))
  /* A leitura honesta aparece; a proibida (causalidade) não é o que o bloco diz. */
  assert.ok(markup.includes('A região do município'))
  /* O link leva à página regional do mesmo município. */
  assert.ok(markup.includes(`municipio=${matriz.municipality.ibge7}`))
})

test('sem pacote regional, o bloco territorial some — a página não quebra', () => {
  const markup = render({ matriz })
  assert.ok(!markup.includes('Contexto territorial da região'))
  assert.ok(!markup.includes('matriz-territorio'))
  /* O resto da matriz continua no ar. */
  assert.ok(markup.includes('Matriz comparativa das metas'))
})
