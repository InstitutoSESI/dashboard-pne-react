import { PLATFORM_LABEL } from '../../../config/stateConfig'
import type {
  BreakdownValue,
  EnrollmentComparisonValue,
  MunicipalEducationOverviewV1,
  SnapshotPercentage,
  SnapshotValue,
  StageSnapshot,
} from '../municipalEducationOverviewTypes'
import {
  describeOverviewMatrixValue,
  formatOverviewEnrollments,
  formatOverviewPercentage,
  formatSchoolPerformanceRate,
  getMunicipalOverviewMethodologyHighlights,
} from '../municipalEducationOverviewPresentation'
import { hasRelevantNetworkComparison } from '../enrollmentComparisonPresentation'
import {
  formatMunicipalLearningChange,
  formatMunicipalLearningValue,
  type MunicipalLearningMetricSnapshot,
  type MunicipalLearningStageSnapshot,
} from '../municipalEducationLearningPresentation'

interface MunicipalEducationOverviewPrintReportProps {
  data: MunicipalEducationOverviewV1
  emissionDate: string
  learningStages: readonly MunicipalLearningStageSnapshot[]
}

interface PrintMatrixRow {
  label: string
  select: (stage: StageSnapshot) => BreakdownValue
  subtotal?: boolean
}

const NETWORK_ROWS: ReadonlyArray<PrintMatrixRow> = [
  { label: 'Rede pública', subtotal: true, select: (stage) => stage.byNetwork.publicSubtotal },
  { label: 'Municipal', select: (stage) => stage.byNetwork.municipal },
  { label: 'Estadual', select: (stage) => stage.byNetwork.state },
  { label: 'Federal', select: (stage) => stage.byNetwork.federal },
  { label: 'Privada', select: (stage) => stage.byNetwork.private },
]

const LOCATION_ROWS: ReadonlyArray<PrintMatrixRow> = [
  { label: 'Urbana', select: (stage) => stage.bySchoolLocation.urban },
  { label: 'Rural', select: (stage) => stage.bySchoolLocation.rural },
]

export function MunicipalEducationOverviewPrintReport({
  data,
  emissionDate,
  learningStages,
}: MunicipalEducationOverviewPrintReportProps) {
  const methodology = getMunicipalOverviewMethodologyHighlights(data)

  return (
    <article className="municipal-education-print-report">
      <header className="municipal-education-print-report__header">
        <p className="municipal-education-print-report__institution">{PLATFORM_LABEL} · Inteligência Municipal</p>
        <h1>Panorama educacional</h1>
        <p className="municipal-education-print-report__subtitle">Síntese das matrículas, da oferta educacional, do rendimento escolar e das mudanças observadas no município</p>
        <dl className="municipal-education-print-report__identity">
          <div><dt>Município</dt><dd>{data.municipality.name}</dd></div>
          <div><dt>Código IBGE</dt><dd>{data.municipality.idMunicipality}</dd></div>
          <div><dt>Ano de referência</dt><dd>{data.reference.year}</dd></div>
          <div><dt>Data de emissão</dt><dd>{emissionDate}</dd></div>
        </dl>
      </header>

      <PrintOverviewSummary data={data} />
      <PrintSpecialEducation data={data} />
      <PrintStageSection
        snapshot={data.earlyChildhood}
        stage="earlyChildhood"
        title="Educação Infantil — 2025"
      />
      <PrintStageSection
        snapshot={data.elementary}
        stage="elementary"
        title="Ensino Fundamental — 2025"
      />
      <PrintHighSchoolSection data={data} />
      <PrintSchoolPerformance data={data} />
      <PrintLearningOutcomes stages={learningStages} />
      <PrintEnrollmentComparison data={data} />

      <section className="municipal-education-print-report__sources" aria-labelledby="municipal-education-print-sources-title">
        <h2 id="municipal-education-print-sources-title">Fontes das informações</h2>
        {data.sources.length ? (
          <ul>
            <li>
              <strong>INEP</strong>
              <span>Sistema de Avaliação da Educação Básica (SAEB) e Índice de Desenvolvimento da Educação Básica (IDEB)</span>
            </li>
            {data.sources.map((source) => (
              <li key={source.id}>
                <strong>{source.organization}</strong>
                <span>{source.title} · {source.referenceYear}</span>
                {source.url ? <span className="municipal-education-print-report__source-url">{source.url}</span> : null}
              </li>
            ))}
          </ul>
        ) : null}
        {methodology.length ? (
          <div className="municipal-education-print-report__methodology">
            <h3>Como ler estes dados</h3>
            <ul>{methodology.map((note) => <li key={note}>{note}</li>)}</ul>
          </div>
        ) : null}
      </section>

      <footer className="municipal-education-print-report__footer">
        <span>INEP — Censo Escolar 2025</span>
        <span>{emissionDate}</span>
        <span>{data.municipality.name}</span>
      </footer>
    </article>
  )
}

