import { useEffect, useState } from 'react'
import { DisclosureChevron } from '../../../components/DisclosureChevron.jsx'
import { EducationLineChart } from '../../../components/EducationLineChart.jsx'
import { EducationQuickReading } from '../../../components/EducationQuickReading'
import { EducationTable } from '../../../components/EducationTable.jsx'
import { IndicatorChartHeader } from '../../../components/IndicatorChartHeader.jsx'
import { MetricCard } from '../../../components/MetricCard.jsx'
import {
  SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER,
} from '../../../data/educationIndicatorCatalog.js'
import {
  formatSchoolInfrastructurePercentage,
  formatSchoolInfrastructureQuantity,
  SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION,
  SCHOOL_INFRASTRUCTURE_CUT_LABELS,
  SCHOOL_INFRASTRUCTURE_CUT_ORDER,
  SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER,
  SCHOOL_INFRASTRUCTURE_METHODOLOGY,
  SCHOOL_INFRASTRUCTURE_PUBLIC_COPY,
  SCHOOL_INFRASTRUCTURE_SOURCE,
  selectSchoolInfrastructureResult,
} from '../../../data/schoolInfrastructureContract'
import {
  formatPercent,
  isMissing,
} from '../../../utils/educationFormatters.js'
import { INFRA_METRIC_LABELS } from '../educationViewModels'
import {
  EducationMetricSummary,
} from './EducationIndicatorDetailShell'
import { EducationIndicatorQuickReading } from './EducationIndicatorQuickReading'
import { IndicatorSegmentedControl } from './EducationIndicatorSegmentedControl'
import {
  EducationSourceNotes,
  dataSourceContextForEducation,
} from './EducationSourceNotes'

const EM = '\u2014'

const INFRA_EVOLUTION_KEYS = [
  'salas_climatizadas', 'salas_acessiveis',
  'internet', 'internet_alunos', 'internet_aprendizagem',
  'banda_larga', 'rede_wireless', 'comp_portatil_aluno', 'tablet_aluno',
]

function InfraBar({ value }) {
  const pct = !isMissing(value) ? Math.min(Math.max(Number(value), 0), 100) : 0
  return (
    <span className="infra-bar">
      <span className="infra-bar__fill" style={{ width: `${pct}%` }} />
    </span>
  )
}

const DEP_LABELS = {
  total: 'Total',
  publica: 'Pública',
  municipal: 'Municipal',
  estadual: 'Estadual',
  privada: 'Privada',
  federal: 'Federal',
}

const LOCATION_LABELS = {
  urbana: 'Urbana',
  rural: 'Rural',
}

function extractDimensionData(sourceRows, dimensionKey, selectedKey) {
  const rows = sourceRows.filter((row) => row[dimensionKey] === selectedKey)
  if (!rows.length) return { resumo: {}, series: {}, ultimoAno: null }
  const anos = [...new Set(rows.map((r) => r.ano))].sort((a, b) => a - b)
  const ultimoAno = anos[anos.length - 1]

  // Build resumo: latest year values for all perc_* columns
  const latest = rows.find((r) => r.ano === ultimoAno) || rows[rows.length - 1]
  const allMetricKeys = new Set()
  const resumo = {}
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (k.startsWith('perc_')) allMetricKeys.add(k)
    }
  }
  for (const pk of allMetricKeys) {
    const v = latest[pk]
    if (!isMissing(v)) resumo[pk] = v
  }

  // Build series: per metric key from perc_* columns
  const series = {}
  for (const pk of allMetricKeys) {
    const pts = rows
      .filter((r) => !isMissing(r[pk]))
      .map((r) => ({ ano: r.ano, valor: r[pk] }))
      .sort((a, b) => a.ano - b.ano)
    if (pts.length) series[pk.replace('perc_', '')] = pts
  }

  return { resumo, series, ultimoAno }
}

