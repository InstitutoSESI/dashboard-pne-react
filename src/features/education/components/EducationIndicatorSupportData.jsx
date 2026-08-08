import { EducationBarChart } from '../../../components/EducationBarChart.jsx'
import { EducationLineChart } from '../../../components/EducationLineChart.jsx'
import { EducationStackedBarChart } from '../../../components/EducationStackedBarChart.jsx'
import { EducationTable } from '../../../components/EducationTable.jsx'
import { MethodNote } from '../../../components/MethodNote.jsx'
import { ChartEmptyState } from '../../../components/ChartPrimitives.jsx'
import {
  formatNumber,
  formatRatio,
  isMissing,
} from '../../../utils/educationFormatters.js'
import {
  EducationSupportDataCard,
  EducationSupportDataSection,
} from './EducationIndicatorDetailShell'
import {
  EducationSourceNotes,
  dataSourceContextForEducation,
} from './EducationSourceNotes'
import {
  AgeRangeDetail,
  ColorRaceDetail,
  ModalityDetail,
} from './EducationDemographicDetails'

const EM = '\u2014'

export function EducationIndicatorBreakdown({ indicator }) {
  const detailItems = sortDetailItems(indicator.explore ?? [])

  if (!detailItems.length) return null

  const supportId = `education-support-${String(indicator.key ?? 'detail').replace(/[^a-z0-9_-]/gi, '-')}`
  const profileItems = detailItems.filter(isEducationSupportProfileItem)
  const hasProfilePair = profileItems.length === 2
  const compactItems = detailItems.filter((item) => !isEducationSupportWideItem(item) && !isEducationSupportProfileItem(item))
  const lastCompactItem = compactItems.at(-1)
  const hasOddCompactRow = compactItems.length % 2 === 1

  return (
    <EducationSupportDataSection
      footer={<EducationSourceNotes context={dataSourceContextForEducation(indicator)} />}
      id={supportId}
    >
      {detailItems.map((item) => {
            const wide = isEducationSupportWideItem(item)
            const paired = hasProfilePair && isEducationSupportProfileItem(item)
            const third = item.supportLayout === 'third'
            const fullRow = !third && (wide || (!paired && isEducationSupportProfileItem(item)) || (hasOddCompactRow && item === lastCompactItem))

            return (
              <EducationSupportDataItem
                fullRow={fullRow}
                item={item}
                key={`${item.key}-${item.orientation ?? 'horizontal'}`}
                paired={paired}
                supportId={supportId}
                third={third}
                wide={wide}
              />
            )
      })}
    </EducationSupportDataSection>
  )
}

function EducationSupportDataItem({ fullRow, item, paired, supportId, third, wide }) {
  const itemId = `${supportId}-${String(item.key ?? 'item').replace(/[^a-z0-9_-]/gi, '-')}`
  const contextLabel = getDetailTabLabel(item)
  const title = item.title ?? contextLabel

  return (
    <EducationSupportDataCard
      className={`${wide ? 'education-support-data__item--wide' : ''}${paired ? ' education-support-data__item--paired' : ''}${third ? ' education-support-data__item--third' : ''}${fullRow ? ' education-support-data__item--full-row' : ''}`}
      description={getEducationSupportDescription(item)}
      eyebrow={contextLabel}
      id={itemId}
      title={title}
    >
      <ExploreItem item={item} />
    </EducationSupportDataCard>
  )
}

function isEducationSupportWideItem(item) {
  return item.supportLayout === 'full' || ['modality-range', 'stage-detail', 'table'].includes(item.type)
}

function isEducationSupportProfileItem(item) {
  return ['age-range', 'color-race'].includes(item.type)
}

function getEducationSupportDescription(item) {
  if (item.description) return item.description
  if (item.type === 'stacked') return 'Distribuição histórica do indicador no recorte selecionado.'
  if (item.type === 'bar') return 'Comparação dos valores mais recentes entre as categorias disponíveis.'
  if (item.type === 'line') return 'Evolução anual da série complementar usada nesta leitura.'
  if (item.type === 'table') return 'Valores detalhados que complementam a leitura do indicador.'
  if (item.type === 'stage-detail') return 'Panorama, distribuição e evolução do recorte por etapa.'
  if (item.type === 'stage-context') return 'Síntese dos valores mais recentes para o recorte selecionado.'
  return 'Recorte complementar para interpretar o indicador com mais contexto.'
}

function sortDetailItems(items) {

  return [...items].sort((a, b) => detailTabPriority(a) - detailTabPriority(b))
}

function detailTabPriority(item) {
  if (Number.isFinite(item.tabPriority)) return item.tabPriority
  const label = getDetailTabLabel(item)
  if (label === 'Por rede') return 1
  if (label === 'Por localização') return 2
  if (label === 'Por etapa') return 3
  if (label === 'Por faixa etária') return 4
  if (label === 'Por cor/raça') return 5
  if (label === 'Por modalidade') return 6
  if (label === 'Histórico do indicador') return 7
  if (label === 'Infraestrutura') return 8
  return 10
}

function getDetailTabLabel(item) {
  if (item.tabLabel) return item.tabLabel
  const title = String(item.title ?? '').toLocaleLowerCase('pt-BR')
  if (item.type === 'age-range') return 'Por faixa etária'
  if (item.type === 'color-race') return 'Por cor/raça'
  if (title.includes('faixa et')) return 'Por faixa etária'
  if (title.includes('cor/ra') || title.includes('raça')) return 'Por cor/raça'
  if (title.includes('etapa')) return 'Por etapa'
  if (title.includes('localiza')) return 'Por localização'
  if (title.includes('rede') || title.includes('depend')) return 'Por rede'
  if (title.includes('modalidade')) return 'Por modalidade'
  if (title.includes('infraestrutura')) return 'Infraestrutura'
  if (title.includes('evolu') || title.includes('histórico')) return 'Histórico do indicador'
  if (item.type === 'table') return 'Tabela'
  return item.title ?? 'Detalhamento'
}

