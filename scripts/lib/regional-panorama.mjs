/*
 * Agregações analíticas do Panorama da Região.
 *
 * Este módulo só lê os contratos municipais já publicados que o gerador lhe
 * entrega. Taxas com numerador e denominador regionais conhecidos usam razão
 * de somas. Os demais percentuais e índices usam mediana municipal, sempre
 * rotulada como tal; nunca se apresenta média simples como taxa da região.
 */

import { getPne2026IndicatorReferenceProfile } from '../../src/data/pne2026GoalIndicatorContract.js'

const EXACT_PNE_COVERAGE_KEYS = Object.freeze({
  creche: 'creche',
  pre_escola: 'pre_escola',
  basico_6_17: 'basico_6_17',
  basico_15_17: 'basico_15_17',
})

const FLOW_STAGES = Object.freeze([
  { key: 'fundamental_anos_iniciais', label: 'Ensino fundamental — anos iniciais' },
  { key: 'fundamental_anos_finais', label: 'Ensino fundamental — anos finais' },
  { key: 'medio', label: 'Ensino médio' },
])

const FLOW_METRICS = Object.freeze([
  { key: 'taxa_aprovacao', label: 'Taxa de aprovação' },
  { key: 'taxa_reprovacao', label: 'Taxa de reprovação' },
  { key: 'taxa_abandono', label: 'Taxa de abandono' },
  { key: 'taxa_distorcao', label: 'Distorção idade-série' },
])

const LEARNING_STAGES = Object.freeze([
  { key: 'fundamental_anos_iniciais', label: 'anos iniciais' },
  { key: 'fundamental_anos_finais', label: 'anos finais' },
  { key: 'medio', label: 'ensino médio' },
])

const ORGANIZATION_STAGES = Object.freeze([
  { key: 'infantil', label: 'Educação infantil' },
  { key: 'fundamental', label: 'Ensino fundamental' },
  { key: 'medio', label: 'Ensino médio' },
])

