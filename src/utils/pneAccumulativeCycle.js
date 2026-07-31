const BASELINE_YEAR = 2025
const PUBLIC_EXPANSION_KEY = 'medio_tecnico_participacao_publica'
const SUBSEQUENT_EXPANSION_KEY = 'subsequente_expansao'

const EXPANSION_SHARE_PRESENTATION_MODE = 'expansion-share-baseline'
const ABSOLUTE_EXPANSION_PRESENTATION_MODE = 'absolute-expansion-target'

const PNE_2026_ACCUMULATIVE_INDICATOR_KEYS = new Set([
  PUBLIC_EXPANSION_KEY,
  SUBSEQUENT_EXPANSION_KEY,
])

export function isPne2026AccumulativeIndicator(cycle, indicatorKey) {
  return cycle === 'pne_2026_2036' && PNE_2026_ACCUMULATIVE_INDICATOR_KEYS.has(indicatorKey)
}

export function buildPne2026AccumulativeModel({ cycle, indicatorKey, details }) {
  if (!isPne2026AccumulativeIndicator(cycle, indicatorKey)) return null

  if (indicatorKey === PUBLIC_EXPANSION_KEY) {
    return buildPublicExpansionModel(details)
  }

  return buildSubsequentExpansionModel(details)
}

export function buildRecentPublicExpansionReading(details, maxYears = 5) {
  if (!details) {
    return buildUnavailableRecentPublicExpansion('loading')
  }

  const comparableSeries = buildComparablePublicEnrollmentSeries(details)
  const windowSize = Number.isFinite(Number(maxYears))
    ? Math.max(2, Math.floor(Number(maxYears)))
    : 5
  const recentSeries = comparableSeries.slice(-windowSize)
  const first = recentSeries[0] ?? null
  const last = recentSeries.at(-1) ?? null

  if (!first || !last || first.ano === last.ano) {
    return buildUnavailableRecentPublicExpansion('insufficient-series', recentSeries)
  }

  const publicExpansion = last.publicEnrollment - first.publicEnrollment
  const totalExpansion = last.totalEnrollment - first.totalEnrollment
  const chartSeries = recentSeries.map((point) => {
    const endpointTotalExpansion = point.totalEnrollment - first.totalEnrollment
    const endpointPublicExpansion = point.publicEnrollment - first.publicEnrollment
    return {
      ano: point.ano,
      valor: point.ano === first.ano || endpointTotalExpansion <= 0
        ? null
        : (endpointPublicExpansion / endpointTotalExpansion) * 100,
    }
  })

  const shared = {
    chartSeries,
    endYear: last.ano,
    publicExpansion,
    recentSeries,
    startYear: first.ano,
    targetValue: 50,
    totalExpansion,
  }

  if (!Number.isFinite(publicExpansion) || !Number.isFinite(totalExpansion) || totalExpansion <= 0) {
    return {
      ...buildUnavailableRecentPublicExpansion('no-positive-expansion', recentSeries),
      ...shared,
    }
  }

  const currentValue = (publicExpansion / totalExpansion) * 100
  const isAtReference = Math.abs(currentValue - 50) < 1e-9
  const isAboveReference = currentValue > 50 && !isAtReference
  const status = isAtReference ? 'at-reference' : isAboveReference ? 'above' : 'below'

  return {
    ...shared,
    achieved: currentValue >= 50,
    currentValue,
    excessValue: Math.max(0, currentValue - 50),
    missingValue: Math.max(0, 50 - currentValue),
    status,
    statusLabel: status === 'at-reference'
      ? 'No patamar de 50% no recorte recente'
      : status === 'above'
        ? 'Acima do patamar de 50% no recorte recente'
        : 'Abaixo do patamar de 50% no recorte recente',
    tone: currentValue >= 50 ? 'success' : 'warning',
    unavailableReason: null,
  }
}

