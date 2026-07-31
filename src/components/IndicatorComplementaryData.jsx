import { useEffect, useId, useMemo, useRef, useState } from 'react'

import { loadIndicatorDetail, loadMunicipioSharedInfo } from '../data/staticData'
import { loadEducationMunicipio } from '../data/educationData'
import { isDemographicCensusIndicator } from '../utils/indicatorSeries'
import { AdministrativeDependencyChart } from './AdministrativeDependencyChart'
import { ComplementaryEnrollmentChart } from './ComplementaryEnrollmentChart'
import { PneSourceNotes } from './PneSourceNotes'
import { IndicatorProjectionPanel } from './IndicatorProjectionPanel'
import { IndexedEnrollmentComparison } from './ExpansionShareBaselineDetail'

const numberFormatter = new Intl.NumberFormat('pt-BR')
const percentFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
})

const EJA_PERCENTUAL_INDICATOR_KEY = 'eja_integrada_educacao_profissional_percentual'
const MEDIO_TECNICO_ARTICULADO_INDICATOR_KEY = 'medio_tecnico_articulado_percentual'
const ATTENDANCE_PROJECTION_METHODS = new Set([
  'last_observed_numerator_with_state_age_denominator',
  'municipal_state_shrunk_theil_sen_log_enrollment_with_state_age_denominator',
  'state_aggregate_damped_holt_enrollment_with_state_age_denominator',
])
const TABLE_ONLY_SUPPORT_INDICATORS = new Set(['alfabetizacao_pop_15_mais'])
const TECHNICAL_CALCULATION_LABEL = /\b(?:(?:[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9]*_)+[A-Za-zÀ-ÿ0-9]+|PC_[A-Z0-9_]+|TP_[A-Z0-9_]+|MEDU\d+)\b/u
const PNE_2014_TABLE_ONLY_SUPPORT_INDICATORS = new Set([
  'eja_integrada_educacao_profissional_percentual',
  'ensino_fundamental_ou_completo_pop_6_14',
  'ensino_medio_ou_basica_completa_pop_15_17',
])
const ADEQUATE_TEACHER_INDICATORS = {
  adequacao_ai: { label: 'Docentes com formação adequada nos anos iniciais', stageKey: 'fundamental', stageLabel: 'ensino fundamental' },
  adequacao_af: { label: 'Docentes com formação adequada nos anos finais', stageKey: 'fundamental', stageLabel: 'ensino fundamental' },
  adequacao_em: { label: 'Docentes com formação adequada no ensino médio', stageKey: 'medio', stageLabel: 'ensino médio' },
}
const TEACHER_COMPONENT_INDICATORS = {
  pos_graduacao: {
    denominatorDescription: 'Quantidade anual de docentes da educação básica considerada no cálculo do indicador.',
    denominatorLabel: 'Total de docentes',
    numeratorDescription: 'Quantidade anual de docentes da educação básica com especialização, mestrado ou doutorado.',
    numeratorLabel: 'Docentes com pós-graduação',
  },
  temporarios: {
    denominatorDescription: 'Quantidade anual de docentes da rede pública considerada no cálculo do indicador.',
    denominatorLabel: 'Total de docentes da rede pública',
    numeratorDescription: 'Quantidade anual de docentes da rede pública com contrato temporário.',
    numeratorLabel: 'Docentes com contrato temporário',
  },
}
const EJA_PERCENTUAL_NUMERATOR_LABEL =
  'Matrículas articuladas à\neducação profissional'
const EJA_PERCENTUAL_DENOMINATOR_LABEL =
  'Matrículas da EJA fundamental +\nmatrículas da EJA médio'
const EJA_AUXILIARY_HISTORY_LABEL = 'Matrículas da EJA articuladas à educação profissional'
const EJA_AUXILIARY_HISTORY_FORMATTER = (value) => {
  if (!Number.isFinite(value)) return '-'
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
}

