import { useEffect, useMemo, useState } from 'react'
import { formatNumber } from '../utils/educationFormatters'
import { ContentState } from './ContentState'
import { DataSourceNote } from './DataSourceNote'
import { DetailNavigation } from './DetailNavigation'
import { EducationLineChart } from './EducationLineChart'
import { EducationQuickReading } from './EducationQuickReading'
import { EducationTable } from './EducationTable'
import { MetricCard } from './MetricCard'

const UNIT_ORDER = ['cobertura', 'matriculas', 'estabelecimentos', 'docentes', 'turmas']
const SUMMARY_UNIT_ORDER = ['matriculas', 'estabelecimentos', 'docentes', 'turmas']
const UNIT_LABELS = {
  cobertura: 'Cobertura estimada',
  matriculas: 'Matrículas',
  estabelecimentos: 'Estabelecimentos',
  docentes: 'Docentes',
  turmas: 'Turmas',
}
const UNIT_DESCRIPTIONS = {
  cobertura: 'Relação entre matrículas nas três etapas consideradas e a população indígena de 4 a 17 anos recenseada em 2022.',
  matriculas: 'Total oficial de matrículas registrado no município.',
  estabelecimentos: 'Estabelecimentos com oferta registrada no município.',
  docentes: 'Docentes registrados nas tabelas específicas.',
  turmas: 'Turmas registradas nas tabelas específicas.',
}
const UNIT_ICONS = {
  cobertura: 'measure',
  matriculas: 'current',
  estabelecimentos: 'type',
  docentes: 'status',
  turmas: 'comparison',
}
const INDIGENOUS_EDUCATION_SOURCE = 'INEP — Sinopse Estatística da Educação Básica, tabelas de Educação Escolar Indígena (2023–2025).'
const ENROLLMENT_CUTS = [
  'educacao_infantil',
  'creche',
  'pre_escola',
  'ensino_fundamental',
  'anos_iniciais',
  'anos_finais',
  'ensino_medio',
  'educacao_profissional',
  'eja',
  'eja_ensino_fundamental',
  'eja_ensino_medio',
  'educacao_especial',
  'classes_comuns',
  'classes_exclusivas',
]
const MAIN_STAGE_CUTS = [
  'educacao_infantil',
  'ensino_fundamental',
  'ensino_medio',
  'educacao_profissional',
  'eja',
  'educacao_especial',
]