function getAvailableSchoolInfrastructureCutOptions(contract, indicatorKeys) {
  const options = SCHOOL_INFRASTRUCTURE_CUT_ORDER
    .filter((cutKey) => indicatorKeys.some(
      (indicatorKey) => selectSchoolInfrastructureResult(contract, indicatorKey, cutKey)?.percentage != null,
    ))
    .map((key) => ({ key, label: SCHOOL_INFRASTRUCTURE_CUT_LABELS[key] }))

  return options.length
    ? options
    : [{ key: 'total', label: SCHOOL_INFRASTRUCTURE_CUT_LABELS.total }]
}

function SchoolInfrastructureCutSelector({
  options = SCHOOL_INFRASTRUCTURE_CUT_ORDER.map((key) => ({
    key,
    label: SCHOOL_INFRASTRUCTURE_CUT_LABELS[key],
  })),
  selectedCut,
  setSelectedCut,
}) {
  return (
    <label className="school-infrastructure-cut-select">
      <span>Recorte exibido</span>
      <select
        aria-label="Rede ou localização exibida"
        onChange={(event) => setSelectedCut(event.target.value)}
        value={selectedCut}
      >
        {options.map(({ key, label }) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>
    </label>
  )
}

function formatInfrastructureCount(value) {
  return Number(value ?? 0).toLocaleString('pt-BR')
}

function formatInfrastructureValue(value) {
  return `${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}

function SchoolInfrastructurePanoramaChart({ results }) {
  return (
    <div className="school-infrastructure-panorama-chart" role="list" aria-label="Indicadores de infraestrutura básica">
      {results.map(({ key, label, result }) => {
        const canDraw = result?.percentage != null
        return (
          <div className="school-infrastructure-panorama-row" key={key} role="listitem">
          <span className="school-infrastructure-panorama-row__label">{label}</span>
          <span className="school-infrastructure-panorama-row__track" aria-hidden="true">
            <span style={{ width: `${canDraw ? Math.max(0, Math.min(100, result.percentage)) : 0}%` }} />
          </span>
          <span className="school-infrastructure-panorama-row__result">
            <strong>{formatSchoolInfrastructurePercentage(result)}</strong>
            <small>{formatSchoolInfrastructureQuantity(result)}</small>
          </span>
          </div>
        )
      })}
    </div>
  )
}

export function SchoolInfrastructureCombinedDetail({ contract }) {
  const [selectedCut, setSelectedCut] = useState('total')
  const [supportView, setSupportView] = useState('network')
  const availableCutOptions = getAvailableSchoolInfrastructureCutOptions(
    contract,
    SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER,
  )

  useEffect(() => {
    setSelectedCut('total')
  }, [contract])

  const results = SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.map((key) => ({
    key,
    label: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].shortLabel,
    result: selectSchoolInfrastructureResult(contract, key, selectedCut),
  }))
  const availableResults = results.filter(({ result }) => result?.percentage != null)
  const highestValue = Math.max(...availableResults.map(({ result }) => result.percentage))
  const lowestValue = Math.min(...availableResults.map(({ result }) => result.percentage))
  const highest = availableResults.filter(({ result }) => result.percentage === highestValue)
  const lowest = availableResults.filter(({ result }) => result.percentage === lowestValue)
  const allEqual = availableResults.length === results.length && highestValue === lowestValue
  const selectedCutLabel = SCHOOL_INFRASTRUCTURE_CUT_LABELS[selectedCut]

  const formatResultList = (items) => {
    if (!items.length) return 'Não disponível.'
    const labels = items.map(({ label }) => label)
    const names = labels.length === 1
      ? labels[0]
      : `${labels.slice(0, -1).join(', ')} e ${labels.at(-1)}`
    const verb = labels.length === 1 ? 'apresenta' : 'apresentam'
    return `${names} ${verb} ${formatSchoolInfrastructurePercentage(items[0].result)}.`
  }

  return (
    <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized school-infrastructure-combined">
      <div className="school-infrastructure-summary-grid">
        {results.map(({ key, label, result }) => {
          const quantity = formatSchoolInfrastructureQuantity(result)
          return (
            <div className="school-infrastructure-summary-card" key={key}>
              <span>{label}</span>
              <strong>{formatSchoolInfrastructurePercentage(result)}</strong>
              <small>{quantity === 'Não se aplica' || quantity === 'Não disponível' ? quantity : `${quantity} escolas`}</small>
              <em>Referência {contract.referenceYear}</em>
            </div>
          )
        })}
      </div>

      <div className="education-primary-analysis">
        <div className="indicator-chart-card educacao-main-chart-card school-infrastructure-main-card">
          <IndicatorChartHeader
            eyebrow="Síntese comparativa"
            title={`Panorama da infraestrutura básica — ${contract.referenceYear}`}
            subtitle="Percentual de escolas em cada dimensão, na mesma escala de 0 a 100."
          >
            <SchoolInfrastructureCutSelector
              options={availableCutOptions}
              selectedCut={selectedCut}
              setSelectedCut={setSelectedCut}
            />
          </IndicatorChartHeader>
          <SchoolInfrastructurePanoramaChart results={results} />
        </div>
        <EducationQuickReading
          items={[
            ...(allEqual ? [{
              icon: 'measure',
              key: 'equal-results',
              label: 'Resultados iguais',
              text: 'As cinco dimensões apresentam o mesmo resultado no recorte selecionado.',
            }] : [
              {
                icon: 'trend',
                key: 'highest-results',
                label: 'Maiores resultados',
                text: formatResultList(highest),
              },
              {
                icon: 'measure',
                key: 'lowest-result',
                label: 'Menor resultado',
                text: formatResultList(lowest),
              },
            ]),
            {
              emphasized: true,
              icon: 'cut',
              key: 'cut',
              label: 'Recorte exibido',
              text: selectedCutLabel,
            },
          ]}
        />
      </div>

      <SchoolInfrastructureComparisonData
        contract={contract}
        selectedView={supportView}
        setSelectedView={setSupportView}
      />

      <div className="school-infrastructure-method">
        <span><strong>Fonte:</strong> {SCHOOL_INFRASTRUCTURE_SOURCE} · <strong>Referência:</strong> {contract.referenceYear}</span>
        <span>{SCHOOL_INFRASTRUCTURE_METHODOLOGY}</span>
      </div>
    </section>
  )
}

function SchoolInfrastructureComparisonData({
  contract,
  selectedView,
  setSelectedView,
}) {
  const columns = selectedView === 'network'
    ? ['publica', 'municipal', 'estadual', 'federal', 'privada']
    : ['urbana', 'rural']
  const rows = SCHOOL_INFRASTRUCTURE_BASIC_INDICATOR_ORDER.map((key) => ({
    key,
    label: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].shortLabel,
    cells: columns.map((cutKey) => ({
      cutKey,
      result: selectSchoolInfrastructureResult(contract, key, cutKey),
    })),
  }))

  return (
    <section className="educacao-explore education-support-data education-support-data--organized school-infrastructure-comparisons" aria-labelledby="school-infrastructure-comparisons-title">
      <header className="education-support-data__header">
        <div className="education-support-data__summary">
          <span className="eyebrow">Comparações</span>
          <h3 id="school-infrastructure-comparisons-title">Dados de apoio</h3>
          <p>Compare as cinco dimensões por rede ou por localização.</p>
        </div>
        <IndicatorSegmentedControl
          ariaLabel="Comparação de infraestrutura"
          onSelect={setSelectedView}
          options={[
            { key: 'network', label: 'Por rede' },
            { key: 'location', label: 'Por localização' },
          ]}
          selectedKey={selectedView}
        />
      </header>
      <div className="school-infrastructure-comparison-table-wrap">
        <table className="school-infrastructure-comparison-table">
          <thead>
            <tr>
              <th scope="col">Dimensão</th>
              {columns.map((cutKey) => <th key={cutKey} scope="col">{SCHOOL_INFRASTRUCTURE_CUT_LABELS[cutKey].replace('Rede ', '')}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map(({ key, label, cells }) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                {cells.map(({ cutKey, result }) => (
                  <td key={cutKey}>
                    <strong>{formatSchoolInfrastructurePercentage(result)}</strong>
                    <small>{formatSchoolInfrastructureQuantity(result)}</small>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="school-infrastructure-comparison-cards">
        {rows.map(({ key, label, cells }) => (
          <article key={key}>
            <strong>{label}</strong>
            <dl>
              {cells.map(({ cutKey, result }) => (
                <div key={cutKey}>
                  <dt>{SCHOOL_INFRASTRUCTURE_CUT_LABELS[cutKey]}</dt>
                  <dd>
                    <strong>{formatSchoolInfrastructurePercentage(result)}</strong>
                    <small>{formatSchoolInfrastructureQuantity(result)}</small>
                  </dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}

function SchoolInfrastructureSupportChart({ contract, cutKey, indicatorKey, keys, kicker, title }) {
  return (
    <article className="education-support-data__item school-infrastructure-support-card">
      <header className="education-support-data__item-heading">
        <span className="eyebrow">{kicker}</span>
        <h4>{title}</h4>
      </header>
      <div className="school-infrastructure-support-bars">
        {keys.map((key) => {
          const result = selectSchoolInfrastructureResult(contract, indicatorKey, key)
          const display = formatSchoolInfrastructurePercentage(result)
          const canDraw = result?.totalActiveSchools > 0 && result?.denominator > 0 && result?.percentage != null
          const state = result?.totalActiveSchools === 0
            ? 'not-applicable'
            : !canDraw
              ? 'unavailable'
              : result.percentage === 0
                ? 'zero'
                : 'available'
          return (
            <div className={`school-infrastructure-support-row school-infrastructure-support-row--${state}${cutKey === key ? ' is-selected' : ''}`} key={key}>
              <span>{SCHOOL_INFRASTRUCTURE_CUT_LABELS[key]}</span>
              <span className="school-infrastructure-support-row__track" aria-hidden="true">
                {canDraw ? <span style={{ width: `${Math.max(0, Math.min(100, result.percentage))}%` }} /> : null}
              </span>
              <strong>{display}</strong>
              <small>{canDraw ? `${formatInfrastructureCount(result.numerator)} de ${formatInfrastructureCount(result.denominator)}` : null}</small>
            </div>
          )
        })}
      </div>
    </article>
  )
}

function SchoolInfrastructureSupportData({ contract, cutKey, indicatorKey }) {
  return (
    <section className="educacao-explore education-support-data education-support-data--organized school-infrastructure-support" aria-labelledby="school-infrastructure-support-title">
      <header className="education-support-data__header">
        <div className="education-support-data__summary">
          <span className="eyebrow">Comparações</span>
          <h3 id="school-infrastructure-support-title">Dados de apoio do indicador</h3>
          <p>Comparação dos resultados mais recentes entre as categorias disponíveis.</p>
        </div>
      </header>
      <div className="education-support-data__body">
        <div className="education-support-data__grid">
          <SchoolInfrastructureSupportChart contract={contract} cutKey={cutKey} indicatorKey={indicatorKey} keys={['publica', 'municipal', 'estadual', 'federal', 'privada']} kicker="Por rede" title={`Resultado por rede — ${contract.referenceYear}`} />
          <SchoolInfrastructureSupportChart contract={contract} cutKey={cutKey} indicatorKey={indicatorKey} keys={['urbana', 'rural']} kicker="Por localização" title={`Resultado por localização — ${contract.referenceYear}`} />
        </div>
      </div>
    </section>
  )
}

export function SchoolInfrastructureIndicatorDetail({ indicator }) {
  const [selectedCut, setSelectedCut] = useState('total')
  const contract = indicator.schoolInfrastructure
  const availableCutOptions = getAvailableSchoolInfrastructureCutOptions(
    contract,
    [indicator.schoolInfrastructureKey],
  )
  const result = selectSchoolInfrastructureResult(contract, indicator.schoolInfrastructureKey, selectedCut)
  const cutLabel = SCHOOL_INFRASTRUCTURE_CUT_LABELS[selectedCut]
  const quantity = formatSchoolInfrastructureQuantity(result)
  const snapshotReading = quantity === 'Não se aplica' || quantity === 'Não disponível'
    ? `Em ${contract.referenceYear}, o resultado para o recorte ${cutLabel} está como ${quantity.toLowerCase()}.`
    : `Em ${contract.referenceYear}, o recorte ${cutLabel} apresenta ${formatSchoolInfrastructurePercentage(result)}, equivalente a ${quantity} escolas observadas.`
  const warning = result?.missingSchools > 0
    ? 'Há escolas sem resposta válida para esta informação.'
    : null
  const historicalInitial = indicator.series?.[0]
  const historicalVariation = historicalInitial && result?.percentage != null
    ? {
        raw: result.percentage - historicalInitial.valor,
        display: `${(result.percentage - historicalInitial.valor).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} p.p.`,
        tone: result.percentage > historicalInitial.valor ? 'positive' : result.percentage < historicalInitial.valor ? 'warning' : 'muted',
      }
    : { raw: null, display: EM, tone: 'muted' }
  const historicalReading = selectedCut === 'total' && historicalInitial && result?.percentage != null
    ? `Entre ${historicalInitial.ano} e ${contract.referenceYear}, o resultado passou de ${indicator.formatValue(historicalInitial.valor)} para ${formatSchoolInfrastructurePercentage(result)}. Em ${contract.referenceYear}, são ${formatSchoolInfrastructureQuantity(result)} escolas observadas.`
    : snapshotReading

  useEffect(() => setSelectedCut('total'), [contract])

  return (
    <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized school-infrastructure-detail school-infrastructure-detail--historical">
      <EducationMetricSummary
        currentValue={formatSchoolInfrastructurePercentage(result)}
        currentYear={contract.referenceYear}
        initialValue={historicalInitial ? indicator.formatValue(historicalInitial.valor) : EM}
        initialYear={historicalInitial?.ano}
        statusLabel={indicator.statusLabel}
        statusDetail="Leitura descritiva da série"
        statusTone={historicalVariation.tone}
        variation={historicalVariation}
      />

      <div className="education-primary-analysis">
        <div className="indicator-chart-card educacao-main-chart-card school-infrastructure-main-card">
          <IndicatorChartHeader
            eyebrow="Série histórica"
            title="Evolução do indicador"
            subtitle={`${indicator.label} · histórico municipal`}
          >
            <div className="school-infrastructure-main-card__controls">
              <SchoolInfrastructureCutSelector
                options={availableCutOptions}
                selectedCut={selectedCut}
                setSelectedCut={setSelectedCut}
              />
            </div>
          </IndicatorChartHeader>
          <EducationLineChart
            color={indicator.chartColor}
            formatLabel={indicator.formatValue}
            scaleType={indicator.scaleType}
            series={indicator.series}
            showPointLabels={indicator.showPointLabels}
            title={null}
          />
        </div>
        <EducationIndicatorQuickReading
          cutLabel={cutLabel}
          description={indicator.description}
          firstLabel="Evolução observada"
          text={historicalReading}
          warning={warning}
        />
      </div>

      <SchoolInfrastructureSupportData contract={contract} cutKey={selectedCut} indicatorKey={indicator.schoolInfrastructureKey} />

      <div className="school-infrastructure-method">
        <span><strong>Fonte:</strong> {SCHOOL_INFRASTRUCTURE_SOURCE} · <strong>Referência:</strong> {contract.referenceYear}</span>
        <span>{SCHOOL_INFRASTRUCTURE_METHODOLOGY}</span>
      </div>
    </section>
  )
}

export function InfraDetailPanel({ indicator, blocos }) {
  const detailDescription = indicator.description || 'Condições de conectividade, tecnologia e ambiente físico das escolas.'
  const redeBloco = blocos?.rede_escolar ?? {}
  const infra = redeBloco.infraestrutura ?? {}
  const schoolInfrastructure = infra.contractVersion === SCHOOL_INFRASTRUCTURE_CONTRACT_VERSION
    ? infra
    : indicator.schoolInfrastructure
  const infraResumo = infra.resumo_ultimo_ano ?? {}
  const infraSeries = infra.series ?? {}
  const grupos = infra.grupos ?? null
  const ultimoAno = infra.ultimo_ano
  const por_rede = infra.por_rede ?? []
  const por_localizacao = infra.por_localizacao ?? []

  // ── Filtro por rede ou localização ───────────────────────────────────
  const dependencyOrder = ['publica', 'municipal', 'estadual', 'federal', 'privada']
  const availableDepKeys = [...new Set(por_rede.map((row) => row.dependencia).filter(Boolean))]
    .sort((a, b) => dependencyOrder.indexOf(a) - dependencyOrder.indexOf(b))
  const locationOrder = ['urbana', 'rural']
  const availableLocationKeys = [...new Set(por_localizacao.map((row) => row.localizacao).filter(Boolean))]
    .sort((a, b) => locationOrder.indexOf(a) - locationOrder.indexOf(b))
  const availableCuts = schoolInfrastructure
    ? getAvailableSchoolInfrastructureCutOptions(
        schoolInfrastructure,
        SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER,
      )
    : [
        { key: 'total', label: 'Total' },
        ...availableDepKeys.map((key) => ({ key: `rede:${key}`, label: `Rede ${DEP_LABELS[key]?.toLowerCase() ?? key}` })),
        ...availableLocationKeys.map((key) => ({ key: `localizacao:${key}`, label: LOCATION_LABELS[key] ?? key })),
      ]
  const [selectedCut, setSelectedCut] = useState('total')
  // Reset to total when municipality changes
  useEffect(() => { setSelectedCut('total') }, [blocos?.rede_escolar])

  const [legacyDimension, legacyKey] = selectedCut.split(':')
  const selectedDimension = legacyKey
    ? legacyDimension
    : ['urbana', 'rural'].includes(selectedCut) ? 'localizacao' : 'rede'
  const selectedKey = legacyKey ?? selectedCut
  const isFiltered = selectedCut !== 'total'
  const selectedRows = selectedDimension === 'rede' ? por_rede : por_localizacao
  const selectedDimensionKey = selectedDimension === 'rede' ? 'dependencia' : 'localizacao'
  const cutData = isFiltered ? extractDimensionData(selectedRows, selectedDimensionKey, selectedKey) : null
  const activeResumo = cutData ? cutData.resumo : infraResumo
  const activeUltimoAno = cutData ? cutData.ultimoAno : ultimoAno
  const hasCutSeries = isFiltered && cutData && Object.keys(cutData.series).length > 0

  const GROUP_ORDER = ['ambiente_escolar', 'conectividade', 'rede_e_dispositivos']

  // ── Grupos com metricas ──────────────────────────────────────────────
  const cardGroups = []
  if (grupos) {
    for (const gk of GROUP_ORDER) {
      const grupo = grupos[gk]
      if (!grupo) continue
      const metrics = (grupo.metricas ?? [])
        .map((mk) => {
          const val = isFiltered ? activeResumo[`perc_${mk}`] : activeResumo[mk]
          return {
            key: mk,
            label: INFRA_METRIC_LABELS[mk] ?? mk,
            value: val,
            year: activeUltimoAno,
            isSala: mk.startsWith('salas_'),
          }
        })
        .filter((m) => !isMissing(m.value))
      if (metrics.length) {
        cardGroups.push({ groupKey: gk, groupLabel: grupo.label, metrics })
      }
    }
  }

  // ── Tabela de evolucao ──────────────────────────────────────────────
  const sourceSeries = isFiltered && hasCutSeries ? cutData.series : infraSeries
  const selectedCutLabel = availableCuts.find((cut) => cut.key === selectedCut)?.label ?? selectedKey
  const tableLabel = isFiltered && !hasCutSeries ? 'total do município' : selectedCutLabel.toLowerCase()
  const panoramaResults = schoolInfrastructure
    ? SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.map((key) => ({
        key,
        label: SCHOOL_INFRASTRUCTURE_PUBLIC_COPY[key].shortLabel,
        result: selectSchoolInfrastructureResult(schoolInfrastructure, key, selectedCut),
      }))
    : []
  const panoramaAvailableResults = panoramaResults.filter(({ result }) => result?.percentage != null)
  const panoramaHighestValue = Math.max(...panoramaAvailableResults.map(({ result }) => result.percentage))
  const panoramaLowestValue = Math.min(...panoramaAvailableResults.map(({ result }) => result.percentage))
  const panoramaHighest = panoramaAvailableResults.filter(({ result }) => result.percentage === panoramaHighestValue)
  const panoramaLowest = panoramaAvailableResults.filter(({ result }) => result.percentage === panoramaLowestValue)
  const panoramaAllEqual = panoramaAvailableResults.length > 1 && panoramaHighestValue === panoramaLowestValue
  const panoramaUniverse = panoramaResults[0]?.result?.totalActiveSchools ?? null
  const panoramaCoverageTotals = panoramaResults.reduce((totals, { result }) => ({
    active: totals.active + (result?.totalActiveSchools ?? 0),
    observed: totals.observed + (result?.denominator ?? 0),
  }), { active: 0, observed: 0 })
  const panoramaCoveragePercentage = panoramaCoverageTotals.active > 0
    ? (panoramaCoverageTotals.observed / panoramaCoverageTotals.active) * 100
    : null
  const panoramaCoverageComplete = panoramaCoveragePercentage === 100
  const formatPanoramaResultList = (items) => {
    if (!items.length) return 'Não disponível'
    const labels = items.map(({ label }, index) => index === 0 ? label : label.toLocaleLowerCase('pt-BR'))
    const names = labels.length === 1
      ? labels[0]
      : `${labels.slice(0, -1).join(', ')} e ${labels.at(-1)}`
    return `${names}: ${formatSchoolInfrastructurePercentage(items[0].result)}.`
  }

  const yearSet = new Set()
  for (const mk of INFRA_EVOLUTION_KEYS) {
    for (const pt of sourceSeries[mk] ?? []) {
      if (!isMissing(pt.valor)) yearSet.add(pt.ano)
    }
  }
  let years = [...yearSet].sort((a, b) => a - b)
  const minTableYear = 2019
  years = years.filter((y) => y >= minTableYear)
  if (!years.length) years = [...yearSet].sort((a, b) => a - b)

  const evolutionColumns = [
    { key: 'indicador', label: 'Indicador' },
    ...years.map((y) => ({
      key: String(y),
      label: String(y),
      format: formatPercent,
      className: y === Math.max(...years) ? 'col-latest' : '',
    })),
  ]
  const evolutionRows = INFRA_EVOLUTION_KEYS
    .map((mk) => {
      const serie = sourceSeries[mk] ?? []
      const yearMap = {}
      for (const pt of serie) {
        if (!isMissing(pt.valor)) yearMap[String(pt.ano)] = pt.valor
      }
      const row = { indicador: INFRA_METRIC_LABELS[mk] ?? mk }
      for (const y of years) {
        row[String(y)] = yearMap[String(y)] ?? null
      }
      return row
    })
    .filter((row) => years.some((y) => row[String(y)] !== null))

  // ── Render ───────────────────────────────────────────────────────────
  return (
    <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized school-infrastructure-panorama">
      {schoolInfrastructure ? (
        <>
          <div className="metric-grid metric-grid--four education-metric-summary school-infrastructure-summary">
            <MetricCard icon="type" label="Escolas em atividade" value={panoramaUniverse == null ? EM : formatInfrastructureCount(panoramaUniverse)} detail={selectedCutLabel} />
            <MetricCard icon="status" label="Indicadores apresentados" value={SCHOOL_INFRASTRUCTURE_INDICATOR_ORDER.length} detail="Infraestrutura básica" />
            <MetricCard
              icon="comparison"
              label="Cobertura da informação"
              value={panoramaCoveragePercentage == null ? EM : formatInfrastructureValue(panoramaCoveragePercentage)}
              detail={panoramaCoverageComplete ? 'Cobertura completa' : 'Cobertura parcial'}
            />
            <MetricCard icon="current" label="Referência" value={schoolInfrastructure.referenceYear} detail="Censo Escolar" />
          </div>

          <div className="education-primary-analysis">
            <div className="indicator-chart-card educacao-main-chart-card school-infrastructure-main-card">
              <IndicatorChartHeader
                eyebrow="Síntese comparativa"
                title={`Panorama da infraestrutura básica — ${schoolInfrastructure.referenceYear}`}
                subtitle="Percentual de escolas em cada indicador, na mesma escala de 0 a 100."
              >
                <SchoolInfrastructureCutSelector
                  options={availableCuts}
                  selectedCut={selectedCut}
                  setSelectedCut={setSelectedCut}
                />
              </IndicatorChartHeader>
              <SchoolInfrastructurePanoramaChart results={panoramaAvailableResults} />
            </div>
            <EducationQuickReading
              items={[
                ...(panoramaAllEqual ? [{
                  icon: 'measure',
                  key: 'equal-results',
                  label: 'Resultados iguais',
                  text: 'Os seis indicadores apresentam o mesmo resultado no recorte selecionado.',
                }] : [
                  {
                    icon: 'trend',
                    key: 'highest-results',
                    label: panoramaHighest.length > 1 ? 'Maiores resultados' : 'Maior resultado',
                    text: formatPanoramaResultList(panoramaHighest),
                  },
                  {
                    icon: 'measure',
                    key: 'lowest-results',
                    label: panoramaLowest.length > 1 ? 'Menores resultados' : 'Menor resultado',
                    text: formatPanoramaResultList(panoramaLowest),
                  },
                ]),
                {
                  emphasized: true,
                  icon: 'cut',
                  key: 'cut',
                  label: 'Recorte exibido',
                  text: selectedCutLabel,
                },
              ]}
            />
          </div>
        </>
      ) : (
        <EducationIndicatorQuickReading description={detailDescription} />
      )}

      <section className="educacao-explore education-support-data education-support-data--organized school-infrastructure-panorama__support" aria-labelledby="school-infrastructure-panorama-support-title">
        <header className="education-support-data__header">
          <div className="education-support-data__summary">
            <span className="eyebrow">Detalhamento</span>
            <h3 id="school-infrastructure-panorama-support-title">Dados de apoio</h3>
            <p>Ambiente escolar, conectividade, rede e dispositivos no recorte exibido.</p>
          </div>
        </header>
        <div className="education-support-data__body infra-panorama-grid">
          {cardGroups.map((g) => {
            const refText = g.groupKey === 'ambiente_escolar' ? '% de salas' : '% de escolas'
            const referenceYear = g.metrics.find(({ year }) => year)?.year
            const isFirst = g.groupKey === 'ambiente_escolar'
            return (
              <div key={g.groupKey} className={`infra-panel-group${isFirst ? ' is-primary' : ''}`}>
                <div className="infra-panel-group__head">
                  <span className="infra-panel-group__title">{g.groupLabel}</span>
                  <span className="infra-panel-group__ref">
                    <span>{refText}</span>
                    {referenceYear ? <strong>{referenceYear}</strong> : null}
                  </span>
                </div>
                <div className="infra-panel-group__body">
                  {g.metrics.map((m) => (
                    <div key={m.key} className="infra-row">
                      <span className="infra-row__label">{m.label}</span>
                      <div className="infra-row__meta">
                        <span className="infra-row__value">{formatPercent(m.value)}</span>
                        <span className="infra-row__bar">
                          <InfraBar value={m.value} />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
        <footer className="education-support-data__footer">
          <span><strong>Fonte:</strong> {SCHOOL_INFRASTRUCTURE_SOURCE}</span>
        </footer>
      </section>

      {evolutionRows.length > 0 && years.length > 0 ? (
        <details className="indicator-chart-card infra-evolution-table-wrap platform-support-disclosure">
          <summary className="education-chart-heading platform-support-disclosure__summary">
            <div>
              <span>Histórico de conectividade e condições escolares</span>
              <p>Percentual por ano — {tableLabel}</p>
            </div>
            <DisclosureChevron />
          </summary>
          <div className="infra-table-scroll">
            <EducationTable
              caption="Histórico de conectividade e condições escolares"
              columns={evolutionColumns}
              rows={evolutionRows}
            />
          </div>
          <EducationSourceNotes
            context={dataSourceContextForEducation(indicator, {
              detailType: 'table',
              title: 'Histórico dos principais indicadores de infraestrutura',
            })}
          />
        </details>
      ) : null}
    </section>
  )
}

