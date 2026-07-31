import {
  PNE_2026_GOAL_INDICATOR_CONTRACT,
  getPne2026RelationContext,
} from '../data/pne2026GoalIndicatorContract.js'
import { getPneLegalRelationPresentation } from './pneLegalGoalsPresentation.js'

const SOURCE_CENSO_ESCOLAR = 'Censo Escolar / Sinopse Estatística da Educação Básica — INEP'
const SOURCE_ATU = 'INEP - Média de Alunos por Turma (ATU)'
const SOURCE_POPULATION_ATTENDANCE = 'Censo Escolar — INEP; Estimativas Populacionais — IBGE'
const SOURCE_EDUCATIONAL_INDICATORS = 'Indicadores Educacionais — INEP'
const SOURCE_IDEB_SAEB = 'IDEB / SAEB — INEP'
const SOURCE_FUNDEB = 'SIOPE / FNDE'
const SOURCE_PNATE = 'PNATE / FNDE'
const SOURCE_CENSO_DEMOGRAFICO = 'Censo Demográfico — IBGE'
const SOURCE_EJA_INTEGRADA = 'INEP — Sinopse Estatística da Educação Básica.'
const SOURCE_MEDIO_TECNICO_ARTICULADO = 'INEP — Sinopse Estatística da Educação Básica.'
const SOURCE_CHILD_LITERACY = 'INEP — Avaliação da Alfabetização / Indicador Criança Alfabetizada.'
const METHODOLOGY_CHILD_LITERACY = 'Percentual de estudantes da rede municipal considerados alfabetizados ao final do 2º ano do ensino fundamental. O indicador utiliza o padrão nacional da Avaliação da Alfabetização e não corresponde exatamente ao critério da Meta 5 do PNE 2014–2024, que previa alfabetização até o final do 3º ano.'
const METHODOLOGY_POPULATION_ATTENDANCE = 'Cobertura estimada; valores acima de 100% podem ocorrer por estimativas populacionais, mobilidade escolar e oferta localizada no município.'
const TECHNICAL_METHOD_IDENTIFIER = /\b(?:(?:[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*_)+[A-Za-zÀ-ÿ0-9]+|PC_[A-Z0-9_]+|TP_[A-Z0-9_]+|MEDU\d+)\b/u

const EDUCATION_THEME_SOURCES = {
  aprendizagem: SOURCE_IDEB_SAEB,
  fluxo: SOURCE_EDUCATIONAL_INDICATORS,
  matriculas: SOURCE_CENSO_ESCOLAR,
  oferta: SOURCE_CENSO_ESCOLAR,
  rede: SOURCE_CENSO_ESCOLAR,
  sistema_s: SOURCE_CENSO_ESCOLAR,
  docentes: SOURCE_CENSO_ESCOLAR,
  turmas: SOURCE_ATU,
  alunos_turma: SOURCE_ATU,
}

const POPULATION_ATTENDANCE_KEYS = new Set([
  'basico_15_17',
  'basico_6_17',
  'creche',
  'pre_escola',
])

const CENSO_ESCOLAR_KEYS = new Set([
  'aee',
  'adequacao_af',
  'adequacao_ai',
  'adequacao_em',
  'basico_integral',
  'conselho_escolar',
  'desktop_aluno',
  'eja_integrada_educacao_profissional',
  'eja_integrada_educacao_profissional_percentual',
  'escolas_integral',
  'internet',
  'internet_comunidade',
  'internet_alunos',
  'internet_aprendizagem',
  'acesso_internet_computador',
  'acesso_internet_disp_pessoais',
  'banda_larga',
  'comp_portatil_aluno',
  'medio_tecnico',
  'medio_tecnico_articulado_percentual',
  'medio_tecnico_participacao_publica',
  'medio_tecnico_total',
  'pos_graduacao',
  'proposta_pedagogica',
  'rede_local',
  'rede_wireless',
  'salas_acessiveis',
  'salas_climatizadas',
  'subsequente_expansao',
  'tablet_aluno',
  'temporarios',
])

const METHODOLOGY_NOTES_BY_KEY = {
  aee: 'Indicador de contexto/proxy; a base aberta atual não oferece denominador municipal seguro para medir diretamente o público-alvo do AEE.',
  eja_integrada_educacao_profissional: 'Indicador de contexto; mostra volume absoluto e não calcula a proporção legal da meta.',
  eja_integrada_educacao_profissional_percentual: 'indicador calculado a partir das matrículas da EJA articuladas à educação profissional, considerando curso técnico integrado à EJA, FIC integrado à EJA de nível fundamental, FIC integrado à EJA de nível médio e o total de matrículas da EJA.',
  medio_tecnico_articulado_percentual: 'Indicador calculado pela soma das matrículas em cursos técnicos integrados e concomitantes, dividida pelo total de matrículas do ensino médio. A fonte não identifica estudantes únicos, por isso a relação permanece complementar.',
  internet: 'Indicador de contexto; não gera distância de meta legal por não medir velocidade, qualidade ou uso pedagógico.',
  internet_alunos: 'Indicador de contexto; não gera distância de meta legal por não medir velocidade, qualidade ou uso pedagógico.',
  internet_aprendizagem: 'Indicador de contexto; não gera distância de meta legal por não medir velocidade, qualidade ou uso pedagógico.',
  internet_comunidade: 'Indicador de contexto; não gera distância de meta legal por não medir velocidade, qualidade ou uso pedagógico.',
  acesso_internet_computador: 'Indicador de contexto; não gera distância de meta legal por não medir suficiência de equipamentos ou qualidade de conectividade.',
  acesso_internet_disp_pessoais: 'Indicador de contexto; não gera distância de meta legal por depender de dispositivos pessoais e não medir oferta pública universal.',
  rede_local: 'Indicador de contexto; não gera distância de meta legal por não medir qualidade ou cobertura efetiva da rede interna.',
  rede_wireless: 'Proxy parcial de rede interna sem fio; sem distância de meta legal.',
  banda_larga: 'Proxy parcial de conectividade; sem distância de meta legal por não medir velocidade efetiva ou qualidade.',
  proposta_pedagogica: 'Indicador de contexto; a meta legal depende de política/processo local e não apenas da existência declarada de proposta pedagógica.',
  desktop_aluno: 'Indicador de contexto; não mede suficiência de equipamentos por estudante.',
  comp_portatil_aluno: 'Indicador de contexto; não mede suficiência de equipamentos por estudante.',
  tablet_aluno: 'Indicador de contexto; não mede suficiência de equipamentos por estudante.',
  salas_climatizadas: 'Proxy parcial de conforto térmico; não mede todo o padrão físico do estabelecimento.',
  salas_acessiveis: 'Proxy parcial de acessibilidade; não mede toda a acessibilidade escolar, como circulação, atendimento, materiais, transporte e demais ambientes.',
}

export function getDataSourceParts(context = {}) {
  const block = normalize(context.block ?? context.bloco)
  const theme = normalize(context.themeKey ?? context.theme ?? context.section ?? context.tema)
  const indicatorKey = normalize(context.indicatorKey ?? context.key)
  const detailType = normalize(context.detailType ?? context.type)
  const text = normalize([
    context.indicatorName,
    context.label,
    context.title,
    context.description,
    context.subtitle,
    context.item?.label,
    context.item?.desc,
    context.item?.sub,
    context.details?.title,
    context.details?.subtitle,
    context.details?.source,
    context.details?.fonte,
    context.details?.methodology,
    context.details?.description,
    context.details?.calculation?.source,
    context.result?.source,
    context.result?.fonte,
    context.source,
    context.fonte,
    detailType,
  ].filter(Boolean).join(' '))
  const contractParts = getPne2026ContractSourceParts(context, indicatorKey)
  const isClosedCycleChildLiteracy =
    context.cycle === 'pne_2014_2024' && indicatorKey === 'alfabetizacao'
  const methodologyNote = [
    contractParts.methodology,
    getPne2026DetailContextNote(context, indicatorKey),
    getMethodologyNote(indicatorKey, text, context),
  ].filter(Boolean).join(' ')

  let source = ''

  if (block === 'fundeb' || theme === 'fundeb') {
    source = SOURCE_FUNDEB
  } else if (block === 'pnate' || theme === 'pnate') {
    source = SOURCE_PNATE
  } else if (isClosedCycleChildLiteracy) {
    source = SOURCE_CHILD_LITERACY
  } else if (contractParts.source) {
    source = contractParts.source
  } else if (POPULATION_ATTENDANCE_KEYS.has(indicatorKey)) {
    source = SOURCE_POPULATION_ATTENDANCE
  } else if (indicatorKey === 'eja_integrada_educacao_profissional_percentual') {
    source = SOURCE_EJA_INTEGRADA
  } else if (indicatorKey === 'medio_tecnico_articulado_percentual') {
    source = SOURCE_MEDIO_TECNICO_ARTICULADO
  } else if (isCensoDemografico(indicatorKey, text)) {
    source = SOURCE_CENSO_DEMOGRAFICO
  } else if (CENSO_ESCOLAR_KEYS.has(indicatorKey)) {
    source = SOURCE_CENSO_ESCOLAR
  } else if (isIdebSaeb(indicatorKey, text)) {
    source = SOURCE_IDEB_SAEB
  } else if (isEducationalIndicators(indicatorKey, text)) {
    source = SOURCE_EDUCATIONAL_INDICATORS
  } else if (isAtuAlunosTurma(indicatorKey, theme, text)) {
    source = SOURCE_ATU
  } else if (isCensoEscolarText(text)) {
    source = SOURCE_CENSO_ESCOLAR
  } else {
    const declaredSource = sourceFromDeclaredMetadata(context, text)
    if (declaredSource) {
      source = declaredSource
    } else if (block === 'educacao' && EDUCATION_THEME_SOURCES[theme]) {
      source = EDUCATION_THEME_SOURCES[theme]
    }
  }

  return { source, methodology: methodologyNote }
}

function getPne2026DetailContextNote(context, indicatorKey) {
  if (context.cycle !== 'pne_2026_2036' || !indicatorKey) return ''

  const relationContext = getPne2026RelationContext(
    context.item?.metaRef ?? context.result?.goalId,
    indicatorKey,
    context.result?.end_year,
  )
  if (!relationContext?.relation) return ''

  const presentation = getPneLegalRelationPresentation({
    item: context.item,
    relation: relationContext.relation,
  })
  return [
    presentation.territorialityLabel
      ? `Territorialidade: ${presentation.territorialityLabel}.`
      : '',
    presentation.limitation
      ? `Limitação: ${presentation.limitation}`
      : '',
  ].filter(Boolean).join(' ')
}

function getPne2026ContractSourceParts(context, indicatorKey) {
  if (context.cycle !== 'pne_2026_2036' || !indicatorKey) {
    return { methodology: '', source: '' }
  }

  const indicator = PNE_2026_GOAL_INDICATOR_CONTRACT.indicators?.[indicatorKey]
  if (!indicator) return { methodology: '', source: '' }

  const sourceIds = context.presentation?.sourceIds?.length
    ? context.presentation.sourceIds
    : indicator.sourceIds ?? []
  const resultYear = finiteYear(
    context.result?.end_year
      ?? context.result?.current?.year
      ?? context.details?.end_year,
  )
  const source = sourceIds
    .map((sourceId) => formatContractSource(sourceId, resultYear))
    .filter(Boolean)
    .join('; ')
  const formulaDescription = getPne2026PublicFormulaDescription(
    indicator.formulaId,
    indicator.publicDescription,
  )
  const methodology = [
    resultYear ? `Período do resultado: ${resultYear}.` : '',
    formulaDescription ? `Cálculo: ${formulaDescription}` : '',
    toPublicMethodologyText(indicator.methodologyNote),
  ].filter(Boolean).join(' ')

  return { methodology, source }
}

export function getPne2026PublicFormulaDescription(formulaId, fallback = '') {
  const description = PNE_2026_GOAL_INDICATOR_CONTRACT.formulas?.[formulaId]?.description
  const publicDescription = toPublicMethodologyText(description)
  return publicDescription || toPublicMethodologyText(fallback)
}

function formatContractSource(sourceId, resultYear) {
  const source = PNE_2026_GOAL_INDICATOR_CONTRACT.sources?.[sourceId]
  if (!source) return ''

  if (sourceId === 'inep_censo_escolar') {
    return `INEP — Censo Escolar${resultYear ? ` ${resultYear}` : ''}`
  }
  if (sourceId === 'ibge_censo_demografico_2022_indigena_9970') {
    return 'IBGE — Censo Demográfico 2022, população indígena de 4 a 17 anos'
  }
  if (sourceId === 'ibge_munic_2021') {
    return 'IBGE — MUNIC, Educação 2021'
  }

  const organization = source.organization?.includes('IBGE')
    ? 'IBGE'
    : source.organization?.includes('INEP')
      ? 'INEP'
      : source.organization
  return [organization, source.publicTitle].filter(Boolean).join(' — ')
}

function finiteYear(value) {
  const numeric = Number(value)
  return Number.isInteger(numeric) && numeric > 0 ? numeric : null
}

export function getDataSourceNote(context = {}) {
  const { source, methodology } = getDataSourceParts(context)
  return withMethodology(source, methodology)
}

function getMethodologyNote(indicatorKey, text, context) {
  const notes = []
  const declaredNote = [
    context.details?.methodology ??
      context.details?.methodological_note ??
      context.details?.methodology_note ??
      context.result?.methodology ??
      context.methodology,
  ].find(Boolean)

  if (
    context.cycle === 'pne_2014_2024'
    && indicatorKey === 'alfabetizacao'
  ) {
    notes.push(METHODOLOGY_CHILD_LITERACY)
  }
  if (POPULATION_ATTENDANCE_KEYS.has(indicatorKey)) {
    notes.push(METHODOLOGY_POPULATION_ATTENDANCE)
  }
  if (POPULATION_ATTENDANCE_KEYS.has(indicatorKey) && hasValueAbove100(context)) {
    const rawValue = getRawValueAbove100(context)
    notes.push(
      `Para facilitar a visualização e a comparação entre indicadores, os resumos exibem no máximo 100%. O valor calculado foi ${formatPercent(rawValue)}; resultados acima de 100% podem ocorrer por estimativas populacionais, mobilidade escolar e oferta localizada no município.`,
    )
  }
  if (!POPULATION_ATTENDANCE_KEYS.has(indicatorKey) && hasValueAbove100(context)) {
    const rawValue = getRawValueAbove100(context)
    notes.push(
      `Para facilitar a visualização e a comparação entre indicadores, os resumos exibem no máximo 100%. O valor calculado foi ${formatPercent(rawValue)} e requer leitura conjunta do universo e do denominador declarados.`,
    )
  }
  if (isCensoDemografico(indicatorKey, text)) {
    notes.push(
      'Censo Demográfico e linha censitária, não série anual municipal.',
    )
  }
  if (!CENSO_ESCOLAR_KEYS.has(indicatorKey) && isIdebSaeb(indicatorKey, text)) {
    notes.push(
      'SAEB/IDEB não é indicador anual; resultados por disciplina e etapa são leitura parcial da meta legal, não cumprimento integral.',
    )
  }
  if (METHODOLOGY_NOTES_BY_KEY[indicatorKey]) {
    notes.push(METHODOLOGY_NOTES_BY_KEY[indicatorKey])
  }
  if (declaredNote) {
    const publicDeclaredNote = toPublicMethodologyText(declaredNote)
    if (publicDeclaredNote) notes.push(publicDeclaredNote)
  }

  return [...new Set(notes)].join(' ')
}

function hasValueAbove100(context) {
  return getRawValueAbove100(context) !== null
}

function getRawValueAbove100(context) {
  const candidates = [
    context.result?.end_value,
    context.result?.current?.value,
    context.result?.current?.rawValue,
    context.result?.start_value,
    context.result?.current?.displayValue,
    ...(context.result?.series ?? []).map((point) => point?.valor ?? point?.value),
    ...(context.details?.series ?? []).map((point) => point?.valor ?? point?.value),
  ]

  const rawValue = candidates
    .map(Number)
    .find((value) => Number.isFinite(value) && value > 100)

  return rawValue ?? null
}

function formatPercent(value) {
  return `${Number(value).toLocaleString('pt-BR', {
    maximumFractionDigits: 1,
  })}%`
}

function toPublicMethodologyText(value) {
  if (typeof value !== 'string' || !value.trim()) return ''

  return value
    .trim()
    .split(/(?<=[.!?])\s+/u)
    .filter((sentence) => {
      const normalized = sentence.trim()
      return normalized
        && !/^(?:Numerador|Denominador)\s*:/iu.test(normalized)
        && !TECHNICAL_METHOD_IDENTIFIER.test(normalized)
    })
    .join(' ')
    .trim()
}

function withMethodology(source, note) {
  if (!note) return source
  if (!source) return `Nota metodológica: ${note}`
  return `${source.replace(/[.]\s*$/, '')}. Nota metodológica: ${note}`
}

function sourceFromDeclaredMetadata(context, normalizedText) {
  const fontes = Array.isArray(context.fontes) ? context.fontes : []
  const sourceNames = fontes
    .map((fonte) => normalize(fonte?.nome ?? fonte))
    .filter(Boolean)

  const combined = [normalizedText, ...sourceNames].join(' ')

  if (combined.includes('siope') || combined.includes('fnde')) {
    if (combined.includes('pnate')) {
      return SOURCE_PNATE
    }
    return SOURCE_FUNDEB
  }
  if (combined.includes('saeb') || combined.includes('ideb')) {
    return SOURCE_IDEB_SAEB
  }
  if (
    combined.includes('media de alunos por turma') ||
    combined.includes('alunos por turma (atu)') ||
    combined.includes(' atu')
  ) {
    return SOURCE_ATU
  }
  if (
    combined.includes('taxas de rendimento') ||
    combined.includes('rendimento escolar') ||
    combined.includes('distorcao idade serie') ||
    combined.includes('distorcao idade-serie') ||
    combined.includes('indicadores educacionais')
  ) {
    return SOURCE_EDUCATIONAL_INDICATORS
  }
  if (combined.includes('censo escolar') || combined.includes('sinopse estatistica')) {
    return SOURCE_CENSO_ESCOLAR
  }

  return ''
}

function isAtuAlunosTurma(indicatorKey, theme, text) {
  return (
    indicatorKey.includes('alunos-turma') ||
    theme === 'alunos_turma' ||
    text.includes('alunos por turma (atu)') ||
    text.includes('media de alunos por turma') ||
    text.includes('fonte: inep - media de alunos por turma') ||
    (theme === 'turmas' && (text.includes('alunos por turma') || text.includes('atu')))
  )
}

function isIdebSaeb(indicatorKey, text) {
  return (
    indicatorKey.includes('ideb') ||
    indicatorKey.includes('saeb') ||
    text.includes('ideb') ||
    text.includes('saeb') ||
    text.includes('aprendizagem')
  )
}

function isEducationalIndicators(indicatorKey, text) {
  return (
    indicatorKey.includes('aprovacao') ||
    indicatorKey.includes('reprovacao') ||
    indicatorKey.includes('abandono') ||
    indicatorKey.includes('distorcao') ||
    indicatorKey.includes('fluxo') ||
    indicatorKey.includes('idade_regular') ||
    text.includes('aprovacao') ||
    text.includes('reprovacao') ||
    text.includes('abandono') ||
    text.includes('distorcao idade') ||
    text.includes('fluxo escolar')
  )
}

function isCensoEscolarText(text) {
  return (
    text.includes('matricula') ||
    text.includes('escola') ||
    text.includes('turma') ||
    text.includes('docente') ||
    text.includes('etapa') ||
    text.includes('rede') ||
    text.includes('localizacao') ||
    text.includes('tempo integral') ||
    text.includes('zona rural') ||
    text.includes('oferta tecnica') ||
    text.includes('educacao profissional') ||
    text.includes('censo escolar') ||
    text.includes('sinopse estatistica')
  )
}

function isCensoDemografico(indicatorKey, text) {
  const CENSO_DEMOGRAFICO_KEYS = new Set([
    'alfabetizacao_pop_15_mais',
    'fundamental_concluido_18_mais',
    'fundamental_concluido_15_29',
    'fundamental_concluido_15_mais',
    'medio_concluido_18_mais',
    'medio_concluido_18_29',
    'escolaridade_media_18_29',
    'razao_escolaridade_racial_18_29',
    'ensino_medio_ou_basica_completa_pop_15_17',
    'ensino_fundamental_ou_completo_pop_6_14',
  ])

  if (CENSO_DEMOGRAFICO_KEYS.has(indicatorKey)) return true

  return (
    text.includes('censo demografico') ||
    text.includes('censos demograficos') ||
    text.includes('populacao de 18 anos ou mais') ||
    text.includes('populacao de 15 a 29 anos') ||
    text.includes('ensino medio concluido') ||
    text.includes('ensino fundamental concluido')
  )
}

function normalize(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
}