export function IndigenousEducationPanel({ blocos, initialUnitKey = 'matriculas' }) {
  const block = blocos?.educacao_indigena ?? {}
  const [selectedUnit, setSelectedUnit] = useState(
    UNIT_ORDER.includes(initialUnitKey) ? initialUnitKey : 'matriculas',
  )

  useEffect(() => {
    if (UNIT_ORDER.includes(initialUnitKey)) setSelectedUnit(initialUnitKey)
  }, [initialUnitKey])

  const years = Array.isArray(block.anos_disponiveis) ? block.anos_disponiveis : []
  const latestYear = block.ultimo_ano
  const records = useMemo(
    () => (Array.isArray(block.dados) ? block.dados : []),
    [block.dados],
  )
  const summary = block.resumo_ultimo_ano ?? {}
  const series = block.series_totais ?? {}
  const cutLabels = block.recortes ?? {}
  const coverage = block.coberturaEstimada ?? null
  const latestRecords = useMemo(
    () => records.filter((row) => Number(row.ano) === Number(latestYear)),
    [latestYear, records],
  )

  if (!years.length || !records.length) {
    return (
      <ContentState kind="unavailable" className="state-box">
        <strong>Retrato da Educação Escolar Indígena indisponível</strong>
        <span>Não há dados municipais publicados nas tabelas específicas da Sinopse Estatística.</span>
      </ContentState>
    )
  }

  const enrollmentRows = ENROLLMENT_CUTS.map((cutKey) => ({
    etapa: cutLabels[cutKey] ?? cutKey,
    ...Object.fromEntries(years.map((year) => [
      String(year),
      findValue(records, 'matriculas', cutKey, year),
    ])),
  }))
  const offerRows = MAIN_STAGE_CUTS.map((cutKey) => ({
    etapa: cutLabels[cutKey] ?? cutKey,
    estabelecimentos: findLatestValue(latestRecords, 'estabelecimentos', cutKey),
    docentes: findLatestValue(latestRecords, 'docentes', cutKey),
    turmas: findLatestValue(latestRecords, 'turmas', cutKey),
  }))
  const offerMeasureColumns = [
    { key: 'estabelecimentos', label: 'Estabelecimentos' },
    { key: 'docentes', label: 'Docentes' },
    { key: 'turmas', label: 'Turmas' },
  ].filter((column) => offerRows.some((row) => !isUnavailable(row[column.key])))
  const visibleOfferRows = offerRows.filter((row) => (
    offerMeasureColumns.some((column) => !isUnavailable(row[column.key]))
  ))
  const selectedSeries = Array.isArray(series[selectedUnit]) ? series[selectedUnit] : []
  const selectedIndex = UNIT_ORDER.indexOf(selectedUnit)
  const previousUnit = selectedIndex > 0
    ? { key: UNIT_ORDER[selectedIndex - 1], label: UNIT_LABELS[UNIT_ORDER[selectedIndex - 1]] }
    : null
  const nextUnit = selectedIndex < UNIT_ORDER.length - 1
    ? { key: UNIT_ORDER[selectedIndex + 1], label: UNIT_LABELS[UNIT_ORDER[selectedIndex + 1]] }
    : null
  const periodLabel = years.length > 1 ? `${years[0]} a ${years.at(-1)}` : String(years[0])
  const currentDisplay = formatCount(summary[selectedUnit])

  return (
    <article className="indigenous-education-panel">
      <DetailNavigation
        activeIndex={selectedIndex}
        itemLabel="Medida"
        itemPlural="medidas"
        nextLabel="Próxima medida"
        nextItem={nextUnit}
        onNext={setSelectedUnit}
        onPrevious={setSelectedUnit}
        previousItem={previousUnit}
        showBack={false}
        total={UNIT_ORDER.length}
      />

      <section className="detail-panel educacao-detail-panel educacao-detail-panel--organized">
        <div className="indicator-control-bar platform-control-bar indigenous-education-panel__control">
          <div className="indicator-control-bar__copy">
            <span className="indicator-control-bar__label">Medida analisada</span>
            <span className="indicator-control-bar__hint">Atualiza o histórico e a leitura rápida sem alterar os recortes publicados.</span>
          </div>
          <div className="indigenous-education-panel__tabs" role="tablist" aria-label="Medida da série histórica">
            {UNIT_ORDER.map((unitKey) => (
              <button
                aria-selected={selectedUnit === unitKey}
                className={`infra-dep-pill${selectedUnit === unitKey ? ' is-active' : ''}`}
                key={unitKey}
                onClick={() => setSelectedUnit(unitKey)}
                role="tab"
                type="button"
              >
                {UNIT_LABELS[unitKey]}
              </button>
            ))}
          </div>
        </div>

        {selectedUnit === 'cobertura' ? (
          <CoverageView coverage={coverage} />
        ) : (
          <>
        <section aria-labelledby="indigenous-summary-title">
          <PanelHeading
            eyebrow="Retrato municipal"
            id="indigenous-summary-title"
            title={`Síntese de ${latestYear}`}
            description="Totais oficiais publicados para o município nas quatro tabelas específicas da Educação Indígena."
          />
          <div className="metric-grid metric-grid--four education-metric-summary indigenous-education-panel__summary-grid">
            {SUMMARY_UNIT_ORDER.map((unitKey) => (
              <MetricCard
                detail={valueStateMessage(summary[unitKey])}
                icon={UNIT_ICONS[unitKey]}
                key={unitKey}
                label={UNIT_LABELS[unitKey]}
                size={selectedUnit === unitKey ? 'large' : 'normal'}
                value={formatCount(summary[unitKey])}
              />
            ))}
          </div>
        </section>

        <div className="education-primary-analysis indigenous-education-panel__primary">
          <div className="indicator-chart-card educacao-main-chart-card indigenous-education-panel__chart">
            <div className="education-chart-heading">
              <div>
                <span>Evolução do indicador</span>
                <p>{UNIT_LABELS[selectedUnit]} · Educação Escolar Indígena</p>
              </div>
            </div>
            <EducationLineChart
              color="var(--green-primary)"
              formatLabel={formatCount}
              scaleType="count"
              series={selectedSeries}
              showPointLabels
              title={null}
            />
          </div>
          <EducationQuickReading
            items={[
              {
                key: 'current',
                icon: 'measure',
                label: `Retrato de ${latestYear}`,
                text: `${currentDisplay} em ${UNIT_LABELS[selectedUnit].toLocaleLowerCase('pt-BR')} no total oficial do município.`,
              },
              {
                key: 'period',
                icon: 'period',
                label: 'Período comparável',
                text: `A série total apresentada cobre ${periodLabel}.`,
              },
              {
                key: 'scope',
                icon: 'cut',
                label: 'O que a medida mostra',
                text: UNIT_DESCRIPTIONS[selectedUnit],
              },
            ]}
          />
        </div>

        <section className="educacao-explore education-support-data education-support-data--organized indigenous-education-panel__support" aria-labelledby="indigenous-support-title">
          <header className="education-support-data__header">
            <div className="education-support-data__summary">
              <span className="educacao-explore__eyebrow">Aprofundamento</span>
              <h3 id="indigenous-support-title">Dados de apoio do indicador</h3>
              <p>Matrículas, estabelecimentos, docentes e turmas por etapa e modalidade.</p>
            </div>
          </header>
          <div className="education-support-data__body">
            <div className="education-support-data__grid indigenous-education-panel__table-grid">
              <TableSection
                className="education-support-data__item--wide"
                description="Consulte a distribuição anual das matrículas em cada etapa e modalidade."
                eyebrow="Matrículas"
                id="indigenous-enrollment-title"
                title="Matrículas por etapa e modalidade"
              >
                <EducationTable
                  caption="Matrículas na Educação Escolar Indígena por etapa e ano"
                  className="indigenous-education-table"
                  columns={[
                    { key: 'etapa', label: 'Etapa ou modalidade', className: 'indigenous-education-table__label', rowHeader: true },
                    ...years.map((year) => ({
                      key: String(year),
                      label: String(year),
                      numeric: true,
                      className: 'indigenous-education-table__number',
                      format: formatCount,
                    })),
                  ]}
                  rows={enrollmentRows}
                />
              </TableSection>

              <TableSection
                className="education-support-data__item--wide"
                description="Compare as informações disponíveis sobre a oferta em cada etapa de ensino."
                eyebrow="Oferta e organização"
                id="indigenous-offer-title"
                title={`Oferta por etapa em ${latestYear}`}
              >
                <EducationTable
                  caption={`Oferta de Educação Escolar Indígena por etapa em ${latestYear}`}
                  className="indigenous-education-table"
                  columns={[
                    { key: 'etapa', label: 'Etapa ou modalidade', className: 'indigenous-education-table__label', rowHeader: true },
                    ...offerMeasureColumns.map((column) => ({
                      ...column,
                      numeric: true,
                      className: 'indigenous-education-table__number',
                      format: formatCount,
                    })),
                  ]}
                  rows={visibleOfferRows}
                />
              </TableSection>
            </div>
          </div>
          <footer className="education-support-data__footer" aria-label="Fonte dos dados">
            <DataSourceNote source={INDIGENOUS_EDUCATION_SOURCE} />
          </footer>
        </section>
          </>
        )}
      </section>

      <DetailNavigation
        activeIndex={selectedIndex}
        isBottom
        itemLabel="Medida"
        itemPlural="medidas"
        nextLabel="Próxima medida"
        nextItem={nextUnit}
        onNext={setSelectedUnit}
        onPrevious={setSelectedUnit}
        previousItem={previousUnit}
        showBack={false}
        total={UNIT_ORDER.length}
      />
    </article>
  )
}