export function buildPne2026AccumulativePresentationModel({ cycle, indicatorKey, details, presentationMode }) {
  if (!isPne2026AccumulativeIndicator(cycle, indicatorKey)) return null

  if (indicatorKey === PUBLIC_EXPANSION_KEY) {
    if (presentationMode !== EXPANSION_SHARE_PRESENTATION_MODE) return null
    return buildExpansionSharePresentation(details)
  }

  if (presentationMode !== ABSOLUTE_EXPANSION_PRESENTATION_MODE) return null
  return buildSubsequentExpansionPresentation(details)
}

function buildExpansionSharePresentation(details) {
  const comparableSeries = buildComparablePublicEnrollmentSeries(details)
  const baseline = comparableSeries.find((point) => point.ano === BASELINE_YEAR)
  const latest = comparableSeries.at(-1) ?? null
  const cycleSeries = baseline && latest?.ano > BASELINE_YEAR
    ? comparableSeries.filter((point) => point.ano >= BASELINE_YEAR)
    : []
  const cycleReading = buildPublicExpansionReadingFromSeries(cycleSeries)
  const officialCycleMode = cycleSeries.length >= 2 && Number.isFinite(cycleReading.currentValue)
  const reading = officialCycleMode
    ? cycleReading
    : buildRecentPublicExpansionReading({
        series_components: comparableSeries
          .filter((point) => point.ano <= BASELINE_YEAR)
          .map((point) => ({
            ano: point.ano,
            numerador: point.publicEnrollment,
            denominador: point.totalEnrollment,
          })),
      })
  const mode = officialCycleMode ? 'officialCycleMode' : 'baselineMode'
  const loading = reading.status === 'loading'
  const hasValue = Number.isFinite(reading.currentValue)
  const period = reading.startYear && reading.endYear ? `${reading.startYear}–${reading.endYear}` : null
  const periodInSentence = reading.startYear && reading.endYear
    ? `${reading.startYear} a ${reading.endYear}`
    : 'período disponível'
  const publicChangePercent = getChangePercent(reading.recentSeries[0]?.publicEnrollment, reading.recentSeries.at(-1)?.publicEnrollment)
  const totalChangePercent = getChangePercent(reading.recentSeries[0]?.totalEnrollment, reading.recentSeries.at(-1)?.totalEnrollment)
  const publicStart = reading.recentSeries[0]?.publicEnrollment ?? null
  const publicEnd = reading.recentSeries.at(-1)?.publicEnrollment ?? null
  const totalStart = reading.recentSeries[0]?.totalEnrollment ?? null
  const totalEnd = reading.recentSeries.at(-1)?.totalEnrollment ?? null
  const currentDisplay = loading ? 'Carregando' : hasValue ? formatPercent(reading.currentValue) : '—'
  const distanceNarrative = hasValue
    ? formatReferenceDifference(reading.currentValue, reading.targetValue, 'percent')
    : 'Resultado não calculável para o período'
  const statusLabel = mode === 'baselineMode'
    ? 'Contexto pré-ciclo'
    : hasValue
      ? reading.statusLabel.replace(/ no recorte recente$/i, '')
      : 'Resultado do ciclo não calculável'
  const interpretation = buildExpansionShareInterpretation(reading)
  const tone = mode === 'baselineMode' ? 'muted' : reading.tone
  const model = {
    achieved: mode === 'officialCycleMode' ? reading.achieved : null,
    comparisonTitle: null,
    currentDisplay,
    currentLabel: mode === 'baselineMode' ? 'Contexto pré-ciclo' : 'Resultado do ciclo',
    currentValue: reading.currentValue,
    currentYear: reading.endYear,
    distanceDisplay: hasValue ? formatSignedPp(reading.currentValue - reading.targetValue) : '—',
    distanceLabel: 'Distância do patamar',
    distanceNarrative,
    endYear: reading.endYear,
    footerText: period ? `${period} · ${mode === 'baselineMode' ? 'contexto anterior ao novo ciclo' : 'acompanhamento oficial'}` : 'Dados comparáveis insuficientes',
    indicatorKey: PUBLIC_EXPANSION_KEY,
    kind: 'public-share',
    loading,
    mode,
    presentationMode: EXPANSION_SHARE_PRESENTATION_MODE,
    progress: null,
    referenceDisplay: '50%',
    referenceLabel: 'Patamar PNE',
    startYear: reading.startYear,
    status: mode === 'baselineMode' ? 'baseline' : reading.status,
    statusLabel,
    summaryState: mode === 'officialCycleMode' && hasValue ? (reading.achieved ? 'achieved' : 'attention') : null,
    targetValue: reading.targetValue,
    tone,
  }

  return {
    ...model,
    detail: {
      composition: {
        currentValue: reading.currentValue,
        distanceNarrative,
        endYear: reading.endYear,
        interpretation,
        mode,
        period,
        publicChangePercent,
        publicEnd,
        publicExpansion: reading.publicExpansion,
        publicStart,
        series: reading.recentSeries,
        startYear: reading.startYear,
        targetValue: reading.targetValue,
        totalChangePercent,
        totalEnd,
        totalExpansion: reading.totalExpansion,
        totalStart,
        unavailableReason: reading.unavailableReason,
      },
      description: 'Mede quanto da expansão acumulada das matrículas de EPT de nível médio foi atribuída ao segmento público; não mede a participação pública no estoque total.',
      loading,
      methodology: [
        'O ano-base oficial do ciclo 2026–2036 é 2025. O resultado oficial somente é ativado quando existe um período posterior válido e expansão total suficiente para aplicar a fórmula.',
        `No ${mode === 'baselineMode' ? 'contexto histórico' : 'ciclo oficial'} de ${periodInSentence}, participação pública na expansão = variação das matrículas públicas ÷ variação total das matrículas × 100.`,
        'Valores negativos e superiores a 100% são resultados possíveis da razão entre as variações e não são limitados visualmente.',
      ],
      methodSummary: 'Base oficial 2025 e decomposição da expansão',
      metrics: [
        { detail: mode === 'baselineMode' ? 'Contexto anterior ao novo ciclo' : 'Acompanhamento oficial', label: 'Período de referência', value: period ?? '—' },
        { detail: `${reading.startYear ?? '—'} → ${reading.endYear ?? '—'}`, label: 'Matrículas públicas', value: `${formatCount(publicStart)} → ${formatCount(publicEnd)}` },
        { detail: formatVariationDetail(publicChangePercent), label: 'Variação pública', tone: reading.publicExpansion < 0 ? 'warning' : 'success', value: formatSignedCount(reading.publicExpansion) },
        { detail: `${reading.startYear ?? '—'} → ${reading.endYear ?? '—'}`, label: 'Total da EPT', value: `${formatCount(totalStart)} → ${formatCount(totalEnd)}` },
        { detail: formatVariationDetail(totalChangePercent), label: 'Variação total', tone: reading.totalExpansion < 0 ? 'warning' : 'success', value: formatSignedCount(reading.totalExpansion) },
      ],
      reading: interpretation,
      statusLabel,
      tone,
    },
  }
}

