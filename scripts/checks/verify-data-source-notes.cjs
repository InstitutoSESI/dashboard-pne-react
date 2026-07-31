const assert = require('node:assert/strict')

function legacyConcatenatedOutput(source, methodology) {
  if (!methodology) return source
  if (!source) return `Nota metodológica: ${methodology}`
  return `${source.replace(/[.]\s*$/, '')}. Nota metodológica: ${methodology}`
}

const POPULATION_METHODOLOGY = 'Cobertura estimada; valores acima de 100% podem ocorrer por estimativas populacionais, mobilidade escolar e oferta localizada no município.'
const DEMOGRAPHIC_METHODOLOGY = 'Censo Demográfico e linha censitária, não série anual municipal.'
const IDEB_METHODOLOGY = 'SAEB/IDEB não é indicador anual; resultados por disciplina e etapa são leitura parcial da meta legal, não cumprimento integral.'
const AEE_METHODOLOGY = 'Indicador de contexto/proxy; a base aberta atual não oferece denominador municipal seguro para medir diretamente o público-alvo do AEE.'
const CHILD_LITERACY_METHODOLOGY = 'Percentual de estudantes da rede municipal considerados alfabetizados ao final do 2º ano do ensino fundamental. O indicador utiliza o padrão nacional da Avaliação da Alfabetização e não corresponde exatamente ao critério da Meta 5 do PNE 2014–2024, que previa alfabetização até o final do 3º ano.'

const cases = [
  {
    name: 'FUNDEB',
    context: { block: 'fundeb' },
    expected: { source: 'SIOPE / FNDE', methodology: '' },
  },
  {
    name: 'PNATE',
    context: { block: 'pnate' },
    expected: { source: 'PNATE / FNDE', methodology: '' },
  },
  {
    name: 'atendimento populacional',
    context: { indicatorKey: 'creche' },
    expected: {
      source: 'Censo Escolar — INEP; Estimativas Populacionais — IBGE',
      methodology: POPULATION_METHODOLOGY,
    },
  },
  {
    name: 'Censo Demográfico',
    context: { indicatorKey: 'alfabetizacao_pop_15_mais' },
    expected: {
      source: 'Censo Demográfico — IBGE',
      methodology: DEMOGRAPHIC_METHODOLOGY,
    },
  },
  {
    name: 'Criança Alfabetizada no ciclo encerrado',
    context: {
      cycle: 'pne_2014_2024',
      indicatorKey: 'alfabetizacao',
    },
    expected: {
      source: 'INEP — Avaliação da Alfabetização / Indicador Criança Alfabetizada.',
      methodology: CHILD_LITERACY_METHODOLOGY,
    },
  },
  {
    name: 'Censo Escolar',
    context: { indicatorKey: 'aee' },
    expected: {
      source: 'Censo Escolar / Sinopse Estatística da Educação Básica — INEP',
      methodology: AEE_METHODOLOGY,
    },
  },
  {
    name: 'IDEB/SAEB',
    context: { indicatorKey: 'apr-ideb' },
    expected: {
      source: 'IDEB / SAEB — INEP',
      methodology: IDEB_METHODOLOGY,
    },
  },
  {
    name: 'Indicadores Educacionais',
    context: { indicatorKey: 'taxa_aprovacao' },
    expected: { source: 'Indicadores Educacionais — INEP', methodology: '' },
  },
  {
    name: 'Média de Alunos por Turma',
    context: { indicatorKey: 'alunos-turma' },
    expected: { source: 'INEP - Média de Alunos por Turma (ATU)', methodology: '' },
  },
  {
    name: 'fonte declarada em metadados',
    context: { fontes: [{ nome: 'SIOPE / FNDE' }] },
    expected: { source: 'SIOPE / FNDE', methodology: '' },
  },
  {
    name: 'fallback por tema de Educação',
    context: { block: 'educacao', themeKey: 'docentes' },
    expected: { source: 'Censo Escolar / Sinopse Estatística da Educação Básica — INEP', methodology: '' },
  },
  {
    name: 'Sistema S',
    context: { block: 'educacao', themeKey: 'sistema_s' },
    expected: { source: 'Censo Escolar / Sinopse Estatística da Educação Básica — INEP', methodology: '' },
  },
  {
    name: 'fonte com metodologia',
    context: { block: 'fundeb', methodology: 'Leitura restrita ao período informado.' },
    expected: { source: 'SIOPE / FNDE', methodology: 'Leitura restrita ao período informado.' },
  },
  {
    name: 'somente metodologia',
    context: { methodology: 'Método local de validação.' },
    expected: { source: '', methodology: 'Método local de validação.' },
  },
  {
    name: 'contexto vazio',
    context: {},
    expected: { source: '', methodology: '' },
  },
]

async function run() {
  const { getDataSourceNote, getDataSourceParts } = await import('../../src/utils/dataSourceNotes.js')

  for (const { name, context, expected } of cases) {
    const parts = getDataSourceParts(context)
    const legacyOutput = legacyConcatenatedOutput(expected.source, expected.methodology)

    assert.deepEqual(parts, expected, `${name}: partes estruturadas divergentes`)
    assert.equal(getDataSourceNote(context), legacyOutput, `${name}: saída retrocompatível divergente`)
    assert.equal(
      legacyConcatenatedOutput(parts.source, parts.methodology),
      legacyOutput,
      `${name}: reconstrução das partes divergente`,
    )
  }

  console.log(`Verified ${cases.length} data-source resolver cases.`)
}

run().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