function PrintOverviewSummary({ data }: { data: MunicipalEducationOverviewV1 }) {
  const components = data.basicEducationComposition.components
  const regularStages = [
    ['Educação Infantil', components.earlyChildhood.total, [['Creche', components.earlyChildhood.details.creche], ['Pré-escola', components.earlyChildhood.details.preSchool]]],
    ['Ensino Fundamental', components.elementary.total, [['Anos Iniciais', components.elementary.details.initialYears], ['Anos Finais', components.elementary.details.finalYears]]],
    ['Ensino Médio', components.highSchool.total, [['Técnico integrado', components.highSchool.details.integratedTechnical]]],
  ] as const
  const modalities = [
    ['Educação de Jovens e Adultos — EJA', components.youthAndAdultEducation.total, [['EJA — Ensino Fundamental', components.youthAndAdultEducation.details.elementary], ['EJA — Ensino Médio', components.youthAndAdultEducation.details.highSchool]]],
    ['Educação profissional — outras ofertas', components.otherProfessionalOffers.total, [['Curso técnico concomitante', components.otherProfessionalOffers.details.concomitantTechnical], ['Curso técnico subsequente', components.otherProfessionalOffers.details.subsequentTechnical], ['Outras ofertas profissionais', components.otherProfessionalOffers.details.otherOffers]]],
  ] as const
  return (
    <section className="municipal-education-print-summary" aria-labelledby="municipal-education-print-summary-title">
      <h2 id="municipal-education-print-summary-title">Composição das matrículas da Educação Básica — 2025</h2>
      <dl className="municipal-education-print-summary__primary">
        <dt>Educação Básica</dt>
        <dd>{formatOverviewEnrollments(data.basicEducationComposition.total)}</dd>
        <span>Total oficial do Censo Escolar</span>
      </dl>
      <PrintCompositionCategory label="Etapas regulares" groups={regularStages} />
      <PrintCompositionCategory label="Modalidades e outras ofertas" groups={modalities} />
      <div className="municipal-education-print-summary__notes">
        <p>As matrículas do técnico integrado já estão incluídas no total do Ensino Médio.</p>
        <p>As outras ofertas profissionais apresentadas não estão incluídas no Ensino Médio ou na EJA.</p>
        <p>Somente os cinco componentes principais participam da composição da Educação Básica; os detalhamentos não são somados novamente.</p>
      </div>
    </section>
  )
}