function buildPublicExpansionReadingFromSeries(series) {
  const first = series[0] ?? null
  const last = series.at(-1) ?? null
  if (!first || !last || first.ano === last.ano) {
    return buildUnavailableRecentPublicExpansion('insufficient-series', series)
  }

  const publicExpansion = last.publicEnrollment - first.publicEnrollment
  const totalExpansion = last.totalEnrollment - first.totalEnrollment
  const shared = {
    endYear: last.ano,
    publicExpansion,
    recentSeries: series,
    startYear: first.ano,
    targetValue: 50,
    totalExpansion,
  }
  if (!Number.isFinite(totalExpansion) || totalExpansion <= 0) {
    return { ...buildUnavailableRecentPublicExpansion('no-positive-expansion', series), ...shared }
  }

  const currentValue = (publicExpansion / totalExpansion) * 100
  const status = Math.abs(currentValue - 50) < 1e-9 ? 'at-reference' : currentValue > 50 ? 'above' : 'below'
  return {
    ...shared,
    achieved: currentValue >= 50,
    currentValue,
    status,
    statusLabel: status === 'at-reference' ? 'No patamar de 50%' : status === 'above' ? 'Acima do patamar de 50%' : 'Abaixo do patamar de 50%',
    tone: currentValue >= 50 ? 'success' : 'warning',
    unavailableReason: null,
  }
}