function CoverageView({ coverage }) {
  const seriesEntries = Object.entries(coverage?.series ?? {})
    .map(([year, item]) => ({ year: Number(year), ...item }))
    .sort((a, b) => a.year - b.year)
  const latest = seriesEntries.at(-1)
  const chartSeries = seriesEntries.map((item) => ({
    ano: item.year,
    valor: item.status === 'available' ? item.percentage : null,
  }))
  const population = coverage?.population ?? {}

  if (!coverage || !seriesEntries.length) {
    return (
      <ContentState kind="unavailable" className="state-box">
        <strong>Cobertura estimada indisponível</strong>
        <span>Dados insuficientes para calcular a estimativa.</span>
      </ContentState>
    )
  }

  const tableRows = seriesEntries.map((item) => ({
    ano: item.year,
    preSchool: item.enrollments?.preSchool,
    elementarySchool: item.enrollments?.elementarySchool,
    highSchool: item.enrollments?.highSchool,
    alignedTotal: item.enrollments?.alignedTotal,
    percentage: item.status === 'available' ? item.percentage : null,
    status: coverageStatusMessage(item),
  }))

  return (
    <>
      <section aria-labelledby="indigenous-coverage-title">
        <PanelHeading
          eyebrow="Relação matrículas/população"
          id="indigenous-coverage-title"
          title="Cobertura estimada da educação escolar indígena — 4 a 17 anos"
          description="Aproximação entre as matrículas de pré-escola, ensino fundamental e ensino médio e a população indígena de 4 a 17 anos recenseada em 2022."
        />
        <div className="metric-grid metric-grid--three education-metric-summary indigenous-education-panel__coverage-summary">
          <MetricCard
            detail={latest ? coverageStatusMessage(latest) : 'Dados insuficientes para calcular a estimativa.'}
            icon="measure"
            label={`Cobertura estimada · ${latest?.year ?? '—'}`}
            size="large"
            value={formatCoveragePercentage(latest?.percentage, latest?.status)}
          />
          <MetricCard
            detail="Pré-escola + ensino fundamental + ensino médio"
            icon="current"
            label={`Matrículas consideradas · ${latest?.year ?? '—'}`}
            value={formatCount(latest?.enrollments?.alignedTotal)}
          />
          <MetricCard
            detail="Denominador fixo do Censo Demográfico"
            icon="comparison"
            label="População indígena recenseada em 2022"
            value={formatCount(population.value)}
          />
        </div>
      </section>

      <div className="education-primary-analysis indigenous-education-panel__primary">
        <div className="indicator-chart-card educacao-main-chart-card indigenous-education-panel__chart">
          <div className="education-chart-heading">
            <div>
              <span>Cobertura estimada — 4 a 17 anos</span>
              <p>Matrículas de 2023 a 2025 · população fixa em 2022</p>
            </div>
          </div>
          <EducationLineChart
            color="var(--green-primary)"
            formatLabel={(value) => formatCoveragePercentage(value, 'available')}
            scaleType="count"
            series={chartSeries}
            showPointLabels
            title={null}
          />
        </div>
        <EducationQuickReading
          items={[
            {
              key: 'current',
              icon: 'measure',
              label: `Estimativa de ${latest?.year ?? '—'}`,
              text: latest ? coverageStatusMessage(latest) : 'Dados insuficientes para calcular a estimativa.',
            },
            {
              key: 'denominator',
              icon: 'period',
              label: 'Denominador fixo',
              text: `${formatCount(population.value)} pessoas indígenas de 4 a 17 anos recenseadas em 2022.`,
            },
            {
              key: 'scope',
              icon: 'cut',
              label: 'Como interpretar',
              text: 'É uma estimativa entre universos distintos, não uma taxa oficial de escolarização nem a identificação de pessoas atendidas.',
            },
          ]}
        />
      </div>

      <section className="educacao-explore education-support-data education-support-data--organized indigenous-education-panel__support" aria-labelledby="indigenous-coverage-data-title">
        <header className="education-support-data__header">
          <div className="education-support-data__summary">
            <span className="educacao-explore__eyebrow">Aprofundamento</span>
            <h3 id="indigenous-coverage-data-title">Dados de apoio do indicador</h3>
            <p>Memória de cálculo e limites metodológicos da cobertura estimada.</p>
          </div>
        </header>
        <div className="education-support-data__body">
          <div className="education-support-data__grid indigenous-education-panel__table-grid">
            <TableSection
              className="education-support-data__item--wide"
              description="Compare os totais oficiais das etapas, o numerador alinhado e o resultado de cada ano."
              eyebrow="Série anual"
              id="indigenous-coverage-table-title"
              title="Matrículas consideradas e cobertura estimada"
            >
              <EducationTable
                caption="Matrículas consideradas, população de referência e cobertura estimada"
                className="indigenous-education-table indigenous-education-table--coverage"
                columns={[
                  { key: 'ano', label: 'Ano', numeric: true, rowHeader: true },
                  { key: 'preSchool', label: 'Pré-escola', numeric: true, format: formatCount },
                  { key: 'elementarySchool', label: 'Ensino fundamental', numeric: true, format: formatCount },
                  { key: 'highSchool', label: 'Ensino médio', numeric: true, format: formatCount },
                  { key: 'alignedTotal', label: 'Total considerado', numeric: true, format: formatCount },
                  { key: 'percentage', label: 'Cobertura estimada', numeric: true, format: (value) => formatCoveragePercentage(value, value === null ? 'unavailable' : 'available') },
                  { key: 'status', label: 'Leitura', className: 'indigenous-education-table__reading' },
                ]}
                rows={tableRows}
              />
            </TableSection>
            <TableSection
              className="education-support-data__item--wide"
              description="Cuidados necessários para interpretar a relação entre as duas fontes."
              eyebrow="Metodologia"
              id="indigenous-coverage-methodology-title"
              title="Limites de interpretação"
            >
              <ul className="indigenous-education-panel__methodology-list">
                {(coverage.methodologicalNotes ?? []).map((note) => <li key={note}>{note}</li>)}
              </ul>
            </TableSection>
          </div>
        </div>
        <footer className="education-support-data__footer" aria-label="Fontes dos dados">
          <DataSourceNote source="IBGE — Censo Demográfico 2022, SIDRA 9970; INEP — Sinopse Estatística da Educação Básica, tabelas de Educação Escolar Indígena (2023–2025)." />
        </footer>
      </section>
    </>
  )
}