export function IndicatorComplementaryData({
  allowProjection = true,
  cycle,
  domainOverride,
  indicatorKey,
  item,
  municipioData,
  presentationMode,
  result,
}) {
  const idMunicipio = municipioData?.id_municipio
  const fallbackDetails = municipioData?.indicator_details?.[indicatorKey] ?? null
  const [details, setDetails] = useState(null)
  const [sharedPrivadas, setSharedPrivadas] = useState(null)
  const [educationData, setEducationData] = useState(null)

  useEffect(() => {
    loadMunicipioSharedInfo(idMunicipio, 'privadas_conveniadas').then((data) => {
      setSharedPrivadas(data)
    })
  }, [idMunicipio])

  useEffect(() => {
    let isMounted = true

    if (!indicatorKey) {
      setDetails(null)
      return () => {
        isMounted = false
      }
    }

    if (!idMunicipio) {
      setDetails(fallbackDetails)
      return () => {
        isMounted = false
      }
    }

    loadIndicatorDetail(idMunicipio, indicatorKey)
      .then((data) => {
        if (isMounted) {
          setDetails(data)
        }
      })
      .catch(() => {
        if (isMounted) {
          setDetails(fallbackDetails)
        }
      })

    return () => {
      isMounted = false
    }
  }, [idMunicipio, indicatorKey, fallbackDetails])

  useEffect(() => {
    let isMounted = true

    if (!ADEQUATE_TEACHER_INDICATORS[indicatorKey] || !municipioData?.id_municipio) {
      setEducationData(null)
      return () => {
        isMounted = false
      }
    }

    loadEducationMunicipio(municipioData.id_municipio)
      .then((data) => {
        if (isMounted) setEducationData(data)
      })
      .catch(() => {
        if (isMounted) setEducationData(null)
      })

    return () => {
      isMounted = false
    }
  }, [indicatorKey, municipioData?.id_municipio])

  const cycleRange = useMemo(
    () => resolveCycleRange(cycle, result, details),
    [cycle, result, details],
  )
  const calculationComponents =
    details?.series_components_by_cycle?.[cycle] ?? details?.series_components
  const isCensusIndicator = useMemo(
    () => isDemographicCensusIndicator({ indicatorKey, item: null, details }),
    [indicatorKey, details],
  )
  const filteredTotal = useMemo(
    () => {
      if (isCensusIndicator) return filterRealRows(details?.series_total)
      return normalizeCycleSeries(filterRowsByCycle(details?.series_total, cycleRange), cycleRange)
    },
    [details?.series_total, cycleRange, isCensusIndicator],
  )
  const filteredDependencia = useMemo(
    () => {
      if (isCensusIndicator) return []
      return normalizeCycleSeries(filterRowsByCycle(details?.series_dependencia, cycleRange), cycleRange)
    },
    [details?.series_dependencia, cycleRange, isCensusIndicator],
  )
  const filteredComponents = useMemo(
    () => {
      const rows = isCensusIndicator
        ? filterRealRows(calculationComponents)
        : filterRowsByCycle(calculationComponents, cycleRange)
      return rows
        .slice()
        .sort((a, b) => Number(b?.ano) - Number(a?.ano))
    },
    [calculationComponents, cycleRange, isCensusIndicator],
  )
  const filteredAuxiliarySeries = useMemo(() => {
    const auxiliarySeries = details?.series_auxiliares ?? {}
    return Object.fromEntries(
      Object.entries(auxiliarySeries).map(([key, rows]) => [
        key,
        normalizeCycleSeries(filterRowsByCycle(rows, cycleRange), cycleRange),
      ]),
    )
  }, [details?.series_auxiliares, cycleRange])
  const totalPrivadaRede = useMemo(() => {
    if (!Array.isArray(filteredDependencia)) return null
    const withPrivada = filteredDependencia
      .filter((row) => Number.isFinite(Number(row?.privada)))
      .sort((a, b) => Number(b.ano) - Number(a.ano))
    return withPrivada.length > 0 ? Number(withPrivada[0].privada) : null
  }, [filteredDependencia])

  const hasTotal = isCensusIndicator
    ? countRowsWithValue(filteredTotal, 'valor') >= 2
    : filteredTotal.length > 0
  const isEjaPercentualIndicator = indicatorKey === EJA_PERCENTUAL_INDICATOR_KEY
  const isMedioTecnicoArticuladoIndicator = indicatorKey === MEDIO_TECNICO_ARTICULADO_INDICATOR_KEY
  const adequateTeacherConfig = ADEQUATE_TEACHER_INDICATORS[indicatorKey]
  const teacherComponentConfig = TEACHER_COMPONENT_INDICATORS[indicatorKey]
  const isExpansionShareBaseline = presentationMode === 'expansion-share-baseline'
  const isAbsoluteExpansionTarget = presentationMode === 'absolute-expansion-target'
  const expansionShareSeries = useMemo(
    () => buildExpansionShareSeries(calculationComponents).slice(-5),
    [calculationComponents],
  )
  const hasDependencia =
    !isEjaPercentualIndicator &&
    !isMedioTecnicoArticuladoIndicator &&
    filteredDependencia.some((row) => rowHasRealValue(row))
  const hasComponents = filteredComponents.length > 0
  const teacherStageTotalSeries = useMemo(() => {
    if (!adequateTeacherConfig) return []
    const rows = educationData?.blocos?.turmas_docentes?.series?.por_etapa?.[adequateTeacherConfig.stageKey]
    return filterRowsByCycle(rows, cycleRange)
      .map((row) => ({ ano: Number(row?.ano), valor: Number(row?.docentes) }))
      .filter((row) => Number.isFinite(row.ano) && Number.isFinite(row.valor))
  }, [adequateTeacherConfig, cycleRange, educationData])
  const adequateTeacherEstimateSeries = useMemo(
    () => buildEstimatedTeacherSeries(filteredTotal, teacherStageTotalSeries),
    [filteredTotal, teacherStageTotalSeries],
  )
  const hasTeacherNominalSeries = Boolean(
    (teacherComponentConfig && hasComponents) ||
    (adequateTeacherConfig && teacherStageTotalSeries.length > 0),
  )
  const numeratorLabel = getPublicCalculationLabel(
    details?.calculation?.numerator_label,
    'Numerador',
  )
  const denominatorLabel = getPublicCalculationLabel(
    details?.calculation?.denominator_label,
    'Denominador',
  )
  const historyLabel = resolveHistoryLabel({
    cycle,
    details,
    isAbsoluteExpansionTarget,
    isCensusIndicator,
    isEjaPercentualIndicator,
    isExpansionShareBaseline,
    item,
  })

  const projection = municipioData?.[cycle]?.projecoes?.[indicatorKey]
  const hasProjection =
    allowProjection &&
    cycle === 'pne_2026_2036' &&
    !isExpansionShareBaseline &&
    !isAbsoluteExpansionTarget &&
    projection?.available === true &&
    ATTENDANCE_PROJECTION_METHODS.has(projection?.method)

  const options = useMemo(() => {
    const availableOptions = []

    if (details) {
      if (teacherComponentConfig && hasComponents) {
        const teacherSeries = [
          {
            description: teacherComponentConfig.numeratorDescription,
            key: 'teacher-numerator-history',
            label: teacherComponentConfig.numeratorLabel,
            valueKey: 'numerador',
          },
          {
            description: teacherComponentConfig.denominatorDescription,
            key: 'teacher-total-history',
            label: teacherComponentConfig.denominatorLabel,
            valueKey: 'denominador',
          },
        ]

        teacherSeries.forEach(({ description, key, label, valueKey }) => {
          availableOptions.push({
            key,
            label,
            description,
            content: (
              <ComplementaryEnrollmentChart
                showHeading={false}
                series={buildComponentValueSeries(filteredComponents, valueKey)}
                title={label}
                unit="Docentes"
              />
            ),
          })
        })
      }

      if (adequateTeacherConfig && teacherStageTotalSeries.length > 0) {
        const usesWholeFundamentalStage = adequateTeacherConfig.stageKey === 'fundamental'
        const estimateDescription = usesWholeFundamentalStage
          ? 'Estimativa calculada pela taxa oficial do indicador sobre o total de docentes do ensino fundamental, pois a série nominal disponível não separa anos iniciais e finais.'
          : `Estimativa calculada pela taxa oficial do indicador sobre o total de docentes do ${adequateTeacherConfig.stageLabel}.`

        availableOptions.push({
          key: 'teacher-numerator-history',
          label: `Estimativa de ${adequateTeacherConfig.label.toLowerCase()}`,
          description: estimateDescription,
          content: (
            <ComplementaryEnrollmentChart
              showHeading={false}
              series={adequateTeacherEstimateSeries}
              title={adequateTeacherConfig.label}
              unit="Docentes"
            />
          ),
        })
        availableOptions.push({
          key: 'teacher-total-history',
          label: `Total de docentes no ${adequateTeacherConfig.stageLabel}`,
          description: `Quantidade anual de docentes do ${adequateTeacherConfig.stageLabel} registrada no Censo Escolar.`,
          content: (
            <ComplementaryEnrollmentChart
              showHeading={false}
              series={teacherStageTotalSeries}
              title={`Total de docentes no ${adequateTeacherConfig.stageLabel}`}
              unit="Docentes"
            />
          ),
        })
      }

      if (isMedioTecnicoArticuladoIndicator) {
        const supportingSeries = [
          ['integrado', 'Matrículas integradas'],
          ['concomitante', 'Matrículas concomitantes'],
          ['articulado', 'Matrículas articuladas'],
        ]
        supportingSeries.forEach(([key, label]) => {
          const series = filteredAuxiliarySeries[key] ?? []
          if (series.length === 0) return
          availableOptions.push({
            key: `supporting-${key}`,
            label,
            description: key === 'articulado'
              ? 'Soma das matrículas integradas e concomitantes usada no numerador do indicador.'
              : 'Evolução anual desta modalidade no aprofundamento do indicador.',
            content: (
              <ComplementaryEnrollmentChart
                showHeading={false}
                series={series}
                title={label}
                unit="Matrículas"
                valueMode="count"
                valueFormatter={EJA_AUXILIARY_HISTORY_FORMATTER}
              />
            ),
          })
        })
      }

      if (
        !isMedioTecnicoArticuladoIndicator &&
        !hasTeacherNominalSeries &&
        !TABLE_ONLY_SUPPORT_INDICATORS.has(indicatorKey) &&
        !(cycle === 'pne_2014_2024' && PNE_2014_TABLE_ONLY_SUPPORT_INDICATORS.has(indicatorKey)) &&
        hasTotal
      ) {
        const isCountHistory = isEjaPercentualIndicator || isMedioTecnicoArticuladoIndicator
        availableOptions.push({
          key: 'enrollment-history',
          label: historyLabel,
          description: isExpansionShareBaseline
            ? `Primeiro ano = 100. As duas linhas mostram trajetórias independentes, sem comparar volumes absolutos.`
            : isAbsoluteExpansionTarget
              ? 'Contexto anterior e recente para leitura do indicador. Não representa diretamente o avanço da meta de 2036.'
              : 'Evolu\u00e7\u00e3o anual da s\u00e9rie complementar usada para contextualizar o indicador.',
          content: (
            isExpansionShareBaseline ? (
              <IndexedEnrollmentComparison series={expansionShareSeries} />
            ) : (
              <ComplementaryEnrollmentChart
                showHeading={false}
                series={filteredTotal}
                title={isEjaPercentualIndicator
                  ? EJA_AUXILIARY_HISTORY_LABEL
                  : details.title || 'Matrículas em creche'}
                unit={isCountHistory ? 'Matrículas' : details.unit || 'Matrículas'}
                valueMode={isCountHistory ? 'count' : undefined}
                valueFormatter={isCountHistory ? EJA_AUXILIARY_HISTORY_FORMATTER : undefined}
              />
            )
          ),
        })
      }

      if (hasDependencia) {
        availableOptions.push({
          key: 'administrative-dependency',
          label: 'Dependência administrativa',
          description: 'Distribui\u00e7\u00e3o por rede ou depend\u00eancia administrativa ao longo do ciclo.',
          content: (
            <AdministrativeDependencyChart
              showHeading={false}
              series={filteredDependencia}
              unit={details.dependency_unit || details.unit}
              valueType={details.dependency_value_type}
              title="Por dependência administrativa"
            />
          ),
        })
      }

      if (hasComponents) {
        availableOptions.push({
          key: 'calculation-numbers',
          label: 'Dados usados no cálculo',
          description: 'Numerador, denominador e percentual que comp\u00f5em o indicador selecionado.',
          content: (
            <CalculationComponentsTable
              centerColumns={cycle === 'pne_2014_2024' && isEjaPercentualIndicator}
              denominatorLabel={isEjaPercentualIndicator ? EJA_PERCENTUAL_DENOMINATOR_LABEL : denominatorLabel}
              numeratorLabel={isEjaPercentualIndicator ? EJA_PERCENTUAL_NUMERATOR_LABEL : numeratorLabel}
              rows={filteredComponents}
              showArticulatedBreakdown={isMedioTecnicoArticuladoIndicator}
              wrapHeaders={isEjaPercentualIndicator}
              showHeading={false}
            />
          ),
        })
      }

      if (isAbsoluteExpansionTarget && filteredTotal.length > 0 && !hasComponents) {
        availableOptions.push({
          key: 'calculation-numbers',
          label: 'Série histórica usada no cálculo',
          description: 'Valores considerados para definir o ponto de partida de 2025.',
          content: (
            <AbsoluteExpansionCalculationTable rows={filteredTotal} />
          ),
        })
      }
    }

    if (hasProjection) {
      availableOptions.push({
        key: 'trend-projection',
        label: 'Projeção do indicador',
        description: 'Cen\u00e1rio estimativo para planejamento, sem car\u00e1ter de previs\u00e3o oficial.',
        badge: 'Estimativa',
        content: (
          <IndicatorProjectionPanel
            chartHeight={320}
            chartWidth={860}
            domainOverride={domainOverride}
            pneLayout
            projection={projection}
            showTitle={false}
          />
        ),
      })
    }

    return availableOptions
  }, [
    cycle,
    denominatorLabel,
    details,
    domainOverride,
    filteredComponents,
    filteredDependencia,
    filteredAuxiliarySeries,
    filteredTotal,
    hasComponents,
    hasDependencia,
    hasTeacherNominalSeries,
    hasTotal,
    historyLabel,
    indicatorKey,
    isEjaPercentualIndicator,
    isExpansionShareBaseline,
    isAbsoluteExpansionTarget,
    isMedioTecnicoArticuladoIndicator,
    adequateTeacherConfig,
    adequateTeacherEstimateSeries,
    expansionShareSeries,
    numeratorLabel,
    hasProjection,
    projection,
    teacherComponentConfig,
    teacherStageTotalSeries,
  ])

  if (options.length === 0) {
    return null
  }

  if (cycle !== 'pne_2014_2024' && cycle !== 'pne_2026_2036') {
    return (
      <LegacyComplementaryData
        cycle={cycle}
        details={details}
        hasDependencia={hasDependencia}
        indicatorKey={indicatorKey}
        numberFormatter={numberFormatter}
        options={options}
        result={result}
        sharedPrivadas={sharedPrivadas}
        totalPrivadaRede={totalPrivadaRede}
      />
    )
  }

  const contentId = `indicator-support-data-${indicatorKey || 'detail'}`
  const calculationOptions = options.filter((option) => option.key === 'calculation-numbers')
  const projectionOptions = options.filter((option) => option.key === 'trend-projection')
  const supportOptions = options.filter((option) => (
    option.key !== 'calculation-numbers' && option.key !== 'trend-projection'
  ))

  return (
    <section className="complementary-data complementary-data--organized" aria-labelledby={`${contentId}-title`}>
      <header className="complementary-data__trigger">
        <SupportDataIcon />
        <span className="complementary-data__summary">
          <span className="complementary-data__eyebrow">{isExpansionShareBaseline ? 'Contexto complementar' : 'Aprofundamento'}</span>
          <h3 className="complementary-data__title" id={`${contentId}-title`}>{isExpansionShareBaseline ? 'Dados de apoio' : 'Dados de apoio da meta'}</h3>
          <span className="complementary-data__description">
            {isExpansionShareBaseline
              ? 'Evolução relativa e composição por rede para complementar a leitura principal.'
              : isAbsoluteExpansionTarget
                ? 'Histórico, composição por rede e valores usados para calcular a meta absoluta.'
              : 'Séries auxiliares, recortes e memória de cálculo para interpretar este indicador com mais contexto.'}
          </span>
        </span>
      </header>

      <div className="complementary-data__body" id={contentId}>
        <div className="complementary-data__grid">
          {supportOptions.map((option) => (
            <ComplementaryDataItem
              cycle={cycle}
              details={details}
              indicatorKey={indicatorKey}
              key={option.key}
              option={option}
              result={result}
            />
          ))}
          {hasDependencia && !isExpansionShareBaseline ? (
            <PrivadasConveniadasSection
              data={sharedPrivadas}
              numberFormatter={numberFormatter}
              indicatorKey={indicatorKey}
              totalPrivadaRede={totalPrivadaRede}
            />
          ) : null}
          {projectionOptions.map((option) => (
            <ComplementaryDataItem
              cycle={cycle}
              details={details}
              indicatorKey={indicatorKey}
              key={option.key}
              option={option}
              result={result}
              wide
            />
          ))}
          {calculationOptions.map((option) => (
            <ComplementaryDataItem
              cycle={cycle}
              details={details}
              fullRow={projectionOptions.length === 0}
              indicatorKey={indicatorKey}
              key={option.key}
              option={option}
              result={result}
              wide
            />
          ))}
        </div>
      </div>
    </section>
  )
}