function PrintCompositionCategory({
  groups,
  label,
}: {
  groups: ReadonlyArray<readonly [string, SnapshotValue, ReadonlyArray<readonly [string, SnapshotValue]>]>
  label: string
}) {
  return (
    <section className="municipal-education-print-summary__category">
      <h3>{label}</h3>
      <div className={`municipal-education-print-summary__grid municipal-education-print-summary__grid--${groups.length}`}>
        {groups.map(([groupLabel, value, details]) => (
          <div className="municipal-education-print-summary__group" key={groupLabel}>
            <dl><dt>{groupLabel}</dt><dd>{formatOverviewEnrollments(value)}</dd></dl>
            <div className="municipal-education-print-summary__details">
              {details.map(([detailLabel, detailValue]) => <dl key={detailLabel}><dt>{detailLabel}</dt><dd>{formatOverviewEnrollments(detailValue)}</dd></dl>)}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function PrintSpecialEducation({ data }: { data: MunicipalEducationOverviewV1 }) {
  return <section className="municipal-education-print-special" aria-labelledby="municipal-education-print-special-title">
    <h2 id="municipal-education-print-special-title">Educação Especial — 2025</h2>
    <dl>
      <div><dt>Educação Especial</dt><dd>{formatOverviewEnrollments(data.specialEducation.total)}</dd></div>
      <div><dt>Classes comuns</dt><dd>{formatOverviewEnrollments(data.specialEducation.commonClasses)}</dd></div>
      <div><dt>Classes exclusivas</dt><dd>{formatOverviewEnrollments(data.specialEducation.exclusiveClasses)}</dd></div>
    </dl>
    <p>As matrículas da Educação Especial já estão incluídas nas etapas e modalidades apresentadas acima.</p>
  </section>
}

function PrintSchoolPerformance({ data }: { data: MunicipalEducationOverviewV1 }) {
  const rows = [
    ['Ensino Fundamental', data.schoolPerformance.stages.elementary],
    ['Anos Iniciais', data.schoolPerformance.stages.initialYears],
    ['Anos Finais', data.schoolPerformance.stages.finalYears],
    ['Ensino Médio', data.schoolPerformance.stages.highSchool],
  ] as const
  return <section className="municipal-education-print-performance" aria-labelledby="municipal-education-print-performance-title">
    <h2 id="municipal-education-print-performance-title">Rendimento escolar — 2025</h2>
    <table>
      <thead><tr><th scope="col">Etapa</th><th scope="col">Aprovação</th><th scope="col">Reprovação</th><th scope="col">Abandono</th></tr></thead>
      <tbody>{rows.map(([label, stage]) => <tr key={label}><th scope="row">{label}</th><td>{formatSchoolPerformanceRate(stage.approval)}</td><td>{formatSchoolPerformanceRate(stage.failure)}</td><td>{formatSchoolPerformanceRate(stage.dropout)}</td></tr>)}</tbody>
    </table>
    <p>As taxas correspondem ao resultado escolar informado pelo INEP para o conjunto das redes do município. Aprovação, reprovação e abandono totalizam 100%.</p>
  </section>
}

function PrintLearningOutcomes({
  stages,
}: {
  stages: readonly MunicipalLearningStageSnapshot[]
}) {
  return (
    <section className="municipal-education-print-learning" aria-labelledby="municipal-education-print-learning-title">
      <h2 id="municipal-education-print-learning-title">IDEB e notas do SAEB</h2>
      <p>Resultados mais recentes por etapa. A variação mostra a diferença, em pontos, para a edição anterior disponível.</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Etapa</th>
            <th scope="col">IDEB</th>
            <th scope="col">SAEB Língua Portuguesa</th>
            <th scope="col">SAEB Matemática</th>
          </tr>
        </thead>
        <tbody>
          {stages.map((stage) => (
            <tr key={stage.key}>
              <th scope="row">{stage.label}</th>
              <PrintLearningMetric metric={stage.metrics.ideb} />
              <PrintLearningMetric metric={stage.metrics.saebLp} />
              <PrintLearningMetric metric={stage.metrics.saebMt} />
            </tr>
          ))}
        </tbody>
      </table>
      <p>Fonte: INEP — SAEB/IDEB. O ano pode variar quando não houver resultado municipal publicável para uma etapa.</p>
    </section>
  )
}

function PrintLearningMetric({ metric }: { metric: MunicipalLearningMetricSnapshot }) {
  const period = metric.previousYear && metric.currentYear
    ? `${metric.previousYear}–${metric.currentYear}`
    : null
  return (
    <td>
      <strong>{formatMunicipalLearningValue(metric)}</strong>
      {metric.currentYear ? <span>{metric.currentYear}</span> : null}
      <small>{formatMunicipalLearningChange(metric)}{period ? ` · ${period}` : ''}</small>
    </td>
  )
}

const PRINT_COMPARISON_STAGES = [
  ['basicEducation', 'Educação Básica'],
  ['earlyChildhood', 'Educação Infantil'],
  ['creche', 'Creche'],
  ['preSchool', 'Pré-escola'],
  ['elementary', 'Ensino Fundamental'],
  ['initialYears', 'Anos Iniciais'],
  ['finalYears', 'Anos Finais'],
  ['highSchool', 'Ensino Médio'],
  ['youthAndAdultEducation', 'Educação de Jovens e Adultos — EJA'],
] as const

function PrintEnrollmentComparison({ data }: { data: MunicipalEducationOverviewV1 }) {
  const stages = data.enrollmentComparison.stages
  const breakdown = PRINT_COMPARISON_STAGES.filter(([key]) => key !== 'basicEducation')
  return <section className="municipal-education-print-comparison">
    <h2>Comparação das matrículas — 2015 e 2025</h2>
    <p>Os valores mostram as matrículas registradas em 2015 e 2025. A variação corresponde à mudança percentual entre os dois anos.</p>
    <PrintComparisonTable title="Matrículas por etapa e modalidade" rows={PRINT_COMPARISON_STAGES.map(([key, label]) => [label, stages[key].total])} />
    <h3>Dependência administrativa por etapa</h3>
    <p>Rede pública corresponde à soma das matrículas municipal, estadual e federal. Redes sem matrículas registradas em 2015 e 2025 não são exibidas.</p>
    {breakdown.map(([key, label]) => {
      const rows = [
        ['Rede pública', stages[key].byNetwork!.publicSubtotal],
        ['Municipal', stages[key].byNetwork!.municipal],
        ['Estadual', stages[key].byNetwork!.state],
        ['Federal', stages[key].byNetwork!.federal],
        ['Privada', stages[key].byNetwork!.private],
      ] as Array<readonly [string, EnrollmentComparisonValue]>
      const visibleRows = rows.filter(([, value]) => hasRelevantNetworkComparison(value))
      return visibleRows.length
        ? <PrintComparisonTable key={`network-${key}`} title={label} rows={visibleRows} />
        : null
    })}
    <h3>Localização da escola por etapa</h3>
    {breakdown.map(([key, label]) => <PrintComparisonTable key={`location-${key}`} title={label} rows={[
      ['Urbana', stages[key].bySchoolLocation!.urban],
      ['Rural', stages[key].bySchoolLocation!.rural],
    ]} />)}
    <p>{data.enrollmentComparison.methodologyNote}</p>
  </section>
}

function PrintComparisonTable({ rows, title }: {
  rows: Array<readonly [string, EnrollmentComparisonValue]>
  title: string
}) {
  return <section className="municipal-education-print-comparison__table">
    <h4>{title}</h4>
    <table>
      <thead><tr><th scope="col">Etapa ou recorte</th><th scope="col">2015</th><th scope="col">2025</th><th scope="col">Variação 2015–2025</th></tr></thead>
      <tbody>{rows.map(([label, value]) => <tr key={label}><th scope="row">{label}</th><td>{formatOverviewEnrollments(value.value2015)}</td><td>{formatOverviewEnrollments(value.value2025)}</td><td>{formatPrintComparisonPercentage(value)}</td></tr>)}</tbody>
    </table>
  </section>
}

function formatPrintComparisonPercentage(value: EnrollmentComparisonValue): string {
  const percentage = value.percentageChange
  if (percentage.state !== 'observed' || percentage.value === null) return '—'
  if (percentage.value === 0) return '0,0%'
  const formatted = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Math.abs(percentage.value))
  return `${percentage.value > 0 ? '+' : '−'}${formatted}%`
}

function PrintStageSection({
  snapshot,
  stage,
  title,
}: {
  snapshot: MunicipalEducationOverviewV1['earlyChildhood'] | MunicipalEducationOverviewV1['elementary']
  stage: 'earlyChildhood' | 'elementary'
  title: string
}) {
  const isEarlyChildhood = stage === 'earlyChildhood'
  const total = snapshot.total
  const first = isEarlyChildhood
    ? (snapshot as MunicipalEducationOverviewV1['earlyChildhood']).creche
    : (snapshot as MunicipalEducationOverviewV1['elementary']).initialYears
  const second = isEarlyChildhood
    ? (snapshot as MunicipalEducationOverviewV1['earlyChildhood']).preSchool
    : (snapshot as MunicipalEducationOverviewV1['elementary']).finalYears
  const totalLabel = isEarlyChildhood ? 'Educação Infantil' : 'Ensino Fundamental'
  const firstLabel = isEarlyChildhood ? 'Creche' : 'Anos Iniciais'
  const secondLabel = isEarlyChildhood ? 'Pré-escola' : 'Anos Finais'
  const sectionId = `municipal-education-print-${stage}-title`
  const stages = [
    { label: totalLabel, value: total },
    { label: firstLabel, value: first },
    { label: secondLabel, value: second },
  ]

  return (
    <section className={`municipal-education-print-stage municipal-education-print-stage--${stage}`} aria-labelledby={sectionId}>
      <h2 id={sectionId}>{title}</h2>
      <dl className="municipal-education-print-stage__summary">
        <PrintMetric
          label={totalLabel}
          share={total.shareOfBasicEducation}
          shareLabel={`${totalLabel} em relação à Educação Básica`}
          value={total.total}
        />
        <PrintMetric
          label={firstLabel}
          share={first.shareOfParentStage}
          shareLabel={`${firstLabel} em relação ${isEarlyChildhood ? 'à Educação Infantil' : 'ao Ensino Fundamental'}`}
          value={first.total}
        />
        <PrintMetric
          label={secondLabel}
          share={second.shareOfParentStage}
          shareLabel={`${secondLabel} em relação ${isEarlyChildhood ? 'à Educação Infantil' : 'ao Ensino Fundamental'}`}
          value={second.total}
        />
      </dl>
      <PrintMatrix rows={NETWORK_ROWS} stages={stages} title="Dependência administrativa" />
      <PrintMatrix rows={LOCATION_ROWS} stages={stages} title="Localização da escola" />
    </section>
  )
}

function PrintHighSchoolSection({ data }: { data: MunicipalEducationOverviewV1 }) {
  const stages = [{ label: 'Ensino Médio', value: data.highSchool.total }]
  return (
    <section className="municipal-education-print-stage municipal-education-print-stage--highSchool" aria-labelledby="municipal-education-print-high-school-title">
      <h2 id="municipal-education-print-high-school-title">Ensino Médio — 2025</h2>
      <dl className="municipal-education-print-stage__summary municipal-education-print-stage__summary--two-columns">
        <PrintMetric label="Ensino Médio" share={data.highSchool.total.shareOfBasicEducation} shareLabel="Ensino Médio em relação à Educação Básica" value={data.highSchool.total.total} />
        <PrintMetric label="Técnico integrado" share={data.highSchool.integratedTechnical.shareOfHighSchool} shareLabel="Técnico integrado em relação ao Ensino Médio" value={data.highSchool.integratedTechnical.total} />
      </dl>
      <p className="municipal-education-print-stage__note">As matrículas do técnico integrado já estão incluídas no total do Ensino Médio.</p>
      <PrintMatrix rows={NETWORK_ROWS} splitSingleStage stages={stages} title="Dependência administrativa" />
      <PrintMatrix columnsLabel="Localização da escola" rows={LOCATION_ROWS} splitSingleStage stages={stages} title="Localização da escola" />
    </section>
  )
}

function PrintMetric({
  label,
  share,
  shareLabel,
  value,
}: {
  label: string
  share?: SnapshotPercentage
  shareLabel: string
  value: SnapshotValue
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{formatOverviewEnrollments(value)}</dd>
      <p><strong>{formatOverviewPercentage(share)}</strong> {shareLabel}</p>
    </div>
  )
}

function PrintMatrix({
  columnsLabel = 'Recorte',
  rows,
  splitSingleStage = false,
  stages,
  title,
}: {
  columnsLabel?: string
  rows: ReadonlyArray<PrintMatrixRow>
  splitSingleStage?: boolean
  stages: ReadonlyArray<{ label: string; value: StageSnapshot }>
  title: string
}) {
  const splitStage = splitSingleStage ? stages[0] : undefined
  return (
    <section className={`municipal-education-print-matrix${splitStage ? ' municipal-education-print-matrix--split' : ''}`}>
      <h3>{title}</h3>
      <table>
        <caption>{title}: número de matrículas e participação em cada etapa</caption>
        <thead>
          <tr>
            <th scope="col">{columnsLabel}</th>
            {splitStage ? <><th scope="col">Matrículas</th><th scope="col">Participação</th></> : stages.map((stage) => <th scope="col" key={stage.label}>{stage.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className={row.subtotal ? 'municipal-education-print-matrix__subtotal' : undefined} key={row.label}>
              <th scope="row">{row.label}</th>
              {splitStage ? (() => {
                const value = row.select(splitStage.value)
                return <><td>{formatOverviewEnrollments(value.enrollments)}</td><td className="municipal-education-print-matrix__percentage">{formatOverviewPercentage(value.share)}</td></>
              })() : stages.map((stage) => {
                const value = row.select(stage.value)
                return (
                  <td aria-label={`${stage.label}: ${describeOverviewMatrixValue(value)}`} key={stage.label}>
                    {formatPrintMatrixValue(value)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function formatPrintMatrixValue(value: BreakdownValue): string {
  const enrollments = formatOverviewEnrollments(value.enrollments)
  return enrollments === '—' ? '—' : `${enrollments} · ${formatOverviewPercentage(value.share)}`
}