function buildExpansionShareInterpretation(reading) {
  if (!Number.isFinite(reading.currentValue)) {
    if (reading.totalExpansion === 0) return 'Não houve expansão total no período; por isso, a participação acumulada não pode ser calculada.'
    if (Number.isFinite(reading.totalExpansion) && reading.totalExpansion < 0) return 'As matrículas totais diminuíram no período, sem expansão total válida para calcular uma participação acumulada interpretável.'
    return 'Resultado não calculável para o período por insuficiência de dados comparáveis.'
  }
  if (reading.publicExpansion < 0 && reading.totalExpansion > 0) return 'No período de referência, as matrículas totais da EPT cresceram, enquanto as matrículas públicas diminuíram. Por isso, a participação calculada do segmento público na expansão ficou negativa.'
  if (reading.publicExpansion > reading.totalExpansion) return 'O crescimento público superou a expansão líquida total, podendo produzir participação superior a 100%.'
  if (reading.publicExpansion >= 0 && reading.totalExpansion > 0) return 'O segmento público participou da expansão total da EPT no período.'
  return 'O resultado descreve a relação entre a variação pública e a variação total no período.'
}

function getChangePercent(startValue, endValue) {
  const start = Number(startValue)
  const end = Number(endValue)
  return Number.isFinite(start) && start !== 0 && Number.isFinite(end) ? ((end - start) / start) * 100 : null
}

function formatSignedCount(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  const sign = numeric > 0 ? '+' : numeric < 0 ? '−' : ''
  return `${sign}${formatCount(Math.abs(numeric))} matrículas`
}

function formatVariationDetail(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 'Variação percentual indisponível'
  if (numeric === 0) return 'Sem variação'
  return `${numeric < 0 ? 'Queda' : 'Crescimento'} de ${formatDecimal(Math.abs(numeric))}%`
}