function fail(message) {
  throw new Error(`Panorama regional: ${message}`)
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function round2(value) {
  return Math.round(value * 100) / 100
}

function median(values) {
  if (values.length === 0) return null
  const ordered = [...values].toSorted((left, right) => left - right)
  const middle = Math.floor(ordered.length / 2)
  const value = ordered.length % 2 === 1
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2
  return round2(value)
}

function minimum(values) {
  return values.length === 0 ? null : Math.min(...values)
}

function maximum(values) {
  return values.length === 0 ? null : Math.max(...values)
}

function valueAtYear(result, year) {
  if (!Number.isInteger(year) || result === null || typeof result !== 'object') return null
  const point = Array.isArray(result.series)
    ? result.series.find((entry) => entry.ano === year && isFiniteNumber(entry.valor))
    : null
  if (point !== null && point !== undefined) return point.valor
  return result.end_year === year && isFiniteNumber(result.end_value)
    ? result.end_value
    : null
}

function availableYears(results) {
  const years = new Set()
  for (const result of results) {
    for (const point of result?.series ?? []) {
      if (Number.isInteger(point.ano) && isFiniteNumber(point.valor)) years.add(point.ano)
    }
    if (Number.isInteger(result?.end_year) && isFiniteNumber(result?.end_value)) {
      years.add(result.end_year)
    }
  }
  return [...years].toSorted((left, right) => left - right)
}

function valuesAtYear(sources, indicatorKey, year) {
  return sources
    .map((source) => valueAtYear(source.pne2026.indicadores[indicatorKey], year))
    .filter(isFiniteNumber)
}

function targetReached(value, reference) {
  if (!isFiniteNumber(value) || reference === null) return false
  return reference.direcao === 'at_most'
    ? value <= reference.valor
    : value >= reference.valor
}

function distanceToReference(value, reference) {
  if (!isFiniteNumber(value) || reference === null) return null
  return round2(reference.direcao === 'at_most'
    ? reference.valor - value
    : value - reference.valor)
}

function fallbackReference(results) {
  const result = results.find((candidate) => (
    candidate?.tracks_goal === true
    && isFiniteNumber(candidate.meta)
    && ['at_least', 'at_most'].includes(candidate.direction)
  ))
  if (result === undefined) return null
  const yearMatch = String(result.meta_label ?? '').match(/\b20\d{2}\b/)
  return {
    tipo: 'published',
    label: String(result.meta_label ?? 'Referência publicada'),
    valor: result.meta,
    ano: yearMatch === null ? null : Number(yearMatch[0]),
    direcao: result.direction,
  }
}

function resolveReference(indicatorKey, observedYear, results) {
  const canonical = getPne2026IndicatorReferenceProfile(
    indicatorKey,
    Number.isInteger(observedYear) ? observedYear : 2026,
  )
  if (canonical !== undefined) {
    return {
      tipo: canonical.kind,
      label: canonical.kind === 'legal' ? 'Meta do PNE' : canonical.label,
      valor: canonical.value,
      ano: canonical.year,
      direcao: canonical.direction,
    }
  }
  return fallbackReference(results)
}

function findCoverageIndicator(block, indicatorKey) {
  return block.indicadores.find((indicator) => indicator.chave === indicatorKey) ?? null
}

function findCoveragePoint(block, indicatorKey, year) {
  return findCoverageIndicator(block, indicatorKey)?.series
    .find((point) => point.ano === year) ?? null
}

function buildPneIndicator({
  catalogItem,
  regionalSources,
  stateSources,
  regionalCoverage,
  stateCoverage,
}) {
  const indicatorKey = catalogItem.key
  const stateResults = stateSources.map((source) => source.pne2026.indicadores[indicatorKey])
  if (stateResults.some((result) => result === undefined)) {
    fail(`o indicador PNE "${indicatorKey}" não está presente em todos os municípios.`)
  }
  const years = availableYears(stateResults)
  const year = years.at(-1) ?? null
  const reference = resolveReference(indicatorKey, year, stateResults)
  const regionalValues = valuesAtYear(regionalSources, indicatorKey, year)
  const stateValues = valuesAtYear(stateSources, indicatorKey, year)
  const exactCoverageKey = EXACT_PNE_COVERAGE_KEYS[indicatorKey]

  let method = 'municipal_median'
  let value = median(regionalValues)
  let stateValue = median(stateValues)
  let municipalitiesWithData = regionalValues.length
  let stateMunicipalitiesWithData = stateValues.length

  if (exactCoverageKey !== undefined && year !== null) {
    const regionalPoint = findCoveragePoint(regionalCoverage, exactCoverageKey, year)
    const statePoint = findCoveragePoint(stateCoverage, exactCoverageKey, year)
    method = 'regional_ratio'
    value = regionalPoint?.valor ?? null
    stateValue = statePoint?.valor ?? null
    municipalitiesWithData = regionalPoint?.municipiosComDado ?? 0
    stateMunicipalitiesWithData = statePoint?.municipiosComDado ?? 0
  }

  const municipalitiesAtReference = reference === null || regionalValues.length === 0
    ? null
    : regionalValues.filter((candidate) => targetReached(candidate, reference)).length

  return {
    chave: indicatorKey,
    titulo: String(catalogItem.label ?? indicatorKey),
    descricao: String(catalogItem.desc ?? catalogItem.label ?? indicatorKey),
    unidade: 'percent',
    acompanhaReferencia: reference !== null,
    referencia: reference,
    resultado: {
      metodo: method,
      ano: year,
      valor: value,
      valorEstado: stateValue,
      municipiosComDado: municipalitiesWithData,
      municipiosEstadoComDado: stateMunicipalitiesWithData,
      minimoMunicipal: minimum(regionalValues),
      maximoMunicipal: maximum(regionalValues),
      municipiosNaReferencia: municipalitiesAtReference,
      distanciaReferencia: distanceToReference(value, reference),
    },
  }
}

export function buildRegionalPneBlock({
  regionalSources,
  stateSources,
  catalog,
  regionalCoverage,
  stateCoverage,
}) {
  const categories = catalog?.categories
  if (!Array.isArray(categories) || categories.length === 0) {
    fail('o catálogo PNE 2026–2036 não publica categorias.')
  }
  const catalogKeys = new Set()
  const projectedCategories = categories.map((category) => {
    if (!Array.isArray(category.items) || category.items.length === 0) {
      fail(`a categoria PNE "${category.key}" não publica indicadores.`)
    }
    const indicators = category.items.map((item) => {
      if (typeof item.key !== 'string' || catalogKeys.has(item.key)) {
        fail(`chave PNE inválida ou duplicada: ${String(item.key)}.`)
      }
      catalogKeys.add(item.key)
      return buildPneIndicator({
        catalogItem: item,
        regionalSources,
        stateSources,
        regionalCoverage,
        stateCoverage,
      })
    })
    return {
      chave: String(category.key),
      label: String(category.label),
      indicadores: indicators,
    }
  })

  const municipalKeys = Object.keys(stateSources[0]?.pne2026?.indicadores ?? {}).toSorted()
  if (
    municipalKeys.length !== catalogKeys.size
    || municipalKeys.some((key) => !catalogKeys.has(key))
  ) {
    fail('o catálogo PNE e os indicadores municipais não têm o mesmo conjunto de chaves.')
  }

  const indicators = projectedCategories.flatMap((category) => category.indicadores)
  const withReference = indicators.filter((indicator) => indicator.referencia !== null)
  const evaluated = withReference.filter((indicator) => indicator.resultado.valor !== null)
  const met = evaluated.filter((indicator) => indicator.resultado.distanciaReferencia >= 0)

  return {
    cicloId: 'pne_2026_2036',
    label: 'PNE 2026–2036',
    descricao:
      'Posição regional diante das metas e referências do ciclo. Taxas regionais são usadas apenas quando numerador e denominador podem ser somados; nos demais casos, a leitura é a mediana dos municípios.',
    totalIndicadores: indicators.length,
    totalReferencias: withReference.length,
    referenciasAvaliadas: evaluated.length,
    referenciasAtingidas: met.length,
    indicadoresSemResultado: indicators.filter((indicator) => indicator.resultado.valor === null).length,
    categorias: projectedCategories,
  }
}

function annualCountSeries(
  sources,
  readSeries,
  readValue,
  { structuralZero = false, yearSources = sources } = {},
) {
  const years = new Set()
  for (const source of yearSources) {
    for (const point of readSeries(source) ?? []) {
      if (Number.isInteger(point.ano)) years.add(point.ano)
    }
  }
  return [...years]
    .toSorted((left, right) => left - right)
    .map((year) => {
      let total = 0
      let municipalitiesWithData = 0
      for (const source of sources) {
        const point = (readSeries(source) ?? []).find((candidate) => candidate.ano === year)
        const value = point === undefined ? null : readValue(point)
        if (isFiniteNumber(value)) {
          total += value
          municipalitiesWithData += 1
        } else if (structuralZero) {
          municipalitiesWithData += 1
        }
      }
      return {
        ano: year,
        valor: municipalitiesWithData === sources.length ? total : null,
        municipiosComDado: municipalitiesWithData,
      }
    })
}

function latestCountIndicator(definition, sources, yearSources) {
  const series = annualCountSeries(
    sources,
    definition.readSeries,
    definition.readValue,
    {
      structuralZero: definition.structuralZero === true,
      yearSources,
    },
  )
  const latest = series.findLast((point) => point.valor !== null) ?? null
  return {
    chave: definition.key,
    titulo: definition.label,
    grupo: definition.group,
    ano: latest?.ano ?? null,
    valor: latest?.valor ?? null,
    municipiosComDado: latest?.municipiosComDado ?? 0,
  }
}

const COUNT_INDICATORS = Object.freeze([
  {
    key: 'escolas',
    label: 'Escolas de educação básica',
    group: 'rede',
    readSeries: (source) => source.education.blocos.rede_escolar.series.total,
    readValue: (point) => point.valor,
  },
  {
    key: 'turmas',
    label: 'Turmas',
    group: 'rede',
    readSeries: (source) => source.education.blocos.turmas_docentes.series.total,
    readValue: (point) => point.turmas,
  },
  {
    key: 'docentes',
    label: 'Vínculos docentes informados',
    group: 'rede',
    readSeries: (source) => source.education.blocos.turmas_docentes.series.total,
    readValue: (point) => point.docentes,
  },
  {
    key: 'matriculas_tecnicas',
    label: 'Matrículas em cursos técnicos',
    group: 'oferta',
    readSeries: (source) => source.education.blocos.oferta_tecnica.series.total,
    readValue: (point) => point.valor,
  },
  ...['matriculas', 'estabelecimentos', 'turmas', 'docentes'].map((metric) => ({
    key: `educacao_indigena_${metric}`,
    label: {
      matriculas: 'Matrículas na educação escolar indígena',
      estabelecimentos: 'Estabelecimentos com educação escolar indígena',
      turmas: 'Turmas de educação escolar indígena',
      docentes: 'Docentes na educação escolar indígena',
    }[metric],
    group: 'educacao_indigena',
    readSeries: (source) => source.education.blocos.educacao_indigena.series_totais[metric],
    readValue: (point) => point.valor,
  })),
  ...['total_escolas', 'matriculas', 'turmas', 'docentes'].map((metric) => ({
    key: `sistema_s_${metric}`,
    label: {
      total_escolas: 'Escolas do Sistema S',
      matriculas: 'Matrículas no Sistema S',
      turmas: 'Turmas no Sistema S',
      docentes: 'Docentes no Sistema S',
    }[metric],
    group: 'sistema_s',
    structuralZero: true,
    readSeries: (source) => source.education.blocos.sistema_s.series[metric],
    readValue: (point) => point.valor,
  })),
])

function distributionMetric({
  key,
  label,
  unit,
  regionalSources,
  stateSources,
  readPoints,
}) {
  const years = new Set()
  for (const source of stateSources) {
    for (const point of readPoints(source) ?? []) {
      if (Number.isInteger(point.ano) && isFiniteNumber(point.valor)) years.add(point.ano)
    }
  }
  const year = [...years].toSorted((left, right) => left - right).at(-1) ?? null
  const valuesFor = (sources) => sources
    .map((source) => (readPoints(source) ?? [])
      .find((point) => point.ano === year && isFiniteNumber(point.valor))?.valor ?? null)
    .filter(isFiniteNumber)
  const regionalValues = valuesFor(regionalSources)
  const stateValues = valuesFor(stateSources)
  return {
    chave: key,
    titulo: label,
    unidade: unit,
    ano: year,
    valor: median(regionalValues),
    valorEstado: median(stateValues),
    minimoMunicipal: minimum(regionalValues),
    maximoMunicipal: maximum(regionalValues),
    municipiosComDado: regionalValues.length,
    municipiosEstadoComDado: stateValues.length,
  }
}

function fieldPoints(series, field) {
  return (series ?? []).map((point) => ({ ano: point.ano, valor: point[field] }))
}

function summaryPoint(block, yearField, valueField) {
  const summary = block?.resumo_ultimo_ano ?? {}
  return Number.isInteger(summary[yearField]) && isFiniteNumber(summary[valueField])
    ? [{ ano: summary[yearField], valor: summary[valueField] }]
    : []
}

function buildQualityCategories(regionalSources, stateSources) {
  const flowIndicators = FLOW_STAGES.flatMap((stage) => FLOW_METRICS.map((metric) => (
    distributionMetric({
      key: `fluxo_${stage.key}_${metric.key}`,
      label: `${metric.label} — ${stage.label}`,
      unit: 'percent',
      regionalSources,
      stateSources,
      readPoints: (source) => fieldPoints(
        source.education.blocos.fluxo.series.por_etapa[stage.key],
        metric.key,
      ),
    })
  )))

  const learningIndicators = []
  for (const stage of LEARNING_STAGES) {
    for (const metric of [
      { key: 'ideb', label: 'IDEB', unit: 'index' },
      { key: 'saeb_lp', label: 'Proficiência média em Língua Portuguesa', unit: 'score' },
      { key: 'saeb_mt', label: 'Proficiência média em Matemática', unit: 'score' },
    ]) {
      learningIndicators.push(distributionMetric({
        key: `aprendizagem_${metric.key}_${stage.key}`,
        label: `${metric.label} — ${stage.label}`,
        unit: metric.unit,
        regionalSources,
        stateSources,
        readPoints: (source) => fieldPoints(
          source.education.blocos.aprendizagem.series.ideb[stage.key],
          metric.key,
        ),
      }))
    }
  }
  learningIndicators.push(
    distributionMetric({
      key: 'aprendizagem_alfabetizacao',
      label: 'Estudantes alfabetizados ao final do 2º ano',
      unit: 'percent',
      regionalSources,
      stateSources,
      readPoints: (source) => summaryPoint(
        source.education.blocos.aprendizagem,
        'ano_alfabetizacao',
        'taxa_alfabetizacao',
      ),
    }),
    distributionMetric({
      key: 'aprendizagem_inse',
      label: 'Indicador de Nível Socioeconômico (INSE)',
      unit: 'index',
      regionalSources,
      stateSources,
      readPoints: (source) => summaryPoint(
        source.education.blocos.aprendizagem,
        'ano_inse',
        'media_inse',
      ),
    }),
  )

  const organizationIndicators = ORGANIZATION_STAGES.map((stage) => distributionMetric({
    key: `alunos_turma_${stage.key}`,
    label: `Média de alunos por turma — ${stage.label}`,
    unit: 'decimal',
    regionalSources,
    stateSources,
    readPoints: (source) => fieldPoints(
      source.education.blocos.alunos_turma.series.por_etapa[stage.key],
      'valor',
    ),
  }))
  organizationIndicators.push(
    distributionMetric({
      key: 'alunos_por_docente',
      label: 'Matrículas por vínculo docente informado',
      unit: 'decimal',
      regionalSources,
      stateSources,
      readPoints: (source) => fieldPoints(
        source.education.blocos.turmas_docentes.series.total,
        'alunos_por_docente',
      ),
    }),
  )

  return [
    { chave: 'fluxo', label: 'Fluxo e distorção', indicadores: flowIndicators },
    { chave: 'aprendizagem', label: 'Aprendizagem', indicadores: learningIndicators },
    { chave: 'organizacao', label: 'Organização da oferta', indicadores: organizationIndicators },
  ]
}

function buildVaarBlock(regionalSources, stateSources) {
  const year = Math.max(...stateSources
    .map((source) => source.education.blocos.vaar.ultimo_ano)
    .filter(Number.isInteger))
  const definitions = [
    ['habilitado_condicionalidades', 'Municípios habilitados nas condicionalidades'],
    ['recebe_aprendizagem', 'Municípios que recebem a parcela de aprendizagem'],
    ['recebe_atendimento', 'Municípios que recebem a parcela de atendimento'],
    ['melhorou_aprendizagem', 'Municípios com melhora no indicador de aprendizagem'],
    ['melhorou_atendimento', 'Municípios com melhora no indicador de atendimento'],
  ]
  return {
    label: 'VAAR/FUNDEB',
    descricao: 'Quantidade de municípios da região em cada condição publicada para o exercício mais recente.',
    ano: Number.isFinite(year) ? year : null,
    indicadores: definitions.map(([key, label]) => {
      const summarize = (sources) => {
        const values = sources
          .map((source) => source.education.blocos.vaar.resumo_ultimo_ano)
          .filter((summary) => summary?.ano_fundeb === year && typeof summary[key] === 'boolean')
        return {
          value: values.filter((summary) => summary[key] === true).length,
          withData: values.length,
        }
      }
      const regional = summarize(regionalSources)
      const state = summarize(stateSources)
      return {
        chave: key,
        titulo: label,
        valor: regional.withData === 0 ? null : regional.value,
        valorEstado: state.withData === 0 ? null : state.value,
        municipiosComDado: regional.withData,
        municipiosEstadoComDado: state.withData,
      }
    }),
  }
}

export function buildRegionalEducationBlock({ regionalSources, stateSources }) {
  return {
    label: 'Panorama educacional completo',
    descricao:
      'Estrutura, oferta, trajetória e aprendizagem agregadas a partir dos mesmos documentos municipais usados nas páginas de Educação.',
    contagens: COUNT_INDICATORS.map((definition) => (
      latestCountIndicator(definition, regionalSources, stateSources)
    )),
    qualidade: buildQualityCategories(regionalSources, stateSources),
    vaar: buildVaarBlock(regionalSources, stateSources),
  }
}
