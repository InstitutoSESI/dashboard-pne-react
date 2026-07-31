const CENSUS_INDICATOR_KEYS = new Set([
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

function normalizeText(value) {
  if (!value) return ''
  return String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
}

function toSeries(rows, valueKey) {
  if (!Array.isArray(rows)) return []

  const byYear = new Map()

  for (const row of rows) {
    const ano = Number(row?.ano)
    const valor = Number(row?.[valueKey])
    if (!Number.isFinite(ano) || !Number.isFinite(valor)) continue
    byYear.set(ano, { ano, valor })
  }

  return Array.from(byYear.values()).sort((a, b) => a.ano - b.ano)
}

export function isDemographicCensusIndicator({ indicatorKey, item, details }) {
  if (CENSUS_INDICATOR_KEYS.has(indicatorKey)) return true

  const text = normalizeText([
    item?.label,
    item?.desc,
    item?.sub,
    details?.title,
    details?.subtitle,
    details?.source,
    details?.fonte,
    details?.methodology,
    details?.description,
    details?.calculation?.source,
    details?.calculation?.numerator_label,
    details?.calculation?.denominator_label,
  ].filter(Boolean).join(' '))

  if (text.includes('censo demografico')) return true

  return (
    details?.unit === 'pessoas' &&
    text.includes('populacao') &&
    !Array.isArray(details?.series_dependencia)
  )
}

function buildCensusChartSeries({ result, details }) {
  const componentSeries = toSeries(details?.series_components, 'percentual')
  if (componentSeries.length > 0) return componentSeries

  const resultSeries = toSeries(result?.series, 'valor')
  if (resultSeries.length > 0) return resultSeries

  return toSeries(details?.series_total, 'valor')
}

export function buildDisplayIndicatorSeries({
  cycle,
  result,
  details,
  item,
  indicatorKey,
}) {
  if (!result) return []

  const isCensus = isDemographicCensusIndicator({ indicatorKey, item, details })

  if (isCensus) {
    return buildCensusChartSeries({ result, details })
  }

  const baseSeries = toSeries(result?.series, 'valor')

  if (cycle === 'pne_2014_2024') {
    return baseSeries.filter((point) => point.ano >= 2014 && point.ano <= 2024)
  }

  return baseSeries
}