function buildSubsequentExpansionPresentation(details) {
  const cycleModel = buildSubsequentExpansionModel(details)
  const loading = cycleModel.loading
  const currentValue = Number(cycleModel.currentValue)
  const targetValue = Number(cycleModel.targetValue)
  const baselineValue = Number(cycleModel.baselineValue)
  const hasValues = !loading && Number.isFinite(currentValue) && Number.isFinite(targetValue)
  const achieved = hasValues ? currentValue >= targetValue : null
  const recentSeries = takeRecentSeries(details?.series_total)
  const currentYear = cycleModel.currentYear ?? recentSeries.at(-1)?.ano ?? BASELINE_YEAR
  const isBaseline = hasValues && currentYear === BASELINE_YEAR
  const hasCycleGrowth = hasValues && currentValue > baselineValue
  const statusLabel = achieved === true
    ? 'Meta atingida'
    : isBaseline
      ? 'Ponto de partida definido'
      : hasCycleGrowth
        ? 'Acompanhamento em andamento'
        : achieved === false
          ? 'Sem avanço desde 2025'
          : 'Carregando dados do ciclo'
  const tone = achieved === true ? 'success' : hasCycleGrowth ? 'warning' : 'muted'
  const currentDisplay = loading ? 'Carregando' : formatCount(currentValue)
  const referenceDisplay = loading ? 'Carregando' : formatCount(targetValue)
  const distanceDisplay = hasValues
    ? formatCountDifference(currentValue, targetValue)
    : 'Carregando'
  const progress = hasValues ? cycleModel.progress : null
  const missingValue = hasValues ? Math.max(0, targetValue - currentValue) : null
  const targetIncrease = hasValues ? targetValue - baselineValue : null
  const currentIncrease = hasValues ? Math.max(0, currentValue - baselineValue) : null
  const model = {
    achieved,
    baselineValue,
    comparisonAriaLabel: hasValues
      ? `Ponto de partida em 2025, ${formatCount(baselineValue)} matrículas, mais ${formatCount(targetIncrease)} matrículas de expansão necessária, resulta na meta de 2036, ${referenceDisplay} matrículas`
      : 'Comparação com a referência de 2036 em carregamento',
    comparisonTitle: 'Ponto de partida + expansão necessária = meta 2036',
    currentDisplay,
    currentLabel: 'Valor atual do ciclo',
    currentValue: hasValues ? currentValue : null,
    currentYear,
    distanceDisplay,
    distanceLabel: 'Diferença',
    distanceNarrative: hasValues
      ? formatReferenceDifference(currentValue, targetValue, 'count')
      : 'Carregando',
    endYear: recentSeries.at(-1)?.ano ?? currentYear,
    footerText: currentYear === BASELINE_YEAR ? 'Ponto de partida · 2025' : `Atualizado em ${currentYear}`,
    indicatorKey: SUBSEQUENT_EXPANSION_KEY,
    kind: 'subsequent-enrollment',
    loading,
    missingValue,
    presentationMode: ABSOLUTE_EXPANSION_PRESENTATION_MODE,
    progress,
    referenceDisplay,
    referenceLabel: 'Referência 2036',
    startYear: recentSeries[0]?.ano ?? currentYear,
    status: isBaseline ? 'baseline' : achieved === true ? 'achieved' : achieved === false ? 'below' : 'loading',
    statusLabel,
    summaryState: isBaseline ? null : achieved === true ? 'achieved' : achieved === false ? 'attention' : null,
    targetValue: hasValues ? targetValue : null,
    tone,
  }

  return {
    ...model,
    detail: {
      composition: {
        baselineValue: hasValues ? baselineValue : null,
        baselineYear: BASELINE_YEAR,
        currentValue: hasValues ? currentValue : null,
        currentYear,
        missingValue,
        mode: ABSOLUTE_EXPANSION_PRESENTATION_MODE,
        progress,
        currentIncrease,
        targetIncrease,
        targetValue: hasValues ? targetValue : null,
      },
      description: 'A meta do ciclo é ampliar em 60% as matrículas em cursos técnicos subsequentes, tomando 2025 como linha de base.',
      loading,
      methodology: [
        `A linha de base de 2025 é ${hasValues ? formatCount(cycleModel.baselineValue) : 'carregada a partir da série validada'} matrículas. A referência de 2036 corresponde a um aumento de 60% sobre essa base${hasValues ? `, totalizando ${referenceDisplay} matrículas` : ''}.`,
        currentYear === BASELINE_YEAR
          ? 'O dado mais recente ainda é a própria linha de base. Por isso, a página compara o nível atual com a referência absoluta, sem tratar essa relação como avanço acumulado do ciclo.'
          : 'A evolução posterior à base permanece calculada segundo a metodologia validada do ciclo.',
      ],
      methodSummary: 'Base 2025 e referência de +60%',
      metrics: [
        { detail: 'matrículas', label: 'Ponto de partida — 2025', size: 'large', value: hasValues ? formatCount(baselineValue) : 'Carregando' },
        { detail: 'matrículas até 2036 · +60% sobre o valor de 2025', label: 'Expansão necessária', tone: 'success', value: hasValues ? `+${formatCount(targetIncrease)}` : 'Carregando' },
        { detail: 'matrículas', label: 'Meta — 2036', value: model.referenceDisplay },
        isBaseline
          ? { detail: '2025 define apenas o ponto de partida', label: 'Acompanhamento', tone: 'muted', value: 'Começa com os dados de 2026' }
          : { detail: `${formatPercent(progress)} do acréscimo previsto`, label: 'Acompanhamento', tone: progress > 0 ? 'success' : 'muted', value: `+${formatCount(currentIncrease)} matrículas` },
      ],
      reading: loading
        ? 'Carregando a matrícula mais recente.'
        : `Partimos de ${formatCount(baselineValue)} matrículas em 2025, precisamos acrescentar ${formatCount(targetIncrease)} e chegar a ${referenceDisplay} matrículas em 2036.`,
      statusLabel: model.statusLabel,
      tone: model.tone,
    },
  }
}