function getPublicCalculationLabel(value, fallback) {
  if (typeof value !== 'string' || !value.trim()) return fallback
  return TECHNICAL_CALCULATION_LABEL.test(value) ? fallback : value.trim()
}

function resolveHistoryLabel({
  cycle,
  details,
  isAbsoluteExpansionTarget,
  isCensusIndicator,
  isEjaPercentualIndicator,
  isExpansionShareBaseline,
  item,
}) {
  if (cycle !== 'pne_2014_2024' && cycle !== 'pne_2026_2036') {
    return isCensusIndicator ? 'Histórico' : 'Histórico de matrículas'
  }
  if (isExpansionShareBaseline) return 'Evolução relativa das matrículas'
  if (isEjaPercentualIndicator) return EJA_AUXILIARY_HISTORY_LABEL
  if (isAbsoluteExpansionTarget) return 'Matrículas em cursos técnicos subsequentes'

  const unit = String(details?.unit ?? '').trim().toLocaleLowerCase('pt-BR')
  const isIndicatorRate = unit === '%' || unit.includes('percent') || unit.includes('razão')

  if (isIndicatorRate && item?.label) return item.label
  return details?.title || item?.label || 'Histórico do indicador'
}

function AbsoluteExpansionCalculationTable({ rows }) {
  const orderedRows = rows
    .filter((row) => Number.isFinite(Number(row?.ano)) && Number.isFinite(Number(row?.valor)))
    .slice()
    .sort((a, b) => Number(b.ano) - Number(a.ano))
  const chronologicalRows = orderedRows.slice().reverse()
  const firstRow = chronologicalRows[0]
  const baselineRow = orderedRows.find((row) => Number(row.ano) === 2025) ?? orderedRows[0]
  const maximumRow = orderedRows.reduce((maximum, row) => (
    Number(row.valor) > Number(maximum?.valor ?? Number.NEGATIVE_INFINITY) ? row : maximum
  ), null)
  const minimumRow = orderedRows.reduce((minimum, row) => (
    Number(row.valor) < Number(minimum?.valor ?? Number.POSITIVE_INFINITY) ? row : minimum
  ), null)
  const milestones = [
    { label: 'Início da série', row: firstRow },
    { label: 'Maior valor', row: maximumRow },
    { label: 'Menor valor', row: minimumRow },
    { label: 'Ponto de partida', row: baselineRow },
  ]

  return (
    <div className="absolute-expansion-calculation">
      <div className="absolute-expansion-calculation__layout">
        <div
          aria-label="Série histórica de matrículas usada no cálculo"
          className="complementary-components__table-wrap absolute-expansion-calculation__table-wrap"
          role="region"
          tabIndex="0"
        >
          <table className="complementary-components__table absolute-expansion-calculation__table">
            <caption className="u-sr-only">Série histórica usada no cálculo</caption>
            <thead>
              <tr>
                <th scope="col">Ano</th>
                <th scope="col">Matrículas</th>
              </tr>
            </thead>
            <tbody>
              {orderedRows.map((row) => (
                <tr key={row.ano}>
                  <td>{row.ano}</td>
                  <td>{numberFormatter.format(Number(row.valor))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <aside className="absolute-expansion-calculation__milestones" aria-label="Marcos da série">
          <h5>Marcos da série</h5>
          <dl>
            {milestones.map(({ label, row }) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>
                  <strong>{row?.ano}</strong>
                  <span>{numberFormatter.format(Number(row?.valor))} matrículas</span>
                </dd>
              </div>
            ))}
          </dl>
          <div className="absolute-expansion-calculation__formula">
            <span>Fórmula da meta</span>
            <strong>Meta 2036 = matrículas registradas em 2025 × 1,60</strong>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SupportDataIcon() {
  return (
    <svg aria-hidden="true" className="complementary-data__trigger-icon" fill="none" viewBox="0 0 24 24">
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <rect height="5" rx="1" width="3" x="7" y="12" />
      <rect height="9" rx="1" width="3" x="12" y="8" />
      <rect height="12" rx="1" width="3" x="17" y="5" />
    </svg>
  )
}

function ComplementaryDataItem({ fullRow = false, indicatorKey, option, wide = false }) {
  const headingId = `indicator-support-${indicatorKey || 'detail'}-${option.key}`

  return (
    <section
      className={`complementary-data__item complementary-data__item--${option.key}${wide ? ' complementary-data__item--wide' : ''}${fullRow ? ' complementary-data__item--full-row' : ''}`}
      aria-labelledby={headingId}
    >
      <div className="complementary-data__panel-heading">
        <div>
          <h4 id={headingId}>{option.label}</h4>
          {option.description ? <p>{option.description}</p> : null}
        </div>
        {option.badge ? (
          <span className="complementary-data__tab-badge">{option.badge}</span>
        ) : null}
      </div>
      <div className="complementary-data__item-content">{option.content}</div>
    </section>
  )
}

function LegacyComplementaryData({
  cycle,
  details,
  hasDependencia,
  indicatorKey,
  numberFormatter,
  options,
  result,
  sharedPrivadas,
  totalPrivadaRede,
}) {
  const [activeTab, setActiveTab] = useState(options[0]?.key ?? '')
  const tabSetId = useId().replace(/:/g, '')
  const tabRefs = useRef([])
  const activeOption = options.find((option) => option.key === activeTab) ?? options[0]
  const contentId = `indicator-explore-more-${indicatorKey || 'detail'}`
  const panelId = `complementary-panel-${tabSetId}`

  useEffect(() => {
    setActiveTab(options[0]?.key ?? '')
  }, [indicatorKey, options])

  function selectTab(index) {
    const option = options[index]
    if (!option) return
    setActiveTab(option.key)
    tabRefs.current[index]?.focus()
  }

  function handleTabKeyDown(event, index) {
    let nextIndex = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % options.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + options.length) % options.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = options.length - 1
    if (nextIndex === null) return
    event.preventDefault()
    selectTab(nextIndex)
  }

  return (
    <section className="complementary-data is-open" aria-label="Dados de apoio da meta">
      <div className="complementary-data__trigger">
        <SupportDataIcon />
        <span className="complementary-data__summary">
          <span className="complementary-data__eyebrow">Aprofundamento</span>
          <span className="complementary-data__title">Dados de apoio da meta</span>
          <span className="complementary-data__description">
            Séries auxiliares, recortes e memória de cálculo para interpretar este indicador com mais contexto.
          </span>
        </span>
      </div>

      <div className="complementary-data__body" id={contentId}>
        {options.length > 1 ? (
          <div className="complementary-data__tabs platform-tab-list" role="tablist" aria-label="Opções de exploração">
            {options.map((option, index) => (
              <button
                ref={(element) => { tabRefs.current[index] = element }}
                type="button"
                className={`complementary-data__tab platform-tab${activeOption?.key === option.key ? ' is-active' : ''}`}
                key={option.key}
                id={`complementary-tab-${tabSetId}-${option.key}`}
                role="tab"
                aria-selected={activeOption?.key === option.key}
                aria-controls={panelId}
                tabIndex={activeOption?.key === option.key ? 0 : -1}
                onClick={() => setActiveTab(option.key)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
              >
                <span>{option.label}</span>
                {option.badge ? (
                  <span className="complementary-data__tab-badge">{option.badge}</span>
                ) : null}
              </button>
            ))}
          </div>
        ) : null}
        <div
          className="complementary-data__panel"
          id={panelId}
          role="tabpanel"
          aria-labelledby={`complementary-tab-${tabSetId}-${activeOption.key}`}
        >
          <div className="complementary-data__panel-heading">
            <h5>{activeOption?.label}</h5>
            {activeOption?.description ? <p>{activeOption.description}</p> : null}
          </div>
          {activeOption?.content}
          <PneSourceNotes
            context={{
              block: 'pne',
              cycle,
              detailType: activeOption?.key,
              details,
              indicatorKey,
              result,
              title: activeOption?.label,
            }}
          />
        </div>
        {hasDependencia ? (
          <PrivadasConveniadasSection
            activeTab={activeTab}
            data={sharedPrivadas}
            indicatorKey={indicatorKey}
            numberFormatter={numberFormatter}
            totalPrivadaRede={totalPrivadaRede}
          />
        ) : null}
      </div>
    </section>
  )
}

const INDICATOR_TO_SECAO = {
  creche: 'creche',
  pre_escola: 'pre_escola',
  ensino_fundamental_ou_completo_pop_6_14: 'ensino_fundamental',
  fundamental_concluido_18_mais: 'ensino_fundamental',
  fundamental_concluido_15_29: 'ensino_fundamental',
  fundamental_concluido_15_mais: 'ensino_fundamental',
  idade_regular_quinto: 'anos_iniciais',
  idade_regular_nono: 'anos_finais',
  basico_15_17: 'ensino_medio',
  ensino_medio_ou_basica_completa_pop_15_17: 'ensino_medio',
  idade_regular_medio: 'ensino_medio',
  medio_concluido_18_mais: 'ensino_medio',
  medio_concluido_18_29: 'ensino_medio',
  medio_tecnico: 'educacao_profissional',
  medio_tecnico_articulado_percentual: 'educacao_profissional',
  medio_tecnico_total: 'educacao_profissional',
  medio_tecnico_participacao_publica: 'educacao_profissional',
  subsequente_expansao: 'educacao_profissional',
  eja_integrada_educacao_profissional: 'eja',
  eja_integrada_educacao_profissional_percentual: 'eja',
  aee: 'educacao_especial',
}

const SECAO_LABELS = {
  educacao_basica: 'Educação básica',
  educacao_infantil: 'Educação infantil',
  creche: 'Creche',
  pre_escola: 'Pré-escola',
  ensino_fundamental: 'Ensino fundamental',
  anos_iniciais: 'Anos iniciais',
  anos_finais: 'Anos finais',
  ensino_medio: 'Ensino médio',
  educacao_profissional: 'Educação profissional',
  eja: 'EJA',
  educacao_especial: 'Educação especial',
}

const SECAO_LABELS_LC = {
  educacao_basica: 'educação básica',
  educacao_infantil: 'educação infantil',
  creche: 'creche',
  pre_escola: 'pré-escola',
  ensino_fundamental: 'ensino fundamental',
  anos_iniciais: 'anos iniciais',
  anos_finais: 'anos finais',
  ensino_medio: 'ensino médio',
  educacao_profissional: 'educação profissional',
  eja: 'EJA',
  educacao_especial: 'educação especial',
}

function resolveSecaoFromIndicator(indicatorKey) {
  return INDICATOR_TO_SECAO[indicatorKey] ?? null
}

function findSecaoEntry(porSecao, secao) {
  if (!Array.isArray(porSecao)) return null
  return porSecao.find((entry) => entry.secao === secao) ?? null
}

function PrivadasConveniadasSection({ data, numberFormatter, indicatorKey, activeTab, totalPrivadaRede }) {
  if (!data) return null
  if (activeTab && activeTab !== 'administrative-dependency') return null

  const secao = resolveSecaoFromIndicator(indicatorKey)
  if (!secao) return null

  const entry = findSecaoEntry(data.por_secao, secao)
  if (!entry) return null

  const values = entry
  const rotuloRecorte = SECAO_LABELS[secao] ?? secao
  const rotuloRecorteLc = SECAO_LABELS_LC[secao] ?? secao

  const calcPercent = (numerador, denominador) => {
    if (numerador == null || denominador == null || typeof denominador !== 'number' || denominador <= 0) return null
    if (!Number.isFinite(numerador) || !Number.isFinite(denominador)) return null
    return (numerador / denominador) * 100
  }

  const pctMunicipalTotal = calcPercent(values.municipal_total, totalPrivadaRede)

  const formatValue = (val) => {
    if (val == null || (typeof val === 'number' && !Number.isFinite(val))) return '—'
    return numberFormatter.format(val)
  }

  const formatPercent = (val) => {
    if (val == null || !Number.isFinite(val)) return null
    return `${val.toLocaleString('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 })}% da rede privada`
  }

  const primaryHelper =
    totalPrivadaRede != null && Number.isFinite(totalPrivadaRede) && totalPrivadaRede > 0
      ? `${formatValue(values.municipal_total)} de ${formatValue(totalPrivadaRede)} matrículas privadas em ${rotuloRecorteLc}.`
      : null

  const pctLabel = pctMunicipalTotal != null ? formatPercent(pctMunicipalTotal) : null
  const barPct = pctMunicipalTotal != null ? Math.min(pctMunicipalTotal, 100) : 0
  const showBar = pctMunicipalTotal != null

  return (
    <section className="privadas-conveniadas complementary-data__item complementary-data__item--private-network">
      <div className="privadas-conveniadas__header">
        <h5 className="privadas-conveniadas__title">
          Rede privada conveniada sob responsabilidade municipal
        </h5>
        {rotuloRecorte ? (
          <span className="privadas-conveniadas__chip">{rotuloRecorte}</span>
        ) : null}
      </div>
      <p className="privadas-conveniadas__desc">
        Matrículas da rede privada conveniada cujo convênio é de responsabilidade do
        município, isoladamente ou em conjunto com o Estado.
      </p>
      <div className="privadas-conveniadas__body">
        <div className="privadas-conveniadas__primary">
          <div className="privadas-conveniadas__primary-inner">
            <span className="privadas-conveniadas__primary-label">
              Total com participação municipal
            </span>
            <strong className="privadas-conveniadas__primary-value">
              {formatValue(values.municipal_total)}
            </strong>
            {pctLabel ? (
              <span className="privadas-conveniadas__primary-pct">{pctLabel}</span>
            ) : null}
            {primaryHelper ? (
              <span className="privadas-conveniadas__primary-helper">{primaryHelper}</span>
            ) : null}
            {showBar ? (
              <div className="privadas-conveniadas__bar">
                <div
                  className="privadas-conveniadas__bar-fill"
                  style={{ width: `${barPct}%` }}
                />
              </div>
            ) : null}
          </div>
        </div>
        <div className="privadas-conveniadas__secondary">
          <div className="privadas-conveniadas__sec-card">
            <span className="privadas-conveniadas__sec-label">Total conveniado</span>
            <strong className="privadas-conveniadas__sec-value">
              {formatValue(values.total_conveniado)}
            </strong>
          </div>
          <div className="privadas-conveniadas__sec-card">
            <span className="privadas-conveniadas__sec-label">Município</span>
            <strong className="privadas-conveniadas__sec-value">
              {formatValue(values.municipio)}
            </strong>
          </div>
          <div className="privadas-conveniadas__sec-card">
            <span className="privadas-conveniadas__sec-label">Estado e Município</span>
            <strong className="privadas-conveniadas__sec-value">
              {formatValue(values.estado_municipio)}
            </strong>
          </div>
        </div>
      </div>
      <p className="privadas-conveniadas__fonte">
        Dado disponível a partir de {data.disponivel_desde} na Sinopse Estatística do
        Censo Escolar.
      </p>
    </section>
  )
}

export function CalculationComponentsTable({
  centerColumns = false,
  denominatorLabel,
  numeratorLabel,
  rows,
  singleYearLayout = false,
  showHeading = true,
  showArticulatedBreakdown = false,
  summary = null,
  wrapHeaders = false,
}) {
  const tableClassName = [
    'complementary-components__table',
    centerColumns ? 'complementary-components__table--centered' : null,
    wrapHeaders ? 'complementary-components__table--eja' : null,
    showArticulatedBreakdown ? 'complementary-components__table--articulated' : null,
    !wrapHeaders && !showArticulatedBreakdown ? 'complementary-components__table--fit' : null,
    singleYearLayout ? 'complementary-components__table--single-year' : null,
    singleYearLayout ? 'single-year-indicator-table' : null,
  ].filter(Boolean).join(' ')
  const renderHeader = (label) => (
    wrapHeaders ? <span className="complementary-components__table-header">{label}</span> : label
  )

  return (
    <div className="complementary-components">
      {showHeading ? <h5>Dados usados no cálculo</h5> : null}
      {summary ? (
        <div className="expansion-share-calculation-summary" aria-label="Resumo do cálculo do período de referência">
          <span><small>Variação pública</small><strong>{summary.publicExpansion}</strong></span>
          <span><small>Variação total</small><strong>{summary.totalExpansion}</strong></span>
          <span><small>Participação calculada</small><strong>{summary.share}</strong></span>
          <p>Participação pública na expansão = variação das matrículas públicas ÷ variação total das matrículas × 100.</p>
        </div>
      ) : null}
      <div
        className={`complementary-components__table-wrap${singleYearLayout ? ' complementary-components__table-wrap--single-year' : ''}`}
        role={singleYearLayout ? undefined : 'region'}
        aria-label={singleYearLayout
          ? undefined
          : 'Dados usados no cálculo do indicador. Role horizontalmente para consultar todas as colunas quando necessário.'}
        tabIndex={singleYearLayout ? undefined : 0}
      >
        <table className={tableClassName}>
          <caption className="u-sr-only">Dados usados no cálculo do indicador</caption>
          <thead>
            <tr>
              <th scope="col">Ano</th>
              {showArticulatedBreakdown ? (
                <>
                  <th scope="col">Matrículas integradas</th>
                  <th scope="col">Matrículas concomitantes</th>
                </>
              ) : null}
              <th scope="col">{renderHeader(
                showArticulatedBreakdown
                  ? 'Matrículas articuladas (integrada + concomitante)'
                  : numeratorLabel,
              )}</th>
              <th scope="col">{renderHeader(
                showArticulatedBreakdown ? 'Total do ensino médio' : denominatorLabel,
              )}</th>
              <th scope="col">{renderHeader(
                showArticulatedBreakdown
                  ? 'Percentual integrado (componente)'
                  : 'Percentual',
              )}</th>
              {showArticulatedBreakdown ? (
                <th scope="col">{renderHeader('Percentual integrado ou concomitante')}</th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.ano}>
                <td>{row.ano}</td>
                {showArticulatedBreakdown ? (
                  <>
                    <td>{numberFormatter.format(row.integrado)}</td>
                    <td>{numberFormatter.format(row.concomitante)}</td>
                  </>
                ) : null}
                <td>{numberFormatter.format(
                  showArticulatedBreakdown ? row.articulado : row.numerador,
                )}</td>
                <td>{numberFormatter.format(row.denominador)}</td>
                <td>{percentFormatter.format(row.percentual)}%</td>
                {showArticulatedBreakdown ? (
                  <td>{percentFormatter.format(row.percentual_articulado)}%</td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function buildExpansionShareSeries(rows) {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => ({
      ano: Number(row?.ano),
      publicEnrollment: Number(row?.numerador),
      totalEnrollment: Number(row?.denominador),
    }))
    .filter((row) => Number.isFinite(row.ano) && Number.isFinite(row.publicEnrollment) && Number.isFinite(row.totalEnrollment))
    .sort((a, b) => a.ano - b.ano)
}

function buildComponentValueSeries(rows, valueKey) {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => ({
      ano: Number(row?.ano),
      valor: Number(row?.[valueKey]),
    }))
    .filter((row) => Number.isFinite(row.ano) && Number.isFinite(row.valor))
}

function buildEstimatedTeacherSeries(percentSeries, totalSeries) {
  const totalsByYear = new Map(totalSeries.map((row) => [Number(row?.ano), Number(row?.valor)]))
  return percentSeries
    .map((row) => {
      const ano = Number(row?.ano)
      const percentual = Number(row?.valor)
      const total = totalsByYear.get(ano)
      return {
        ano,
        valor: Number.isFinite(percentual) && Number.isFinite(total)
          ? Math.round((percentual / 100) * total)
          : null,
      }
    })
    .filter((row) => Number.isFinite(row.ano) && Number.isFinite(row.valor))
}

function filterRowsByCycle(rows, range) {
  if (!Array.isArray(rows)) return []
  return rows.filter((row) => {
    const year = Number(row?.ano)
    if (!Number.isFinite(year)) return false
    if (Number.isFinite(range?.min) && year < range.min) return false
    if (Number.isFinite(range?.max) && year > range.max) return false
    return true
  })
}

function filterRealRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows.filter((row) => Number.isFinite(Number(row?.ano)) && rowHasRealValue(row))
}

function rowHasRealValue(row) {
  if (!row) return false
  return Object.entries(row).some(([key, value]) => {
    if (key === 'ano') return false
    if (value === null || value === undefined || value === '') return false
    const numeric = Number(value)
    return Number.isFinite(numeric)
  })
}

function countRowsWithValue(rows, key) {
  if (!Array.isArray(rows)) return 0
  return rows.filter((row) => Number.isFinite(Number(row?.[key]))).length
}

function resolveCycleRange(cycle, result, details) {
  const resultYears = collectYears(result?.series)
  const detailYears = [
    ...collectYears(details?.series_total),
    ...collectYears(details?.series_dependencia),
    ...collectYears(details?.series_components_by_cycle?.[cycle] ?? details?.series_components),
    ...Object.values(details?.series_auxiliares ?? {}).flatMap((rows) => collectYears(rows)),
  ]

  if (cycle === 'pne_2014_2024') {
    return {
      min: 2014,
      max: 2024,
    }
  }

  if (cycle === 'pne_2026_2036') {
    const availableYears = resultYears.length ? resultYears : detailYears
    return {
      min: availableYears.length ? Math.min(...availableYears) : 2026,
      max: availableYears.length ? Math.min(Math.max(...availableYears), 2036) : 2036,
    }
  }

  const fallbackYears = resultYears.length ? resultYears : detailYears
  return fallbackYears.length
    ? { min: Math.min(...fallbackYears), max: Math.max(...fallbackYears) }
    : { min: Number.NaN, max: Number.NaN }
}

function collectYears(rows) {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => Number(row?.ano))
    .filter((year) => Number.isFinite(year))
}

function normalizeCycleSeries(rows, range) {
  if (!Array.isArray(rows) || !Number.isFinite(range?.min) || !Number.isFinite(range?.max)) {
    return rows ?? []
  }
  const existing = new Map()
  for (const row of rows) {
    const year = Number(row?.ano)
    if (Number.isFinite(year)) {
      existing.set(year, row)
    }
  }
  const hasDependencyFields = rows.some(
    (r) => r && ('federal' in r || 'estadual' in r || 'municipal' in r || 'privada' in r)
  )
  const result = []
  for (let year = range.min; year <= range.max; year++) {
    const row = existing.get(year)
    if (row) {
      result.push(row)
    } else if (hasDependencyFields) {
      result.push({ ano: year, federal: null, estadual: null, municipal: null, privada: null })
    } else {
      result.push({ ano: year, valor: null })
    }
  }
  return result
}