function ExploreItem({ item }) {
  const isSchoolStageMethodology = item.key === 'rede-etapa' && Boolean(item.note)
  const noteEl = isSchoolStageMethodology ? (
    <MethodNote className="educacao-explore__note">{item.note}</MethodNote>
  ) : item.note ? (
    <p className="educacao-explore__note">{item.note}</p>
  ) : null
  if (item.type === 'stacked') {
    return (
      <>
        <EducationStackedBarChart
          categories={item.categories}
          data={item.data}
          formatLabel={item.formatLabel}
          title={item.title}
        />
        {noteEl}
      </>
    )
  }

  if (item.type === 'bar') {
    if (item.presentation === 'compact-comparison') {
      return (
        <>
          <EducationCompactComparison data={item.data} formatLabel={item.formatLabel} title={item.title} />
          {noteEl}
        </>
      )
    }
    return (
      <>
        <EducationBarChart color={item.color} data={item.data} formatLabel={item.formatLabel} orientation={item.orientation} preserveOrder={item.preserveOrder} size={item.chartSize} title={item.title} />
        {noteEl}
      </>
    )
  }
  if (item.type === 'stage-detail') {
    return (
      <>
        {item.panoramaRows && item.panoramaRows.length ? (
          <div className="educacao-explore-table educacao-explore-table--spaced">
            <h4>{item.panoramaTitle}</h4>
            <EducationTable columns={item.panoramaColumns} rows={item.panoramaRows} />
          </div>
        ) : null}
        <EducationBarChart
          color={item.distributionColor ?? '#16713a'}
          data={item.distributionData}
          formatLabel={item.formatLabel}
          title={item.distributionTitle}
        />
        {item.historyCategories && item.historyData && item.historyData.length >= 2 ? (
          <div className="educacao-explore-block--spaced">
            <EducationStackedBarChart
              categories={item.historyCategories}
              data={item.historyData}
              formatLabel={item.formatLabel}
              title={item.historyTitle}
            />
          </div>
        ) : item.note ? (
          <p className="educacao-explore__note">{item.note}</p>
        ) : null}
      </>
    )
  }
  if (item.type === 'stage-context') {
    const format = item.formatLabel ?? formatNumber
    const primaryValue = item.value ?? item.turmas
    const primaryLabel = item.valueLabel ?? 'Turmas'
    return (
      <div className="educacao-stage-context">
        <span>Resumo{item.ano ? ` — ${item.ano}` : ''}</span>
        <div className="educacao-stage-context__grid">
          <div className="educacao-stage-context__card">
            <span className="educacao-stage-context__value">{!isMissing(primaryValue) ? format(primaryValue) : EM}</span>
            <span className="educacao-stage-context__label">{primaryLabel}</span>
          </div>
          <div className="educacao-stage-context__card">
            <span className="educacao-stage-context__value">{!isMissing(item.alunosPorTurma) ? formatRatio(item.alunosPorTurma) : EM}</span>
            <span className="educacao-stage-context__label">Média de alunos por turma</span>
          </div>
          <div className="educacao-stage-context__card">
            <span className="educacao-stage-context__value">{!isMissing(item.docentes) ? formatNumber(item.docentes) : EM}</span>
            <span className="educacao-stage-context__label">Docentes</span>
          </div>
        </div>
      </div>
    )
  }
  if (item.type === 'age-range') {
    return <AgeRangeDetail key={item.key} item={item} />
  }
  if (item.type === 'color-race') {
    return <ColorRaceDetail key={item.key} item={item} />
  }
  if (item.type === 'modality-range') {
    return <ModalityDetail key={item.key} item={item} />
  }
  if (item.type === 'line') {
    return item.series.length >= 2
      ? <EducationLineChart color={item.color} formatLabel={item.formatLabel} scaleType={item.scaleType} series={item.series} title={item.title} />
      : <div className="education-chart-empty"><p>Não há dados suficientes para exibir o gráfico.</p></div>
  }
  if (item.type === 'table') {
    return (
      <div className="educacao-explore-table">
        <h4>{item.title}</h4>
        <EducationTable columns={item.columns} rows={item.rows} />
        {noteEl}
      </div>
    )
  }
  return null
}

function EducationCompactComparison({ data, formatLabel = String, title }) {
  const rows = (Array.isArray(data) ? data : [])
    .filter((row) => !isMissing(row?.value) && Number(row.value) >= 0)
    .map((row) => ({ ...row, value: Number(row.value) }))
    .sort((a, b) => b.value - a.value)

  if (!rows.length) return <ChartEmptyState />

  const maxValue = Math.max(...rows.map((row) => row.value), 1)

  return (
    <dl className="education-compact-comparison" aria-label={title}>
      {rows.map((row) => (
        <div className="education-compact-comparison__item" key={row.label}>
          <dt>{row.label}</dt>
          <dd>
            <strong>{formatLabel(row.value)}</strong>
            <progress aria-label={`${row.label}: ${formatLabel(row.value)}`} max={maxValue} value={row.value} />
          </dd>
        </div>
      ))}
    </dl>
  )
}