function buildPublicExpansionModel(details) {
  const dependencySeries = normalizeSeries(details?.series_dependencia)
  const baseline = dependencySeries.find((point) => point.ano === BASELINE_YEAR)
  const cycleSeries = dependencySeries.filter((point) => point.ano >= BASELINE_YEAR)
  const latest = cycleSeries.at(-1) ?? null

  if (!baseline || !latest) {
    return buildLoadingModel(PUBLIC_EXPANSION_KEY)
  }

  const baselinePublic = publicEnrollment(baseline)
  const latestPublic = publicEnrollment(latest)
  const baselineTotal = baselinePublic + numericValue(baseline.privada)
  const latestTotal = latestPublic + numericValue(latest.privada)
  const publicExpansion = latestPublic - baselinePublic
  const totalExpansion = latestTotal - baselineTotal
  const hasPostBaselineYear = latest.ano > BASELINE_YEAR
  const hasExpansion = hasPostBaselineYear && totalExpansion > 0
  const currentValue = hasExpansion ? (publicExpansion / totalExpansion) * 100 : null
  const targetValue = 50
  const missingValue = hasExpansion ? Math.max(0, targetValue - currentValue) : null
  const achieved = hasExpansion ? currentValue >= targetValue : null
  const status = achieved === true
    ? 'achieved'
    : achieved === false
      ? 'below'
      : hasPostBaselineYear
        ? 'pending'
        : 'baseline'

  return {
    indicatorKey: PUBLIC_EXPANSION_KEY,
    kind: 'public-share',
    baselineYear: BASELINE_YEAR,
    currentYear: latest.ano,
    currentValue,
    targetValue,
    missingValue,
    publicExpansion,
    totalExpansion,
    progress: hasExpansion ? clampPercent((currentValue / targetValue) * 100) : null,
    achieved,
    hasExpansion,
    loading: false,
    status,
    statusLabel: status === 'achieved'
      ? 'Meta atingida no ciclo'
      : status === 'below'
        ? 'Em acompanhamento'
        : status === 'pending'
          ? 'Aguardando expansão do ciclo'
          : 'Linha de base definida',
    tone: status === 'achieved' ? 'success' : status === 'below' ? 'warning' : 'muted',
    description: 'Pelo menos 50% das novas matrículas de EPT de nível médio criadas no ciclo 2026–2036 deverão ser públicas.',
    reading: hasExpansion
      ? `Desde a linha de base de 2025, a rede pública responde por ${formatPercent(currentValue)} da expansão acumulada de matrículas no ciclo.`
      : hasPostBaselineYear
        ? 'Ainda não houve expansão líquida positiva de matrículas após 2025. O indicador permanece sem classificação de alcance da meta.'
        : 'A linha de base do novo ciclo foi definida em 2025. O resultado estará disponível a partir de 2026, quando houver expansão de matrículas.',
  }
}