function PanelHeading({ description, eyebrow, id, title }) {
  return (
    <div className="indigenous-education-panel__heading">
      <span className="eyebrow">{eyebrow}</span>
      <h3 id={id}>{title}</h3>
      {description ? <p>{description}</p> : null}
    </div>
  )
}

function TableSection({ children, className = '', description, eyebrow, id, title }) {
  return (
    <section className={`education-support-data__item${className ? ` ${className}` : ''}`} aria-labelledby={id}>
      <header className="education-support-data__item-heading">
        <div>
          <span>{eyebrow}</span>
          <h4 id={id}>{title}</h4>
          <p>{description}</p>
        </div>
      </header>
      <div className="education-support-data__item-content">{children}</div>
    </section>
  )
}

function findValue(records, unitKey, cutKey, year) {
  return records.find((row) => (
    row.unidade === unitKey
    && row.recorte === cutKey
    && Number(row.ano) === Number(year)
  ))?.valor ?? null
}

function findLatestValue(records, unitKey, cutKey) {
  return records.find((row) => row.unidade === unitKey && row.recorte === cutKey)?.valor ?? null
}

function formatCount(value) {
  return value === null || value === undefined ? '—' : formatNumber(value)
}

function formatCoveragePercentage(value, status) {
  if (status !== 'available' || value === null || value === undefined) return '—'
  return `${Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`
}

function coverageStatusMessage(item) {
  if (!item) return 'Dados insuficientes para calcular a estimativa.'
  if (item.status === 'not_applicable') {
    return 'Não havia população indígena de 4 a 17 anos recenseada no município em 2022.'
  }
  if (item.status === 'denominator_zero_with_enrollments') {
    return 'O município possui matrículas registradas, mas não apresentou população indígena de 4 a 17 anos no Censo 2022. O indicador não pode ser calculado.'
  }
  if (item.status !== 'available') {
    return 'Dados insuficientes para calcular a estimativa.'
  }
  if (Number(item.enrollments?.alignedTotal) === 0) {
    return 'Não foram registradas matrículas nas etapas consideradas.'
  }
  if (Number(item.percentage) > 100) {
    return 'O resultado pode superar 100% porque as matrículas não representam necessariamente pessoas únicas e os universos territorial e temporal das fontes não são idênticos.'
  }
  return 'Estimativa calculada com os totais oficiais das três etapas consideradas.'
}

function isUnavailable(value) {
  return value === null || value === undefined
}

function valueStateMessage(value) {
  if (value === null || value === undefined) return 'Dado indisponível'
  if (Number(value) === 0) return 'Nenhuma ocorrência registrada no universo medido'
  return 'Ocorrência registrada no universo medido'
}