function buildSubsequentExpansionModel(details) {
  const totalSeries = normalizeSeries(details?.series_total)
  const baseline = totalSeries.find((point) => point.ano === BASELINE_YEAR)
  const cycleSeries = totalSeries.filter((point) => point.ano >= BASELINE_YEAR)
  const latest = cycleSeries.at(-1) ?? null

  if (!baseline || !latest) {
    return buildLoadingModel(SUBSEQUENT_EXPANSION_KEY)
  }

  const baselineValue = numericValue(baseline.valor)
  const currentValue = numericValue(latest.valor)
  const targetValue = Math.round(baselineValue * 1.6)
  const targetIncrease = targetValue - baselineValue
  const currentIncrease = currentValue - baselineValue
  const missingValue = Math.max(0, targetValue - currentValue)
  const progress = targetIncrease > 0
    ? clampPercent((currentIncrease / targetIncrease) * 100)
    : 0
  const isBaseline = latest.ano === BASELINE_YEAR
  const achieved = isBaseline ? null : currentValue >= targetValue
  const status = isBaseline ? 'baseline' : achieved ? 'achieved' : 'below'

  return {
    indicatorKey: SUBSEQUENT_EXPANSION_KEY,
    kind: 'subsequent-enrollment',
    baselineYear: BASELINE_YEAR,
    baselineValue,
    currentYear: latest.ano,
    currentValue,
    targetValue,
    targetPercent: 60,
    missingValue,
    progress,
    achieved,
    hasExpansion: currentIncrease > 0,
    loading: false,
    status,
    statusLabel: status === 'baseline'
      ? 'Linha de base definida'
      : status === 'achieved'
        ? 'Meta atingida no ciclo'
        : 'Em acompanhamento',
    tone: status === 'achieved' ? 'success' : status === 'below' ? 'warning' : 'muted',
    description: 'A meta do ciclo é ampliar em 60% as matrículas em cursos técnicos subsequentes, tomando 2025 como linha de base.',
    reading: isBaseline
      ? `Em 2025, o município registra ${formatCount(currentValue)} matrículas, que passam a ser a linha de base do novo ciclo. A meta de +60% corresponde a ${formatCount(targetValue)} matrículas.`
      : `Em ${latest.ano}, o município registra ${formatCount(currentValue)} matrículas. O progresso é acompanhado entre a base de ${formatCount(baselineValue)} e a meta de ${formatCount(targetValue)} matrículas.`,
  }
}

function buildLoadingModel(indicatorKey) {
  const isPublicShare = indicatorKey === PUBLIC_EXPANSION_KEY
  return {
    indicatorKey,
    kind: isPublicShare ? 'public-share' : 'subsequent-enrollment',
    baselineYear: BASELINE_YEAR,
    currentYear: BASELINE_YEAR,
    currentValue: null,
    targetValue: isPublicShare ? 50 : null,
    missingValue: null,
    progress: null,
    achieved: null,
    hasExpansion: false,
    loading: true,
    status: 'baseline',
    statusLabel: 'Linha de base definida',
    tone: 'muted',
    description: isPublicShare
      ? 'Pelo menos 50% das novas matrículas de EPT de nível médio criadas no ciclo 2026–2036 deverão ser públicas.'
      : 'A meta do ciclo é ampliar em 60% as matrículas em cursos técnicos subsequentes, tomando 2025 como linha de base.',
    reading: 'Carregando os dados da linha de base de 2025.',
  }
}

function buildComparablePublicEnrollmentSeries(details) {
  const componentRows = Array.isArray(details?.series_components)
    ? details.series_components.map((point) => ({
        ano: strictNumericValue(point?.ano),
        publicEnrollment: strictNumericValue(point?.numerador),
        totalEnrollment: strictNumericValue(point?.denominador),
      }))
    : []

  const dependencyRows = Array.isArray(details?.series_dependencia)
    ? details.series_dependencia.map((point) => {
        const federal = strictNumericValue(point?.federal)
        const estadual = strictNumericValue(point?.estadual)
        const municipal = strictNumericValue(point?.municipal)
        const privada = strictNumericValue(point?.privada)
        const components = [federal, estadual, municipal, privada]

        if (components.some((value) => value === null)) {
          return { ano: strictNumericValue(point?.ano), publicEnrollment: null, totalEnrollment: null }
        }

        const publicEnrollment = federal + estadual + municipal
        return {
          ano: strictNumericValue(point?.ano),
          publicEnrollment,
          totalEnrollment: publicEnrollment + privada,
        }
      })
    : []

  const sourceRows = componentRows.length > 0 ? componentRows : dependencyRows
  const byYear = new Map()

  for (const point of sourceRows) {
    if (
      !Number.isFinite(point.ano) ||
      !Number.isFinite(point.publicEnrollment) ||
      !Number.isFinite(point.totalEnrollment) ||
      point.publicEnrollment < 0 ||
      point.totalEnrollment < 0 ||
      point.publicEnrollment > point.totalEnrollment
    ) {
      continue
    }

    byYear.set(point.ano, point)
  }

  return Array.from(byYear.values()).sort((a, b) => a.ano - b.ano)
}

function buildUnavailableRecentPublicExpansion(unavailableReason, recentSeries = []) {
  const first = recentSeries[0] ?? null
  const last = recentSeries.at(-1) ?? null

  return {
    achieved: null,
    chartSeries: [],
    currentValue: null,
    endYear: last?.ano ?? null,
    excessValue: null,
    missingValue: null,
    publicExpansion: null,
    recentSeries,
    startYear: first?.ano ?? null,
    status: unavailableReason === 'loading' ? 'loading' : 'insufficient',
    statusLabel: unavailableReason === 'loading'
      ? 'Carregando recorte recente'
      : 'Sem expansão suficiente para calcular',
    targetValue: 50,
    tone: 'muted',
    totalExpansion: null,
    unavailableReason,
  }
}

function normalizeSeries(series) {
  if (!Array.isArray(series)) return []

  return series
    .filter((point) => Number.isFinite(Number(point?.ano)))
    .map((point) => ({ ...point, ano: Number(point.ano) }))
    .sort((a, b) => a.ano - b.ano)
}

function publicEnrollment(point) {
  return numericValue(point?.federal) + numericValue(point?.estadual) + numericValue(point?.municipal)
}

function numericValue(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

function strictNumericValue(value) {
  if (value === null || value === undefined || value === '') return null
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function takeRecentSeries(series, maxPoints = 5) {
  if (!Array.isArray(series)) return []

  return series
    .map((point) => ({
      ano: strictNumericValue(point?.ano),
      valor: strictNumericValue(point?.valor),
    }))
    .filter((point) => Number.isFinite(point.ano) && Number.isFinite(point.valor))
    .sort((a, b) => a.ano - b.ano)
    .slice(-maxPoints)
}

function formatReferenceDifference(currentValue, targetValue, unit) {
  const difference = Number(currentValue) - Number(targetValue)
  if (!Number.isFinite(difference)) return 'Não calculável'
  if (Math.abs(difference) < 1e-9) return 'No patamar da referência'

  const formatted = unit === 'count'
    ? `${formatCount(Math.abs(difference))} matrículas`
    : `${formatDecimal(Math.abs(difference))} p.p.`

  return difference < 0 ? `Faltam ${formatted}` : `Excede em ${formatted}`
}

function formatCountDifference(currentValue, targetValue) {
  const difference = Number(currentValue) - Number(targetValue)
  if (!Number.isFinite(difference)) return '—'
  if (Math.abs(difference) < 1e-9) return 'No patamar'
  return difference < 0
    ? `Faltam ${formatCount(Math.abs(difference))}`
    : `Excede em ${formatCount(difference)}`
}

function formatSignedPp(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '—'
  const normalized = Math.abs(numeric) < 1e-9 ? 0 : numeric
  const sign = normalized > 0 ? '+' : normalized < 0 ? '−' : ''
  return `${sign}${formatDecimal(Math.abs(normalized))} p.p.`
}

function formatDecimal(value) {
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, value))
}

function formatCount(value) {
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

function formatPercent(value) {
  return `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}
